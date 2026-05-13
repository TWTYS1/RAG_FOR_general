"""集中配置管理 —— 从 .env 读取，提供默认值"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- 路径 ---
DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
CHROMA_COLLECTION = "rag_docs"

# --- LLM ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# --- Embedding ---
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")

# --- 分块 ---
CHUNK_SIZE = 800           # 3GPP 段落密度适配
CHUNK_OVERLAP = 150
KEYWORD_BOOST_CHUNKS = True  # 为含 3GPP 关键词的段落生成强化索引副本

# --- 检索 ---
TOP_K = 8
HYBRID_TOP_K = 50          # 混合检索初召回数
RERANK_TOP_K = 15          # 重排序后保留数
RERANK_ENABLED = True       # 启用 Cross-Encoder 重排序
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

# --- 支持的文件格式 ---
SUPPORTED_EXTENSIONS = {".md", ".pdf", ".txt", ".docx", ".html", ".htm"}
IGNORE_NAMES = {"readme.txt", "readme.md", "readme"}
