"""跨语言查询处理: 中文 → 英文翻译 + 3GPP 术语扩展 + 关键词提取"""

import re


# ── 3GPP 术语映射：中文 → 英文 + 同义词扩展 ───────────

_TERM_MAP: dict[str, list[str]] = {
    # 未解决问题
    "未解决": ["remaining issue", "open issue", "unresolved issue", "FFS", "for further study", "not agreed", "pending"],
    "遗留问题": ["remaining issue", "open issue", "pending issue", "not resolved", "FFS"],
    "remaining": ["remaining issue", "open issue", "FFS", "for further study", "not agreed", "unresolved"],

    # 高层参数
    "高层参数": ["higher layer parameters", "RRC parameters", "LPP parameters", "NRPPa IE", "NGAP IE", "configuration parameters"],
    "参数配置": ["parameter configuration", "RRC configuration", "LPP configuration", "NRPPa configuration"],

    # gNB 侧模型
    "gnb侧模型": ["gNB-sided model", "gNB-side model", "NG-RAN node assisted positioning", "Case 3a"],
    "gnb模型": ["gNB-sided model", "gNB-side model", "network-side model", "NG-RAN model"],

    # 数据采集
    "数据采集": ["data collection", "measurement collection", "OAM triggered reporting", "UE measurement report", "data gathering"],
    "数据收集": ["data collection", "measurement collection", "data gathering", "reporting procedure"],

    # 模型监控
    "模型监控": ["model monitoring", "model performance monitoring", "AI/ML model monitoring", "model supervision"],
    "监控": ["monitoring", "supervision", "performance monitoring", "model monitoring"],

    # 定位
    "定位": ["positioning", "location", "localization", "LMF positioning", "NR positioning"],
    "ai定位": ["AI/ML assisted positioning", "AI positioning", "ML positioning", "AI/ML positioning"],
    "ai/ml定位": ["AI/ML assisted positioning", "AI/ML positioning", "intelligent positioning"],

    # PRS
    "prs": ["PRS", "positioning reference signal", "PRS measurement", "PRS configuration"],
    "参考信号": ["PRS", "positioning reference signal", "reference signal", "SRS"],

    # Case 3
    "case3": ["Case 3a", "Case 3b", "Case 3", "gNB-sided", "UE-sided"],

    # Way forward
    "方案": ["way forward", "solution", "proposal", "approach", "candidate solution"],
    "建议": ["proposal", "suggestion", "recommendation", "way forward", "candidate"],

    # LPP/NRPPa/NGAP
    "lpp": ["LPP", "LTE Positioning Protocol", "NRPPa", "positioning protocol"],
    "nrppa": ["NRPPa", "NR Positioning Protocol A", "positioning protocol"],
    "ngap": ["NGAP", "NG Application Protocol", "NG interface"],

    # RAN
    "ran1": ["RAN1", "RAN1 PHY", "physical layer positioning"],
    "ran3": ["RAN3", "RAN3 protocol", "higher layer positioning"],

    # LS
    "ls": ["LS", "Liaison Statement", "LS in", "LS out"],
    "联络函": ["LS", "Liaison Statement"],

    # Spec
    "协议": ["specification", "TS", "TR", "technical specification", "protocol"],
    "规范": ["specification", "TS", "TR", "technical report"],

    # 其他
    "回退": ["fallback", "legacy fallback", "positioning fallback", "model fallback"],
    "主动": ["proactive", "proactive reporting", "proactive NGAP", "event-triggered"],
    "测量报告": ["measurement report", "PRS measurement report", "measurement result", "measurement quantity"],
    "oam": ["OAM", "operation and maintenance", "OAM triggered", "network management"],
    "接口": ["interface", "NRPPa", "NGAP", "LPP", "RRC", "Xn", "F1"],
    "影响": ["impact", "impacts", "affects", "implications"],
}

