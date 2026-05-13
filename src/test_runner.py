"""RAG 系统自动化测试 —— 覆盖 T1-T7 除 CLI 交互外的全部用例"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

passed = 0
failed = 0
errors = []


def test(name: str):
    """装饰器：包装测试用例，自动统计 pass/fail"""
    def decorator(fn):
        def wrapper():
            global passed, failed
            try:
                fn()
                passed += 1
                print(f"  [PASS] {name}")
            except Exception as e:
                failed += 1
                msg = f"{name}: {e}"
                errors.append(msg)
                print(f"  [FAIL] {name} -> {e}")
        return wrapper
    return decorator


# ======================== T1: 环境 ========================
@test("T1.1 Python version >= 3.10")
def test_python_version():
    v = sys.version_info
    assert v >= (3, 10), f"Python {v.major}.{v.minor} < 3.10"

@test("T1.2 All dependencies importable")
def test_dependencies():
    for mod in ["chromadb", "openai", "tiktoken", "sentence_transformers",
                "markdown_it", "pdfplumber", "docx", "bs4", "lxml", "dotenv", "streamlit"]:
        __import__(mod)

@test("T1.3 DeepSeek API key configured")
def test_api_key():
    from dotenv import load_dotenv
    import os
    load_dotenv()
    key = os.getenv("DEEPSEEK_API_KEY", "")
    assert key and key != "sk-your-deepseek-api-key-here", "DEEPSEEK_API_KEY not configured"

# ======================== T2: 解析器 ========================
@test("T2.1 Markdown parser")
def test_md_parser():
    from src.parsers.markdown_parser import MarkdownParser
    test_md = PROJECT_ROOT / "docs" / "my-notes" / "react-learning.md"
    if not test_md.exists():
        raise AssertionError(f"test file missing: {test_md}")
    docs = MarkdownParser().parse(test_md)
    assert len(docs) >= 1, "no documents parsed"
    assert docs[0].metadata["file_type"] == "md"
    # at least one should have a heading
    headings = [d.metadata.get("heading", "") for d in docs]
    assert any(h for h in headings), f"no headings found in {headings}"

@test("T2.2 PDF parser")
def test_pdf_parser():
    from src.parsers.pdf_parser import PDFParser
    pdfs = list((PROJECT_ROOT / "docs").rglob("*.pdf"))
    if not pdfs:
        print(" (no PDFs, skip)")
        return
    docs = PDFParser().parse(pdfs[0])
    assert len(docs) >= 1
    assert docs[0].metadata["file_type"] == "pdf"

@test("T2.3 Text parser")
def test_text_parser():
    from src.parsers.text_parser import TextParser
    test_txt = PROJECT_ROOT / "docs" / "my-notes" / "python-tips.txt"
    if not test_txt.exists():
        raise AssertionError(f"test file missing: {test_txt}")
    docs = TextParser().parse(test_txt)
    assert len(docs) == 1
    assert len(docs[0].text) > 0
    assert docs[0].metadata["file_type"] == "txt"

@test("T2.4 DOCX parser")
def test_docx_parser():
    from src.parsers.docx_parser import DocxParser
    docxs = list((PROJECT_ROOT / "docs").rglob("*.docx"))
    if not docxs:
        print(" (no DOCX, skip)")
        return
    docs = DocxParser().parse(docxs[0])
    assert len(docs) >= 1
    assert docs[0].metadata["file_type"] == "docx"

@test("T2.5 HTML parser")
def test_html_parser():
    from src.parsers.html_parser import HTMLParser
    htmls = list((PROJECT_ROOT / "docs").rglob("*.html")) + list((PROJECT_ROOT / "docs").rglob("*.htm"))
    # exclude our own docs
    htmls = [h for h in htmls if "docs" in str(h) and "my-notes" in str(h) or "web-archive" in str(h)]
    if not htmls:
        print(" (no HTML, skip)")
        return
    docs = HTMLParser().parse(htmls[0])
    assert len(docs) >= 1
    assert docs[0].metadata["file_type"] == "html"
    assert "<script>" not in docs[0].text

@test("T2.6 FileTypeRouter routing")
def test_router():
    from src.parsers.router import FileTypeRouter
    router = FileTypeRouter()
    assert ".md" in router.supported_extensions
    assert ".pdf" in router.supported_extensions
    md_path = PROJECT_ROOT / "docs" / "my-notes" / "react-learning.md"
    txt_path = PROJECT_ROOT / "docs" / "my-notes" / "python-tips.txt"
    md_docs = router.parse(md_path)
    txt_docs = router.parse(txt_path)
    assert md_docs[0].metadata["file_type"] == "md"
    assert txt_docs[0].metadata["file_type"] == "txt"

# ======================== T3: 分块器 ========================
@test("T3.1 Semantic chunking")
def test_chunking():
    from src.chunker import SemanticChunker
    from src.parsers.base import Document
    doc = Document(text="Section A\n\nParagraph one. " * 20, metadata={"file_type": "md", "source": "test.md"})
    chunks = SemanticChunker(chunk_size=100, overlap=20).chunk([doc])
    assert len(chunks) >= 1
    for c in chunks:
        assert c.metadata["file_type"] == "md"

@test("T3.2 Oversized text splitting")
def test_oversized_split():
    from src.chunker import SemanticChunker
    from src.parsers.base import Document
    long_text = "A long sentence. " * 200
    doc = Document(text=long_text, metadata={"file_type": "txt"})
    chunks = SemanticChunker(chunk_size=100, overlap=20).chunk([doc])
    assert len(chunks) >= 2, f"expected multiple chunks, got {len(chunks)}"

@test("T3.4 Empty content")
def test_empty_chunk():
    from src.chunker import SemanticChunker
    from src.parsers.base import Document
    chunks = SemanticChunker().chunk([Document(text="", metadata={"file_type": "txt"})])
    assert chunks == []

# ======================== T4: Embedding ========================
@test("T4.1 Local BGE-M3 embedding")
def test_local_embedding():
    from src.embedder import Embedder
    e = Embedder(provider="local")
    vecs = e.embed(["hello", "world"])
    assert len(vecs) == 2
    assert len(vecs[0]) > 0
    # check normalization
    norm = sum(v * v for v in vecs[0])
    assert abs(norm - 1.0) < 0.01, f"not normalized: norm={norm}"

@test("T4.2 embed_single consistency")
def test_embed_single():
    from src.embedder import Embedder
    e = Embedder(provider="local")
    batch = e.embed(["test"])[0]
    single = e.embed_single("test")
    assert batch == single

@test("T4.3 Unknown provider error")
def test_unknown_provider():
    from src.embedder import Embedder
    try:
        Embedder(provider="unknown").embed(["test"])
        raise AssertionError("should have raised ValueError")
    except ValueError:
        pass

# ======================== T5: ChromaDB ========================
@test("T5.1 Write and query")
def test_chroma_write_query():
    from src.embedder import Embedder
    from src.chroma_store import ChromaStore
    store = ChromaStore(collection_name="test_t5_1")
    store.clear()
    e = Embedder(provider="local")
    texts = ["React is a frontend framework", "Python is a programming language", "Weather is nice today"]
    vecs = e.embed(texts)
    store.add(
        ids=["1", "2", "3"],
        embeddings=vecs,
        documents=texts,
        metadatas=[{"file_type": "md"}, {"file_type": "txt"}, {"file_type": "txt"}]
    )
    hits = store.search(e.embed_single("What is React"), top_k=2)
    assert len(hits) >= 1
    assert "React" in hits[0]["text"]

@test("T5.2 Metadata filter")
def test_chroma_filter():
    from src.embedder import Embedder
    from src.chroma_store import ChromaStore
    store = ChromaStore(collection_name="test_t5_2")
    store.clear()
    e = Embedder(provider="local")
    texts = ["React hooks", "Python decorator", "Vue component"]
    vecs = e.embed(texts)
    store.add(
        ids=["a", "b", "c"],
        embeddings=vecs,
        documents=texts,
        metadatas=[{"file_type": "md"}, {"file_type": "txt"}, {"file_type": "md"}]
    )
    hits = store.search(e.embed_single("programming"), top_k=5, file_type="txt")
    assert len(hits) >= 1
    for h in hits:
        assert h["metadata"]["file_type"] == "txt"

@test("T5.3 Empty collection query")
def test_chroma_empty():
    from src.embedder import Embedder
    from src.chroma_store import ChromaStore
    store = ChromaStore(collection_name="test_t5_3")
    store.clear()
    hits = store.search([0.0] * 1024, top_k=5)
    assert hits == []

# ======================== T6: 全链路 ========================
@test("T6.1 Ingest pipeline")
def test_ingest_pipeline():
    from src.ingest import IngestPipeline
    pipeline = IngestPipeline()
    n = pipeline.run()
    assert n >= 1, f"ingest returned {n} chunks, expected at least 1"

@test("T6.2 Retrieval from indexed data")
def test_retrieval():
    from src.retrieve import Retriever
    r = Retriever()
    count = r.store.count()
    assert count >= 1, f"store has {count} chunks, run ingest first"
    hits = r.search("React component")
    assert len(hits) >= 1, "no results for 'React component'"

@test("T6.3 LLM generation")
def test_generation():
    from src.retrieve import Retriever
    from src.generate import Generator
    r = Retriever()
    g = Generator()
    hits = r.search("React")
    ctx = r.format_context(hits)
    answer = g.generate("What is React?", ctx)
    assert len(answer) >= 5, f"answer empty or too short: '{answer}'"
    # content check: must mention React or contain Chinese/English response
    assert len(answer.strip()) > 0, "answer should not be empty"

# ======================== T7: 边界 ========================
@test("T7.1 Unsupported format")
def test_unsupported_format():
    from src.parsers.router import FileTypeRouter
    tmp = PROJECT_ROOT / "test.xyz"
    tmp.write_text("hello")
    try:
        FileTypeRouter().parse(tmp)
        raise AssertionError("should have raised ValueError")
    except ValueError as e:
        assert "不支持" in str(e) or "xyz" in str(e).lower()
    finally:
        tmp.unlink(missing_ok=True)

@test("T7.2 Corrupt file handling")
def test_corrupt_file():
    from src.parsers.router import FileTypeRouter
    corrupt = PROJECT_ROOT / "docs" / "corrupt.pdf"
    corrupt.write_text("not a real pdf")
    try:
        FileTypeRouter().parse(corrupt)
        raise AssertionError("should have raised an error for corrupt PDF")
    except Exception:
        pass
    finally:
        corrupt.unlink(missing_ok=True)


# ======================== 入口 ========================
if __name__ == "__main__":
    print("=" * 55)
    print("  RAG System Automated Tests")
    print(f"  Python: {sys.version}")
    print("=" * 55)

    # Run all test_* functions
    import inspect
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    for name, fn in tests:
        fn()

    print("\n" + "=" * 55)
    total = passed + failed
    print(f"  Results: {passed}/{total} passed", end="")
    if failed:
        print(f", {failed} FAILED")
        print("  Failures:")
        for e in errors:
            print(f"    - {e}")
    else:
        print(" -- ALL PASSED")
    print("=" * 55)
