from pathlib import Path
from .base import BaseParser, Document


class PDFParser(BaseParser):
    def parse(self, file_path: Path) -> list[Document]:
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber 未安装，请执行: pip install pdfplumber")

        docs = []
        with pdfplumber.open(str(file_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if not text or not text.strip():
                    continue
                docs.append(
                    Document(
                        text=text.strip(),
                        metadata={
                            "source": str(file_path),
                            "file_type": "pdf",
                            "page": page_num,
                        },
                    )
                )
        if not docs:
            return [Document(text="", metadata={"source": str(file_path), "file_type": "pdf", "error": "no_text"})]
        return docs
