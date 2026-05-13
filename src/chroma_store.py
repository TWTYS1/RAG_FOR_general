"""ChromaDB 存储层: 向量写入、查询、metadata 过滤 + Hybrid Search (RRF)"""

import chromadb
from chromadb.config import Settings
from pathlib import Path
from .config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION, HYBRID_TOP_K
from .parsers.base import Document


class ChromaStore:
    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str | None = None,
        bm25_index=None,
    ):
        persist_dir = persist_dir or CHROMA_PERSIST_DIR
        collection_name = collection_name or CHROMA_COLLECTION
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._name = collection_name
        self._collection = self._client.get_or_create_collection(name=collection_name)
        self._bm25 = bm25_index  # 外部注入 BM25Index 实例

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
        # 同步 BM25 索引
        if self._bm25 is not None:
            self._bm25.add(ids, documents, metadatas)

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

    # ── Hybrid Search ─────────────────────────────────

    def search_hybrid(
        self,
        query_embedding: list[float],
        bm25_queries: list[str] | None = None,
        exact_terms: list[str] | None = None,
        boost_terms: list[str] | None = None,
        top_k: int = HYBRID_TOP_K,
        metadata_filter: dict | None = None,
    ) -> list[dict]:
        """Dense + BM25 混合检索，RRF 融合

        Args:
            query_embedding: Dense 向量
            bm25_queries: BM25 检索用的文本（多个 variant）
            exact_terms: TDoc/CR/Spec 精确匹配加权
            boost_terms: remaining issue 等关键词加权
            top_k: 初召回数（默认 50）
            metadata_filter: ChromaDB where 条件
        """
        # 1. Dense Search
        dense_results = self.search(query_embedding, top_k=top_k)
        dense_ranks: dict[str, tuple[int, float, dict]] = {}
        for rank, hit in enumerate(dense_results):
            cid = hit["id"]
            dense_ranks[cid] = (rank + 1, 1.0 / (1.0 + hit.get("distance", 0)), hit)

        # 2. BM25 Search（多 query 合并）
        bm25_ranks: dict[int, tuple[int, float, dict]] = {}
        bm25_seen: set[str] = set()
        if self._bm25 is not None and bm25_queries:
            for bq in bm25_queries:
                if not bq.strip():
                    continue
                bm25_hits = self._bm25.search(
                    bq, top_k=top_k, exact_terms=exact_terms, boost_terms=boost_terms,
                )
                for rank, (corpus_idx, score, meta) in enumerate(bm25_hits):
                    cid = self._bm25._ids[corpus_idx] if corpus_idx < len(self._bm25._ids) else ""
                    if cid in bm25_seen:
                        continue
                    bm25_seen.add(cid)
                    bm25_ranks[corpus_idx] = (rank + 1, score, meta)

        # 3. RRF 融合
        rrf_k = 60
        candidate_scores: dict[str, float] = {}
        candidate_data: dict[str, dict] = {}
        candidate_reasons: dict[str, list[str]] = {}

        for cid, (rank, dense_score, hit) in dense_ranks.items():
            rrf = 1.0 / (rrf_k + rank)
            candidate_scores[cid] = candidate_scores.get(cid, 0) + rrf
            candidate_data[cid] = hit
            candidate_reasons.setdefault(cid, []).append("dense")

        for corpus_idx, (rank, bm25_score, meta) in bm25_ranks.items():
            cid = self._bm25._ids[corpus_idx] if corpus_idx < len(self._bm25._ids) else ""
            if cid:
                rrf = 1.0 / (rrf_k + rank)
                candidate_scores[cid] = candidate_scores.get(cid, 0) + rrf * 1.2
                if cid not in candidate_data:
                    candidate_data[cid] = {
                        "id": cid,
                        "text": self._bm25._corpus[corpus_idx] if corpus_idx < len(self._bm25._corpus) else "",
                        "metadata": meta,
                        "distance": None,
                    }
                candidate_reasons.setdefault(cid, []).append("bm25")

        # 4. Metadata filter
        if metadata_filter:
            filtered_scores: dict[str, float] = {}
            for cid, score in candidate_scores.items():
                meta = candidate_data.get(cid, {}).get("metadata", {})
                match = True
                for k, v in metadata_filter.items():
                    meta_val = meta.get(k, "")
                    if isinstance(meta_val, list):
                        if v not in meta_val and str(v) not in str(meta_val):
                            match = False
                            break
                    elif str(v).lower() not in str(meta_val).lower():
                        match = False
                        break
                if match:
                    filtered_scores[cid] = score
            candidate_scores = filtered_scores

        # 5. 排序输出
        sorted_ids = sorted(candidate_scores, key=candidate_scores.get, reverse=True)[:top_k]
        hits = []
        for cid in sorted_ids:
            data = dict(candidate_data.get(cid, {}))
            data["rrf_score"] = round(candidate_scores[cid], 6)
            data["match_reasons"] = candidate_reasons.get(cid, [])
            hits.append(data)
        return hits

    # ── 基础操作 ─────────────────────────────────────

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
        if self._bm25 is not None:
            self._bm25.clear()
