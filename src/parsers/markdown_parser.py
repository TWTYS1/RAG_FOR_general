from pathlib import Path
from markdown_it import MarkdownIt
from .base import BaseParser, Document


class MarkdownParser(BaseParser):
    def parse(self, file_path: Path) -> list[Document]:
        text = file_path.read_text(encoding="utf-8")
        md = MarkdownIt()
        tokens = md.parse(text)

        sections: list[dict] = []
        current_heading = ""
        current_lines: list[str] = []
        in_heading = False
        heading_level = 0

        for token in tokens:
            if token.type == "heading_open":
                if current_lines:
                    sections.append({"heading": current_heading, "text": "\n".join(current_lines)})
                heading_level = int(token.tag[1])
                in_heading = True
                current_lines = []
            elif token.type == "heading_close":
                in_heading = False
            elif token.type == "inline":
                if in_heading:
                    current_heading = f"H{heading_level}: {token.content}"
                else:
                    current_lines.append(token.content)
            elif token.type == "fence":
                current_lines.append(token.content)
            elif token.type in (
                "paragraph_open", "paragraph_close",
                "bullet_list_open", "bullet_list_close",
                "ordered_list_open", "ordered_list_close",
                "list_item_open", "list_item_close",
                "blockquote_open", "blockquote_close",
                "table_open", "table_close",
                "thead_open", "thead_close", "tbody_open", "tbody_close",
                "tr_open", "tr_close", "th_open", "th_close", "td_open", "td_close",
            ):
                pass

        if current_lines:
            sections.append({"heading": current_heading, "text": "\n".join(current_lines)})

        if not sections:
            return [Document(text=text.strip(), metadata={"source": str(file_path), "file_type": "md"})]

        docs = []
        for sec in sections:
            if not sec["text"].strip():
                continue
            docs.append(
                Document(
                    text=sec["text"].strip(),
                    metadata={
                        "source": str(file_path),
                        "file_type": "md",
                        "heading": sec["heading"] or "",
                    },
                )
            )
        return docs or [Document(text=text.strip(), metadata={"source": str(file_path), "file_type": "md"})]
