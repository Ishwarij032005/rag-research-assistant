# app.py  ── Production Entry Point v3.1
# Fixed: prefill_q default removed (was causing ghost submit on first load)

import streamlit as st
import time
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils.config  import APP_NAME, APP_ICON, APP_VERSION
from utils.logger  import get_logger
from ui.theme      import inject_theme
from ui.components import user_avatar, empty_state
from auth.auth_manager import AuthManager
from analytics.tracker import AnalyticsTracker

logger = get_logger(__name__)

st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_theme()


# ── Singletons ─────────────────────────────────────────────────
@st.cache_resource
def get_auth():
    return AuthManager()

@st.cache_resource
def get_tracker():
    return AnalyticsTracker()

@st.cache_resource
def get_embedder():
    from rag.embedder import ResearchEmbedder
    from utils.config import VECTORSTORE_DIR
    e = ResearchEmbedder(str(VECTORSTORE_DIR))
    e.load_index()
    return e

@st.cache_resource
def get_llm():
    from rag.llm_chain import ResearchLLMChain
    return ResearchLLMChain()


auth    = get_auth()
tracker = get_tracker()


# ── Startup Health Check ───────────────────────────────────────
if "health_ok" not in st.session_state:
    try:
        from utils.config import GROQ_API_KEY
        if not GROQ_API_KEY:
            st.error("❌ CRITICAL: GROQ_API_KEY not found in .env")
            st.stop()
        st.session_state.health_ok = True
    except Exception as e:
        st.error(f"Startup check failed: {e}")
        st.stop()


# ── Session init ───────────────────────────────────────────────
def init_state():
    defaults = {
        "authenticated"   : False,
        "chat_history"    : [],
        "summaries_cache" : {},
        "active_page"     : "Chat",
        "index_ready"     : False,
        # NOTE: prefill_q intentionally NOT set here — only set on button click
        # to avoid ghost submit on page load.
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Dev helper: allow auto-auth in local dev by setting env var DEV_AUTO_AUTH=1
try:
    if os.getenv("DEV_AUTO_AUTH", "0") == "1":
        st.session_state["authenticated"] = True
        st.session_state["username"] = "dev"
        st.session_state["role"] = "admin"
        st.session_state["display_name"] = "Developer"
        st.session_state["avatar_color"] = "#4f8ef7"
except Exception:
    pass

if not auth.is_authenticated():
    from ui.pages.login_page import render_login_page
    render_login_page(auth)
    st.stop()


# ── Sidebar ────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(
            f"<div style='font-size:1.4rem;font-weight:700;"
            f"padding:10px 0 4px'>{APP_ICON} {APP_NAME}</div>"
            f"<div style='color:#8b949e;font-size:0.75rem;"
            f"margin-bottom:16px'>v{APP_VERSION} PRO</div>",
            unsafe_allow_html=True
        )

        user_avatar(
            st.session_state.get("display_name", "User"),
            st.session_state.get("avatar_color", "#4f8ef7")
        )
        role = st.session_state.get("role", "user")
        st.markdown(
            f"<span class='chip-paper'>{'👑 Admin' if role=='admin' else '👤 User'}</span>",
            unsafe_allow_html=True
        )

        st.divider()

        st.markdown(
            "<div style='font-size:0.75rem;color:#8b949e;"
            "font-weight:600;letter-spacing:0.08em;"
            "margin-bottom:8px'>NAVIGATION</div>",
            unsafe_allow_html=True
        )

        nav_items = [
            ("💬", "Chat",      "Ask questions with citations"),
            ("📝", "Summary",   "Paper summaries"),
            ("⚖️", "Compare",   "Compare papers"),
            ("📤", "Upload",    "Add new papers (Auto-indexes)"),
        ]
        if auth.is_admin():
            nav_items.append(("📊", "Analytics", "Usage dashboard"))

        for icon, label, tip in nav_items:
            active = st.session_state.active_page == label
            if st.button(
                f"{icon}  {label}",
                key=f"nav_{label}",
                use_container_width=True,
                help=tip,
                type="primary" if active else "secondary"
            ):
                st.session_state.active_page = label
                st.rerun()

        st.divider()

        # ── Index status ───────────────────────────────────────
        try:
            emb   = get_embedder()
            ready = emb.index is not None and emb.index.ntotal > 0
        except Exception:
            ready = False

        if ready:
            stats = emb.get_stats()
            st.success("✅ Index active")
            c1, c2 = st.columns(2)
            c1.metric("Papers",  len(stats["papers"]))
            c2.metric("Chunks",  stats["total_chunks"])
        else:
            st.warning("⚠️ No papers indexed — go to Upload")

        st.divider()

        # ── Search settings ────────────────────────────────────
        st.markdown(
            "<div style='font-size:0.75rem;color:#8b949e;"
            "font-weight:600;letter-spacing:0.08em;"
            "margin-bottom:8px'>SEARCH SETTINGS</div>",
            unsafe_allow_html=True
        )

        st.session_state["top_k"] = st.slider("Top K chunks", 3, 10, 5)

        paper_opts = ["All Papers"]
        sec_opts   = ["All Sections"]
        if ready:
            paper_opts += emb.get_papers()
            sec_opts   += emb.get_sections()

        st.session_state["filter_paper"]   = st.selectbox("Filter by paper",   paper_opts)
        st.session_state["filter_section"] = st.selectbox("Filter by section", sec_opts)

        st.divider()

        # ── Cache & System Status ──────────────────────────────
        from utils.disk_cache import get_cache_stats, cache_size_bytes, cache_clear
        c_stats = get_cache_stats()
        sz_mb   = cache_size_bytes() / (1024 * 1024)

        with st.expander("⚙️ System Status", expanded=False):
            st.caption(f"**Cache Hit Rate:** {c_stats.get('hit_rate_pct', 0)}%")
            st.caption(f"**Disk Usage:** {sz_mb:.1f} MB")

            if st.button("🧹 Clear Disk Cache"):
                cache_clear()
                st.rerun()

            if st.button("🔨 Force Index Rebuild", help="Only needed if index gets corrupted."):
                _build_index()

        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            auth.logout()
            st.rerun()


