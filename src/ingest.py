"""文档预处理入口: 遍历 -> 解析 -> 分块 -> 向量化 -> 存储（含 BM25）"""

import json
import uuid
import time
from pathlib import Path
from .config import DOCS_DIR, SUPPORTED_EXTENSIONS, CHROMA_PERSIST_DIR
from .parsers.router import FileTypeRouter
from .chunker import SemanticChunker
from .embedder import Embedder
from .chroma_store import ChromaStore
from .bm25_index import get_shared_bm25


class IngestPipeline:
    def __init__(self, docs_dir: str | None = None, use_bm25: bool = True):
        self.docs_dir = Path(docs_dir or DOCS_DIR).resolve()
        self.router = FileTypeRouter()
        self.chunker = SemanticChunker()
        self.embedder = Embedder()
        self.store = ChromaStore(bm25_index=get_shared_bm25() if use_bm25 else None)
        self._manifest_path = Path(CHROMA_PERSIST_DIR).resolve() / "manifest.json"

    # ── Manifest 管理 ─────────────────────────────

    def _load_manifest(self) -> dict[str, float]:
        if not self._manifest_path.exists():
            return {}
        try:
            return json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_manifest(self, manifest: dict[str, float]):
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── 主流程 ────────────────────────────────────

    def run(self, clear: bool = False, incremental: bool = False) -> int:
        if clear:
            self.store.clear()
            self._save_manifest({})
            incremental = False  # clear 后不需要增量逻辑

        # 维度兼容检测
        stored_dim = self.store.peek_dimension()
        current_dim = self.embedder.dimension
        if stored_dim is not None and stored_dim != current_dim:
            print(
                f"\n[!] 维度不匹配！当前模型={current_dim}维，ChromaDB 里是={stored_dim}维\n"
                f"    请用 --clear 重新索引，否则 ChromaDB 会报错。\n"
            )
            return 0

        current_files = self._scan_files()
        if not current_files:
            print(f"[WARN] No supported files found under {self.docs_dir}")
            return 0

        if incremental and self.store.count() > 0:
            return self._run_incremental(current_files)

        return self._run_full(current_files)

    def _run_full(self, files: list[Path]) -> int:
        """全量索引（首次或无增量信息时）"""
        manifest: dict[str, float] = {}
        total_chunks = 0
        for file_path in files:
            chunks = self._process_file(file_path)
            if chunks is not None:
                total_chunks += chunks
            rel = str(file_path.relative_to(self.docs_dir))
            manifest[rel] = file_path.stat().st_mtime

        self._save_manifest(manifest)
        print(f"\n[DONE] Full index: {len(files)} files -> {total_chunks} chunks")
        return total_chunks

    def _run_incremental(self, files: list[Path]) -> int:
        """增量索引：只处理新增/修改/删除的文件"""
        old_manifest = self._load_manifest()
        new_manifest: dict[str, float] = {}
        added, changed, deleted = 0, 0, 0
        total_chunks = 0

        # 索引当前文件
        for file_path in files:
            rel = str(file_path.relative_to(self.docs_dir))
            mtime = file_path.stat().st_mtime
            new_manifest[rel] = mtime

            if rel not in old_manifest:
                # 新文件
                chunks = self._process_file(file_path)
                if chunks is not None:
                    total_chunks += chunks
                    added += 1
                    print(f"  [+] {rel} -> {chunks} chunks")
            elif abs(old_manifest[rel] - mtime) > 1:
                # 文件已修改，删旧入新
                self.store.remove_by_source(str(file_path))
                chunks = self._process_file(file_path)
                if chunks is not None:
                    total_chunks += chunks
                    changed += 1
                    print(f"  [~] {rel} -> {chunks} chunks (updated)")
            else:
                # 未变，跳过
                pass

        # 删除已不存在的文件
        for old_rel in old_manifest:
            if old_rel not in new_manifest:
                old_path = self.docs_dir / old_rel
                self.store.remove_by_source(str(old_path))
                deleted += 1
                print(f"  [-] {old_rel} (removed)")

        # 重建 BM25
        self.store.rebuild_bm25()

        self._save_manifest(new_manifest)
        summary = f"added={added} changed={changed} deleted={deleted}"
        print(f"\n[DONE] Incremental: {summary} -> {self.store.count()} chunks")
        return total_chunks

    def _process_file(self, file_path: Path) -> int | None:
        """解析 + 分块 + 向量化 + 入库一个文件，返回 chunk 数"""
        try:
            parsed = self.router.parse(file_path)
        except Exception as e:
            print(f"[SKIP] Parse failed [{file_path.name}]: {e}")
            return None

        chunks = self.chunker.chunk(parsed)
        if not chunks:
            return None

        ids = [str(uuid.uuid4()) for _ in chunks]
        texts = [chunk.text for chunk in chunks]
        metadatas = [dict(chunk.metadata) for chunk in chunks]
        embeddings = self.embedder.embed(texts)

        self.store.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        rel = file_path.relative_to(self.docs_dir)
        print(f"  [{rel}] -> {len(chunks)} chunks")
        return len(chunks)

    def _scan_files(self) -> list[Path]:
        """扫描 docs_dir 下所有支持的文件（递归）"""
        if not self.docs_dir.exists():
            self.docs_dir.mkdir(parents=True, exist_ok=True)
            return []
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(self.docs_dir.rglob(f"*{ext}"))
        return sorted(files)
