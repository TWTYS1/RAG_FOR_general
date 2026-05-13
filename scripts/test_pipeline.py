"""端到端测试：索引 → 检索 → 生成"""
import sys
sys.path.insert(0, "D:/vibecoding/project1")

import os
os.environ["HF_HUB_CACHE"] = "D:/vibecoding/models"

from src.ingest import IngestPipeline
from src.retrieve import Retriever
from src.generate import Generator

print("=== 1. 清库 + 重索引 ===")
p = IngestPipeline()
p.run(clear=True)

print()
print("=== 2. 检索测试 ===")
r = Retriever()
hits = r.search("React 中 useEffect 怎么用？")
print(f"检索到 {len(hits)} 条")
for i, h in enumerate(hits[:3]):
    src = h["metadata"].get("source", "?")
    print(f"  [{i+1}] {src}  dist={h['distance']:.4f}")
    text_preview = h["text"][:120].replace("\n", " ")
    print(f"      {text_preview}...")

print()
print("=== 3. 生成测试 ===")
g = Generator()
ctx = r.format_context(hits[:3])
ans = g.generate("React 中 useEffect 怎么用？", ctx)
print(ans[:600])
print()
print("=== 全部通过! ===")
