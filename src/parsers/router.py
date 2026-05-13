"""FileTypeRouter: 根据扩展名路由到对应解析器"""

import mimetypes
from pathlib import Path
from .base import BaseParser, Document
from .markdown_parser import MarkdownParser
from .pdf_parser import PDFParser
from .text_parser import TextParser
from .docx_parser import DocxParser
from .html_parser import HTMLParser

_PARSER_MAP = {
    ".md": MarkdownParser,
    ".pdf": PDFParser,
    ".txt": TextParser,
    ".docx": DocxParser,
    ".html": HTMLParser,
    ".htm": HTMLParser,
}


class FileTypeRouter:
    def __init__(self, parser_map: dict[str, type[BaseParser]] | None = None):
        self._map = parser_map or _PARSER_MAP
        self._instances: dict[str, BaseParser] = {}

    def _get_parser(self, extension: str) -> BaseParser | None:
        ext = extension.lower()
        if ext not in self._map:
            return None
        if ext not in self._instances:
            self._instances[ext] = self._map[ext]()
        return self._instances[ext]

    def _detect_type(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()
        if ext in self._map:
            return ext
        mime, _ = mimetypes.guess_type(str(file_path))
        if mime:
            if "pdf" in mime:
                return ".pdf"
            if "html" in mime:
                return ".html"
        return ext

    def parse(self, file_path: Path) -> list[Document]:
        ext = self._detect_type(file_path)
        parser = self._get_parser(ext)
        if parser is None:
            raise ValueError(f"不支持的文件格式: {ext} ({file_path})")
        return parser.parse(file_path)

    @property
    def supported_extensions(self) -> set[str]:
        return set(self._map.keys())