def _build_index():
    from rag.pdf_loader import load_all_pdfs
    from rag.chunker    import chunk_pages
    from utils.config   import PAPERS_DIR
    from utils.disk_cache import cache_clear

    try:
        emb = get_embedder()
        with st.spinner("📄 Loading PDFs..."):
            pages = load_all_pdfs(str(PAPERS_DIR))
        with st.spinner("✂️  Chunking..."):
            chunks = chunk_pages(pages)
        with st.spinner("🔢 Embedding (~1-2 min)..."):
            emb.build_index(chunks)

        st.session_state.summaries_cache = {}
        cache_clear()
        get_embedder.clear()
        st.success("✅ Full index rebuild complete!")
    except Exception as e:
        st.error(f"Build failed: {e}")


# ── Render active page ─────────────────────────────────────────
render_sidebar()

page = st.session_state.active_page

if page == "Chat":
    from ui.pages.chat_page import render_chat_page
    render_chat_page(get_embedder, get_llm, auth, tracker)

elif page == "Summary":
    from ui.pages.summary_page import render_summary_page
    render_summary_page(get_embedder, get_llm, tracker)

elif page == "Compare":
    from ui.pages.compare_page import render_compare_page
    render_compare_page(get_embedder, get_llm, tracker)

elif page == "Upload":
    from ui.pages.upload_page import render_upload_page
    render_upload_page(get_embedder, auth, tracker)

elif page == "Analytics":
    auth.require_admin()
    from analytics.dashboard import render_analytics_dashboard
    render_analytics_dashboard(tracker)
