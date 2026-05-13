"""BM25 稀疏索引: 内存中维护，用于 3GPP 精确术语/编号匹配"""

import re
from rank_bm25 import BM25Okapi

# 模块级共享实例
_shared_index: "BM25Index | None" = None


def get_shared_bm25() -> "BM25Index":
    global _shared_index
    if _shared_index is None:
        _shared_index = BM25Index()
    return _shared_index


class BM25Index:
    """BM25 关键词索引，与 ChromaDB Dense 互补"""

    def __init__(self):
        self._corpus: list[str] = []
        self._metadatas: list[dict] = []
        self._ids: list[str] = []
        self._bm25: BM25Okapi | None = None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """小写 + 保留字母数字 + 特殊符（TDoc/CR/Spec 编号中的 /#-）"""
        return re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_/#+-]*", text.lower())

    def add(self, ids: list[str], texts: list[str], metadatas: list[dict]):
        """同步添加文档到 BM25，全量重建索引"""
        tokenized = [self._tokenize(t) for t in texts]
        self._corpus.extend(texts)
        self._metadatas.extend(metadatas)
        self._ids.extend(ids)
        self._bm25 = BM25Okapi(tokenized)

    def search(
        self,
        query: str,
        top_k: int = 50,
        exact_terms: list[str] | None = None,
        boost_terms: list[str] | None = None,
    ) -> list[tuple[int, float, dict]]:
        """BM25 检索 + 加权 boost

        Args:
            query: 搜索词
            top_k: 返回数量
            exact_terms: 精确匹配词（TDoc/CR/Spec编号）→ ×1.5 per hit
            boost_terms: 关键词（remaining issue 等）→ ×1.15 per hit

        Returns:
            list of (corpus_index, score, metadata)
        """
        if not self._bm25 or not self._corpus:
            return []

        tokenized = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized)
        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

        exact_lower = [t.lower() for t in (exact_terms or [])]
        boost_lower = [t.lower() for t in (boost_terms or [])]

        results: list[tuple[int, float, dict]] = []
        for idx, base in indexed:
            if base <= 0:
                continue
            bonus = 1.0
            text_lower = self._corpus[idx].lower() if idx < len(self._corpus) else ""
            for et in exact_lower:
                if et in text_lower:
                    bonus *= 1.5
            for bt in boost_lower:
                if bt in text_lower:
                    bonus *= 1.15
            results.append((idx, base * bonus, self._metadatas[idx]))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def clear(self):
        self._corpus.clear()
        self._metadatas.clear()
        self._ids.clear()
        self._bm25 = None

    def __len__(self) -> int:
        return len(self._corpus)
