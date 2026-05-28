# ui/pages/chat_page.py — Production v4.1
# Split-Screen AI Research Workspace
# Left: Chat + Citations + Streaming | Right: PDF Viewer
# Fixed: session_state.pop() → get()+del, quick question row bug, prefill state handling

import time
import streamlit as st
from ui.components import page_header, render_sources, empty_state
from ui.pdf_viewer import (
    render_pdf_panel,
    render_source_page_buttons,
    extract_unique_papers,
)
from utils.disk_cache import cache_get, cache_set, make_key, TTL_QA
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_all_cited_sources() -> list[dict]:
    """Collect all sources from chat history for the PDF panel."""
    all_sources = []
    for turn in st.session_state.chat_history:
        for src in turn.get("sources", []):
            all_sources.append(src)
    return all_sources


def _auto_select_pdf(sources: list[dict]):
    """Auto-select the highest-scored source's PDF after a new answer."""
    if not sources:
        return
    best = max(sources, key=lambda s: s.get("score", 0))
    if best.get("file_path"):
        st.session_state.active_pdf_path = best["file_path"]
        st.session_state.active_pdf_page = best.get("page_number", 1)
        st.session_state.active_pdf_paper_name = best.get("paper_name", "")


def _render_chat_column(get_embedder, get_llm, auth, tracker):
    """Render the left chat column with full Q&A functionality."""
    try:
        emb = get_embedder()
        llm = get_llm()
    except Exception as e:
        st.error(f"Backend error: {e}")
        return

    if emb.index is None:
        empty_state(
            "📭",
            "No papers indexed yet",
            "Go to the Upload tab to add research papers, then build the index.",
        )
        return

    # ── Quick Questions ────────────────────────────────────────
    examples = [
        "What is the main contribution?",
        "What methodology was used?",
        "What were the key results?",
        "What datasets were used?",
        "What are the limitations?",
        "How does the model work?",
    ]

    is_proc = st.session_state.get("is_processing", False)

    st.markdown("#### 💡 Quick Questions")
    row1 = st.columns(3)
    row2 = st.columns(3)
    for i in range(3):
        if row1[i].button(
            examples[i], key=f"q{i}", use_container_width=True, disabled=is_proc
        ):
            st.session_state.prefill_q = examples[i]
            st.rerun()
    for i in range(3):
        if row2[i].button(
            examples[i + 3],
            key=f"q{i+3}",
            use_container_width=True,
            disabled=is_proc,
        ):
            st.session_state.prefill_q = examples[i + 3]
            st.rerun()

    st.divider()

    # ── Chat history ───────────────────────────────────────────
    for turn in st.session_state.chat_history:
        with st.chat_message("user"):
            st.markdown(turn["question"])
        with st.chat_message("assistant"):
            st.markdown(turn["answer"])
            if turn.get("sources"):
                with st.expander(f"📚 View {len(turn['sources'])} sources"):
                    render_sources(turn["sources"])
                    render_source_page_buttons(turn["sources"])

    # Paper selector for cited papers
    all_sources = _get_all_cited_sources()
    unique_papers = extract_unique_papers(all_sources)
    if unique_papers:
        if len(unique_papers) > 1:
            paper_names = [p["paper_name"] for p in unique_papers]
            current = st.session_state.get("active_pdf_paper_name", paper_names[0])
            try:
                idx = paper_names.index(current)
            except ValueError:
                idx = 0

            sel = st.selectbox(
                "📚 Open cited paper",
                paper_names,
                index=idx,
                key="chat_pdf_select",
                format_func=lambda x: x.replace("_", " "),
            )

            if sel and sel != st.session_state.get("active_pdf_paper_name"):
                chosen = next(
                    (p for p in unique_papers if p["paper_name"] == sel),
                    unique_papers[0],
                )
                st.session_state.active_pdf_path = chosen["file_path"]
                st.session_state.active_pdf_paper_name = sel
                st.session_state.active_pdf_page = chosen.get("page_number", 1)
        else:
            p = unique_papers[0]
            if st.session_state.get("active_pdf_path") != p.get("file_path"):
                st.session_state.active_pdf_path = p.get("file_path")
                st.session_state.active_pdf_page = p.get("page_number", 1)
                st.session_state.active_pdf_paper_name = p.get("paper_name")

    # ── Input & Generation ─────────────────────────────────────
    # Fixed: st.session_state.pop() doesn't exist → use get() + conditional delete
    prefill = st.session_state.get("prefill_q", "")
    if prefill:
        del st.session_state["prefill_q"]

    question = (
        st.chat_input("Ask a question about your papers...", disabled=is_proc)
        or prefill
    )

    if question:
        pf = st.session_state.get("filter_paper", "All Papers")
        sf = st.session_state.get("filter_section", "All Sections")
        tk = st.session_state.get("top_k", 5)
        pf = None if pf == "All Papers" else pf
        sf = None if sf == "All Sections" else sf

        disk_key = make_key("qa", question.strip().lower(), pf, sf, tk)

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            disk_res = cache_get("qa", disk_key)

            if disk_res:
                st.caption("📦 Cached answer")
                st.markdown(disk_res["answer"])
                turn = disk_res
                _auto_select_pdf(turn.get("sources", []))
            else:
                last_time = st.session_state.get("last_query_time", 0.0)
                if time.time() - last_time < 3.0:
                    st.warning("⏳ Please wait a few seconds before asking another question.")
                    return

                st.session_state.is_processing = True

                try:
                    with st.spinner("🔍 Retrieving context..."):
                        t0 = time.time()
                        retrieved = emb.search(
                            question,
                            top_k=tk,
                            paper_filter=pf,
                            section_filter=sf,
                        )
                        retrieval_ms = int((time.time() - t0) * 1000)

                    if not retrieved:
                        st.warning("No matching content found. Try removing filters.")
                        st.session_state.is_processing = False
                        return

                    with st.spinner("🤖 Generating answer..."):
                        t1 = time.time()
                        result = llm.answer_question(question, retrieved, stream=True)
                        full_answer = st.write_stream(result["answer"])
                        llm_ms = int((time.time() - t1) * 1000)

                    model_used = result.get("meta_ref", [""])[0]
                    mode_label = result.get("mode_label", "⚡ Fast Mode")

                    st.caption(
                        f"{mode_label} — `{model_used}` | "
                        f"⏱️ Retrieval: {retrieval_ms}ms | "
                        f"Generation: {llm_ms}ms | "
                        f"Tokens: ~{result['tokens_estimated']}"
                    )

                    turn = {
                        "question": question,
                        "answer": full_answer,
                        "sources": result["sources"],
                        "stats": {
                            "retrieval_ms": retrieval_ms,
                            "llm_ms": llm_ms,
                            "tokens": result["tokens_estimated"],
                        },
                        "model_used": result.get("meta_ref", [""])[0],
                        "mode_label": result.get("mode_label", "⚡ Fast Mode"),
                    }

                    if (
                        "❌ Stream error" not in full_answer
                        and "❌ Fallback also failed" not in full_answer
                    ):
                        cache_set("qa", disk_key, turn, ttl=TTL_QA)

                    _auto_select_pdf(result["sources"])

                finally:
                    st.session_state.is_processing = False
                    st.session_state.last_query_time = time.time()

            if turn.get("sources"):
                with st.expander(f"📚 View {len(turn['sources'])} sources"):
                    render_sources(turn["sources"])
                    render_source_page_buttons(turn["sources"])

            st.session_state.chat_history.append(turn)

            top_score = (
                turn.get("sources")[0].get("score", 0)
                if turn.get("sources")
                else 0
            )
            total_ms = (
                turn.get("stats", {}).get("retrieval_ms", 0)
                + turn.get("stats", {}).get("llm_ms", 0)
            )
            tracker.track_query(
                question,
                pf,
                sf,
                len(turn.get("sources", [])),
                total_ms,
                top_score,
            )
            auth.increment_query_count()

    # ── Download chat ──────────────────────────────────────────
    if st.session_state.chat_history:
        st.divider()
        lines = ["RESEARCH ASSISTANT CHAT\n" + "=" * 50]
        for i, t in enumerate(st.session_state.chat_history, 1):
            lines.append(f"\nQ{i}: {t['question']}")
            lines.append(f"A{i}: {t['answer']}")
            for s in t.get("sources", []):
                lines.append(
                    f"  [{s['source_num']}] {s['paper_name']} "
                    f"p.{s['page_number']} | {s['section']}"
                )
        col_dl, col_clr = st.columns([3, 1])
        col_dl.download_button(
            "📥 Download Chat",
            data="\n".join(lines),
            file_name="chat_history.txt",
            mime="text/plain",
        )
        if col_clr.button("🗑️ Clear Chat", help="Clear chat history"):
            st.session_state.chat_history = []
            st.session_state.pop("active_pdf_path", None)
            st.session_state.pop("active_pdf_page", None)
            st.session_state.pop("active_pdf_paper_name", None)
            st.rerun()


def _render_pdf_column():
    """Render the right PDF viewer column."""
    all_sources = _get_all_cited_sources()
    render_pdf_panel(all_sources)


def render_chat_page(get_embedder, get_llm, auth, tracker):
    """Main entry point: renders the split-screen research workspace."""

    page_header(
        "Research Workspace",
        "Ask anything — the relevant paper opens automatically alongside your answer.",
        "🔬",
    )

    # ── Split-Screen Layout ────────────────────────────────────
    has_pdf = bool(st.session_state.get("active_pdf_path"))

    if has_pdf or st.session_state.get("chat_history"):
        chat_col, pdf_col = st.columns([11, 9], gap="medium")
    else:
        chat_col, pdf_col = st.columns([13, 7], gap="medium")

    with chat_col:
        st.markdown(
            """<div style="font-size:0.75rem;color:#8b949e;font-weight:600;
                letter-spacing:0.08em;margin-bottom:8px">
                AI CHAT ASSISTANT
            </div>""",
            unsafe_allow_html=True,
        )
        _render_chat_column(get_embedder, get_llm, auth, tracker)

    with pdf_col:
        _render_pdf_column()
