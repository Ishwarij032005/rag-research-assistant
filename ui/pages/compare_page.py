# ui/pages/compare_page.py — Production v3.0

import time
import streamlit as st
from datetime import datetime
from ui.components import page_header, render_sources, empty_state
from utils.disk_cache import cache_get, cache_set, make_key, TTL_SUMMARY


def render_compare_page(get_embedder, get_llm, tracker):
    page_header(
        "Compare Papers",
        "Side-by-side structured comparison of methodology, results, and contributions.",
        "⚖️"
    )

    try:
        emb = get_embedder()
        llm = get_llm()
    except Exception as e:
        st.error(f"Backend error: {e}")
        return

    papers = emb.get_papers() if emb.index else []

    if len(papers) < 2:
        empty_state(
            "⚖️",
            "Need 2+ papers",
            "Upload at least 2 research papers to compare them."
        )
        return

    c1, c2 = st.columns([2, 1])
    selected = c1.multiselect(
        "Select papers (2 or more):",
        papers, default=papers[:2]
    )
    aspect = c2.selectbox(
        "Compare aspect:",
        ["overall", "methodology", "results", "contribution"]
    )

    if len(selected) < 2:
        st.info("Please select at least 2 papers.")
        return

    generate_clicked = st.button(
        "⚖️ Generate Comparison",
        type="primary", use_container_width=True
    )
    
    key      = f"cmp_{'_'.join(sorted(selected))}_{aspect}"
    disk_key = make_key("compare", *sorted(selected), aspect)

    if generate_clicked and key not in st.session_state.summaries_cache:
        disk_res = cache_get("summaries", disk_key)
        if disk_res:
            st.session_state.summaries_cache[key] = disk_res
            st.toast("📦 Loaded from persistent cache!", icon="⚡")
        else:
            with st.spinner("Comparing papers..."):
                t0  = time.time()
                st.markdown(
                    "### " + " vs ".join(f"`{p}`" for p in selected)
                )
                st.caption(f"Aspect: {aspect}")
                st.markdown("---")
                
                res = llm.compare_papers(selected, emb.chunks, aspect=aspect, stream=True)
                full_comparison = st.write_stream(res["comparison"])
                res["comparison"] = full_comparison
                
                elapsed = int((time.time() - t0) * 1000)
                
                model_used = res.get('meta_ref', ['llama-3.3-70b-versatile'])[0]
                mode_label = res.get('mode_label', '🧠 Deep Compare')
                st.caption(f"✨ Generated | {mode_label} — `{model_used}`")
            
            st.session_state.summaries_cache[key] = res
            
            # Prevent Cache Poisoning
            if "❌ Stream error" not in res["comparison"] and "❌ Fallback also failed" not in res["comparison"]:
                cache_set("summaries", disk_key, res, ttl=TTL_SUMMARY)
                
            tracker.track_summary("compare", aspect, elapsed)

    if key in st.session_state.summaries_cache:
        res = st.session_state.summaries_cache[key]
        if not generate_clicked:
            st.markdown(
                "### " + " vs ".join(f"`{p}`" for p in res["paper_names"])
            )
            st.caption(f"Aspect: {res['aspect']}")
            st.markdown("---")
            
            model_used = res.get('meta_ref', ['llama-3.3-70b-versatile'])[0]
            mode_label = res.get('mode_label', '🧠 Deep Compare')
            st.caption(f"📦 Cached | {mode_label} — `{model_used}`")
            st.markdown(
                f"<div class='summary-card'>{res['comparison']}</div>",
                unsafe_allow_html=True
            )
            
        if res.get("sources"):
            with st.expander(f"📚 View {len(res['sources'])} sources used for comparison"):
                render_sources(res["sources"])

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "📥 Download",
            data=res["comparison"],
            file_name=f"comparison_{'_vs_'.join(res['paper_names'])}_{ts}.txt",
            mime="text/plain"
        )