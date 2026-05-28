# ui/theme.py

DARK_THEME_CSS = """
<style>
/* ── Reset & Base ─────────────────────────────────────── */
* { box-sizing: border-box; }

[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f1117 0%, #141824 100%);
    color: #e1e4e8;
}
[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid #21262d;
}
[data-testid="stHeader"] {
    background: rgba(13,17,23,0.95);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid #21262d;
}

/* ── Cards ────────────────────────────────────────────── */
.pro-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px 24px;
    margin: 10px 0;
    transition: border-color 0.2s ease;
}
.pro-card:hover { border-color: #4f8ef7; }

.metric-card {
    background: linear-gradient(135deg, #161b22, #1c2128);
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}
.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #4f8ef7;
}
.metric-label {
    font-size: 0.82rem;
    color: #8b949e;
    margin-top: 4px;
}

/* ── Buttons ──────────────────────────────────────────── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f8ef7, #6f42c1) !important;
    border: none !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 15px rgba(79,142,247,0.4) !important;
}

/* ── Source cards ─────────────────────────────────────── */
.source-card {
    background: #1c2128;
    border-left: 3px solid #4f8ef7;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: 0.88em;
}
.source-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}

/* ── Chips ────────────────────────────────────────────── */
.chip-paper {
    background: #1f3a5f;
    color: #7ab3f7;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.78em;
    font-weight: 600;
    display: inline-block;
}
.chip-section {
    background: #2d1f4a;
    color: #c07af7;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.78em;
    display: inline-block;
}
.chip-score {
    background: #1a3a1f;
    color: #7dd67d;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.78em;
    font-weight: 700;
    display: inline-block;
}
.chip-page {
    background: #3a2a1f;
    color: #f7c34f;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.78em;
    display: inline-block;
}

/* ── Chat ─────────────────────────────────────────────── */
.chat-question {
    background: #1f2d45;
    border-radius: 12px 12px 0 12px;
    padding: 14px 18px;
    margin: 8px 0;
    border: 1px solid #2d4a7a;
}
.chat-answer {
    background: #1a2a1a;
    border-radius: 12px 12px 12px 0;
    padding: 14px 18px;
    margin: 8px 0;
    border: 1px solid #2a4a2a;
    line-height: 1.8;
}

/* ── Auth pages ───────────────────────────────────────── */
.auth-container {
    max-width: 420px;
    margin: 60px auto;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 16px;
    padding: 40px;
}
.auth-logo {
    text-align: center;
    font-size: 3rem;
    margin-bottom: 8px;
}
.auth-title {
    text-align: center;
    font-size: 1.5rem;
    font-weight: 700;
    color: #e1e4e8;
    margin-bottom: 4px;
}
.auth-subtitle {
    text-align: center;
    color: #8b949e;
    font-size: 0.9rem;
    margin-bottom: 28px;
}

/* ── Validation result ─────────────────────────────────  */
.valid-badge {
    background: linear-gradient(135deg, #1a3a1f, #1f4a24);
    border: 1px solid #2ea043;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 10px 0;
}
.invalid-badge {
    background: linear-gradient(135deg, #3a1a1a, #4a1f1f);
    border: 1px solid #f85149;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 10px 0;
}
.confidence-bar-wrap {
    background: #21262d;
    border-radius: 6px;
    height: 8px;
    margin: 8px 0;
    overflow: hidden;
}
.confidence-bar-fill {
    height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, #4f8ef7, #7dd67d);
    transition: width 0.5s ease;
}

/* ── Sidebar nav ──────────────────────────────────────── */
.nav-item {
    padding: 10px 14px;
    border-radius: 8px;
    margin: 3px 0;
    cursor: pointer;
    transition: background 0.15s;
    font-size: 0.92rem;
}
.nav-item:hover { background: #21262d; }
.nav-item.active {
    background: #1f3a5f;
    color: #4f8ef7;
    font-weight: 600;
}

/* ── Summary cards ────────────────────────────────────── */
.summary-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 24px;
    margin: 12px 0;
    line-height: 1.8;
}

/* ── Upload zone ──────────────────────────────────────── */
[data-testid="stFileUploader"] {
    background: #161b22 !important;
    border: 2px dashed #4f8ef7 !important;
    border-radius: 12px !important;
    padding: 20px !important;
}

/* ── Progress ─────────────────────────────────────────── */
.stProgress > div > div {
    background: linear-gradient(90deg, #4f8ef7, #7dd67d) !important;
    border-radius: 4px !important;
}

/* ── Hide Streamlit branding ──────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }

/* ── PDF Viewer ──────────────────────────────────────── */
.pdf-viewer-container {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 12px;
    overflow: hidden;
    margin-top: 4px;
}
.pdf-viewer-container iframe {
    display: block;
}

.pdf-toolbar {
    background: linear-gradient(135deg, #161b22 0%, #1c2128 100%);
    border-bottom: 1px solid #21262d;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-radius: 12px 12px 0 0;
}
.pdf-toolbar .paper-title {
    color: #e1e4e8;
    font-weight: 600;
    font-size: 0.88rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 220px;
}
.pdf-toolbar .page-badge {
    background: #1f3a5f;
    color: #7ab3f7;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
}

.pdf-viewer-empty {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    border: 2px dashed #21262d;
    border-radius: 16px;
    padding: 80px 30px;
    text-align: center;
    margin-top: 4px;
    min-height: 400px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

/* ── Split Layout Enhancements ───────────────────────── */
[data-testid="stHorizontalBlock"] {
    align-items: flex-start !important;
}

/* ── Source Card — View Button ────────────────────────── */
.source-card .view-pdf-btn {
    background: #1f3a5f;
    color: #7ab3f7;
    border: 1px solid #2d4a7a;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    margin-top: 6px;
    display: inline-block;
}
.source-card .view-pdf-btn:hover {
    background: #2d4a7a;
    border-color: #4f8ef7;
}

/* ── Active Source Indicator ──────────────────────────── */
.source-card.active-source {
    border-left-color: #7dd67d;
    background: #1a2a1f;
}

/* ── Responsive — Mobile Fallback ────────────────────── */
@media (max-width: 768px) {
    .pdf-viewer-container iframe {
        height: 400px !important;
    }
    .pdf-toolbar .paper-title {
        max-width: 140px;
        font-size: 0.8rem;
    }
    .pdf-viewer-empty {
        min-height: 250px;
        padding: 40px 20px;
    }
}
</style>
"""


def inject_theme():
    """Call once at app startup to inject all CSS."""
    import streamlit as st
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)