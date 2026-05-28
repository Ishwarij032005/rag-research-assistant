# validators/pdf_validator.py
# Main validation orchestrator

import pdfplumber
from pathlib import Path

from validation_utils.section_detector   import detect_sections
from validation_utils.citation_detector  import detect_citations
from validation_utils.keyword_classifier import classify_academic_keywords
from utils.config import (
    MIN_PAGES, MAX_PAGES, MIN_TEXT_CHARS,
    MIN_ACADEMIC_SCORE, MIN_SECTIONS_FOUND
)
from utils.logger import get_logger

logger = get_logger(__name__)


class ValidationResult:
    """Holds the complete result of a PDF validation."""

    def __init__(self):
        self.is_valid        = False
        self.confidence      = 0.0
        self.rejection_reason= ""
        self.warnings        = []
        self.details         = {}

    def to_dict(self) -> dict:
        return {
            "is_valid"        : self.is_valid,
            "confidence"      : self.confidence,
            "rejection_reason": self.rejection_reason,
            "warnings"        : self.warnings,
            "details"         : self.details,
        }


def validate_research_paper(pdf_path: str) -> ValidationResult:
    """
    Full validation pipeline for an uploaded PDF.

    Checks (in order):
    1. File exists and is readable
    2. Page count (3–200 pages)
    3. Has extractable text (not image-only)
    4. Minimum text length
    5. Academic section detection
    6. Citation pattern detection
    7. Academic keyword classification
    8. Combined confidence score

    Args:
        pdf_path: Path to the PDF file

    Returns:
        ValidationResult object
    """
    result = ValidationResult()
    path   = Path(pdf_path)

    logger.info(f"Validating: {path.name}")

    # ── 1. File check ──────────────────────────────────────────
    if not path.exists():
        result.rejection_reason = "File not found."
        return result

    if not path.suffix.lower() == ".pdf":
        result.rejection_reason = "Only PDF files are accepted."
        return result

    # ── 2. Open and extract ────────────────────────────────────
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)

            # ── Page count check ───────────────────────────────
            if total_pages < MIN_PAGES:
                result.rejection_reason = (
                    f"Document has only {total_pages} page(s). "
                    f"Research papers typically have {MIN_PAGES}+ pages."
                )
                return result

            if total_pages > MAX_PAGES:
                result.rejection_reason = (
                    f"Document has {total_pages} pages. "
                    f"Maximum allowed is {MAX_PAGES} pages. "
                    f"Please upload individual research papers, not books."
                )
                return result

            # ── Extract all text ───────────────────────────────
            all_text  = ""
            text_pages = 0

            for page in pdf.pages:
                txt = page.extract_text()
                if txt and len(txt.strip()) > 50:
                    all_text  += txt + "\n"
                    text_pages += 1

            # ── Text extraction check ──────────────────────────
            if text_pages == 0:
                result.rejection_reason = (
                    "This PDF contains only images or scanned pages. "
                    "Please upload a text-based research paper PDF. "
                    "Scanned papers require OCR processing."
                )
                return result

            text_ratio = text_pages / total_pages
            if text_ratio < 0.4:
                result.warnings.append(
                    f"Only {int(text_ratio*100)}% of pages have "
                    f"extractable text. Some content may be missed."
                )

    except Exception as e:
        result.rejection_reason = f"Could not read PDF: {str(e)}"
        return result

    # ── 3. Minimum text check ──────────────────────────────────
    if len(all_text.strip()) < MIN_TEXT_CHARS:
        result.rejection_reason = (
            "Insufficient text content found. "
            "Please upload a complete research paper."
        )
        return result

    # ── 4. Section detection ───────────────────────────────────
    section_result = detect_sections(all_text)
    found_sections = section_result["found_sections"]
    section_score  = min(1.0, section_result["total_score"] / 12.0)

    if len(found_sections) < MIN_SECTIONS_FOUND:
        result.rejection_reason = (
            f"Only {len(found_sections)} academic section(s) found "
            f"({', '.join(found_sections) or 'none'}). "
            f"Research papers need sections like Abstract, "
            f"Introduction, Methodology, and References."
        )
        result.details["sections"] = section_result
        return result

    # ── 5. Citation detection ──────────────────────────────────
    citation_result = detect_citations(all_text)
    citation_score  = citation_result["citation_score"]

    if citation_result["citation_count"] < 3:
        result.warnings.append(
            "Very few citations detected. "
            "Academic papers typically cite prior work."
        )

    # ── 6. Keyword classification ──────────────────────────────
    keyword_result = classify_academic_keywords(all_text)
    keyword_score  = keyword_result["academic_score"]

    if keyword_result["non_paper_hits"] > 0:
        result.rejection_reason = (
            "This document appears to be a resume, book, or "
            "non-academic document. "
            "Please upload a valid academic research paper."
        )
        result.details["keywords"] = keyword_result
        return result

    # ── 7. Combined confidence score ───────────────────────────
    # Weighted average of all signals
    confidence = (
        section_score  * 0.40 +
        citation_score * 0.30 +
        keyword_score  * 0.30
    )

    result.details = {
        "total_pages"   : total_pages,
        "text_pages"    : text_pages,
        "text_ratio"    : round(text_ratio, 2),
        "sections"      : section_result,
        "citations"     : citation_result,
        "keywords"      : keyword_result,
        "section_score" : round(section_score,  3),
        "citation_score": round(citation_score, 3),
        "keyword_score" : round(keyword_score,  3),
        "confidence"    : round(confidence,     3),
    }

    result.confidence = round(confidence, 3)

    # ── 8. Final decision ──────────────────────────────────────
    if confidence < MIN_ACADEMIC_SCORE:
        result.rejection_reason = (
            f"This document does not appear to be a research paper "
            f"(confidence: {int(confidence*100)}%). "
            f"Found sections: {', '.join(found_sections)}. "
            f"Please upload an academic research paper with proper "
            f"structure (Abstract, Introduction, Methodology, References)."
        )
        return result

    # ── Passed ─────────────────────────────────────────────────
    result.is_valid = True
    logger.info(
        f"✅ Valid paper: {path.name} "
        f"(confidence={confidence:.2f}, "
        f"sections={found_sections})"
    )
    return result


def validate_uploaded_file(uploaded_file, save_dir: str) -> tuple[bool, str, dict]:
    """
    Convenience wrapper for Streamlit file uploads.
    Saves the file temporarily, validates, returns result.

    Returns:
        (is_valid, message, details)
    """
    import tempfile
    import os

    # Save to temp file
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix
    ) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        result = validate_research_paper(tmp_path)
        msg    = result.rejection_reason if not result.is_valid else "Valid research paper."
        return result.is_valid, msg, result.details
    finally:
        os.unlink(tmp_path)