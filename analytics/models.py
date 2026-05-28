# analytics/models.py

from datetime import datetime


def query_event(
    username: str,
    question: str,
    paper_filter: str,
    section_filter: str,
    num_results: int,
    response_time_ms: int,
    top_score: float
) -> dict:
    return {
        "event_type"     : "query",
        "username"       : username,
        "question"       : question,
        "paper_filter"   : paper_filter,
        "section_filter" : section_filter,
        "num_results"    : num_results,
        "response_time_ms": response_time_ms,
        "top_score"      : top_score,
        "timestamp"      : datetime.utcnow(),
    }


def upload_event(
    username: str,
    paper_name: str,
    is_valid: bool,
    confidence: float,
    pages: int
) -> dict:
    return {
        "event_type" : "upload",
        "username"   : username,
        "paper_name" : paper_name,
        "is_valid"   : is_valid,
        "confidence" : confidence,
        "pages"      : pages,
        "timestamp"  : datetime.utcnow(),
    }


def summary_event(
    username: str,
    summary_type: str,
    paper_name: str,
    response_time_ms: int
) -> dict:
    return {
        "event_type"      : "summary",
        "username"        : username,
        "summary_type"    : summary_type,
        "paper_name"      : paper_name,
        "response_time_ms": response_time_ms,
        "timestamp"       : datetime.utcnow(),
    }