# analytics/dashboard.py

import streamlit as st
import plotly.express     as px
import plotly.graph_objects as go
import pandas as pd
from analytics.tracker import AnalyticsTracker


def render_analytics_dashboard(tracker: AnalyticsTracker):
    """Full analytics dashboard using Plotly."""

    st.markdown("## 📊 Analytics Dashboard")
    st.markdown("Real-time insights into system usage and performance.")

    stats = tracker.get_summary_stats()

    # ── KPI Metrics ────────────────────────────────────────────
    st.markdown("### 🎯 Key Metrics")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Total Queries",    stats["total_queries"])
    c2.metric("Papers Uploaded",  stats["total_uploads"])
    c3.metric("Valid Papers",     stats["valid_uploads"])
    c4.metric("Rejected",         stats["rejected_uploads"],
              delta=f"-{stats['rejected_uploads']}", delta_color="inverse")
    c5.metric("Avg Response",    f"{stats['avg_response_ms']}ms")
    c6.metric("Unique Users",     stats["unique_users"])

    st.divider()

    # ── Row 1: User activity ──────────────────────────────────
    st.markdown("#### 👥 Top Users")
    user_data = tracker.get_user_activity()
    if user_data:
        df = pd.DataFrame(user_data)
        fig = px.bar(
            df, x="queries", y="username",
            orientation="h",
            color="queries",
            color_continuous_scale="Blues",
            template="plotly_dark",
            labels={"queries": "Queries", "username": "User"}
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            height=280,
            showlegend=False,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No user data yet.")

    # ── Row 2: Top keywords + Section usage ────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("#### 🔍 Most Searched Keywords")
        kw_data = tracker.get_top_questions(12)
        if kw_data:
            df = pd.DataFrame(kw_data)
            fig = px.bar(
                df, x="count", y="word",
                orientation="h",
                color="count",
                color_continuous_scale="Viridis",
                template="plotly_dark",
                labels={"count": "Frequency", "word": "Keyword"}
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=0, b=0),
                height=320,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No keyword data yet.")

    with col4:
        st.markdown("#### § Section Filter Usage")
        sec_data = tracker.get_section_filter_usage()
        if sec_data:
            df = pd.DataFrame(sec_data)
            fig = px.pie(
                df, values="count", names="section",
                color_discrete_sequence=px.colors.qualitative.Set3,
                template="plotly_dark"
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0),
                height=320,
                legend=dict(orientation="v", x=1.0)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No section filter data yet.")

    # ── Row 3: Response time histogram ─────────────────────────
    st.markdown("#### ⚡ Response Time Distribution")
    rt_data = tracker.get_response_times()
    if rt_data:
        fig = px.histogram(
            x=rt_data,
            nbins=20,
            color_discrete_sequence=["#7dd67d"],
            template="plotly_dark",
            labels={"x": "Response Time (ms)", "count": "Frequency"}
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            height=250
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No response time data yet.")

    # ── Upload validation stats ────────────────────────────────
    st.markdown("#### 📤 Upload Validation Results")
    v, r = stats["valid_uploads"], stats["rejected_uploads"]
    if v + r > 0:
        fig = go.Figure(go.Pie(
            labels=["✅ Valid Papers", "❌ Rejected"],
            values=[v, r],
            hole=0.5,
            marker_colors=["#4ff77a", "#f74f4f"]
        ))
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            height=280,
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No upload data yet.")