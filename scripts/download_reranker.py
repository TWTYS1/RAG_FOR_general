"""通过 ModelScope 下载 bge-reranker-v2-m3，带进度条"""
from modelscope import snapshot_download

model_id = "BAAI/bge-reranker-v2-m3"
cache = "D:/vibecoding/models"

print(f"Downloading {model_id} via ModelScope...")
print(f"Cache: {cache}\n")

snapshot_download(model_id, cache_dir=cache)

print("\nDone! Model downloaded to:", cache)
