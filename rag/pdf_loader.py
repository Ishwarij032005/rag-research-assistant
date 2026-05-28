# rag/pdf_loader.py

import os
import re
import pdfplumber
from pathlib import Path


# ─────────────────────────────────────────────
# SECTION KEYWORDS
# We'll scan each page's text for these headers
# to detect which section we're in.
# ─────────────────────────────────────────────
SECTION_PATTERNS = [
    (r'\babstract\b',                  'Abstract'),
    (r'\b1[\.\s]+introduction\b',      'Introduction'),
    (r'\bintroduction\b',              'Introduction'),
    (r'\b2[\.\s]+related\s+work\b',    'Related Work'),
    (r'\brelated\s+work\b',            'Related Work'),
    (r'\bliterature\s+review\b',       'Related Work'),
    (r'\b\d[\.\s]+methodology\b',      'Methodology'),
    (r'\bmethodology\b',               'Methodology'),
    (r'\bproposed\s+method\b',         'Methodology'),
    (r'\bapproach\b',                  'Methodology'),
    (r'\b\d[\.\s]+experiment\b',       'Experiments'),
    (r'\bexperiments?\b',              'Experiments'),
    (r'\bevaluation\b',                'Experiments'),
    (r'\bimplementation\b',            'Experiments'),
    (r'\b\d[\.\s]+result\b',           'Results'),
    (r'\bresults?\b',                   'Results'),
    (r'\bperformance\b',               'Results'),
    (r'\b\d[\.\s]+discussion\b',       'Discussion'),
    (r'\bdiscussion\b',                'Discussion'),
    (r'\banalysis\b',                  'Discussion'),
    (r'\b\d[\.\s]+conclusion\b',       'Conclusion'),
    (r'\bconclusion\b',                'Conclusion'),
    (r'\bfuture\s+work\b',             'Conclusion'),
    (r'\breferences?\b',               'References'),
    (r'\bbibliography\b',              'References'),
]


def detect_section(text: str, current_section: str) -> str:
    """
    Given a block of text and the current running section,
    return the new section if a header is found, else keep current.

    We only look at the FIRST 300 characters of a page —
    section headers almost always appear at the top.
    """
    # Look at top of page only (headers live here)
    snippet = text[:300].lower()

    for pattern, section_name in SECTION_PATTERNS:
        if re.search(pattern, snippet, re.IGNORECASE):
            return section_name

    # No new section found → stay in current section
    return current_section


def clean_text(text: str) -> str:
    """
    Clean raw PDF text:
    - Remove excessive whitespace
    - Remove page numbers standing alone
    - Remove weird unicode artifacts
    """
    if not text:
        return ""

    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Replace multiple spaces with single space
    text = re.sub(r'[ \t]+', ' ', text)

    # Remove lines that are ONLY a number (page numbers)
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def load_pdf(pdf_path: str) -> list[dict]:
    """
    Load a single PDF and return a list of page dictionaries.

    Each dictionary looks like:
    {
        "paper_name": "attention_is_all_you_need",
        "page_number": 3,
        "section": "Methodology",
        "text": "The encoder maps an input sequence...",
        "char_count": 842
    }

    Args:
        pdf_path: Full path to the PDF file

    Returns:
        List of page dicts with metadata
    """
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if not path.suffix.lower() == '.pdf':
        raise ValueError(f"Not a PDF file: {pdf_path}")

    # Paper name = filename without extension
    # e.g., "attention_is_all_you_need.pdf" → "attention_is_all_you_need"
    paper_name = path.stem

    pages_data = []
    current_section = "Unknown"  # Running tracker of current section

    print(f"  📄 Loading: {paper_name}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"     Total pages: {total_pages}")

            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract raw text from this page
                raw_text = page.extract_text()

                if not raw_text:
                    # Some pages are images / scanned — skip them
                    print(f"     ⚠️  Page {page_num}: No text extracted (image-only page?)")
                    continue

                # Clean the text
                cleaned = clean_text(raw_text)

                if len(cleaned) < 50:
                    # Less than 50 chars = probably a blank/header page
                    continue

                # Detect if this page starts a new section
                current_section = detect_section(cleaned, current_section)

                # Build the page record
                page_data = {
                    "paper_name": paper_name,
                    "page_number": page_num,
                    "section": current_section,
                    "text": cleaned,
                    "char_count": len(cleaned)
                }

                pages_data.append(page_data)

        print(f"     ✅ Extracted {len(pages_data)} pages")

    except Exception as e:
        print(f"     ❌ Error loading {paper_name}: {str(e)}")
        raise

    return pages_data


def load_all_pdfs(papers_dir: str) -> list[dict]:
    """
    Load ALL PDFs from a directory.

    Args:
        papers_dir: Path to folder containing PDFs

    Returns:
        Combined list of all page dicts from all papers
    """
    papers_path = Path(papers_dir)

    if not papers_path.exists():
        raise FileNotFoundError(f"Papers directory not found: {papers_dir}")

    # Find all PDF files
    pdf_files = list(papers_path.glob("*.pdf"))

    if not pdf_files:
        raise ValueError(f"No PDF files found in: {papers_dir}")

    print(f"\n📚 Found {len(pdf_files)} PDF(s) in '{papers_dir}':")
    for f in pdf_files:
        print(f"   - {f.name}")

    all_pages = []

    for pdf_file in pdf_files:
        try:
            pages = load_pdf(str(pdf_file))
            all_pages.extend(pages)
        except Exception as e:
            print(f"  ⚠️  Skipping {pdf_file.name} due to error: {e}")
            continue

    print(f"\n✅ Total pages loaded across all papers: {len(all_pages)}")

    # Print section distribution for debugging
    print_section_summary(all_pages)

    return all_pages


def print_section_summary(pages_data: list[dict]):
    """
    Print a summary of how many pages belong to each section,
    per paper. Useful for debugging section detection quality.
    """
    print("\n📊 Section Detection Summary:")
    print("-" * 50)

    # Group by paper
    papers = {}
    for page in pages_data:
        pname = page["paper_name"]
        section = page["section"]

        if pname not in papers:
            papers[pname] = {}

        papers[pname][section] = papers[pname].get(section, 0) + 1

    for paper, sections in papers.items():
        print(f"\n  📄 {paper}:")
        for section, count in sorted(sections.items()):
            bar = "█" * min(count, 20)
            print(f"     {section:<20} {bar} ({count} pages)")

    print("-" * 50)


def get_paper_names(papers_dir: str) -> list[str]:
    """
    Get list of paper names (without extension) from directory.
    Used by the UI to populate dropdowns.
    """
    papers_path = Path(papers_dir)
    return [f.stem for f in papers_path.glob("*.pdf")]


def get_sections_for_paper(pages_data: list[dict], paper_name: str) -> list[str]:
    """
    Get unique sections found in a specific paper.
    Used by the UI for section-wise filtering.
    """
    sections = set()
    for page in pages_data:
        if page["paper_name"] == paper_name:
            sections.add(page["section"])
    return sorted(list(sections))