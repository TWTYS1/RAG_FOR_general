from pathlib import Path
from .base import BaseParser, Document


class HTMLParser(BaseParser):
    def parse(self, file_path: Path) -> list[Document]:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("beautifulsoup4 未安装，请执行: pip install beautifulsoup4 lxml")

        html = file_path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)

        if not cleaned:
            return [Document(text="", metadata={"source": str(file_path), "file_type": "html", "error": "no_text"})]

        return [
            Document(
                text=cleaned,
                metadata={"source": str(file_path), "file_type": "html"},
            )
        ]
