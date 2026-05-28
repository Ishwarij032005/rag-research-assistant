# analytics/tracker.py — Production v3.0
# Extended with cache hit tracking and token usage

import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from analytics.models import query_event, upload_event, summary_event
from utils.config import MONGODB_URI, MONGODB_DB
from utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsTracker:
    def __init__(self):
        self.db = self._connect()
        self._cache = {}
        import time
        self._time = time

    def _get_cached(self, key: str, fetch_func, ttl: int = 60):
        now = self._time.time()
        if key in self._cache:
            data, ts = self._cache[key]
            if now - ts < ttl:
                return data
        data = fetch_func()
        self._cache[key] = (data, now)
        return data

    def _connect(self):
        try:
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
            client.admin.command("ping")
            return client[MONGODB_DB]
        except Exception:
            logger.warning("Analytics DB unavailable — events not tracked")
            return None

    @property
    def events(self):
        return self.db["events"] if self.db is not None else None

    def _insert(self, doc: dict):
        try:
            if self.events is not None:
                self.events.insert_one(doc)
        except Exception as e:
            logger.warning(f"Analytics insert failed: {e}")

    def track_query(self, question, paper_filter, section_filter,
                    num_results, response_time_ms, top_score, tokens=0):
        username = st.session_state.get("username", "anonymous")
        doc = query_event(
            username, question, paper_filter, section_filter,
            num_results, response_time_ms, top_score
        )
        doc["tokens"] = tokens
        self._insert(doc)

    def track_upload(self, paper_name, is_valid, confidence, pages):
        username = st.session_state.get("username", "anonymous")
        self._insert(upload_event(username, paper_name, is_valid, confidence, pages))

    def track_summary(self, summary_type, paper_name, response_time_ms):
        username = st.session_state.get("username", "anonymous")
        self._insert(summary_event(username, summary_type, paper_name, response_time_ms))


    # ── Dashboard Queries ────────────────────────────────────────

    def get_summary_stats(self) -> dict:
        def _fetch():
            if self.db is None:
                return self._empty_stats()

            events = list(self.events.find({}))
            queries  = [e for e in events if e["event_type"] == "query"]
            uploads  = [e for e in events if e["event_type"] == "upload"]
            valid_up = [e for e in uploads if e.get("is_valid")]

            avg_rt = sum(q.get("response_time_ms", 0) for q in queries) / len(queries) if queries else 0
            avg_sc = sum(q.get("top_score", 0) for q in queries) / len(queries) if queries else 0
            tot_tk = sum(q.get("tokens", 0) for q in queries)

            # Get local cache stats to blend into dashboard
            from utils.disk_cache import get_cache_stats
            c_stats = get_cache_stats()

            return {
                "total_queries"    : len(queries),
                "total_uploads"    : len(uploads),
                "valid_uploads"    : len(valid_up),
                "rejected_uploads" : len(uploads) - len(valid_up),
                "avg_response_ms"  : round(avg_rt),
                "avg_top_score"    : round(avg_sc, 3),
                "unique_users"     : len(set(e.get("username", "") for e in events)),
                "cache_hit_rate"   : c_stats.get("hit_rate_pct", 0.0),
                "total_tokens"     : tot_tk,
            }
        return self._get_cached("summary_stats", _fetch, ttl=60)

    def get_queries_over_time(self, days: int = 14) -> list[dict]:
        def _fetch():
            if self.db is None:
                return []
            since = datetime.utcnow() - timedelta(days=days)
            events = list(self.events.find({
                "event_type": "query",
                "timestamp" : {"$gte": since}
            }))
            by_date = {}
            for e in events:
                d = e["timestamp"].strftime("%Y-%m-%d")
                by_date[d] = by_date.get(d, 0) + 1
            return [{"date": k, "count": v} for k, v in sorted(by_date.items())]
        return self._get_cached(f"queries_over_time_{days}", _fetch, ttl=120)

    def get_top_questions(self, n: int = 10) -> list[dict]:
        def _fetch():
            if self.db is None:
                return []
            events = list(self.events.find({"event_type": "query"}))
            from collections import Counter
            import re
            words = Counter()
            for e in events:
                q = e.get("question", "")
                for w in re.findall(r'\b[a-z]{4,}\b', q.lower()):
                    if w not in {
                        "what", "when", "where", "which", "this", "that",
                        "with", "from", "have", "were", "they", "their",
                        "does", "used", "were", "been"
                    }:
                        words[w] += 1
            return [{"word": w, "count": c} for w, c in words.most_common(n)]
        return self._get_cached(f"top_questions_{n}", _fetch, ttl=120)

    def get_user_activity(self) -> list[dict]:
        def _fetch():
            if self.db is None:
                return []
            events = list(self.events.find({"event_type": "query"}))
            from collections import Counter
            counts = Counter(e.get("username", "?") for e in events)
            return [{"username": u, "queries": c} for u, c in counts.most_common(10)]
        return self._get_cached("user_activity", _fetch, ttl=120)

    def get_response_times(self) -> list[int]:
        def _fetch():
            if self.db is None:
                return []
            events = list(self.events.find({"event_type": "query"}))
            return [e.get("response_time_ms", 0) for e in events]
        return self._get_cached("response_times", _fetch, ttl=60)

    def get_section_filter_usage(self) -> list[dict]:
        def _fetch():
            if self.db is None:
                return []
            events = list(self.events.find({
                "event_type"    : "query",
                "section_filter": {"$ne": None}
            }))
            from collections import Counter
            counts = Counter(e.get("section_filter", "None") for e in events)
            return [{"section": s, "count": c} for s, c in counts.most_common()]
        return self._get_cached("section_filter_usage", _fetch, ttl=120)

    def _empty_stats(self) -> dict:
        return {
            "total_queries"   : 0, "total_uploads"   : 0,
            "valid_uploads"   : 0, "rejected_uploads": 0,
            "avg_response_ms" : 0, "avg_top_score"   : 0,
            "unique_users"    : 0, "cache_hit_rate"  : 0.0,
            "total_tokens"    : 0,
        }