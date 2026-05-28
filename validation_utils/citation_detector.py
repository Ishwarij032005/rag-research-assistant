# validators/citation_detector.py

import re


# Citation patterns used in academic papers
CITATION_PATTERNS = [
    # [1], [2, 3], [1-5]
    r'\[\d+(?:[,\-]\s*\d+)*\]',
    # (Author, 2023), (Smith et al., 2021)
    r'\([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s+\d{4}\)',
    # Author (2023)
    r'[A-Z][a-z]+\s+\(\d{4}\)',
    # et al.
    r'\bet\s+al\.?',
    # DOI patterns
    r'doi:\s*10\.\d{4,}',
    r'https?://doi\.org/10\.\d{4,}',
    # arXiv
    r'arXiv:\d{4}\.\d{4,}',
    # Reference list patterns: [1] Author...
    r'^\s*\[\d+\]\s+[A-Z]',
]

REFERENCE_SECTION_PATTERNS = [
    r'\breferences?\b',
    r'\bbibliography\b',
]


def detect_citations(full_text: str) -> dict:
    """
    Detect citation patterns and reference sections.

    Returns:
        {
            "citation_count"     : 42,
            "has_reference_section": True,
            "has_doi"            : True,
            "citation_score"     : 0.85,
            "patterns_found"     : [...]
        }
    """
    total_count   = 0
    patterns_hit  = []

    for pattern in CITATION_PATTERNS:
        matches = re.findall(pattern, full_text, re.MULTILINE)
        if matches:
            total_count  += len(matches)
            patterns_hit.append(pattern[:30])

    has_ref_section = any(
        re.search(p, full_text, re.IGNORECASE)
        for p in REFERENCE_SECTION_PATTERNS
    )

    has_doi = bool(re.search(r'doi', full_text, re.IGNORECASE))

    # Score: 0-1 based on citation density
    # Papers typically have 10-100+ citations
    score = min(1.0, total_count / 20.0)
    if has_ref_section:
        score = min(1.0, score + 0.3)

    return {
        "citation_count"      : total_count,
        "has_reference_section": has_ref_section,
        "has_doi"             : has_doi,
        "citation_score"      : round(score, 3),
        "patterns_found"      : patterns_hit
    }