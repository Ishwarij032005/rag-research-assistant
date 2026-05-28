# utils/disk_cache.py
# Persistent SQLite-backed cache — Thread-safe for Streamlit & parallel workers
# Fixed: get_cache_stats() key initialization guard

import os
import time
import hashlib
import sqlite3
import pickle
import threading
from pathlib import Path
from utils.config import BASE_DIR
from utils.logger import get_logger

logger = get_logger(__name__)

CACHE_DIR  = BASE_DIR / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = CACHE_DIR / "cache.sqlite"

# TTLs (seconds)
TTL_SUMMARY  = 86_400   # 24 h
TTL_QA       = 3_600    # 1  h
TTL_EMBED    = 604_800  # 7  d

# ── Global stats ───────────────────────────────────────────────
_stats: dict[str, int] = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}
_stats_lock = threading.Lock()

def _stats_inc(key: str, n: int = 1):
    with _stats_lock:
        _stats[key] = _stats.get(key, 0) + n

def get_cache_stats() -> dict:
    with _stats_lock:
        hits   = _stats.get("hits", 0)
        misses = _stats.get("misses", 0)
        total  = hits + misses
        hit_rate = (hits / total * 100) if total else 0.0
        return {
            "hits"        : hits,
            "misses"      : misses,
            "sets"        : _stats.get("sets", 0),
            "evictions"   : _stats.get("evictions", 0),
            "hit_rate_pct": round(hit_rate, 1),
        }

# ── SQLite connection & init ───────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache_store (
            namespace TEXT,
            key TEXT,
            value BLOB,
            expires_at REAL,
            created_at REAL,
            PRIMARY KEY (namespace, key)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache_store(expires_at)")
    return conn

# ── Helpers ────────────────────────────────────────────────────

def make_key(*parts) -> str:
    combined = "|".join(str(p) for p in parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:32]

# ── Core cache operations ──────────────────────────────────────

def cache_get(namespace: str, key: str):
    try:
        with _get_conn() as conn:
            cursor = conn.execute(
                "SELECT value, expires_at FROM cache_store WHERE namespace=? AND key=?",
                (namespace, key)
            )
            row = cursor.fetchone()
            if row is None:
                _stats_inc("misses")
                return None
            val_bytes, expires_at = row
            if time.time() > expires_at:
                conn.execute(
                    "DELETE FROM cache_store WHERE namespace=? AND key=?",
                    (namespace, key)
                )
                _stats_inc("evictions")
                _stats_inc("misses")
                return None
            _stats_inc("hits")
            return pickle.loads(val_bytes)
    except sqlite3.DatabaseError:
        logger.error("SQLite DB corrupt — auto-healing by dropping table...")
        try:
            with _get_conn() as conn:
                conn.execute("DROP TABLE IF EXISTS cache_store")
        except Exception:
            if DB_PATH.exists():
                DB_PATH.unlink(missing_ok=True)
        return None
    except Exception as e:
        logger.warning(f"disk_cache GET error [{namespace}]: {e}")
        _stats_inc("misses")
        return None


def cache_set(namespace: str, key: str, value, ttl: int = TTL_QA):
    try:
        val_bytes = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        now = time.time()
        with _get_conn() as conn:
            conn.execute("""
                REPLACE INTO cache_store (namespace, key, value, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (namespace, key, val_bytes, now + ttl, now))
        _stats_inc("sets")
    except Exception as e:
        logger.warning(f"disk_cache SET error [{namespace}]: {e}")


def cache_delete(namespace: str, key: str):
    try:
        with _get_conn() as conn:
            conn.execute(
                "DELETE FROM cache_store WHERE namespace=? AND key=?",
                (namespace, key)
            )
    except Exception as e:
        logger.warning(f"disk_cache DELETE error [{namespace}]: {e}")


def cache_clear(namespace: str = None):
    try:
        with _get_conn() as conn:
            if namespace:
                conn.execute("DELETE FROM cache_store WHERE namespace=?", (namespace,))
            else:
                conn.execute("DELETE FROM cache_store")
        logger.info(f"Cache cleared: [{namespace or 'ALL'}]")
    except Exception as e:
        logger.warning(f"disk_cache CLEAR error [{namespace}]: {e}")


def cache_size_bytes(namespace: str = None) -> int:
    try:
        if DB_PATH.exists():
            return DB_PATH.stat().st_size
        return 0
    except Exception:
        return 0
