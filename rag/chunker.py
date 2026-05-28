# rag/chunker.py

import re
import hashlib
from langchain.text_splitter import RecursiveCharacterTextSplitter


# ─────────────────────────────────────────────────────────────
# CHUNKING CONFIGURATION
# These numbers are tuned for research papers specifically.
# ─────────────────────────────────────────────────────────────

CHUNK_SIZE     = 1000   # characters per chunk (~200 words)
CHUNK_OVERLAP  = 200    # overlap between consecutive chunks
MIN_CHUNK_SIZE = 100    # discard chunks smaller than this


def generate_chunk_id(paper_name: str, page_number: int, chunk_index: int) -> str:
    """
    Generate a unique, reproducible ID for each chunk.
    Format: paperName_p3_c2 (page 3, chunk 2)

    Also creates a short hash to guarantee uniqueness
    even if paper names are similar.
    """
    raw = f"{paper_name}_{page_number}_{chunk_index}"
    short_hash = hashlib.md5(raw.encode()).hexdigest()[:6]
    return f"{paper_name}_p{page_number}_c{chunk_index}_{short_hash}"


def clean_chunk_text(text: str) -> str:
    """
    Final cleaning pass on a chunk before storing.
    - Collapse whitespace
    - Remove orphaned punctuation lines
    - Strip
    """
    # Collapse multiple spaces/tabs
    text = re.sub(r'[ \t]+', ' ', text)

    # Collapse 3+ newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove lines that are only punctuation/symbols
    text = re.sub(r'^\s*[^a-zA-Z0-9\s]{1,3}\s*$', '', text, flags=re.MULTILINE)

    return text.strip()


def chunk_pages(pages_data: list[dict]) -> list[dict]:
    """
    Take the list of page dicts from pdf_loader and split each page
    into overlapping chunks. Each chunk gets full metadata inherited
    from its parent page.

    Args:
        pages_data: Output from load_all_pdfs() — list of page dicts

    Returns:
        List of chunk dicts. Each looks like:
        {
            "chunk_id"    : "bert_paper_p3_c2_a1b2c3",
            "paper_name"  : "bert_paper",
            "page_number" : 3,
            "section"     : "Methodology",
            "text"        : "The encoder maps an input...",
            "char_count"  : 487,
            "chunk_index" : 2,       ← which chunk within this page
            "total_chunks_in_page": 4
        }
    """

    # LangChain's splitter — works on plain text
    # separators = try splitting on paragraph, then sentence, then word
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    all_chunks = []
    total_pages = len(pages_data)

    print(f"\n✂️  Chunking {total_pages} pages...")

    for page in pages_data:
        page_text = page["text"]

        # Skip very short pages
        if len(page_text) < MIN_CHUNK_SIZE:
            continue

        # Split this page's text into chunks
        raw_chunks = splitter.split_text(page_text)

        # Filter out tiny chunks (noise)
        raw_chunks = [c for c in raw_chunks if len(c.strip()) >= MIN_CHUNK_SIZE]

        total_in_page = len(raw_chunks)

        for i, chunk_text in enumerate(raw_chunks):
            cleaned = clean_chunk_text(chunk_text)

            if len(cleaned) < MIN_CHUNK_SIZE:
                continue

            chunk_dict = {
                # ── Identity ──────────────────────────────
                "chunk_id"   : generate_chunk_id(
                                    page["paper_name"],
                                    page["page_number"],
                                    i
                                ),

                # ── Source metadata (for citations) ───────
                "paper_name" : page["paper_name"],
                "page_number": page["page_number"],
                "section"    : page["section"],

                # ── Content ───────────────────────────────
                "text"       : cleaned,
                "char_count" : len(cleaned),

                # ── Position info ─────────────────────────
                "chunk_index"          : i,
                "total_chunks_in_page" : total_in_page,
            }

            all_chunks.append(chunk_dict)

    print(f"✅ Created {len(all_chunks)} chunks from {total_pages} pages")
    print_chunk_summary(all_chunks)

    return all_chunks


def chunk_single_paper(pages_data: list[dict], paper_name: str) -> list[dict]:
    """
    Chunk only pages belonging to a specific paper.
    Used when user uploads a NEW paper and we need to
    add it to an existing vector store without re-processing everything.

    Args:
        pages_data : All pages (from load_all_pdfs)
        paper_name : Filter to this paper only

    Returns:
        Chunks for that one paper only
    """
    filtered = [p for p in pages_data if p["paper_name"] == paper_name]

    if not filtered:
        raise ValueError(f"No pages found for paper: {paper_name}")

    print(f"\n✂️  Chunking single paper: {paper_name} ({len(filtered)} pages)")
    return chunk_pages(filtered)


def filter_chunks_by_section(
    chunks: list[dict],
    section: str
) -> list[dict]:
    """
    Return only chunks belonging to a specific section.

    Example:
        filter_chunks_by_section(chunks, "Methodology")
        → Only chunks from Methodology sections across all papers
    """
    filtered = [c for c in chunks if c["section"].lower() == section.lower()]
    return filtered


def filter_chunks_by_paper(
    chunks: list[dict],
    paper_name: str
) -> list[dict]:
    """
    Return only chunks from a specific paper.
    """
    return [c for c in chunks if c["paper_name"] == paper_name]


def filter_chunks_by_paper_and_section(
    chunks: list[dict],
    paper_name: str,
    section: str
) -> list[dict]:
    """
    Return chunks from a specific paper AND section.

    Example:
        "Explain the methodology of paper 2"
        → filter by paper_name='bert_paper' AND section='Methodology'
    """
    return [
        c for c in chunks
        if c["paper_name"] == paper_name
        and c["section"].lower() == section.lower()
    ]


def get_all_sections(chunks: list[dict]) -> list[str]:
    """Return sorted list of unique section names across all chunks."""
    return sorted(set(c["section"] for c in chunks))


def get_all_papers(chunks: list[dict]) -> list[str]:
    """Return sorted list of unique paper names across all chunks."""
    return sorted(set(c["paper_name"] for c in chunks))


def print_chunk_summary(chunks: list[dict]):
    """
    Print a breakdown of chunk counts by paper and section.
    Helps verify chunking quality.
    """
    print("\n📊 Chunk Distribution:")
    print("-" * 55)

    # Group by paper
    by_paper = {}
    for chunk in chunks:
        p = chunk["paper_name"]
        s = chunk["section"]
        if p not in by_paper:
            by_paper[p] = {}
        by_paper[p][s] = by_paper[p].get(s, 0) + 1

    total = 0
    for paper, sections in by_paper.items():
        paper_total = sum(sections.values())
        total += paper_total
        print(f"\n  📄 {paper}  ({paper_total} chunks)")
        for section, count in sorted(sections.items()):
            bar = "█" * min(count, 25)
            print(f"     {section:<22} {bar} ({count})")

    print(f"\n  TOTAL CHUNKS: {total}")
    print("-" * 55)