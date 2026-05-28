# ui/components.py

import streamlit as st


def page_header(title: str, subtitle: str = "", icon: str = ""):
    """Consistent page header across all tabs."""
    if icon:
        st.markdown(f"## {icon} {title}")
    else:
        st.markdown(f"## {title}")
    if subtitle:
        st.markdown(
            f"<p style='color:#8b949e;margin-top:-10px;"
            f"margin-bottom:16px'>{subtitle}</p>",
            unsafe_allow_html=True
        )


def source_card(src: dict):
    """
    Render a single source card with chips.
    Safe to use inside st.chat_message (no expander).
    Includes 'View in PDF' button if file_path is available.
    """
    score_pct = int(src.get("score", 0) * 100)

    # Check if this source is the currently active PDF
    active_path = st.session_state.get("active_pdf_path", "")
    active_page = st.session_state.get("active_pdf_page", 0)
    is_active = (
        src.get("file_path") == active_path
        and src.get("page_number") == active_page
    )
    card_class = "source-card active-source" if is_active else "source-card"

    st.markdown(
        f"""<div class="{card_class}">
          <div class="source-header">
            <span style="font-weight:700;color:#e1e4e8">
              [Source {src['source_num']}]
            </span>
            <span class="chip-paper">📄 {src['paper_name']}</span>
            <span class="chip-section">§ {src['section']}</span>
            <span class="chip-page">p.{src['page_number']}</span>
            <span class="chip-score">↑ {score_pct}%</span>
          </div>
          <div style="color:#8b949e;font-size:0.85em;
                      line-height:1.6;margin-top:6px;">
            {src['snippet'][:280]}...
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # "View in PDF" button — updates the PDF panel
    if src.get("file_path"):
        if st.button(
            f"📖 View p.{src['page_number']}",
            key=f"viewpdf_{src['source_num']}_{src.get('paper_name','')}_{src.get('page_number',0)}",
            use_container_width=False,
            help=f"Open {src['paper_name']} at page {src['page_number']}",
        ):
            st.session_state.active_pdf_path = src["file_path"]
            st.session_state.active_pdf_page = src["page_number"]
            st.session_state.active_pdf_paper_name = src["paper_name"]
            st.rerun()


def render_sources(sources: list[dict], label: str = "📚 Sources"):
    """Render all source cards with a header."""
    if not sources:
        return
    st.markdown(f"**{label}**")
    for src in sources:
        source_card(src)


def validation_result_card(is_valid: bool, confidence: float,
                            message: str, details: dict):
    """Show validation result with confidence bar."""
    pct = int(confidence * 100)

    if is_valid:
        sections = details.get("sections", {}).get(
            "found_sections", []
        )
        st.markdown(
            f"""<div class="valid-badge">
              <div style="font-size:1.2rem;font-weight:700;
                          color:#7dd67d;margin-bottom:8px">
                ✅ Valid Research Paper
              </div>
              <div style="color:#8b949e;font-size:0.88em">
                Confidence: <strong style="color:#e1e4e8">
                {pct}%</strong>
              </div>
              <div class="confidence-bar-wrap">
                <div class="confidence-bar-fill"
                     style="width:{pct}%"></div>
              </div>
              <div style="font-size:0.83em;color:#7dd67d;
                          margin-top:8px">
                Sections found: {', '.join(sections)}
              </div>
            </div>""",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""<div class="invalid-badge">
              <div style="font-size:1.2rem;font-weight:700;
                          color:#f85149;margin-bottom:8px">
                ❌ Not a Research Paper
              </div>
              <div style="color:#e1e4e8;font-size:0.9em;
                          margin-bottom:8px">
                {message}
              </div>
              <div style="color:#8b949e;font-size:0.83em">
                Confidence score: {pct}%
              </div>
            </div>""",
            unsafe_allow_html=True
        )


def user_avatar(display_name: str, color: str):
    """Small colored avatar circle with initials."""
    initials = "".join(
        w[0].upper() for w in display_name.split()[:2]
    ) or "U"
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:10px;
                        padding:10px 0">
          <div style="width:36px;height:36px;border-radius:50%;
                      background:{color};display:flex;
                      align-items:center;justify-content:center;
                      font-weight:700;font-size:0.85rem;color:white">
            {initials}
          </div>
          <div>
            <div style="font-weight:600;font-size:0.92rem">
              {display_name}
            </div>
          </div>
        </div>""",
        unsafe_allow_html=True
    )


def empty_state(icon: str, title: str, subtitle: str):
    """Show a centered empty state illustration."""
    st.markdown(
        f"""<div style="text-align:center;padding:60px 20px;
                        color:#8b949e">
          <div style="font-size:3.5rem">{icon}</div>
          <div style="font-size:1.1rem;font-weight:600;
                      color:#e1e4e8;margin:12px 0 6px">
            {title}
          </div>
          <div style="font-size:0.9rem">{subtitle}</div>
        </div>""",
        unsafe_allow_html=True
    )