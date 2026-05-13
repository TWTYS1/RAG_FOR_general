"""跨语言查询处理: 中文 → 英文翻译 + 3GPP 术语扩展 + 关键词提取

可通过外部文件扩展术语（无需改代码）:
  - config/fixed_terms.txt   每行一个固定术语，支持 # 注释
  - config/term_map.txt      每行: 中文词 -> 英文词1, 英文词2, ...
"""

import re
from pathlib import Path

# ── 外部配置文件加载 ───────────────────────────

_PROJECT_ROOT = Path(__file__).parent.parent


def _load_extra_terms(file_name: str) -> list[str]:
    """从 config/ 目录加载额外术语（每行一条，# 开头为注释）"""
    path = _PROJECT_ROOT / "config" / file_name
    if not path.exists():
        return []
    terms = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                terms.append(line)
    return terms


def _load_extra_mappings(file_name: str) -> dict[str, list[str]]:
    """从 config/ 目录加载额外术语映射（格式: 中文 -> 英文1, 英文2）"""
    path = _PROJECT_ROOT / "config" / file_name
    if not path.exists():
        return {}
    mapping: dict[str, list[str]] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "->" in line:
                key, values = line.split("->", 1)
                mapping[key.strip()] = [v.strip() for v in values.split(",") if v.strip()]
    return mapping


# ── 3GPP 术语映射：中文 → 英文 + 同义词扩展 ───────────

