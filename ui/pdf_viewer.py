# ui/pdf_viewer.py — Embedded PDF Viewer for Research Workspace v2.0
# Fixed: dead code bug (render_pdf_viewer), localStorage blocked in iframes → sessionStorage fallback
# Uses base64 + PDF.js iframe rendering. Dark-mode compatible.

import base64
import os
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path


def _load_pdf_base64(file_path: str) -> str:
    """Load a PDF file and return its base64-encoded content."""
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""


@st.cache_data(ttl=600, show_spinner=False)
def _cached_pdf_base64(file_path: str, _mtime: float) -> str:
    """Cache PDF base64 by path + modification time (auto-invalidates on file change)."""
    return _load_pdf_base64(file_path)


def get_pdf_base64(file_path: str) -> str:
    """Get base64 PDF with disk-aware caching."""
    if not os.path.exists(file_path):
        return ""
    mtime = os.path.getmtime(file_path)
    return _cached_pdf_base64(file_path, mtime)


def extract_unique_papers(sources: list[dict]) -> list[dict]:
    """Extract unique papers from sources, keeping the highest-scored entry per paper."""
    seen = {}
    for src in sources:
        name = src.get("paper_name", "")
        fp = src.get("file_path", "")
        if not name or not fp:
            continue
        if name not in seen or src.get("score", 0) > seen[name].get("score", 0):
            seen[name] = src
    return list(seen.values())


