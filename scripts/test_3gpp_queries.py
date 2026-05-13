"""Step 8: 3GPP 评估测试查询集 —— 5 维度 × 3+ 查询

用法:
  # 仅测试 query expansion（无需索引）
  python scripts/test_3gpp_queries.py --dry-run

  # 完整测试（需要已索引的 3GPP 文档）
  python scripts/test_3gpp_queries.py

  # 指定查询子集
  python scripts/test_3gpp_queries.py --category gap
"""
import sys
import json
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.query_processor import QueryProcessor
from src.templates import detect_template, TEMPLATE_TRIGGERS

# ── 测试查询集 ─────────────────────────────────
# 每条: (category, query, expected_terms, description)

TEST_QUERIES = [
    # ═══ 维度 1: 差距分析 (Gap Analysis) ═══
    ("gap",
     "Rel-19 AI/ML positioning 中 UE-sided model 和 gNB-sided model 在规范定义上有哪些 gap？",
     ["AI/ML positioning", "UE-sided", "gNB-sided", "Rel-19"],
     "Spec gap between UE and gNB models in NR positioning"),

    ("gap",
     "NR Sidelink Positioning 在 Rel-18 和 Rel-19 之间有哪些未覆盖的场景？",
     ["Sidelink Positioning", "Rel-18", "Rel-19", "NR"],
     "Release comparison gap for sidelink positioning"),

    ("gap",
     "PRS measurement and reporting 流程中，现有的 RRC 信令是否能支持 AI/ML-based 的测量预测？存在哪些信令缺失？",
     ["PRS", "measurement", "reporting", "RRC", "AI/ML", "信令"],
     "Signaling gap for AI/ML-based PRS measurement prediction"),

    ("gap",
     "TDoc 中关于 positioning integrity 的定义在不同 WG (RAN1 vs RAN2 vs SA2) 之间是否有矛盾？",
     ["positioning integrity", "RAN1", "RAN2", "SA2", "TDoc"],
     "Cross-WG contradiction in positioning integrity"),

    # ═══ 维度 2: 剩余问题 (Remaining Issues) ═══
    ("issue",
     "TR 38.859 关于 AI/ML positioning 的 study 还有哪些 remaining issue 未解决？",
     ["TR 38.859", "AI/ML positioning", "remaining issue"],
     "Open issues in AI/ML positioning study"),

    ("issue",
     "RAN1#119bis 会议关于 sidelink positioning 的讨论遗留了哪些 open issue？",
     ["RAN1", "119bis", "sidelink positioning", "open issue"],
     "Meeting-specific open issues"),

    ("issue",
     "NR Positioning enhancement 中关于 low-latency positioning 的进一步研究方向是什么？哪些公司提出了后续建议？",
     ["NR Positioning", "low-latency", "further study", "enhancement"],
     "Future study directions for low-latency positioning"),

    # ═══ 维度 3: 专利机会 (Patent Opportunity) ═══
    ("patent",
     "Multi-RTT positioning 中是否存在技术空白可以申请专利？特别是误差补偿方面",
     ["Multi-RTT", "positioning", "误差补偿", "技术空白"],
     "Patent opportunity in Multi-RTT error compensation"),

    ("patent",
     "Reconfigurable Intelligent Surface (RIS) assisted positioning 在标准化过程中有哪些未定义的信令流程可以形成专利？",
     ["RIS", "Reconfigurable Intelligent Surface", "positioning", "信令流程"],
     "Patent opportunity in RIS positioning signaling"),

    ("patent",
     "Sidelink positioning 中 collaborative/relay-based 定位方法的资源分配机制是否有标准空白可申请专利？",
     ["Sidelink", "collaborative", "relay", "资源分配", "标准空白"],
     "Patent opportunity in sidelink collaborative positioning"),

    # ═══ 维度 4: 跨语言 (Cross-language) ═══
    ("crosslang",
     "Rel-19 Case 3a 还有哪些 remaining issue？",
     ["Rel-19", "Case 3a", "remaining issue"],
     "Chinese query with English 3GPP terms — 简短口语化"),

    ("crosslang",
     "前向兼容性在 6G 定位标准中如何保证？有哪些技术方案被讨论过？",
     ["forward compatibility", "6G", "positioning", "technical solution"],
     "Chinese-dominant query needing English term expansion"),

    ("crosslang",
     "测量间隙冲突对定位精度的影响在标准中怎么解决的？",
     ["measurement gap", "collision", "positioning accuracy", "MG"],
     "Technical scenario query in Chinese"),

    # ═══ 维度 5: 精确术语匹配 (Exact Term) ═══
    ("exact",
     "TS 38.355 LPP 协议中关于 positioning measurement report 的最新 CR 有哪些？",
     ["TS 38.355", "LPP", "CR", "positioning measurement report"],
     "Exact spec number + CR search"),

    ("exact",
     "查找涉及 'model monitoring' 和 'fallback mechanism' 的 TDoc",
     ["model monitoring", "fallback mechanism", "TDoc"],
     "Exact TDoc topic search"),

    ("exact",
     "RAN1 提到的 'proactive NGAP solution' 是什么？在哪个 TDoc 中讨论的？",
     ["RAN1", "proactive NGAP", "solution", "TDoc"],
     "Exact term with WG/TDoc cross-reference"),
]


