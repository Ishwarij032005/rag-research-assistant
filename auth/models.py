# auth/models.py
# User database schema

from datetime import datetime


def create_user_doc(
    username: str,
    email: str,
    hashed_password: str,
    role: str = "user"
) -> dict:
    """
    Build a user document for MongoDB insertion.

    Roles:
        "user"  → standard access
        "admin" → full access including analytics
    """
    return {
        "username"        : username.lower().strip(),
        "email"           : email.lower().strip(),
        "password_hash"   : hashed_password,
        "role"            : role,
        "created_at"      : datetime.utcnow(),
        "last_login"      : None,
        "is_active"       : True,
        "query_count"     : 0,
        "papers_uploaded" : 0,
        "profile": {
            "display_name": username,
            "avatar_color": _pick_color(username)
        }
    }


def _pick_color(username: str) -> str:
    """Pick a consistent avatar color from username."""
    colors = [
        "#4f8ef7", "#f74f4f", "#4ff77a",
        "#f7c34f", "#c74ff7", "#4ff7e8"
    ]
    return colors[sum(ord(c) for c in username) % len(colors)]