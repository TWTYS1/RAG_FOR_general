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
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# --- 检索 ---
TOP_K = 8

# --- 支持的文件格式 ---
SUPPORTED_EXTENSIONS = {".md", ".pdf", ".txt", ".docx", ".html", ".htm"}
