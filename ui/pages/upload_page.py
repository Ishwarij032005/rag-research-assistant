# ui/pages/upload_page.py — Production v3.1
# Fixed: background thread closure bug (dest captured by reference in loop → pass by value via args)
# Fixed: get_embedder.clear() called inside thread → moved to main thread only

import time
import threading
import streamlit as st
from pathlib import Path
import pandas as pd

from validation_utils.pdf_validator import validate_uploaded_file
from rag.pdf_loader           import load_pdf, load_all_pdfs
from rag.chunker              import chunk_pages
from ui.components            import page_header, validation_result_card, empty_state
from utils.config             import PAPERS_DIR
from utils.logger             import get_logger

logger = get_logger(__name__)


def render_upload_page(get_embedder, auth, tracker):
    page_header(
        "Upload Research Papers",
        "Only valid academic research papers accepted. Auto-indexes instantly.",
        "📤"
    )

    # ── Current papers grid ────────────────────────────────────
    st.markdown("### 📚 Current Knowledge Base")
    existing = sorted(PAPERS_DIR.glob("*.pdf"))

    if existing:
        cols = st.columns(4)
        for i, f in enumerate(existing):
            with cols[i % 4]:
                kb = f.stat().st_size / 1024
                st.markdown(
                    f"<div class='pro-card' style='padding:14px'>"
                    f"<div style='font-size:1.5rem'>📄</div>"
                    f"<div style='font-weight:600;font-size:0.85rem;"
                    f"margin:4px 0;color:#e1e4e8'>"
                    f"{f.stem[:20]}</div>"
                    f"<div style='color:#8b949e;font-size:0.78rem'>"
                    f"{kb:.0f} KB</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    else:
        empty_state("📭", "No papers yet", "Upload below to get started")

    st.divider()

    # ── Upload UI ──────────────────────────────────────────────
    st.markdown("### ➕ Upload New Papers")
    st.info(
        "🤖 **Smart Validation Active** — Auto-indexes immediately after upload."
    )

    uploaded = st.file_uploader(
        "Drag & drop research paper PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="uploader_v3"
    )

    if not uploaded:
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.markdown(
            "**✅ Accepted**\n\n"
            "Journal papers, conference papers, "
            "preprints, theses, technical reports"
        )
        c2.markdown(
            "**❌ Rejected**\n\n"
            "Resumes, books, invoices, image-only PDFs, "
            "random documents"
        )
        c3.markdown(
            "**💡 Best Practices**\n\n"
            "Use simple filenames. "
            "Text-based PDFs work best. "
            "3–200 pages."
        )
        return

    # ── Preview table ──────────────────────────────────────────
    st.markdown(f"**{len(uploaded)} file(s) selected**")
    rows = []
    for f in uploaded:
        safe = (f.name.replace(" ", "_").replace("(", "")
                .replace(")", "").lower())
        rows.append({
            "File"      : f.name,
            "Safe Name" : safe,
            "Size"      : f"{len(f.getvalue())/1024:.0f} KB",
            "Exists"    : "⚠️ Overwrite" if (PAPERS_DIR / safe).exists() else "✅ New"
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    if not st.button("🚀 Upload & Auto-Index", type="primary", use_container_width=True):
        return

    # ── Process & Auto-Index ──────────────────────────────────
    emb      = get_embedder()
    progress = st.progress(0)
    status   = st.empty()
    results  = []
    accepted = []

    for i, uf in enumerate(uploaded):
        safe = (uf.name.replace(" ", "_").replace("(", "")
                .replace(")", "").lower())
        dest = PAPERS_DIR / safe

        # 1. Validate
        status.markdown(f"🔍 **Validating** `{safe}`...")
        is_valid, msg, details = validate_uploaded_file(uf, str(PAPERS_DIR))
        confidence = details.get("confidence", 0.0) if isinstance(details, dict) else 0.0
        pages      = details.get("total_pages", 0)  if isinstance(details, dict) else 0

        validation_result_card(is_valid, confidence, msg, details)
        tracker.track_upload(safe, is_valid, confidence, pages)

        if not is_valid:
            results.append(f"❌ Rejected: {safe} — {msg}")
            progress.progress((i + 1) / len(uploaded))
            continue

        paper_name = Path(safe).stem
        if emb.index is not None and paper_name in emb.get_papers():
            results.append(f"⚠️ Skipped: `{safe}` already exists in the Knowledge Base.")
            progress.progress((i + 1) / len(uploaded))
            continue

        # 2. Save
        status.markdown(f"💾 **Saving** `{safe}`...")
        with open(dest, "wb") as fh:
            fh.write(uf.getvalue())
        accepted.append(str(dest))
        results.append(f"✅ Saved: {safe}")

        # 3. Background indexing
        # FIX: pass dest_path and safe_name as explicit args (not closure over loop vars)
        status.markdown(f"⚙️ **Queued for Background Indexing** `{safe}`...")

        def _bg_index(dest_path: str, safe_name: str, embedder):
            """Run in daemon thread — never call get_embedder.clear() here."""
            try:
                pages_data = load_pdf(str(dest_path))
                chunks     = chunk_pages(pages_data)
                if embedder.index is not None and embedder.index.ntotal > 0:
                    embedder.add_chunks(chunks)
                else:
                    embedder.build_index(chunks)
                logger.info(
                    f"Background indexing complete for {safe_name} "
                    f"({len(chunks)} chunks)"
                )
            except Exception as e:
                logger.error(f"Background indexing failed for {safe_name}: {e}")

        # Pass values by position so the closure captures the right objects
        t = threading.Thread(
            target=_bg_index,
            args=(str(dest), safe, emb),
            daemon=True
        )
        t.start()

        results.append(f"⚡ Queued for indexing: {Path(safe).stem}")
        progress.progress((i + 1) / len(uploaded))

    if accepted:
        # Clear caches in the main thread (safe to do here)
        from utils.disk_cache import cache_clear
        st.session_state.summaries_cache = {}
        cache_clear("qa")
        cache_clear("summaries")
        # NOTE: do NOT call get_embedder.clear() here — the bg thread is
        # using that same embedder object and clearing it causes data loss.

    status.markdown("✅ **Processing Complete!**")
    progress.progress(1.0)

    with st.expander("📋 Processing Log", expanded=True):
        for r in results:
            st.markdown(f"• {r}")

    if accepted:
        st.success(f"🎉 {len(accepted)} paper(s) uploaded and queued for indexing!")
        st.info(
            "💡 The index is being updated in the background. "
            "Refresh the sidebar in a few seconds to see updated chunk counts."
        )
        st.balloons()
