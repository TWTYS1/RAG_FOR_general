from pathlib import Path
from .base import BaseParser, Document


class TextParser(BaseParser):
    def parse(self, file_path: Path) -> list[Document]:
        text = file_path.read_text(encoding="utf-8")
        if not text.strip():
            return [Document(text="", metadata={"source": str(file_path), "file_type": "txt", "error": "empty"})]
        return [
            Document(
                text=text.strip(),
                metadata={"source": str(file_path), "file_type": "txt"},
            )
        ]