# 3GPP 固定术语（用于精确检索）
_FIXED_TERMS = [
    "RAN1", "RAN2", "RAN3", "RAN4", "SA2", "SA3", "SA5", "CT1", "CT3", "CT4",
    "NRPPa", "NGAP", "LPP", "RRC", "XnAP", "F1AP", "E1AP", "X2AP",
    "LMF", "gNB", "ng-eNB", "UE", "AMF", "UPF", "SMF",
    "Case 3a", "Case 3b", "Case 1", "Case 2",
    "Rel-17", "Rel-18", "Rel-19", "Rel-20",
    "TS 38.455", "TS 38.331", "TS 38.215", "TS 37.355", "TR 38.889",
    "AI/ML", "AI ML", "ML model", "neural network",
    "Sidelink positioning", "SL positioning",
    "MRO", "MDT", "SON",
    "PRS", "SRS", "CSI-RS",
    "RSRP", "RSRQ", "SINR", "RSTD", "RTOA", "AOA",
]


class QueryProcessor:
    """跨语言查询处理器"""

    def __init__(self):
        self._cjk_pattern = re.compile(
            r"[一-鿿㐀-䶿豈-﫿぀-ゟ゠-ヿ가-힯]"
        )

    def process(self, raw_query: str) -> dict:
        """处理 query，返回多 variant 检索用字典

        Returns:
            {
                "original": str,           # 原始 query
                "is_chinese": bool,
                "english_terms": list[str],  # 英文翻译 + 术语扩展
                "keywords": list[str],       # 提取的关键词列表
                "fixed_terms": list[str],    # 匹配到的 3GPP 固定术语
                "variants": list[str],       # 全部 variant query 字符串
            }
        """
        is_cn = bool(self._cjk_pattern.search(raw_query))

        # 1. 术语映射扩展
        english_terms, keywords = self._expand_terms(raw_query)

        # 2. 固定术语精确匹配
        fixed_terms = self._match_fixed_terms(raw_query, english_terms)

        # 3. 组装 variant query 字符串
        variant_a = raw_query  # 原 query
        variant_b = " ".join(english_terms) if english_terms else raw_query  # 英文术语
        variant_c = " ".join(fixed_terms) if fixed_terms else ""  # 固定术语
        variant_d = " ".join(keywords) if keywords else ""  # 关键词

        variants = [v for v in [variant_a, variant_b, variant_c, variant_d] if v]

        return {
            "original": raw_query,
            "is_chinese": is_cn,
            "english_terms": english_terms,
            "keywords": keywords,
            "fixed_terms": fixed_terms,
            "variants": variants,
        }

    def _expand_terms(self, query: str) -> tuple[list[str], list[str]]:
        """术语映射：中文 → 英文 + 关键词"""
        lower = query.lower()
        english_set: set[str] = set()
        keyword_set: set[str] = set()

        # 匹配已知术语
        for cn_term, en_list in _TERM_MAP.items():
            if cn_term in lower:
                for en in en_list:
                    english_set.add(en)
                    # 把每个词也拆成关键词
                    for part in en.split():
                        if len(part) > 2 and not part.isdigit():
                            keyword_set.add(part)

        # 始终添加原始 query 中的英文单词作为关键词
        english_words = re.findall(r"[a-zA-Z][a-zA-Z0-9/+#._-]{2,}", query)
        for w in english_words:
            keyword_set.add(w)

        return sorted(english_set), sorted(keyword_set)

    def _match_fixed_terms(self, query: str, english_terms: list[str]) -> list[str]:
        """匹配 3GPP 固定术语"""
        matched: set[str] = set()
        lower_q = query.lower()
        lower_terms = " ".join(english_terms).lower()

        for term in _FIXED_TERMS:
            if term.lower() in lower_q or term.lower() in lower_terms:
                matched.add(term)

        return sorted(matched)

    @staticmethod
    def is_chinese(text: str) -> bool:
        """判断是否包含中文"""
        return bool(re.search(r"[一-鿿]", text))
