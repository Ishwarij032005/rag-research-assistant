# ui/pages/summary_page.py — Production v3.0
# Parallel summarization + disk cache + streaming + live progress

import time
import streamlit as st
from datetime import datetime
from ui.components import page_header, render_sources, empty_state
from utils.disk_cache import cache_get, cache_set, make_key, TTL_SUMMARY


def render_summary_page(get_embedder, get_llm, tracker):
    page_header(
        "Paper Summaries",
        "Generate structured summaries — per paper, combined, or section-wise.",
        "📝"
    )

    try:
        emb = get_embedder()
        llm = get_llm()
    except Exception as e:
        st.error(f"Backend error: {e}")
        return

    if emb.index is None:
        empty_state("📭", "No index", "Build index first from Upload tab.")
        return

    papers   = emb.get_papers()
    sections = emb.get_sections()

    mode = st.radio(
        "Summary mode:",
        ["📚 All Papers", "📄 Single Paper", "§ Section-wise"],
        horizontal=True
    )
    speed_mode = st.radio(
        "Speed & Detail Level:",
        ["⚡ Fast Mode (Default)", "📚 Detailed Mode (70B)"],
        horizontal=True
    )
    smode = "fast" if "Fast" in speed_mode else "detailed"
    st.divider()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ALL PAPERS — Parallel summarization with live progress
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if mode == "📚 All Papers":
        st.info(
            f"Summarizing **{len(papers)}** paper(s): "
            + " · ".join(f"`{p}`" for p in papers)
        )

        # Show active model
        st.caption(f"🚀 Speed Profile: `{smode.upper()}` | ⚡ Parallel mode enabled")

        key      = f"all_{smode}"
        disk_key = make_key("summary_all", smode, *papers)

        generate_clicked = st.button(
            "🚀 Generate All Summaries",
            type="primary", use_container_width=True
        )

        # Check session cache → disk cache → generate
        if generate_clicked and key not in st.session_state.summaries_cache:
            # Try disk cache first
            disk_res = cache_get("summaries", disk_key)
            if disk_res:
                st.session_state.summaries_cache[key] = disk_res
                st.toast("📦 Loaded from persistent cache!", icon="⚡")
            else:
                # Progressive UI Setup
                st.info("Starting progressive parallel summarization...")
                
                # Create a placeholder container for each paper
                containers = {}
                for p in papers:
                    containers[p] = st.empty()
                    with containers[p].container():
                        with st.expander(f"⏳ Processing: {p}"):
                            st.markdown(f"*{'Aggressively trimming context...' if smode == 'fast' else 'Reading full context...'}*")

                t0  = time.time()
                
                # Consume the asynchronous generator
                for step in llm.summarize_all_papers(emb.chunks, mode=smode):
                    if step["type"] == "paper":
                        pname = step["paper_name"]
                        res = step["result"]
                        
                        # Instantly inject the finished summary into its container
                        with containers[pname].container():
                            with st.expander(f"✅ {pname}"):
                                st.markdown(res["summary"])
                                
                    elif step["type"] == "synthesis":
                        final_res = step["result"]

                elapsed_ms = int((time.time() - t0) * 1000)

                # Store in session + disk cache
                st.session_state.summaries_cache[key] = final_res
                cache_set("summaries", disk_key, final_res, ttl=TTL_SUMMARY)
                tracker.track_summary("all", "all", elapsed_ms)

                # Show timing badge
                st.success(
                    f"🎉 Generated in **{elapsed_ms/1000:.1f}s** "
                    f"(parallel, {len(papers)} papers)"
                )

        if key in st.session_state.summaries_cache:
            res = st.session_state.summaries_cache[key]
            model_used = res.get('meta_ref', ['llama-3.1-8b-instant'])[0]
            mode_label = res.get('mode_label', '⚡ Fast Mode')
            
            if not generate_clicked:
                st.caption(f"📦 Cached result | {mode_label} — `{model_used}`")
            else:
                st.caption(f"✨ Generated | {mode_label} — `{model_used}`")

            for pname, data in res["individual_summaries"].items():
                with st.expander(f"📄 {pname}"):
                    st.markdown(data["summary"])

            st.markdown("### 🔗 Combined Synthesis")
            st.markdown(
                f"<div class='summary-card'>{res['combined_summary']}</div>",
                unsafe_allow_html=True
            )
            _download_btn(
                "all_papers",
                "\n\n".join(
                    d["summary"] for d in res["individual_summaries"].values()
                ) + "\n\nSYNTHESIS:\n" + res["combined_summary"]
            )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SINGLE PAPER — Streaming summary
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif mode == "📄 Single Paper":
        sel = st.selectbox("Select paper:", papers)
        key      = f"p_{sel}_{smode}"
        disk_key = make_key("summary_paper", smode, sel)

        generate_clicked = st.button(
            "🚀 Generate", type="primary", use_container_width=True
        )

        if generate_clicked and key not in st.session_state.summaries_cache:
            # Disk cache check
            disk_res = cache_get("summaries", disk_key)
            if disk_res:
                st.session_state.summaries_cache[key] = disk_res
                st.toast("📦 From persistent cache!", icon="⚡")
            else:
                t0 = time.time()
                with st.spinner(f"📝 Summarizing {sel} ({smode})..."):
                    res = llm.summarize_paper(sel, emb.chunks, stream=True, mode=smode)
                    full_summary = st.write_stream(res["summary"])
                    res["summary"] = full_summary
                elapsed = int((time.time() - t0) * 1000)
                st.session_state.summaries_cache[key] = res
                
                # Prevent Cache Poisoning
                if "❌ Stream error" not in res["summary"] and "❌ Fallback also failed" not in res["summary"]:
                    cache_set("summaries", disk_key, res, ttl=TTL_SUMMARY)
                
                tracker.track_summary("single", sel, elapsed)

        if key in st.session_state.summaries_cache:
            res = st.session_state.summaries_cache[key]
            model_used = res.get('meta_ref', ['llama-3.1-8b-instant'])[0]
            mode_label = res.get('mode_label', '⚡ Fast Mode')
            
            if not generate_clicked:
                st.caption(f"📦 Cached | {mode_label} — `{model_used}`")
            else:
                st.caption(f"✨ Generated | {mode_label} — `{model_used}`")
                st.markdown(
                    f"<div class='summary-card'>{res['summary']}</div>",
                    unsafe_allow_html=True
                )
            _download_btn(sel, res["summary"])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION-WISE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif mode == "§ Section-wise":
        c1, c2 = st.columns(2)
        sel_p = c1.selectbox("Paper:", papers, key="sw_p")
        sel_s = c2.selectbox("Section:", sections, key="sw_s")
        key      = f"sw_{sel_p}_{sel_s}_{smode}"
        disk_key = make_key("summary_section", smode, sel_p, sel_s)

        generate_clicked = st.button(
            "🚀 Generate", type="primary", use_container_width=True
        )

        if generate_clicked and key not in st.session_state.summaries_cache:
            disk_res = cache_get("summaries", disk_key)
            if disk_res:
                st.session_state.summaries_cache[key] = disk_res
                st.toast("📦 From persistent cache!", icon="⚡")
            else:
                t0 = time.time()
                with st.spinner(f"Summarizing section ({smode})..."):
                    res = llm.summarize_paper(
                        sel_p, emb.chunks, section=sel_s, stream=True, mode=smode
                    )
                    st.markdown(f"#### {res['section']} — {res['paper_name']}")
                    full_summary = st.write_stream(res["summary"])
                    res["summary"] = full_summary
                elapsed = int((time.time() - t0) * 1000)
                st.session_state.summaries_cache[key] = res
                
                # Prevent Cache Poisoning
                if "❌ Stream error" not in res["summary"] and "❌ Fallback also failed" not in res["summary"]:
                    cache_set("summaries", disk_key, res, ttl=TTL_SUMMARY)
                
                tracker.track_summary("section", sel_p, elapsed)

        if key in st.session_state.summaries_cache:
            res = st.session_state.summaries_cache[key]
            model_used = res.get('meta_ref', ['llama-3.1-8b-instant'])[0]
            mode_label = res.get('mode_label', '⚡ Fast Mode')
            
            if not generate_clicked:
                st.caption(f"📦 Cached | {mode_label} — `{model_used}`")
            else:
                st.caption(f"✨ Generated | {mode_label} — `{model_used}`")
                st.markdown(f"#### {res['section']} — {res['paper_name']}")
                st.markdown(
                    f"<div class='summary-card'>{res['summary']}</div>",
                    unsafe_allow_html=True
                )
            if res.get("sources"):
                render_sources(res["sources"])
            _download_btn(f"{sel_p}_{sel_s}", res["summary"])


def _download_btn(name: str, content: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "📥 Download",
        data=content,
        file_name=f"summary_{name}_{ts}.txt",
        mime="text/plain"
    )