# auth/auth_manager.py

import streamlit as st
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo.errors import ConfigurationError

from auth.models import create_user_doc
from auth.password_utils import (
    hash_password, verify_password,
    validate_password_strength, validate_email
)
from utils.config  import MONGODB_URI, MONGODB_DB
from utils.logger  import get_logger

logger = get_logger(__name__)


class AuthManager:
    """
    Handles all authentication operations:
    - signup, login, logout
    - session management via Streamlit session_state
    - role-based access control
    """

    def __init__(self):
        self.db = self._connect_db()

    def _connect_db(self):
        """Connect to MongoDB. Returns None if unavailable."""
        try:
            client = MongoClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                retryWrites=False,
            )
            client.admin.command("ping")
            db = client[MONGODB_DB]
            logger.info("MongoDB connected successfully")
            return db
        except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError) as e:
            logger.error(f"MongoDB connection failed: {e} — running without auth")
            return None
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e} — running without auth")
            return None

    @property
    def users(self):
        """Users collection."""
        return self.db["users"] if self.db is not None else None

    # ──────────────────────────────────────────────────────────
    # SIGNUP
    # ──────────────────────────────────────────────────────────
    def signup(
        self, username: str, email: str,
        password: str, confirm: str
    ) -> tuple[bool, str]:
        """
        Register a new user.
        Returns (success, message)
        """
        if self.db is None:
            return False, "Database unavailable. Contact admin."

        # ── Input validation ───────────────────────────────────
        if not username or len(username.strip()) < 3:
            return False, "Username must be at least 3 characters."

        if not validate_email(email):
            return False, "Please enter a valid email address."

        if password != confirm:
            return False, "Passwords do not match."

        ok, msg = validate_password_strength(password)
        if not ok:
            return False, msg

        # ── Duplicate check ────────────────────────────────────
        if self.users.find_one({"username": username.lower().strip()}):
            return False, "Username already taken."

        if self.users.find_one({"email": email.lower()}):
            return False, "Email already registered."

        # ── Create user ────────────────────────────────────────
        hashed = hash_password(password)
        # First user ever becomes admin
        role   = "admin" if self.users.count_documents({}) == 0 \
                 else "user"
        doc    = create_user_doc(username, email, hashed, role)

        self.users.insert_one(doc)
        logger.info(f"New user registered: {username.lower().strip()} (role={role})")
        return True, f"Account created! {'You are the admin.' if role == 'admin' else ''}"

    # ──────────────────────────────────────────────────────────
    # LOGIN
    # ──────────────────────────────────────────────────────────
    def login(self, username: str, password: str) -> tuple[bool, str]:
        username = username.lower().strip()

        """
        Authenticate user and set session state.
        Returns (success, message)
        """
        if self.db is None:
            return False, "Database unavailable."

        user = self.users.find_one({"username": username})

        if not user:
            return False, "Username not found."

        if not user.get("is_active", True):
            return False, "Account is deactivated. Contact admin."

        if not verify_password(password, user["password_hash"]):
            return False, "Incorrect password."

        # ── Set session ────────────────────────────────────────
        st.session_state["authenticated"] = True
        st.session_state["username"]      = user["username"]
        st.session_state["role"]          = user["role"]
        st.session_state["display_name"]  = user["profile"]["display_name"]
        st.session_state["avatar_color"]  = user["profile"]["avatar_color"]
        st.session_state["user_id"]       = str(user["_id"])

        # Update last login
        self.users.update_one(
            {"username": user["username"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )

        logger.info(f"User logged in: {username.lower().strip()}")
        return True, f"Welcome back, {user['profile']['display_name']}!"

    # ──────────────────────────────────────────────────────────
    # LOGOUT
    # ──────────────────────────────────────────────────────────
    def logout(self):
        """Clear session state."""
        keys = [
            "authenticated", "username", "role",
            "display_name", "avatar_color", "user_id",
            "chat_history", "summaries_cache",
            "embedder", "llm", "index_ready"
        ]
        for k in keys:
            st.session_state.pop(k, None)
        logger.info("User logged out")

    # ──────────────────────────────────────────────────────────
    # SESSION HELPERS
    # ──────────────────────────────────────────────────────────
    def is_authenticated(self) -> bool:
        return st.session_state.get("authenticated", False)

    def is_admin(self) -> bool:
        return st.session_state.get("role") == "admin"

    def current_user(self) -> str:
        return st.session_state.get("username", "")

    def require_auth(self) -> bool:
        """
        Call at the top of any protected page.
        Returns True if authenticated, else redirects to login.
        """
        if not self.is_authenticated():
            st.warning("🔒 Please log in to access this page.")
            st.stop()
        return True

    def require_admin(self) -> bool:
        """Require admin role."""
        self.require_auth()
        if not self.is_admin():
            st.error("⛔ Admin access required.")
            st.stop()
        return True

    def increment_query_count(self):
        """Track how many queries the current user made."""
        if self.db is not None and self.current_user():
            self.users.update_one(
                {"username": self.current_user()},
                {"$inc": {"query_count": 1}}
            )

    def get_all_users(self) -> list[dict]:
        """Admin only: get all users."""
        if self.db is None:
            return []
        return list(self.users.find(
            {}, {"password_hash": 0}  # never expose hashes
        ))