_TERM_MAP: dict[str, list[str]] = {
    # ── 问题/差距 ──
    "未解决": ["remaining issue", "open issue", "unresolved issue", "FFS", "for further study", "not agreed", "pending"],
    "遗留问题": ["remaining issue", "open issue", "pending issue", "not resolved", "FFS"],
    "remaining": ["remaining issue", "open issue", "FFS", "for further study", "not agreed", "unresolved"],
    "gap": ["gap", "missing", "undefined", "not specified", "specification gap"],
    "差距": ["gap", "missing functionality", "undefined behavior", "specification gap"],
    "空白": ["gap", "missing", "not defined", "void", "technical gap"],
    "缺失": ["missing", "absent", "not defined", "undefined", "gap"],
    "矛盾": ["contradiction", "inconsistent", "conflicting", "misaligned"],
    "冲突": ["conflict", "collision", "contradiction", "incompatible"],
    "问题": ["issue", "problem", "error case", "limitation", "drawback"],

    # ── 定义/规范 ──
    "定义": ["definition", "defined", "specified", "specification", "requirement"],
    "规范": ["specification", "TS", "TR", "technical report", "technical specification"],
    "标准": ["standard", "specification", "TS", "TR", "normative"],
    "流程": ["procedure", "flow", "process", "sequence", "signaling flow"],
    "信令": ["signaling", "RRC signaling", "LPP signaling", "NRPPa signaling", "NGAP signaling"],

    # ── 高层参数 ──
    "高层参数": ["higher layer parameters", "RRC parameters", "LPP parameters", "NRPPa IE", "NGAP IE", "configuration parameters"],
    "参数配置": ["parameter configuration", "RRC configuration", "LPP configuration", "NRPPa configuration"],

    # ── gNB 侧模型 ──
    "gnb侧模型": ["gNB-sided model", "gNB-side model", "NG-RAN node assisted positioning", "Case 3a"],
    "gnb模型": ["gNB-sided model", "gNB-side model", "network-side model", "NG-RAN model"],
    "ue侧模型": ["UE-sided model", "UE-side model", "UE-based positioning", "Case 3b"],
    "ue模型": ["UE-sided model", "UE-side model", "UE-based model"],

    # ── 数据采集 ──
    "数据采集": ["data collection", "measurement collection", "OAM triggered reporting", "UE measurement report", "data gathering"],
    "数据收集": ["data collection", "measurement collection", "data gathering", "reporting procedure"],
    "数据集": ["dataset", "training data", "measurement data", "data samples"],

    # ── 模型监控/回退 ──
    "模型监控": ["model monitoring", "model performance monitoring", "AI/ML model monitoring", "model supervision"],
    "监控": ["monitoring", "supervision", "performance monitoring", "model monitoring"],
    "回退": ["fallback", "legacy fallback", "positioning fallback", "model fallback"],
    "fallback": ["fallback mechanism", "legacy fallback", "fallback procedure", "model fallback"],
    "切换": ["switch", "handover", "fallback", "transition"],

    # ── 定位 ──
    "定位": ["positioning", "location", "localization", "LMF positioning", "NR positioning"],
    "测量": ["measurement", "measurement result", "measurement quantity", "RSTD", "RTOA", "AOA"],
    "测量报告": ["measurement report", "PRS measurement report", "measurement result", "measurement quantity"],
    "精度": ["accuracy", "positioning accuracy", "location accuracy", "error"],
    "完好性": ["integrity", "positioning integrity", "integrity monitoring", "reliability"],
    "延迟": ["latency", "delay", "time to fix", "TTFF", "low latency"],

    # ── AI/ML ──
    "ai定位": ["AI/ML assisted positioning", "AI positioning", "ML positioning", "AI/ML positioning"],
    "ai/ml定位": ["AI/ML assisted positioning", "AI/ML positioning", "intelligent positioning"],
    "模型推理": ["model inference", "AI/ML inference", "neural network inference", "model prediction"],
    "训练": ["training", "model training", "AI/ML training", "training data"],
    "推理": ["inference", "model inference", "AI/ML inference", "prediction"],

    # ── PRS/SRS 参考信号 ──
    "prs": ["PRS", "positioning reference signal", "PRS measurement", "PRS configuration"],
    "srs": ["SRS", "sounding reference signal", "SRS for positioning"],
    "参考信号": ["PRS", "positioning reference signal", "reference signal", "SRS", "CSI-RS"],
    "csi-rs": ["CSI-RS", "channel state information reference signal", "CSI-RS for positioning"],

    # ── Case 3 ──
    "case3": ["Case 3a", "Case 3b", "Case 3", "gNB-sided", "UE-sided"],

    # ── 提案/方案 ──
    "方案": ["way forward", "solution", "proposal", "approach", "candidate solution"],
    "建议": ["proposal", "suggestion", "recommendation", "way forward", "candidate"],
    "提案": ["proposal", "contribution", "TDoc", "CR", "LS"],
    "创新": ["novel", "innovation", "invention", "new approach", "novel solution"],
    "专利": ["patent", "IPR", "intellectual property", "invention disclosure"],

    # ── LPP/NRPPa/NGAP 协议 ──
    "lpp": ["LPP", "LTE Positioning Protocol", "NRPPa", "positioning protocol"],
    "nrppa": ["NRPPa", "NR Positioning Protocol A", "positioning protocol"],
    "ngap": ["NGAP", "NG Application Protocol", "NG interface"],
    "rrc": ["RRC", "radio resource control", "RRC signaling", "RRC configuration"],

    # ── WG ──
    "ran1": ["RAN1", "RAN1 PHY", "physical layer positioning"],
    "ran2": ["RAN2", "RAN2 protocol", "higher layer protocol"],
    "ran3": ["RAN3", "RAN3 protocol", "higher layer positioning"],
    "sa2": ["SA2", "SA2 architecture", "system architecture"],
    "wg": ["WG", "working group", "RAN1", "RAN2", "RAN3", "SA2"],

    # ── LS ──
    "ls": ["LS", "Liaison Statement", "LS in", "LS out"],
    "联络函": ["LS", "Liaison Statement"],

    # ── OAM/MDT ──
    "oam": ["OAM", "operation and maintenance", "OAM triggered", "network management"],
    "mdt": ["MDT", "minimization of drive tests", "MDT measurement", "logged MDT"],
    "son": ["SON", "self-organizing network", "SON function"],

    # ── 接口/架构 ──
    "接口": ["interface", "NRPPa", "NGAP", "LPP", "RRC", "Xn", "F1"],
    "架构": ["architecture", "network architecture", "system architecture", "functional architecture"],
    "影响": ["impact", "impacts", "affects", "implications"],

    # ── 兼容性/互操作 ──
    "兼容性": ["compatibility", "backward compatible", "forward compatible", "interoperable"],
    "互操作": ["interoperability", "interworking", "compatibility", "coexistence"],
    "前向兼容": ["forward compatibility", "forward compatible", "future proof", "extensible"],
    "后向兼容": ["backward compatibility", "backward compatible", "legacy support"],
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
        # 加载外部配置扩展
        self._extra_terms = _load_extra_terms("fixed_terms.txt")
        self._extra_mappings = _load_extra_mappings("term_map.txt")

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
        """术语映射：中文 → 英文 + 关键词（合并内置 + 外部文件）"""
        lower = query.lower()
        english_set: set[str] = set()
        keyword_set: set[str] = set()

        # 合并内置映射和外部配置文件
        all_mappings = dict(_TERM_MAP)
        all_mappings.update(self._extra_mappings)

        for cn_term, en_list in all_mappings.items():
            if cn_term in lower:
                for en in en_list:
                    english_set.add(en)
                    for part in en.split():
                        if len(part) > 2 and not part.isdigit():
                            keyword_set.add(part)

        # 原始 query 中的英文单词作为关键词
        english_words = re.findall(r"[a-zA-Z][a-zA-Z0-9/+#._-]{2,}", query)
        for w in english_words:
            keyword_set.add(w)

        # 原始 query 中的英文单词也加入 english_terms（避免变体太弱）
        for w in english_words:
            english_set.add(w)

        return sorted(english_set), sorted(keyword_set)

    def _match_fixed_terms(self, query: str, english_terms: list[str]) -> list[str]:
        """匹配 3GPP 固定术语（合并内置 + 外部文件）"""
        matched: set[str] = set()
        lower_q = query.lower()
        lower_terms = " ".join(english_terms).lower()

        all_terms = set(_FIXED_TERMS) | set(self._extra_terms)

        for term in all_terms:
            if term.lower() in lower_q or term.lower() in lower_terms:
                matched.add(term)

        return sorted(matched)

    @staticmethod
    def is_chinese(text: str) -> bool:
        """判断是否包含中文"""
        return bool(re.search(r"[一-鿿]", text))
