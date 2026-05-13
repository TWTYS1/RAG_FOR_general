"""CLI 交互式问答"""

import sys
from .ingest import IngestPipeline
from .retrieve import Retriever
from .generate import Generator

BANNER = """
╔══════════════════════════════════════════╗
║      RAG 问答系统 · 多格式文档检索      ║
╠══════════════════════════════════════════╣
║  命令:                                   ║
║    /index    — 重新索引文档库            ║
║    /filter   — 按文件类型筛选 (md/pdf)   ║
║    /sources  — 显示上次检索来源          ║
║    /help     — 帮助                      ║
║    /exit     — 退出                      ║
╚══════════════════════════════════════════╝
"""


def run_cli():
    print(BANNER)

    retriever = Retriever()
    generator = Generator()
    last_hits: list[dict] = []
    file_filter: str | None = None

    # 启动时检查索引状态
    count = retriever.store.count()
    if count == 0:
        print("📭 向量库为空，正在执行首次索引...\n")
        pipeline = IngestPipeline()
        pipeline.run()
        count = retriever.store.count()
    print(f"📚 已索引 {count} 个 chunk，可以开始提问\n")

    while True:
        try:
            raw = input("🔍 问题: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见")
            break

        if not raw:
            continue

        # --- 命令处理 ---
        if raw.startswith("/"):
            handled = _handle_command(raw, retriever, last_hits, file_filter)
            if handled == "EXIT":
                break
            if isinstance(handled, str) and handled.startswith("FILTER:"):
                file_filter = handled.split(":", 1)[1] or None
                print(f"📂 筛选器: {file_filter or '全部'}")
            continue

        # --- 问答流程 ---
        print("⏳ 检索中...")
        hits = retriever.search(raw, file_type=file_filter)
        last_hits = hits

        if not hits:
            print("😕 未找到相关文档。")
            print()
            continue

        context = retriever.format_context(hits)
        print(f"📄 找到 {len(hits)} 条相关内容，正在生成回答...\n")
        answer = generator.generate(raw, context)
        print("─" * 60)
        print(answer)
        print("─" * 60)
        print()


def _handle_command(cmd: str, retriever: Retriever, hits: list[dict], current_filter: str | None) -> str | None:
    parts = cmd.split()
    action = parts[0].lower()

    if action == "/exit":
        print("👋 再见")
        return "EXIT"

    elif action == "/index":
        print("🔄 重新索引文档库（清空旧数据）...")
        pipeline = IngestPipeline()
        pipeline.run(clear=True)
        print(f"📚 当前索引: {retriever.store.count()} 个 chunk\n")
        return None

    elif action == "/sources":
        if not hits:
            print("📭 暂无检索结果。先提一个问题。\n")
        else:
            print(f"\n📎 上一次检索来源 ({len(hits)} 条):")
            for i, hit in enumerate(hits, start=1):
                meta = hit.get("metadata", {})
                print(f"  [{i}] {meta.get('source','?')}  [{meta.get('file_type','')}]  {meta.get('heading','')}")
            print()
        return None

    elif action == "/filter":
        if len(parts) > 1:
            ft = parts[1].lower()
            return f"FILTER:{ft}"
        else:
            print("用法: /filter md|pdf|txt|docx|html  或 /filter 清空筛选\n")
            return None

    elif action == "/help":
        print("""
命令列表:
  /index      — 重新扫描 docs/ 目录，重新索引全部文档
  /filter md  — 只搜 Markdown 文件（也支持 pdf/txt/docx/html）
  /filter     — 清空筛选
  /sources    — 显示上一次问题检索到的来源文档
  /exit       — 退出
直接输入问题即可开始问答。
""")
        return None

    else:
        print(f"未知命令: {action}，输入 /help 查看帮助\n")
        return None


if __name__ == "__main__":
    run_cli()
