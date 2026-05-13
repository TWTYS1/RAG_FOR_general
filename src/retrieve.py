"""检索模块: Query 向量化 → ChromaDB 语义搜索"""

from .embedder import Embedder
from .chroma_store import ChromaStore
from .config import TOP_K


class Retriever:
    def __init__(self):
        self.embedder = Embedder()
        self.store = ChromaStore()

    def search(self, query: str, top_k: int = TOP_K, file_type: str | None = None) -> list[dict]:
        if self.store.count() == 0:
            return []
        query_vec = self.embedder.embed_single(query)
        return self.store.search(query_vec, top_k=top_k, file_type=file_type)

    def format_context(self, hits: list[dict]) -> str:
        """将检索结果格式化为 Prompt 用的 Context"""
        parts = []
        for i, hit in enumerate(hits, start=1):
            meta = hit.get("metadata", {})
            source = meta.get("source", "未知来源")
            file_type = meta.get("file_type", "")
            page = meta.get("page", "")
            heading = meta.get("heading", "")

            label_parts = [source, f"[{file_type.upper()}]"]
            if page:
                label_parts.append(f"第{page}页")
            if heading:
                label_parts.append(heading)
            label = " · ".join(label_parts)

            parts.append(f"[{i}] 来源: {label}\n{hit['text']}")
        return "\n\n".join(parts)
