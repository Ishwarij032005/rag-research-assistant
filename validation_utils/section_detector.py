# validators/section_detector.py

import re

# Academic section headers and their weights
SECTION_DEFINITIONS = {
    "Abstract": [
        r'\babstract\b',
        r'\bsummary\b',
        r'\boverview\b'
    ],
    "Introduction": [
        r'\b\d*\.?\s*introduction\b',
        r'\bbackground\b',
        r'\bmotivation\b'
    ],
    "Related Work": [
        r'\brelated\s+work\b',
        r'\bliterature\s+review\b',
        r'\bprior\s+work\b',
        r'\bbackground\s+and\s+related\b'
    ],
    "Methodology": [
        r'\bmethodology\b',
        r'\bmethod\b',
        r'\bapproach\b',
        r'\bproposed\s+(method|model|approach|framework)\b',
        r'\barchitecture\b',
        r'\bmodel\b'
    ],
    "Experiments": [
        r'\bexperiment(s|al)?\b',
        r'\bevaluation\b',
        r'\bimplementation\b',
        r'\bsetup\b',
        r'\bbaseline\b'
    ],
    "Results": [
        r'\bresult(s)?\b',
        r'\bperformance\b',
        r'\bfindings?\b',
        r'\boutcome(s)?\b',
        r'\baccuracy\b'
    ],
    "Discussion": [
        r'\bdiscussion\b',
        r'\banalysis\b',
        r'\bablation\b',
        r'\berror\s+analysis\b'
    ],
    "Conclusion": [
        r'\bconclusion(s)?\b',
        r'\bfuture\s+work\b',
        r'\blimitation(s)?\b',
        r'\bsummary\s+and\s+conclusion\b'
    ],
    "References": [
        r'\breferences?\b',
        r'\bbibliography\b',
        r'\bcitations?\b'
    ]
}

# Minimum weight to count a section as "found"
SECTION_WEIGHT = {
    "Abstract"    : 3,  # very important
    "Introduction": 3,
    "Methodology" : 2,
    "Results"     : 2,
    "Conclusion"  : 2,
    "References"  : 3,
    "Related Work": 1,
    "Experiments" : 1,
    "Discussion"  : 1,
}


def detect_sections(full_text: str) -> dict:
    """
    Scan the full PDF text and detect which academic
    sections are present.

    Returns:
        {
            "found_sections": ["Abstract", "Introduction", ...],
            "section_scores": {"Abstract": 3, ...},
            "total_score"   : 14,
            "details"       : {"Abstract": True, ...}
        }
    """
    text_lower = full_text.lower()
    found      = {}
    scores     = {}

    for section, patterns in SECTION_DEFINITIONS.items():
        matched = any(
            re.search(p, text_lower, re.IGNORECASE)
            for p in patterns
        )
        found[section]  = matched
        scores[section] = SECTION_WEIGHT.get(section, 1) if matched else 0

    found_list  = [s for s, v in found.items() if v]
    total_score = sum(scores.values())

    return {
        "found_sections": found_list,
        "section_scores": scores,
        "total_score"   : total_score,
        "details"       : found
    }