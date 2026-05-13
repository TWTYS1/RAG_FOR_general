"""DOCX 解析器: 保留 Word heading 结构 + 提取 3GPP 元数据 + 表格"""

import re
from pathlib import Path
from .base import BaseParser, Document, extract_3gpp_metadata


class DocxParser(BaseParser):
    """增强 DOCX 解析器，面向 3GPP 标准文档

    提取:
    - heading path (层级路径, eg: "1. Introduction > 1.1 Scope")
    - TDoc 编号、CR 编号、Spec 编号
    - WG、Meeting、Release、Agenda Item
    - 公司/来源
    - 表格内容
    - 关键词 (remaining issue, way forward, etc.)
    """

    # 在文档前 N 个段落中查找 title/source/company
    _HEADER_SCAN_LINES = 30

    # 3GPP 文档常见的来源/公司行前缀
    _SOURCE_PREFIXES = [
        "source:", "company:", "organization:", "from:",
        "contact:", "rapporteur:", "author:",
    ]

    # Word 中可能表示标题的 style 名称模式
    _HEADING_STYLES = re.compile(
        r"(?:^Heading\s*\d|^heading\s*\d|^TOC|^toc\s*\d"
        r"|^Title$|^Subtitle$)",
        re.IGNORECASE,
    )

    def parse(self, file_path: Path) -> list[Document]:
        try:
            from docx import Document as DocxDocument
        except ImportError:
            raise ImportError("python-docx 未安装，请执行: pip install python-docx")

        doc = DocxDocument(str(file_path))
        filename = file_path.name

        # ── 全局文本（用于 3GPP 元数据扫描）──────────
        all_text_parts: list[str] = []

        # ── 段落解析：保留 heading stack ──────────────
        sections: list[dict] = []
        current_heading = ""
        heading_stack: list[str] = []
        current_lines: list[str] = []
        current_heading_level = 0

        for para in doc.paragraphs:
            style = para.style.name if para.style else ""
            text = para.text.strip()
            if not text:
                continue

            all_text_parts.append(text)

            is_heading = bool(self._HEADING_STYLES.search(style))

            if is_heading:
                # 推断 heading level
                level = self._guess_heading_level(style, text)

                if current_lines:
                    sections.append({
                        "heading": current_heading,
                        "heading_path": " > ".join(heading_stack) if heading_stack else "",
                        "text": "\n".join(current_lines),
                    })
                    current_lines = []

                # 更新 heading stack
                while len(heading_stack) >= level:
                    heading_stack.pop()
                heading_stack.append(text)
                current_heading = text
                current_heading_level = level
            else:
                current_lines.append(text)

        # 尾部残余
        if current_lines:
            sections.append({
                "heading": current_heading,
                "heading_path": " > ".join(heading_stack) if heading_stack else "",
                "text": "\n".join(current_lines),
            })

        # ── 表格提取 ─────────────────────────────────
        table_texts: list[str] = []
        for table in doc.tables:
            rows: list[str] = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    rows.append(" | ".join(cells))
            if rows:
                table_texts.append("\n".join(rows))

        # ── 全量文本 ─────────────────────────────────
        full_text = "\n".join(all_text_parts)
        if not full_text.strip():
            return [Document(
                text="",
                metadata={"source": str(file_path), "file_type": "docx", "error": "no_text"},
            )]

        # ── 3GPP 全局元数据 ─────────────────────────
        global_meta = extract_3gpp_metadata(full_text)

        # 从文档头部提取 title / company / meeting 等
        header_text = "\n".join(all_text_parts[:self._HEADER_SCAN_LINES])
        global_meta["title"] = self._extract_title(header_text)
        global_meta["company"] = self._extract_source(header_text)

        # 从文件名推断
        global_meta["filename"] = filename

        # ── 无 section 的情况（纯文本 DOCX）───────
        if not sections:
            base_meta = {
                "source": str(file_path),
                "file_type": "docx",
                "filename": filename,
                **global_meta,
            }
            docs = [Document(text=full_text, metadata=base_meta)]
            if table_texts:
                docs.append(Document(
                    text="\n\n".join(table_texts),
                    metadata={**base_meta, "section_type": "tables"},
                ))
            return docs

        # ── 组装结果 ─────────────────────────────────
        docs: list[Document] = []
        for sec in sections:
            if not sec["text"].strip():
                continue
            section_meta = extract_3gpp_metadata(sec["text"])
            docs.append(Document(
                text=sec["text"].strip(),
                metadata={
                    "source": str(file_path),
                    "file_type": "docx",
                    "filename": filename,
                    "heading": sec["heading"] or "",
                    "heading_path": sec["heading_path"],
                    **global_meta,
                    **section_meta,
                },
            ))

        # 表格作为独立 section
        if table_texts:
            for i, tbl in enumerate(table_texts):
                tbl_meta = extract_3gpp_metadata(tbl)
                docs.append(Document(
                    text=tbl,
                    metadata={
                        "source": str(file_path),
                        "file_type": "docx",
                        "filename": filename,
                        "section_type": "table",
                        "table_index": i + 1,
                        **global_meta,
                        **tbl_meta,
                    },
                ))

        if not docs:
            return [Document(
                text=full_text,
                metadata={
                    "source": str(file_path),
                    "file_type": "docx",
                    "filename": filename,
                    **global_meta,
                },
            )]

        return docs

    # ── 辅助方法 ───────────────────────────────────

    def _guess_heading_level(self, style: str, text: str) -> int:
        """从 style 名或文本编号推断标题层级"""
        digits = re.findall(r"\d+", style)
        if digits:
            return min(int(digits[0]), 6)

        # 文本模式: "1.", "1.1", "A.", "Annex"
        if re.match(r"^[\dA-Z]\.\s", text):
            return 1
        if re.match(r"^\d+\.\d+\.?\s", text):
            return 2
        if re.match(r"^\d+\.\d+\.\d+\.?\s", text):
            return 3
        if re.match(r"^(?:Annex|Appendix|Annexure)\b", text, re.IGNORECASE):
            return 1
        return 1

    def _extract_title(self, header_text: str) -> str:
        """从文档头部提取标题"""
        lines = header_text.split("\n")
        for line in lines[:10]:
            line = line.strip()
            if not line:
                continue
            # 3GPP TDoc 标题通常较长，不全是数字
            if len(line) > 20 and not line.startswith(("3GPP", "TSG", "Technical")):
                return line[:200]
            if len(line) > 10:
                return line[:200]
        return ""

    def _extract_source(self, header_text: str) -> str:
        """从文档头部提取公司/来源"""
        lines = header_text.split("\n")
        for line in lines[:self._HEADER_SCAN_LINES]:
            lower = line.strip().lower()
            for prefix in self._SOURCE_PREFIXES:
                if lower.startswith(prefix):
                    return line.strip().split(":", 1)[-1].strip()[:200]
        return ""
