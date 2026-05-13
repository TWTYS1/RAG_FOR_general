"""Streamlit Web UI —— RAG 问答系统"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from src.retrieve import Retriever
from src.generate import Generator
from src.ingest import IngestPipeline

st.set_page_config(page_title="RAG 问答", page_icon="📚", layout="wide")

# --- 初始化 ---
if "retriever" not in st.session_state:
    st.session_state.retriever = Retriever()
if "generator" not in st.session_state:
    st.session_state.generator = Generator()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_hits" not in st.session_state:
    st.session_state.last_hits = []

retriever: Retriever = st.session_state.retriever
generator: Generator = st.session_state.generator


# --- 侧边栏 ---
with st.sidebar:
    st.title("📚 RAG 问答系统")
    st.caption("多格式文档 · 语义检索")

    count = retriever.store.count()
    st.metric("已索引 chunk", count)

    st.divider()

    file_type = st.selectbox(
        "按文件类型筛选",
        ["全部", "md", "pdf", "txt", "docx", "html"],
        index=0,
    )
    ft = None if file_type == "全部" else file_type

    st.divider()

    if st.button("🔄 重新索引文档库"):
        with st.spinner("索引中（清空旧数据）..."):
            pipeline = IngestPipeline()
            n = pipeline.run(clear=True)
            st.success(f"索引完成: {n} 个 chunk")
            st.rerun()

    st.divider()
    st.caption("LLM: DeepSeek · Embedding: Qwen3-0.6B")


# --- 主区域 ---
st.title("💬 技术文档问答")

# 渲染历史对话
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("📎 来源"):
                for s in msg["sources"]:
                    st.caption(f"[{s['type']}] {s['source']}")

# 输入框
if prompt := st.chat_input("输入你的问题..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("检索中..."):
            hits = retriever.search(prompt, file_type=ft)
            st.session_state.last_hits = hits

        if not hits:
            st.warning("未找到相关文档。")
            st.session_state.messages.append({"role": "assistant", "content": "未找到相关文档。"})
        else:
            context = retriever.format_context(hits)
            answer = generator.generate(prompt, context)

            st.markdown(answer)

            with st.expander(f"📎 来源 ({len(hits)} 条)"):
                for i, hit in enumerate(hits, 1):
                    meta = hit.get("metadata", {})
                    st.caption(
                        f"[{i}] {meta.get('source','?')}  "
                        f"[{meta.get('file_type','').upper()}]  "
                        f"{meta.get('heading','')}  "
                        f"{'第'+str(meta['page'])+'页' if meta.get('page') else ''}"
                    )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "sources": [
                    {"type": h["metadata"].get("file_type", ""), "source": h["metadata"].get("source", "")}
                    for h in hits
                ],
            })
