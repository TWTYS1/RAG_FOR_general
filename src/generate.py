"""生成模块: Prompt 组装 → LLM 调用 → 后处理"""

from openai import OpenAI
from .config import (
    LLM_PROVIDER, LLM_MODEL,
    OPENAI_API_KEY, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
)

SYSTEM_PROMPT = """你是一个技术文档助手。请严格基于下方提供的文档片段回答问题。
文档来源可能包含多种格式（Markdown/PDF/Word/网页等）。
- 如果文档片段足以回答，请给出清晰完整的回答，并在关键信息后标注来源编号，如 [1]、[2]。
- 如果文档片段不足以回答，请明确说"当前文档库未覆盖此问题"，不要编造信息。
- 回答使用中文，保持专业、简洁。"""


class Generator:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider or LLM_PROVIDER
        self.model = model or LLM_MODEL

    def generate(self, query: str, context: str) -> str:
        if not context:
            return "当前文档库未覆盖此问题。"

        client = self._get_client()
        user_prompt = f"## Context（检索到的文档片段）\n\n{context}\n\n## Query\n{query}"

        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return resp.choices[0].message.content or ""

    def _get_client(self) -> OpenAI:
        if self.provider == "deepseek":
            if not DEEPSEEK_API_KEY:
                raise ValueError("DEEPSEEK_API_KEY 未配置，请在 .env 中设置")
            return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        elif self.provider == "openai":
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY 未配置，请在 .env 中设置")
            return OpenAI(api_key=OPENAI_API_KEY)
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.provider}")