def render_pdf_toolbar(paper_name: str, page: int, total_papers: int):
    """Render the top toolbar for the PDF viewer panel."""
    display_name = paper_name.replace("_", " ").replace("-", " ")
    if len(display_name) > 40:
        display_name = display_name[:37] + "…"

    st.markdown(
        f"""<div class="pdf-toolbar">
          <div style="display:flex;align-items:center;gap:10px;overflow:hidden;flex:1">
            <span style="font-size:1.1rem">📄</span>
            <span class="paper-title">{display_name}</span>
            <span class="page-badge">Page {page}</span>
          </div>
          <div style="display:flex;align-items:center;gap:6px">
            <span class="chip-score" style="font-size:0.72rem">
              {total_papers} paper{'s' if total_papers != 1 else ''} cited
            </span>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_paper_selector(sources: list[dict]):
    """Render a dropdown to select which cited paper to view.
    Updates session state with selected paper path and page."""
    papers = extract_unique_papers(sources)
    if not papers:
        return

    if len(papers) == 1:
        p = papers[0]
        st.session_state.active_pdf_path = p["file_path"]
        if "active_pdf_page" not in st.session_state:
            st.session_state.active_pdf_page = p.get("page_number", 1)
        return

    paper_names = [p["paper_name"] for p in papers]
    paper_map = {p["paper_name"]: p for p in papers}

    current = st.session_state.get("active_pdf_paper_name", paper_names[0])
    if current not in paper_names:
        current = paper_names[0]

    selected = st.selectbox(
        "📚 Switch paper",
        paper_names,
        index=paper_names.index(current),
        key="pdf_paper_selector",
        format_func=lambda x: f"📄 {x.replace('_', ' ')}",
    )

    if selected:
        p = paper_map[selected]
        st.session_state.active_pdf_path = p["file_path"]
        st.session_state.active_pdf_paper_name = selected
        if st.session_state.get("_pdf_selector_prev") != selected:
            st.session_state.active_pdf_page = p.get("page_number", 1)
            st.session_state._pdf_selector_prev = selected


def render_pdf_viewer(file_path: str, page: int = 1, height: int = 720):
    """Render an embedded PDF viewer using base64-encoded PDF.js iframe.

    Args:
        file_path: Absolute path to the PDF file
        page: Page number to jump to (1-based)
        height: Viewer height in pixels
    """
    # ── Empty state ────────────────────────────────────────────
    if not file_path or not os.path.exists(file_path):
        st.markdown(
            """<div class="pdf-viewer-empty">
              <div style="font-size:3rem;margin-bottom:12px">📄</div>
              <div style="font-size:1rem;font-weight:600;color:#e1e4e8;margin-bottom:6px">
                No Paper Selected
              </div>
              <div style="font-size:0.85rem;color:#8b949e">
                Ask a question and the relevant paper will appear here automatically
              </div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    # ── Load PDF ───────────────────────────────────────────────
    paper_name = Path(file_path).stem
    pdf_b64 = get_pdf_base64(file_path)

    if not pdf_b64:
        st.error(f"Could not load PDF: {paper_name}")
        return

    # ── Render toolbar ─────────────────────────────────────────
    total_papers = len(st.session_state.get("cited_papers", []))
    render_pdf_toolbar(paper_name, page, max(total_papers, 1))

    # ── Build HTML viewer ──────────────────────────────────────
    # localStorage is blocked in cross-origin iframes in most browsers.
    # We use sessionStorage (same-origin, same session) as a fallback,
    # and wrap the access in try/catch so it never crashes the viewer.
    safe_name = paper_name.replace('"', "").replace("'", "")
    viewer_height = height - 80

    html_template = """
    <div id="pdf-root" style="color:#e6eef8;font-family:sans-serif">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-wrap:wrap">
            <button id="zoom_out" title="Zoom out"
                style="background:#1f2933;color:#fff;padding:6px 10px;border-radius:6px;
                       border:1px solid #30363d;cursor:pointer;font-size:1rem">−</button>
            <button id="zoom_in" title="Zoom in"
                style="background:#1f2933;color:#fff;padding:6px 10px;border-radius:6px;
                       border:1px solid #30363d;cursor:pointer;font-size:1rem">+</button>
            <button id="fit_width" title="Fit to width"
                style="background:#1f2933;color:#adb5bd;padding:6px 10px;border-radius:6px;
                       border:1px solid #30363d;cursor:pointer;font-size:0.8rem">Fit</button>
            <span id="zoom_label"
                style="color:#9aa6b2;font-size:0.82rem;min-width:40px">100%</span>
            <div style="flex:1"></div>
            <span style="font-size:0.85rem;color:#9aa6b2;overflow:hidden;
                         text-overflow:ellipsis;white-space:nowrap;max-width:180px">
                __SAFE_NAME__
            </span>
        </div>
        <div id="viewer"
            style="overflow:auto;height:__HEIGHT__px;border-radius:6px;
                   background:#0b0f12;padding:12px;scroll-behavior:smooth">
        </div>
    </div>
    <script src="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.min.js"></script>
    <script>
    (function(){
        const base64Data = "__PDF_B64__";
        const pageToOpen = __PAGE__;
        const stateKey   = 'pdfstate___FILE_KEY__';

        // Safe storage helper (localStorage blocked in iframes → sessionStorage fallback)
        const store = {
            get: function(k) {
                try { return JSON.parse(sessionStorage.getItem(k) || 'null'); } catch(e) { return null; }
            },
            set: function(k, v) {
                try { sessionStorage.setItem(k, JSON.stringify(v)); } catch(e) {}
            }
        };

        function b64ToBytes(b64) {
            const bin = atob(b64);
            const bytes = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
            return bytes;
        }

        const pdfData = b64ToBytes(base64Data);
        const container = document.getElementById('viewer');
        const zoomLabel = document.getElementById('zoom_label');

        const saved = store.get(stateKey);
        let scale = (saved && saved.scale) ? saved.scale : 1.2;
        let pdfRef = null;

        pdfjsLib.GlobalWorkerOptions.workerSrc =
            'https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js';

        function updateZoomLabel() {
            if (zoomLabel) zoomLabel.textContent = Math.round(scale * 100) + '%';
        }

        function renderAll() {
            while (container.firstChild) container.removeChild(container.firstChild);
            if (!pdfRef) return;

            updateZoomLabel();
            const promises = [];
            for (let p = 1; p <= pdfRef.numPages; p++) {
                const wrapper = document.createElement('div');
                wrapper.id = 'page-' + p;
                wrapper.style.cssText = 'margin-bottom:14px;display:flex;justify-content:center;';
                container.appendChild(wrapper);

                promises.push(pdfRef.getPage(p).then(function(page) {
                    const vp = page.getViewport({ scale: scale });
                    const canvas = document.createElement('canvas');
                    canvas.style.boxShadow = '0 2px 8px rgba(0,0,0,0.5)';
                    canvas.style.borderRadius = '4px';
                    canvas.width = vp.width;
                    canvas.height = vp.height;
                    wrapper.appendChild(canvas);
                    return page.render({ canvasContext: canvas.getContext('2d'), viewport: vp }).promise;
                }));
            }
            return Promise.all(promises);
        }

        function jumpToPage(p) {
            const el = document.getElementById('page-' + p);
            if (el) container.scrollTop = el.offsetTop - 8;
        }

        pdfjsLib.getDocument({ data: pdfData }).promise.then(function(pdf) {
            pdfRef = pdf;
            renderAll().then(function() {
                // Prioritise explicit page request over saved scroll position
                if (pageToOpen && pageToOpen > 1) {
                    jumpToPage(pageToOpen);
                } else if (saved && saved.scroll) {
                    container.scrollTop = saved.scroll;
                }
            });
        }).catch(function(err) {
            container.innerHTML = '<div style="color:#f85149;padding:20px">Failed to load PDF: ' + err.message + '</div>';
        });

        function saveState() {
            store.set(stateKey, { scale: scale, scroll: container.scrollTop });
        }

        document.getElementById('zoom_in').addEventListener('click', function() {
            scale = Math.min(3.0, parseFloat((scale + 0.25).toFixed(2)));
            renderAll().then(function() { jumpToPage(pageToOpen || 1); saveState(); });
        });
        document.getElementById('zoom_out').addEventListener('click', function() {
            scale = Math.max(0.5, parseFloat((scale - 0.25).toFixed(2)));
            renderAll().then(function() { jumpToPage(pageToOpen || 1); saveState(); });
        });
        document.getElementById('fit_width').addEventListener('click', function() {
            // fit to container width at scale ~1
            scale = 1.0;
            renderAll().then(function() { saveState(); });
        });

        container.addEventListener('scroll', function() { saveState(); }, { passive: true });
        window.addEventListener('beforeunload', saveState);
    })();
    </script>
    """

    # Safe placeholder substitution — no f-string brace issues
    file_key = abs(hash(file_path)) % (10**10)  # stable numeric key
    html = (
        html_template
        .replace("__PDF_B64__", pdf_b64)
        .replace("__PAGE__", str(page))
        .replace("__FILE_KEY__", str(file_key))
        .replace("__HEIGHT__", str(viewer_height))
        .replace("__SAFE_NAME__", safe_name)
    )

    st.markdown('<div class="pdf-viewer-container">', unsafe_allow_html=True)
    components.html(html, height=height + 20, scrolling=False)
    st.markdown("</div>", unsafe_allow_html=True)


def render_pdf_panel(sources: list[dict]):
    """Main entry point: renders the full PDF panel (selector + toolbar + viewer).
    Call this inside the right column of the split layout."""

    st.markdown(
        """<div style="font-size:0.75rem;color:#8b949e;font-weight:600;
            letter-spacing:0.08em;margin-bottom:8px">
            RESEARCH PAPER VIEWER
        </div>""",
        unsafe_allow_html=True,
    )

    papers = extract_unique_papers(sources)
    st.session_state.cited_papers = papers

    if not papers and not st.session_state.get("active_pdf_path"):
        render_pdf_viewer("", 1)
        return

    if papers:
        render_paper_selector(sources)

    file_path = st.session_state.get("active_pdf_path", "")
    page = st.session_state.get("active_pdf_page", 1)
    height = 860

    render_pdf_viewer(file_path, page, height)


def render_source_page_buttons(sources: list[dict]):
    """Render small 'jump to page' buttons for each source."""
    if not sources:
        return

    unique_pages = []
    seen = set()
    for src in sources:
        key = (src.get("paper_name"), src.get("page_number"))
        if key not in seen and src.get("file_path"):
            seen.add(key)
            unique_pages.append(src)

    if len(unique_pages) <= 1:
        return

    st.markdown("**📖 Jump to page:**")
    cols = st.columns(min(len(unique_pages), 4))
    for i, src in enumerate(unique_pages[:4]):
        with cols[i]:
            label = f"p.{src['page_number']}"
            if st.button(
                label,
                key=f"jump_{src['source_num']}_{src['page_number']}",
                use_container_width=True,
                help=f"{src['paper_name']} — {src['section']}",
            ):
                st.session_state.active_pdf_path = src["file_path"]
                st.session_state.active_pdf_page = src["page_number"]
                st.session_state.active_pdf_paper_name = src["paper_name"]
                st.rerun()
