"""ChromaDB 存储层: 向量写入、查询、metadata 过滤"""

import chromadb
from chromadb.config import Settings
from pathlib import Path
from .config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION
from .parsers.base import Document


class ChromaStore:
    def __init__(self, persist_dir: str | None = None, collection_name: str | None = None):
        persist_dir = persist_dir or CHROMA_PERSIST_DIR
        collection_name = collection_name or CHROMA_COLLECTION
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._name = collection_name
        self._collection = self._client.get_or_create_collection(name=collection_name)

    def _safe_collection(self):
        """确保 collection 可用（修复删除 chroma_data 后残留引用）"""
        try:
            self._collection.count()
            return self._collection
        except Exception:
            try:
                self._client.delete_collection(self._name)
            except Exception:
                pass
            self._collection = self._client.get_or_create_collection(name=self._name)
            return self._collection

    def add(self, ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]):
        if not ids:
            return
        self._safe_collection().add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def search(self, query_embedding: list[float], top_k: int = 8, file_type: str | None = None) -> list[dict]:
        where = None
        if file_type:
            where = {"file_type": file_type}
        results = self._safe_collection().query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                hits.append({
                    "id": doc_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })
        return hits

    def count(self) -> int:
        return self._safe_collection().count()

    def peek_dimension(self) -> int | None:
        """查看已存储 Embedding 的维度，集合为空返回 None"""
        if self._safe_collection().count() == 0:
            return None
        sample = self._safe_collection().get(limit=1, include=["embeddings"])
        if sample and sample.get("embeddings") and len(sample["embeddings"]) > 0:
            return len(sample["embeddings"][0])
        return None

    def clear(self):
        """清空集合（重新索引时用）"""
        col = self._safe_collection()
        self._client.delete_collection(col.name)
        self._collection = self._client.get_or_create_collection(name=self._name)
