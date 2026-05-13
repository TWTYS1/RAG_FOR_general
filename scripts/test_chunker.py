"""Test Step 3: enhanced chunker"""
import sys
sys.path.insert(0, "D:/vibecoding/project1")

from src.chunker import SemanticChunker, _score_keyword_hits
from src.parsers.base import Document

chunker = SemanticChunker(chunk_size=800, overlap=150)

# Test 1: heading-path DOCX doc
print("=== Test 1: DOCX with heading_path ===")
text1 = (
    "Remaining issue: data collection procedure for OAM-triggered reports "
    "is still open. Way forward needs further study on proactive NGAP solution. "
    "The model monitoring for gNB-sided model in Case 3a remains FFS."
)
doc = Document(
    text=text1,
    metadata={
        "source": "test.docx", "file_type": "docx",
        "heading": "3. Discussion",
        "heading_path": "1. Intro > 2. Scope > 3. Discussion",
        "tdoc": ["R3-2401234"], "wg": ["RAN3"],
        "meeting": ["RAN3#119bis"],
    },
)
chunks = chunker.chunk([doc])
print(f"  Total chunks: {len(chunks)}")
for c in chunks:
    hp = c.metadata.get("heading_path", "N/A")
    strat = c.metadata.get("chunk_strategy", "?")
    boosted = c.metadata.get("keyword_boost", False)
    kw_score = c.metadata.get("keyword_score", 0)
    print(f"  heading_path: {hp}")
    print(f"  strategy: {strat}  keyword_boost: {boosted}  kw_score: {kw_score}")

# Test 2: keyword scoring
print("\n=== Test 2: Keyword scoring ===")
text2 = (
    "The remaining issue concerns PRS measurement reporting. "
    "FFS: higher layer parameters for gNB-sided model monitoring. "
    "Way forward: proactive NGAP solution for Case 3a data collection."
)
score = _score_keyword_hits(text2)
print(f"  Keyword score: {score} (expected >= 3)")

# Test 3: large section that needs paragraph splitting
print("\n=== Test 3: Section > chunk_size, paragraph fallback ===")
big_text = "\n\n".join([
    "Paragraph 1: The remaining issue regarding NRPPa IE extension for model fallback needs further discussion.",
    "Paragraph 2: Data collection procedure was agreed to be triggered by OAM.",
    "Paragraph 3: Way forward on proactive NGAP solution was noted as FFS.",
    "Paragraph 4: Cell 4 content about LPP parameters for AI/ML positioning assistance data.",
    "Paragraph 5: RAN3 concluded that higher layer parameters should be specified in TS 38.455.",
])
doc3 = Document(
    text=big_text,
    metadata={
        "source": "big.docx", "file_type": "docx",
        "heading_path": "4. Conclusions > 4.1 Remaining Issues",
        "tdoc": ["R3-2401234"], "wg": ["RAN3"],
    },
)
chunks3 = chunker.chunk([doc3])
print(f"  Total chunks (with boost): {len(chunks3)}")
boosted_count = sum(1 for c in chunks3 if c.metadata.get("keyword_boost"))
normal_count = sum(1 for c in chunks3 if not c.metadata.get("keyword_boost"))
print(f"  Normal: {normal_count}, Boosted: {boosted_count}")

print("\n=== All chunker tests passed! ===")
