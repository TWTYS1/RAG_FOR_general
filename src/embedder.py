"""Embedding 模块: 支持本地 Qwen3-Embedding 和 OpenAI API 两种后端"""

import time
from .config import EMBEDDING_PROVIDER, EMBEDDING_MODEL, OPENAI_API_KEY

# 模块级缓存：避免重复加载模型
_MODEL_CACHE: dict[str, object] = {}


class Embedder:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider or EMBEDDING_PROVIDER
        self.model = model or EMBEDDING_MODEL
        self._local_model = None
        self._dimension: int | None = None

    def _ensure_local(self):
        if self._local_model is not None:
            return
        cache_key = f"local:{self.model}"
        if cache_key in _MODEL_CACHE:
            self._local_model = _MODEL_CACHE[cache_key]
            self._dimension = self._local_model.get_embedding_dimension()
            return
        from sentence_transformers import SentenceTransformer
        try:
            self._local_model = SentenceTransformer(
                self.model, local_files_only=True
            )
        except Exception:
            self._local_model = SentenceTransformer(self.model)
        _MODEL_CACHE[cache_key] = self._local_model
        self._dimension = self._local_model.get_embedding_dimension()

    @property
    def dimension(self) -> int:
        """返回当前模型的 Embedding 维度（首次调用会触发模型加载）"""
        if self.provider == "local":
            self._ensure_local()
            return self._dimension
        elif self.provider == "openai":
            # text-embedding-3-small: 1536, text-embedding-3-large: 3072
            return 1536
        else:
            raise ValueError(f"未知 Embedding 提供商: {self.provider}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.provider == "local":
            return self._embed_local(texts)
        elif self.provider == "openai":
            return self._embed_openai(texts)
        else:
            raise ValueError(f"不支持的 Embedding 提供商: {self.provider}")

    def embed_single(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        self._ensure_local()
        embeddings = self._local_model.encode(texts, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY 未配置，请在 .env 中设置")
        client = OpenAI(api_key=OPENAI_API_KEY)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = client.embeddings.create(model=self.model, input=texts)
                return [d.embedding for d in resp.data]
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise e
