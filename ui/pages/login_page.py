
# ui/pages/login_page.py

import streamlit as st
from auth.auth_manager import AuthManager


def render_login_page(auth: AuthManager):
    """
    Renders a centered login / signup page.
    Shown when user is not authenticated.
    """

    # Initialize session state
    if "show_login" not in st.session_state:
        st.session_state["show_login"] = False
    if "signup_message" not in st.session_state:
        st.session_state["signup_message"] = ""
    if "signup_success" not in st.session_state:
        st.session_state["signup_success"] = False

    # Center the auth card
    _, center, _ = st.columns([1, 1.6, 1])

    with center:
        st.markdown(
            """<div class="auth-logo">🔬</div>
            <div class="auth-title">Research Assistant</div>
            <div class="auth-subtitle">
                AI-powered scientific paper analysis
            </div>""",
            unsafe_allow_html=True
        )

        # Tabs
        tab_login, tab_signup = st.tabs(["🔑 Login", "✨ Sign Up"])

        # ── LOGIN ──────────────────────────────────────────────
        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)

            username = st.text_input(
                "Username",
                placeholder="your_username",
                key="login_user"
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••",
                key="login_pass"
            )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                "🔑 Login",
                use_container_width=True,
                type="primary",
                key="btn_login"
            ):

                if not username or not password:
                    st.error("Please fill in all fields.")

                else:
                    with st.spinner("Authenticating..."):
                        ok, msg = auth.login(username, password)

                    if ok:
                        st.success(msg)
                        st.rerun()

                    else:
                        st.error(msg)

        # ── SIGNUP ─────────────────────────────────────────────
        with tab_signup:
            st.markdown("<br>", unsafe_allow_html=True)

            if st.session_state.get("signup_success"):
                st.success(st.session_state["signup_message"])
                st.session_state["signup_success"] = False
                st.session_state["signup_message"] = ""
                st.session_state["signup_user"] = ""
                st.session_state["signup_email"] = ""
                st.session_state["signup_pass"] = ""
                st.session_state["signup_confirm"] = ""

            new_user = st.text_input(
                "Username",
                placeholder="choose_a_username",
                key="signup_user"
            )

            new_email = st.text_input(
                "Email",
                placeholder="you@example.com",
                key="signup_email"
            )

            new_pass = st.text_input(
                "Password",
                type="password",
                placeholder="Min 8 chars, 1 uppercase, 1 number",
                key="signup_pass"
            )

            confirm = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="••••••••",
                key="signup_confirm"
            )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                "✨ Create Account",
                use_container_width=True,
                type="primary",
                key="btn_signup"
            ):

                if not all([new_user, new_email, new_pass, confirm]):
                    st.error("Please fill in all fields.")

                else:
                    with st.spinner("Creating account..."):
                        # Convert username to lowercase
                        new_user = new_user.lower().strip()
                        
                        ok, msg = auth.signup(
                            new_user,
                            new_email,
                            new_pass,
                            confirm
                        )

                    if ok:
                        st.session_state["signup_success"] = True
                        st.session_state["signup_message"] = msg + " Please log in."
                        st.rerun()

                    else:
                        st.error(msg)

        # ── Demo hint ──────────────────────────────────────────
        st.markdown(
            "<div style='text-align:center;color:#8b949e;"
            "font-size:0.8rem;margin-top:20px'>"
            "💡 First account created becomes Admin"
            "</div>",
            unsafe_allow_html=True
        )
