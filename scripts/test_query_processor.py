"""Test Step 4: Query Processor"""
import sys
sys.path.insert(0, "D:/vibecoding/project1")
from src.query_processor import QueryProcessor

qp = QueryProcessor()

test_queries = [
    "Rel-19 Case 3a 还有哪些 remaining issue？",
    "RAN1 提到的 AI/ML positioning higher layer parameters 有哪些？",
    "gNB-sided model 的数据采集流程有哪些未解决点？",
    "AI/ML positioning 中 proactive NGAP solution 解决什么问题？",
    "PRS measurement report 相关的 open issue 有哪些？",
    "哪些 TDoc 涉及 model monitoring 和 fallback？",
]

for i, q in enumerate(test_queries, 1):
    result = qp.process(q)
    print(f"=== Query {i}: {q}")
    print(f"  is_chinese: {result['is_chinese']}")
    print(f"  english_terms ({len(result['english_terms'])}): {result['english_terms'][:8]}...")
    print(f"  fixed_terms ({len(result['fixed_terms'])}): {result['fixed_terms']}")
    print(f"  keywords ({len(result['keywords'])}): {result['keywords'][:8]}...")
    print(f"  variants ({len(result['variants'])}):")
    for j, v in enumerate(result['variants']):
        print(f"    [{j+1}] {v[:120]}")
    print()