def run_dry_run():
    """仅测试 Query Processing，不依赖索引"""
    qp = QueryProcessor()
    print("=" * 70)
    print("3GPP 查询处理测试 (Dry Run) —— Query Expansion & Template Detection")
    print("=" * 70)

    results = []
    for cat, query, expected_terms, desc in TEST_QUERIES:
        qp_result = qp.process(query)
        tpl = detect_template(query)

        print(f"\n{'─' * 60}")
        print(f"类别: {cat}  |  模板: {tpl}")
        print(f"描述: {desc}")
        print(f"Query: {query}")
        print(f"  is_chinese: {qp_result['is_chinese']}")
        print(f"  fixed_terms ({len(qp_result['fixed_terms'])}): {qp_result['fixed_terms']}")
        print(f"  keywords ({len(qp_result['keywords'])}): {qp_result['keywords'][:6]}")
        print(f"  variants ({len(qp_result['variants'])}):")
        for j, v in enumerate(qp_result['variants']):
            print(f"    [{j+1}] {v[:130]}")

        # 检查期望术语是否命中
        hits = []
        all_text = " ".join(qp_result['variants']).lower()
        for et in expected_terms:
            if et.lower() in all_text:
                hits.append(et)
        misses = [et for et in expected_terms if et.lower() not in all_text]
        if hits:
            print(f"  ✓ 命中: {hits}")
        if misses:
            print(f"  ✗ 未命中: {misses}")

        results.append({
            "category": cat, "template": tpl,
            "query": query, "expected": expected_terms,
            "hits": hits, "misses": misses,
        })

    # 统计
    total_expected = sum(len(r["expected"]) for r in results)
    total_hits = sum(len(r["hits"]) for r in results)
    print(f"\n{'=' * 70}")
    print(f"命中率: {total_hits}/{total_expected} ({100*total_hits/total_expected:.0f}%)")
    return results


def run_full_test(top_k: int = 8):
    """完整检索 + 生成测试（需要已索引的 3GPP 文档）"""
    from src.retrieve import Retriever
    from src.generate import Generator

    retriever = Retriever()
    generator = Generator()

    if retriever.store.count() == 0:
        print("[ERROR] 向量库为空，请先运行: python -c \"from src.ingest import IngestPipeline; IngestPipeline().run()\"")
        return []

    print("=" * 70)
    print("3GPP 检索 + 生成评估测试")
    print(f"索引 chunk 数: {retriever.store.count()}")
    print("=" * 70)

    results = []
    for cat, query, expected_terms, desc in TEST_QUERIES:
        t0 = time.time()
        tpl = detect_template(query)
        hits = retriever.search(query)
        latency = (time.time() - t0) * 1000

        print(f"\n{'─' * 60}")
        print(f"[{cat}] {desc}")
        print(f"Query: {query}")
        print(f"模板: {tpl}  |  结果: {len(hits)} 条  |  耗时: {latency:.0f}ms")

        for i, h in enumerate(hits[:5], 1):
            meta = h.get("metadata", {})
            reasons = h.get("match_reasons", [])
            rrf = h.get("rrf_score")
            rerank = h.get("rerank_score")
            score_str = ""
            if rerank:
                score_str = f"rerank={rerank:.4f}"
            elif rrf:
                score_str = f"rrf={rrf:.4f}"
            src = meta.get("source", "?")
            tdocs = meta.get("tdoc", [])
            tdoc_str = f" TDoc={tdocs[:2]}" if tdocs else ""
            wg_str = f" WG={meta.get('wg', [])[:2]}" if meta.get("wg") else ""
            print(f"  [{i}] {src}{tdoc_str}{wg_str} [{','.join(reasons)}] {score_str}")

        results.append({
            "category": cat, "template": tpl,
            "query": query, "num_results": len(hits),
            "latency_ms": round(latency, 1),
            "top_sources": [h.get("metadata", {}).get("source", "?") for h in hits[:3]],
        })

    # 汇总
    avg_hits = sum(r["num_results"] for r in results) / max(len(results), 1)
    avg_latency = sum(r["latency_ms"] for r in results) / max(len(results), 1)
    print(f"\n{'=' * 70}")
    print(f"平均结果数: {avg_hits:.1f}  |  平均检索延迟: {avg_latency:.0f}ms")
    print(f"查询总数: {len(results)}  |  类别覆盖: {len(set(r['category'] for r in results))}/5")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="3GPP Evaluation Test Suite")
    parser.add_argument("--dry-run", action="store_true", help="仅测试 query expansion")
    parser.add_argument("--category", choices=["gap", "issue", "patent", "crosslang", "exact"],
                        help="仅测试指定类别")
    parser.add_argument("--top-k", type=int, default=8, help="检索数量")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args()

    queries = TEST_QUERIES
    if args.category:
        queries = [q for q in TEST_QUERIES if q[0] == args.category]

    if args.dry_run:
        results = run_dry_run()
    else:
        results = run_full_test(top_k=args.top_k)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
