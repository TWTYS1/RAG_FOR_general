"""文档预处理入口: 审计 / 遍历 / 解析 / 分块 / 向量化 / 存储（含 BM25）"""

import json
import sys
import uuid
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

    # ── Manifest ──────────────────────────────────

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
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 主入口 ────────────────────────────────────

    def run(
        self,
        clear: bool = False,
        incremental: bool = False,
        audit_only: bool = False,
        dry_run: bool = False,
        resume: bool = False,
        limit: int = 0,
        force_reindex: str | None = None,
    ) -> int:
        if audit_only:
            from .auditor import IngestAuditor
            auditor = IngestAuditor(str(self.docs_dir))
            report = auditor.run()
            auditor.save_report(report)
            auditor.print_summary(report)
            return report["summary"]["processed"]

        if force_reindex:
            return self._force_one(force_reindex)

        if clear:
            self.store.clear()

        stored_dim = self.store.peek_dimension()
        current_dim = self.embedder.dimension
        if stored_dim is not None and stored_dim != current_dim:
            print(f"\n[!] 维度不匹配！当前={current_dim}维, 库={stored_dim}维")
            return 0

        files = self._scan_files()
        if not files:
            print(f"[WARN] No supported files under {self.docs_dir}")
            return 0

        if limit > 0:
            files = files[:limit]

        if dry_run:
            return self._dry_run(files, resume=resume or incremental)

        if resume or incremental:
            return self._run_smart(files)

        return self._run_full(files)

    # ── 智能索引 (resume / incremental 统一入口) ──

    def _run_smart(self, files: list[Path]) -> int:
        """智能索引: mtime 匹配 + ChromaDB 有 chunks → 跳过"""
        manifest = self._load_manifest()
        new_manifest: dict[str, float] = {}
        added, changed, deleted, skipped = 0, 0, 0, 0
        total_chunks = 0

        for file_path in files:
            rel = str(file_path.relative_to(self.docs_dir))
            mtime = file_path.stat().st_mtime
            new_manifest[rel] = mtime
            abs_path = str(file_path)

            if rel in manifest and abs(manifest[rel] - mtime) <= 1:
                # mtime 匹配 → 检查 ChromaDB 是否真有数据
                existing = self.store.count_by_source(abs_path)
                if existing > 0:
                    skipped += 1
                    continue
                # 无 chunks → 重新处理
                self.store.remove_by_source(abs_path)
                chunks = self._process_file(file_path)
                if chunks is not None:
                    total_chunks += chunks
                    changed += 1
                    print(f"  [~] {rel} -> {chunks} chunks (recovered)")
            elif rel not in manifest:
                chunks = self._process_file(file_path)
                if chunks is not None:
                    total_chunks += chunks
                    added += 1
                    print(f"  [+] {rel} -> {chunks} chunks")
            else:
                # mtime 不一致，文件已修改
                self.store.remove_by_source(abs_path)
                chunks = self._process_file(file_path)
                if chunks is not None:
                    total_chunks += chunks
                    changed += 1
                    print(f"  [~] {rel} -> {chunks} chunks (modified)")

        # 清理已删除的文件
        for old_rel in manifest:
            if old_rel not in new_manifest:
                old_abs = str(self.docs_dir / old_rel)
                self.store.remove_by_source(old_abs)
                deleted += 1
                print(f"  [-] {old_rel} (removed)")

        self.store.rebuild_bm25()
        self._save_manifest(new_manifest)

        print(f"\n[DONE] added={added} changed={changed} skipped={skipped} deleted={deleted} → {self.store.count()} chunks")
        return total_chunks

    # ── 全量索引 (首次，支持断点续传) ─────────────

    def _run_full(self, files: list[Path]) -> int:
        manifest = self._load_manifest()
        total_chunks = 0
        for file_path in files:
            rel = str(file_path.relative_to(self.docs_dir))
            mtime = file_path.stat().st_mtime
            if rel in manifest and abs(manifest[rel] - mtime) <= 1:
                abs_path = str(file_path)
                if self.store.count_by_source(abs_path) > 0:
                    continue  # 断点续跑

            chunks = self._process_file(file_path)
            if chunks is not None:
                total_chunks += chunks
            manifest[rel] = mtime
            self._save_manifest(manifest)

        print(f"\n[DONE] Full: {len(files)} files → {total_chunks} chunks")
        return total_chunks

    # ── Dry-run ───────────────────────────────────

    def _dry_run(self, files: list[Path], resume: bool = False) -> int:
        manifest = self._load_manifest()
        would_process, would_skip = 0, 0
        for file_path in files:
            rel = str(file_path.relative_to(self.docs_dir))
            mtime = file_path.stat().st_mtime
            abs_path = str(file_path)

            if resume and rel in manifest and abs(manifest[rel] - mtime) <= 1:
                existing = self.store.count_by_source(abs_path)
                if existing > 0:
                    would_skip += 1
                    continue
            would_process += 1

        print(f"[DRY-RUN] {len(files)} files: would process {would_process}, skip {would_skip}")
        return 0

    # ── 单文件强制重索引 ──────────────────────────

    def _force_one(self, target: str) -> int:
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = self.docs_dir / target
        if not target_path.exists():
            print(f"[ERROR] File not found: {target_path}")
            return 0

        abs_path = str(target_path.resolve())
        self.store.remove_by_source(abs_path)
        chunks = self._process_file(target_path.resolve())
        if chunks is None:
            return 0

        # 更新 manifest
        manifest = self._load_manifest()
        rel = str(target_path.resolve().relative_to(self.docs_dir))
        manifest[rel] = target_path.stat().st_mtime
        self._save_manifest(manifest)

        print(f"[OK] Force reindexed: {rel} -> {chunks} chunks")
        return chunks

    # ── 文件处理 ──────────────────────────────────

    def _process_file(self, file_path: Path) -> int | None:
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
        if not self.docs_dir.exists():
            self.docs_dir.mkdir(parents=True, exist_ok=True)
            return []
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(self.docs_dir.rglob(f"*{ext}"))
        return sorted(files)
