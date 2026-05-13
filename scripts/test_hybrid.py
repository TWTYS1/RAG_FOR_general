"""Test Step 5: Hybrid Search (Dense + BM25 RRF)"""
import sys
sys.path.insert(0, "D:/vibecoding/project1")
from src.retrieve import Retriever
from src.bm25_index import get_shared_bm25

# 确保使用共享 BM25
bm25 = get_shared_bm25()
print(f"Shared BM25 size: {len(bm25)}")

retriever = Retriever(use_hybrid=True)
print(f"Retriever store count: {retriever.store.count()}")
print(f"Retriever BM25 is shared? {retriever.store._bm25 is bm25}")

if retriever.store.count() == 0:
    print("\nNo documents indexed. Run ingest first:")
    print("  python -c \"from src.ingest import IngestPipeline; IngestPipeline().run()\"")
else:
    queries = [
        "PRS measurement report 相关的 open issue 有哪些？",
        "AI/ML positioning 中 proactive NGAP solution 解决什么问题？",
        "gNB-sided model 的数据采集流程有哪些未解决点？",
        "哪些 TDoc 涉及 model monitoring 和 fallback？",
    ]
    for q in queries:
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        hits = retriever.search(q)
        print(f"Results: {len(hits)}")
        for i, h in enumerate(hits[:3], 1):
            meta = h.get("metadata", {})
            reasons = h.get("match_reasons", [])
            score = h.get("rrf_score", "N/A")
            print(f"  [{i}] {meta.get('source','?')} | reasons={reasons} | score={score}")
            print(f"      text: {h['text'][:120]}...")
