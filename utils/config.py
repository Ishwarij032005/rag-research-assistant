# utils/config.py
# Single source of truth for all configuration

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent.parent
PAPERS_DIR      = BASE_DIR / "data" / "papers"
VECTORSTORE_DIR = BASE_DIR / "data" / "vectorstore"
OUTPUTS_DIR     = BASE_DIR / "outputs"
LOGS_DIR        = BASE_DIR / "logs"

# Create dirs if missing
for d in [PAPERS_DIR, VECTORSTORE_DIR, OUTPUTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── API Keys ──────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SECRET_KEY   = os.getenv("SECRET_KEY", "fallback_secret_change_this")

# ── MongoDB ───────────────────────────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB  = os.getenv("MONGODB_DB", "research_assistant")

# ── RAG Settings ──────────────────────────────────────────────
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"
CHUNK_SIZE       = 1000
CHUNK_OVERLAP    = 200
DEFAULT_TOP_K    = 5
MAX_LLM_TOKENS   = 1024
LLM_TEMPERATURE  = 0.2

# ── Validation Thresholds ─────────────────────────────────────
MIN_PAGES            = 3
MAX_PAGES            = 200
MIN_TEXT_CHARS       = 500
MIN_ACADEMIC_SCORE   = 0.35   # 0–1 score; below this → rejected
MIN_SECTIONS_FOUND   = 2      # need at least 2 academic sections

# ── App Settings ──────────────────────────────────────────────
APP_NAME    = "Research Assistant"
APP_VERSION = "3.1.0"
APP_ICON    = "🔬"