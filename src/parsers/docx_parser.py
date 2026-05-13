from pathlib import Path
from .base import BaseParser, Document


class DocxParser(BaseParser):
    def parse(self, file_path: Path) -> list[Document]:
        try:
            from docx import Document as DocxDocument
        except ImportError:
            raise ImportError("python-docx 未安装，请执行: pip install python-docx")

        doc = DocxDocument(str(file_path))

        sections: list[dict] = []
        current_heading = ""
        current_lines: list[str] = []

        for para in doc.paragraphs:
            style = para.style.name if para.style else ""
            text = para.text.strip()
            if not text:
                continue

            if "Heading" in style or "heading" in style:
                if current_lines:
                    sections.append({"heading": current_heading, "text": "\n".join(current_lines)})
                    current_lines = []
                current_heading = text
            else:
                current_lines.append(text)

        if current_lines:
            sections.append({"heading": current_heading, "text": "\n".join(current_lines)})

        if not sections:
            full_text = "\n".join(
                p.text for p in doc.paragraphs if p.text.strip()
            )
            if not full_text.strip():
                return [Document(text="", metadata={"source": str(file_path), "file_type": "docx", "error": "no_text"})]
            return [Document(text=full_text, metadata={"source": str(file_path), "file_type": "docx"})]

        docs = []
        for sec in sections:
            if not sec["text"].strip():
                continue
            docs.append(
                Document(
                    text=sec["text"].strip(),
                    metadata={
                        "source": str(file_path),
                        "file_type": "docx",
                        "heading": sec["heading"] or "",
                    },
                )
            )
        return docs or [Document(text="", metadata={"source": str(file_path), "file_type": "docx"})]
