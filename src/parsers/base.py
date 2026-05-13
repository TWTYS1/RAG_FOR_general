"""Document 数据结构 + BaseParser 抽象基类"""

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path


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
