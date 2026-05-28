# utils/cache.py

import time
import streamlit as st
from utils.logger import get_logger

logger = get_logger(__name__)


def get_cached(key: str):
    """Get value from Streamlit session cache."""
    cache = st.session_state.get("_app_cache", {})
    entry = cache.get(key)
    if not entry:
        return None
    # Check TTL
    if time.time() > entry["expires_at"]:
        del cache[key]
        return None
    return entry["value"]


def set_cached(key: str, value, ttl_seconds: int = 3600):
    """Store value in Streamlit session cache with TTL."""
    if "_app_cache" not in st.session_state:
        st.session_state["_app_cache"] = {}
    st.session_state["_app_cache"][key] = {
        "value"     : value,
        "expires_at": time.time() + ttl_seconds
    }
    logger.debug(f"Cache SET: {key} (TTL={ttl_seconds}s)")


def clear_cache():
    """Clear all app cache."""
    st.session_state["_app_cache"] = {}
    logger.info("Cache cleared")