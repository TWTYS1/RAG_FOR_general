"""Document 数据结构 + BaseParser 抽象基类"""

import re
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path

# ── 3GPP 元数据提取正则 ──────────────────────────────

_3GPP_PATTERNS = {
    "tdoc": re.compile(
        r"\b(R[1-8]-\d{5,7})\b", re.IGNORECASE
    ),
    "cr": re.compile(
        r"\b(CR\s*\d{4,6}(?:[-/]\w+\d*)?(?:\s*[Rr]ev\s*\d+)?)\b"
    ),
    "spec": re.compile(
        r"\b(TS\s*\d{2,3}\.\d{3,4}(?:\s*[Vv]\d+\.\d+\.\d+)?)\b|"
        r"\b(TR\s*\d{2,3}\.\d{3,4}(?:\s*[Vv]\d+\.\d+\.\d+)?)\b"
    ),
    "wg": re.compile(
        r"\b(RAN[1-4]|SA[1-6]|CT[1-6])\b", re.IGNORECASE
    ),
    "meeting": re.compile(
        r"\b((?:RAN[1-4]|SA[1-6]|CT[1-6])\s*#\d{2,4}\w*)\b", re.IGNORECASE
    ),
    "rel": re.compile(
        r"\b(Rel(?:ease)?[-\s]*(?:1[5-9]|2\d))\b", re.IGNORECASE
    ),
    "agenda_item": re.compile(
        r"\b(?:agenda\s*item|AI)\s*[:\-]?\s*(\d[\d\.]+\w*)\b", re.IGNORECASE
    ),
    "ls": re.compile(
        r"\b(LS\s*(?:[iI][nN]|OUT)?\s*(?:to|from)?\s*(?:[A-Z]+\d*)?)\b"
    ),
}

_3GPP_KEYWORDS = [
    "remaining issue", "open issue", "FFS", "for further study",
    "not agreed", "way forward", "conclusion", "agreement",
    "pending", "to be discussed", "candidate", "alternative",
    "model monitoring", "data collection", "Case 3a", "Case 3b",
    "gNB-sided model", "gNB-side model", "UE-sided model",
    "AI/ML assisted positioning", "AI/ML positioning",
    "higher layer parameter", "RRC parameter", "LPP parameter",
    "NRPPa", "NGAP", "OAM", "proactive", "fallback",
    "PRS measurement", "positioning measurement",
    "Sidelink positioning", "SL positioning",
]


def extract_3gpp_metadata(text: str) -> dict:
    """从文本中提取 3GPP 结构化元数据"""
    meta = {}
    for field, pattern in _3GPP_PATTERNS.items():
        found: set[str] = set()
        for m in pattern.finditer(text):
            # 支持多捕获组：取第一个非空 group
            g = next((g for g in m.groups() if g is not None), None)
            if g:
                found.add(g)
        if found:
            meta[field] = sorted(found)[:10]
    # 关键词命中
    found_kw = sorted(set(kw for kw in _3GPP_KEYWORDS if kw.lower() in text.lower()))
    if found_kw:
        meta["keywords"] = found_kw[:20]
    return meta


@dataclass
class Document:
    """解析后的文档片段"""
    text: str
    metadata: dict = field(default_factory=dict)


class BaseParser(ABC):
    """解析器基类 —— 策略模式统一接口"""

    @abstractmethod
    def parse(self, file_path: Path) -> list[Document]:
        """解析文件，返回 Document 列表"""
        ...
