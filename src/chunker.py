"""SemanticChunker: 按文件类型选择分块策略 — 段落 / Markdown感知 / DOCX heading-path / 递归回退 / 关键词强化"""

import re
import tiktoken
from .parsers.base import Document, _3GPP_KEYWORDS
from .config import CHUNK_SIZE, CHUNK_OVERLAP, KEYWORD_BOOST_CHUNKS

_ENC = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_ENC.encode(text))


# 3GPP 高优先级关键词 — 命中后生成 boost chunk
_BOOST_KEYWORDS_LOWER = [kw.lower() for kw in _3GPP_KEYWORDS]


def _score_keyword_hits(text: str) -> int:
    """统计文本中 3GPP 关键词的命中次数（加权）"""
    lower = text.lower()
    score = 0
    for kw in _BOOST_KEYWORDS_LOWER:
        score += lower.count(kw) * (3 if "remaining" in kw or "open issue" in kw or "way forward" in kw or "ffs" == kw else 1)
    return score


class SemanticChunker:
    def __init__(self, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._boost_enabled = KEYWORD_BOOST_CHUNKS

    def chunk(self, documents: list[Document]) -> list[Document]:
        chunks: list[Document] = []
        for doc in documents:
            file_type = doc.metadata.get("file_type", "")

            # DOCX 且有 heading_path → 用 heading-path 保留切分
            if file_type == "docx" and doc.metadata.get("heading_path"):
                chunks.extend(self._heading_path_split(doc))
            elif file_type in (".md", "markdown"):
                chunks.extend(self._markdown_split(doc))
            else:
                chunks.extend(self._paragraph_split(doc))

        # ── 关键词强化：为含 3GPP 关键词的 chunk 生成副本 ──
        if self._boost_enabled:
            boost_chunks: list[Document] = []
            for c in chunks:
                kw_score = _score_keyword_hits(c.text)
                if kw_score >= 3:  # 至少命中 3 次
                    boost_meta = dict(c.metadata)
                    boost_meta["keyword_boost"] = True
                    boost_meta["keyword_score"] = kw_score
                    boost_chunks.append(Document(text=c.text, metadata=boost_meta))
            chunks.extend(boost_chunks)

        return chunks

    def _paragraph_split(self, doc: Document) -> list[Document]:
        """按双换行切段，超长段落强制按句子切"""
        text = doc.text
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        chunks: list[Document] = []
        buf: list[str] = []
        buf_tokens = 0

        def flush():
            nonlocal buf, buf_tokens
            if buf:
                chunks.append(self._make_chunk(doc, "\n\n".join(buf)))
            overlap_text = self._extract_overlap(buf, self.overlap)
            buf = [overlap_text] if overlap_text else []
            buf_tokens = _count_tokens(buf[0]) if buf else 0

        for para in paragraphs:
            para_tokens = _count_tokens(para)
            # 单段不超限：正常累积
            if buf_tokens + para_tokens <= self.chunk_size:
                buf.append(para)
                buf_tokens += para_tokens
                continue
            # 单段超限且 buf 非空：先把 buf 输出
            if buf:
                flush()
            # 单段超限：按句子强制切分
            if para_tokens > self.chunk_size:
                sub_chunks = self._force_split(doc, para)
                chunks.extend(sub_chunks)
                # 从最后一个 sub-chunk 提取 overlap 作为新 buf
                if sub_chunks:
                    overlap_text = self._extract_text_overlap(sub_chunks[-1].text, self.overlap)
                    buf = [overlap_text] if overlap_text else []
                    buf_tokens = _count_tokens(buf[0]) if buf else 0
            else:
                buf.append(para)
                buf_tokens = para_tokens

        if buf:
            chunks.append(self._make_chunk(doc, "\n\n".join(buf)))
        return chunks

    def _force_split(self, doc: Document, text: str) -> list[Document]:
        """对超长文本按句子 + token 上限强制切分"""
        sentences = self._split_sentences(text)
        if not sentences:
            return []

        chunks: list[Document] = []
        buf: list[str] = []
        buf_tokens = 0

        for sent in sentences:
            sent_tokens = _count_tokens(sent)
            if buf_tokens + sent_tokens > self.chunk_size and buf:
                chunks.append(self._make_chunk(doc, " ".join(buf)))
                overlap_text = self._extract_text_overlap(" ".join(buf), self.overlap)
                buf = [overlap_text] if overlap_text else []
                buf_tokens = _count_tokens(buf[0]) if buf else 0
            buf.append(sent)
            buf_tokens += sent_tokens

        if buf:
            chunks.append(self._make_chunk(doc, " ".join(buf)))
        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """按句号、问号、感叹号、换行切句子"""
        import re
        parts = re.split(r'(?<=[。！？!?.\n])\s*', text)
        return [p.strip() for p in parts if p.strip()]

    def _extract_overlap(self, buf: list[str], target_tokens: int) -> str:
        if not buf:
            return ""
        collected = []
        tokens = 0
        for para in reversed(buf):
            t = _count_tokens(para)
            if tokens + t > target_tokens:
                break
            collected.append(para)
            tokens += t
        return "\n\n".join(reversed(collected))

    def _extract_text_overlap(self, text: str, target_tokens: int) -> str:
        """从文本末尾提取约 target_tokens 的内容"""
        sentences = self._split_sentences(text)
        if not sentences:
            return ""
        collected = []
        tokens = 0
        for s in reversed(sentences):
            t = _count_tokens(s)
            if tokens + t > target_tokens:
                break
            collected.append(s)
            tokens += t
        return " ".join(reversed(collected))

    # ── DOCX heading-path 感知分割 ────────────────────

    def _heading_path_split(self, doc: Document) -> list[Document]:
        """按 section heading_path 优先切分，保留层级上下文"""
        text = doc.text
        heading_path = doc.metadata.get("heading_path", "")
        heading = doc.metadata.get("heading", "")

        # 小 section 直接作为一个 chunk
        if _count_tokens(text) <= self.chunk_size:
            meta = dict(doc.metadata)
            meta["chunk_strategy"] = "heading-path"
            return [Document(text=text, metadata=meta)]

        # 大 section → 尝试段落分割，但注入 heading_path 到每个子 chunk
        sub_chunks = self._paragraph_split(doc)
        for c in sub_chunks:
            c.metadata["heading_path"] = heading_path
            c.metadata["heading"] = heading
            c.metadata["chunk_strategy"] = "heading-path+paragraph"
            for k in ("tdoc", "cr", "spec", "wg", "meeting", "company",
                       "title", "keywords", "agenda_item", "rel", "ls"):
                if k in doc.metadata and k not in c.metadata:
                    c.metadata[k] = doc.metadata[k]
        return sub_chunks

    # ── Markdown 感知分割 ──────────────────────────────

    _MD_HEADER_RE = re.compile(r"^(#{1,6}\s.*)$", re.MULTILINE)

    def _markdown_split(self, doc: Document) -> list[Document]:
        """按 Markdown 标题切分，每节内部做段落 token 限制"""
        text = doc.text
        # 找出所有标题位置
        header_matches = list(self._MD_HEADER_RE.finditer(text))
        if not header_matches:
            # 没有标题 → 回退段落分割
            return self._paragraph_split(doc)

        sections: list[str] = []
        for i, m in enumerate(header_matches):
            start = m.start()
            end = header_matches[i + 1].start() if i + 1 < len(header_matches) else len(text)
            sections.append(text[start:end].strip())

        # 标题之前的导言部分也保留
        if header_matches and header_matches[0].start() > 0:
            preamble = text[:header_matches[0].start()].strip()
            if preamble:
                sections.insert(0, preamble)

        chunks: list[Document] = []
        buf: list[str] = []
        buf_tokens = 0

        def flush():
            nonlocal buf, buf_tokens
            if buf:
                chunks.append(self._make_chunk(doc, "\n\n".join(buf)))
            overlap_text = self._extract_overlap(buf, self.overlap)
            buf = [overlap_text] if overlap_text else []
            buf_tokens = _count_tokens(buf[0]) if buf else 0

        for section in sections:
            sec_tokens = _count_tokens(section)
            if buf_tokens + sec_tokens <= self.chunk_size:
                buf.append(section)
                buf_tokens += sec_tokens
            else:
                if buf:
                    flush()
                if sec_tokens > self.chunk_size:
                    # 单节超限 → 递归段落分割该节
                    sub_doc = Document(text=section, metadata=dict(doc.metadata))
                    sub_chunks = self._paragraph_split(sub_doc)
                    chunks.extend(sub_chunks)
                    if sub_chunks:
                        overlap_text = self._extract_text_overlap(sub_chunks[-1].text, self.overlap)
                        buf = [overlap_text] if overlap_text else []
                        buf_tokens = _count_tokens(buf[0]) if buf else 0
                else:
                    buf.append(section)
                    buf_tokens = sec_tokens

        if buf:
            chunks.append(self._make_chunk(doc, "\n\n".join(buf)))
        return chunks

    # ── 递归字符分割（通用回退）──────────────────────

    _RECURSIVE_SEPARATORS = ["\n\n", "\n", "。", ". ", "! ", "? ", "；", ";", ", ", " "]

    def _recursive_split(self, doc: Document) -> list[Document]:
        """递归按分隔符优先级切分，最终按字符硬切"""
        return self._recursive_split_text(doc, doc.text, self._RECURSIVE_SEPARATORS)

    def _recursive_split_text(self, doc: Document, text: str, separators: list[str]) -> list[Document]:
        if _count_tokens(text) <= self.chunk_size:
            return [self._make_chunk(doc, text)] if text.strip() else []

        if not separators:
            # 最后手段：按 chunk_size token 硬切
            return self._hard_split(doc, text)

        sep = separators[0]
        rest = separators[1:]
        parts = text.split(sep)

        chunks: list[Document] = []
        buf: list[str] = []
        buf_tokens = 0

        for part in parts:
            part_tokens = _count_tokens(part)
            if buf_tokens + part_tokens <= self.chunk_size:
                buf.append(part)
                buf_tokens += part_tokens
            else:
                if buf:
                    merged = sep.join(buf)
                    if _count_tokens(merged) <= self.chunk_size:
                        chunks.append(self._make_chunk(doc, merged))
                    else:
                        chunks.extend(self._recursive_split_text(doc, merged, rest))
                # 处理当前 part
                if part_tokens > self.chunk_size:
                    chunks.extend(self._recursive_split_text(doc, part, rest))
                else:
                    buf = [part]
                    buf_tokens = part_tokens

        if buf:
            merged = sep.join(buf)
            if _count_tokens(merged) <= self.chunk_size:
                chunks.append(self._make_chunk(doc, merged))
            else:
                chunks.extend(self._recursive_split_text(doc, merged, rest))

        return chunks

    def _hard_split(self, doc: Document, text: str) -> list[Document]:
        """按 chunk_size token 硬切，带 overlap"""
        tokens = _ENC.encode(text)
        chunks: list[Document] = []
        step = max(1, self.chunk_size - self.overlap)
        i = 0
        while i < len(tokens):
            chunk_tokens = tokens[i:i + self.chunk_size]
            chunk_text = _ENC.decode(chunk_tokens)
            chunks.append(self._make_chunk(doc, chunk_text))
            i += step
        return chunks

    def _make_chunk(self, doc: Document, text: str) -> Document:
        return Document(text=text, metadata=dict(doc.metadata))
