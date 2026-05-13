"""文档预处理入口: 遍历 -> 解析 -> 分块 -> 向量化 -> 存储（含 BM25）"""

import uuid
from pathlib import Path
from .config import DOCS_DIR, SUPPORTED_EXTENSIONS
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

    def run(self, clear: bool = False) -> int:
        if clear:
            self.store.clear()

        # 维度兼容检测：换了 Embedding 模型必须清库重建
        stored_dim = self.store.peek_dimension()
        current_dim = self.embedder.dimension
        if stored_dim is not None and stored_dim != current_dim:
            print(
                f"\n[!] 维度不匹配！当前模型={current_dim}维，ChromaDB 里是={stored_dim}维\n"
                f"    请用 --clear 重新索引，否则 ChromaDB 会报错。\n"
            )
            return 0

        files = self._collect_files()
        if not files:
            print(f"[WARN] No supported files found under {self.docs_dir}")
            return 0

        total_chunks = 0
        for file_path in files:
            try:
                parsed = self.router.parse(file_path)
            except Exception as e:
                print(f"[SKIP] Parse failed [{file_path.name}]: {e}")
                continue

            chunks = self.chunker.chunk(parsed)
            if not chunks:
                continue

            ids = [str(uuid.uuid4()) for _ in chunks]
            texts = [chunk.text for chunk in chunks]
            metadatas = [dict(chunk.metadata) for chunk in chunks]
            embeddings = self.embedder.embed(texts)

            self.store.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
            total_chunks += len(chunks)
            rel = file_path.relative_to(self.docs_dir)
            print(f"  [OK] {rel} -> {len(chunks)} chunks")

        print(f"\n[DONE] Indexed: {len(files)} files -> {total_chunks} chunks")
        return total_chunks

    def _collect_files(self) -> list[Path]:
        if not self.docs_dir.exists():
            self.docs_dir.mkdir(parents=True, exist_ok=True)
            return []
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(self.docs_dir.rglob(f"*{ext}"))
        return sorted(files)
