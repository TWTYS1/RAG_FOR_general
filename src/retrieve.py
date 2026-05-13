"""检索模块: Query 向量化 → Hybrid Search (Dense + BM25 RRF) → Rerank"""

from .embedder import Embedder
from .chroma_store import ChromaStore
from .bm25_index import get_shared_bm25
from .query_processor import QueryProcessor
from .reranker import Reranker
from .config import TOP_K, HYBRID_TOP_K, RERANK_TOP_K, RERANK_ENABLED, RERANK_MODEL


class Retriever:
    def __init__(
        self,
        store: ChromaStore | None = None,
        use_hybrid: bool = True,
        use_rerank: bool = RERANK_ENABLED,
    ):
        self.embedder = Embedder()
        self.store = store or ChromaStore()
        self.query_processor = QueryProcessor()
        self._use_hybrid = use_hybrid
        self._use_rerank = use_rerank
        self._reranker: Reranker | None = None

        if use_hybrid and self.store._bm25 is None:
            self.store._bm25 = get_shared_bm25()

    def search(
        self,
        query: str,
        top_k: int = TOP_K,
        file_type: str | None = None,
        use_hybrid: bool | None = None,
        metadata_filter: dict | None = None,
    ) -> list[dict]:
        """检索入口: hybrid/pure dense → rerank"""
        if self.store.count() == 0:
            return []

        hybrid = use_hybrid if use_hybrid is not None else self._use_hybrid

        if hybrid:
            hits = self._search_hybrid(
                query, top_k=top_k, file_type=file_type,
                metadata_filter=metadata_filter,
            )
        else:
            query_vec = self.embedder.embed_single(query)
            hits = self.store.search(query_vec, top_k=max(top_k, HYBRID_TOP_K),
                                     file_type=file_type)

        # Rerank
        if self._use_rerank and len(hits) > top_k:
            hits = self._rerank(query, hits, top_k)

        return hits[:top_k]

    def _rerank(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        if self._reranker is None:
            self._reranker = Reranker(RERANK_MODEL)
        # 优先用 QueryProcessor 的英文 variant 作为 rerank query
        qp = self.query_processor.process(query)
        rerank_query = query
        if qp.get("is_chinese") and len(qp.get("variants", [])) > 1:
            rerank_query = qp["variants"][1]
        return self._reranker.rerank(rerank_query, candidates, top_k=top_k)

    def _search_hybrid(
        self,
        query: str,
        top_k: int = TOP_K,
        file_type: str | None = None,
        metadata_filter: dict | None = None,
    ) -> list[dict]:
        """Hybrid: Dense + BM25 RRF"""

        # 1. 跨语言处理 → 多个 variant query
        qp_result = self.query_processor.process(query)

        # 2. Dense Embedding（用原始 query + 英文术语版本）
        dense_query = qp_result.get("variants", [query])[0]
        if qp_result.get("is_chinese") and len(qp_result.get("variants", [])) > 1:
            dense_query = qp_result["variants"][1]  # 英文术语版本，embedding 效果更好
        query_vec = self.embedder.embed_single(dense_query)

        # 3. BM25 queries（全部 variant）
        bm25_queries = qp_result.get("variants", [query])

        # 4. Exclusive or boost terms
        exact_terms = qp_result.get("fixed_terms", [])
        boost_terms = qp_result.get("keywords", [])

        # 5. Metadata filter
        mf = dict(metadata_filter or {})
        if file_type:
            mf["file_type"] = file_type

        return self.store.search_hybrid(
            query_embedding=query_vec,
            bm25_queries=bm25_queries,
            exact_terms=exact_terms,
            boost_terms=boost_terms,
            top_k=max(top_k, HYBRID_TOP_K),
            metadata_filter=mf if mf else None,
        )

    def format_context(self, hits: list[dict]) -> str:
        """将检索结果格式化为 Prompt 用的 Context（增强版）"""
        parts = []
        for i, hit in enumerate(hits, start=1):
            meta = hit.get("metadata", {})
            source = meta.get("source", "未知来源")
            filename = meta.get("filename", "")
            file_type = meta.get("file_type", "")
            heading = meta.get("heading", "")
            heading_path = meta.get("heading_path", "")
            tdoc = meta.get("tdoc", [])
            wg = meta.get("wg", [])
            meeting = meta.get("meeting", [])
            keywords = meta.get("keywords", [])
            match_reasons = hit.get("match_reasons", [])
            rrf_score = hit.get("rrf_score")
            rerank_score = hit.get("rerank_score")

            label_parts = [source]
            if filename:
                label_parts.append(filename)
            if file_type:
                label_parts.append(f"[{file_type.upper()}]")
            if tdoc:
                label_parts.append(f"TDoc={','.join(tdoc[:3])}")
            if wg:
                label_parts.append(f"WG={','.join(wg[:3])}")
            if meeting:
                label_parts.append(f"Meeting={','.join(meeting[:2])}")
            if heading_path:
                label_parts.append(heading_path)
            elif heading:
                label_parts.append(heading)
            if keywords:
                label_parts.append(f"KW: {','.join(keywords[:5])}")

            label = " · ".join(label_parts)
            header = f"[{i}] {label}"
            if match_reasons:
                header += f"  [matched by: {', '.join(match_reasons)}]"
            if rerank_score is not None:
                header += f"  (rerank={rerank_score:.4f})"
            elif rrf_score is not None:
                header += f"  (rrf={rrf_score:.4f})"

            parts.append(f"{header}\n{hit['text']}")
        return "\n\n".join(parts)

