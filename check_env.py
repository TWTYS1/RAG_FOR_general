"""RAG 项目环境验证脚本 —— 一条命令检查所有依赖"""
import sys

def check(name, import_name=None):
    if import_name is None:
        import_name = name
    try:
        mod = __import__(import_name)
        ver = getattr(mod, "__version__", "OK")
        print(f"  [OK]    {name:<25} {ver}")
        return True
    except ImportError:
        print(f"  [MISS]  {name:<25} not installed")
        return False

print("=" * 55)
print("  RAG Project Environment Check")
print(f"  Python: {sys.version}")
print("=" * 55)

all_ok = True

print("\n-- Core Dependencies --")
all_ok &= check("chromadb")
all_ok &= check("openai")
all_ok &= check("tiktoken")
all_ok &= check("sentence_transformers", "sentence_transformers")

print("\n-- Document Parsers --")
all_ok &= check("markdown-it-py", "markdown_it")
all_ok &= check("pdfplumber")
all_ok &= check("python-docx", "docx")
all_ok &= check("beautifulsoup4", "bs4")
all_ok &= check("lxml")

print("\n-- Tools --")
all_ok &= check("python-dotenv", "dotenv")
all_ok &= check("streamlit")

print("\n-- .env Config Check --")
try:
    from dotenv import load_dotenv
    import os
    load_dotenv()
    deepseek = os.getenv("DEEPSEEK_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    if deepseek and deepseek != "sk-your-deepseek-api-key-here":
        print(f"  [OK]    DEEPSEEK_API_KEY       configured ({deepseek[:10]}...)")
    else:
        print(f"  [WARN]  DEEPSEEK_API_KEY       not configured (apply at platform.deepseek.com)")
        all_ok = False
    if openai_key and openai_key != "sk-your-openai-api-key-here":
        print(f"  [OK]    OPENAI_API_KEY         configured ({openai_key[:10]}...)")
    else:
        print(f"  [INFO]  OPENAI_API_KEY         not configured (optional)")
except Exception as e:
    print(f"  [FAIL]  .env read error: {e}")
    all_ok = False

print("\n" + "=" * 55)
if all_ok:
    print("  ALL CHECKS PASSED - environment is ready.")
else:
    print("  Some checks failed. Fix [MISS] items above and re-run.")
print("=" * 55)
