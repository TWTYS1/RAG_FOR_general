"""生成模块: Prompt 组装 → 3GPP 模板选择 → LLM 调用"""

from openai import OpenAI
from .config import (
    LLM_PROVIDER, LLM_MODEL,
    OPENAI_API_KEY, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
)
from .templates import build_prompt, detect_template, SYSTEM_PROMPT_3GPP


class Generator:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider or LLM_PROVIDER
        self.model = model or LLM_MODEL

    def generate(self, query: str, context: str, template: str | None = None) -> str:
        if not context:
            return "当前文档库未覆盖此问题。"

        client = self._get_client()
        user_prompt = build_prompt(query, context, template=template)
        tpl = template or detect_template(query)

        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_3GPP},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=3000,
        )
        answer = resp.choices[0].message.content or ""

        # 添加模板标签便于调试
        if answer:
            tag = {"gap": "📐 差距分析", "issue": "🔍 剩余问题追踪", "patent": "💡 专利机会发现"}.get(tpl, "")
            if tag:
                answer = f"**{tag}**\n\n{answer}"
        return answer

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
