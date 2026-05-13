"""Cross-Encoder 重排序: 对初召回的候选集精排，提升 3GPP 术语匹配精度"""

import torch
from .config import RERANK_TOP_K

_MODEL_CACHE: dict[str, object] = {}


class Reranker:
    """Cross-Encoder 重排序器，加载一次后模块级缓存复用"""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or "BAAI/bge-reranker-v2-m3"
        self._model = None
        self._tokenizer = None
        self._device = None

    def _ensure_model(self):
        if self._model is not None:
            return
        cache_key = f"reranker:{self.model_name}"
        if cache_key in _MODEL_CACHE:
            self._model, self._tokenizer, self._device = _MODEL_CACHE[cache_key]
            return
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, local_files_only=True
            )
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name, local_files_only=True
            )
        except Exception:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)

        self._model.to(self._device)
        self._model.eval()
        _MODEL_CACHE[cache_key] = (self._model, self._tokenizer, self._device)

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = RERANK_TOP_K,
    ) -> list[dict]:
        """Cross-Encoder 重排序

        Args:
            query: 搜索问题（使用英文 variant 效果更好）
            candidates: 初召回候选，每个含 "text" 字段
            top_k: 返回数量

        Returns:
            重排后的候选列表，额外包含 rerank_score 字段
        """
        if len(candidates) <= top_k:
            for c in candidates:
                c["rerank_score"] = None
            return candidates

        self._ensure_model()
        pairs = [(query, c["text"]) for c in candidates]

        with torch.no_grad():
            inputs = self._tokenizer(
                pairs, padding=True, truncation=True,
                max_length=512, return_tensors="pt",
            ).to(self._device)
            scores = self._model(**inputs, return_dict=True).logits.squeeze(-1)
            scores = scores.cpu().tolist()
            if isinstance(scores, float):
                scores = [scores]

        for c, score in zip(candidates, scores):
            c["rerank_score"] = round(score, 6)

        candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return candidates[:top_k]

    @property
    def device(self) -> str | None:
        return self._device
