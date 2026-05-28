# verify_setup.py
# Run this to check every module imports correctly

import sys
import os
from pathlib import Path

# Ensure project root (parent of scripts/) is on sys.path for package imports
ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

errors   = []
warnings = []

def check(label, fn):
    try:
        fn()
        print(f"  ✅  {label}")
    except Exception as e:
        print(f"  ❌  {label}: {e}")
        errors.append((label, str(e)))


print("\n" + "="*55)
print("  PRODUCTION SETUP VERIFICATION")
print("="*55)

# ── Core packages ──────────────────────────────────────────────
print("\n[1/6] Core Packages")
check("streamlit",    lambda: __import__("streamlit"))
check("langchain",    lambda: __import__("langchain"))
check("pdfplumber",   lambda: __import__("pdfplumber"))
check("faiss",        lambda: __import__("faiss"))
check("sentence_transformers",
      lambda: __import__("sentence_transformers"))
check("groq",         lambda: __import__("groq"))

# ── New packages ───────────────────────────────────────────────
print("\n[2/6] New Packages")
check("nltk",         lambda: __import__("nltk"))
check("sklearn",      lambda: __import__("sklearn"))
check("plotly",       lambda: __import__("plotly"))
check("pymongo",      lambda: __import__("pymongo"))
check("bcrypt",       lambda: __import__("bcrypt"))
check("pandas",       lambda: __import__("pandas"))
check("dotenv",       lambda: __import__("dotenv"))

# ── Utils ──────────────────────────────────────────────────────
print("\n[3/6] Utils Modules")
check("utils.config",
      lambda: __import__("utils.config", fromlist=["BASE_DIR"]))
check("utils.logger",
      lambda: __import__("utils.logger", fromlist=["get_logger"]))
check("utils.cache",
      lambda: __import__("utils.cache",  fromlist=["get_cached"]))

# ── Auth ───────────────────────────────────────────────────────
print("\n[4/6] Auth Modules")
check("auth.models",
      lambda: __import__("auth.models",
                         fromlist=["create_user_doc"]))
check("auth.password_utils",
      lambda: __import__("auth.password_utils",
                         fromlist=["hash_password"]))
check("auth.auth_manager",
      lambda: __import__("auth.auth_manager",
                         fromlist=["AuthManager"]))

# ── Validators ─────────────────────────────────────────────────
print("\n[5/6] Validator Modules")
check("validation_utils.section_detector",
    lambda: __import__("validation_utils.section_detector",
                 fromlist=["detect_sections"]))
check("validation_utils.citation_detector",
    lambda: __import__("validation_utils.citation_detector",
                 fromlist=["detect_citations"]))
check("validation_utils.keyword_classifier",
    lambda: __import__("validation_utils.keyword_classifier",
                 fromlist=["classify_academic_keywords"]))
check("validation_utils.pdf_validator",
    lambda: __import__("validation_utils.pdf_validator",
                 fromlist=["validate_research_paper"]))

# ── Analytics ──────────────────────────────────────────────────
print("\n[6/6] Analytics Modules")
check("analytics.models",
      lambda: __import__("analytics.models",
                         fromlist=["query_event"]))
check("analytics.tracker",
      lambda: __import__("analytics.tracker",
                         fromlist=["AnalyticsTracker"]))
check("analytics.dashboard",
      lambda: __import__("analytics.dashboard",
                         fromlist=["render_analytics_dashboard"]))

# ── RAG ────────────────────────────────────────────────────────
print("\n[RAG] RAG Modules")
check("rag.pdf_loader",
      lambda: __import__("rag.pdf_loader",
                         fromlist=["load_all_pdfs"]))
check("rag.chunker",
      lambda: __import__("rag.chunker",
                         fromlist=["chunk_pages"]))
check("rag.embedder",
      lambda: __import__("rag.embedder",
                         fromlist=["ResearchEmbedder"]))
check("rag.llm_chain",
      lambda: __import__("rag.llm_chain",
                         fromlist=["ResearchLLMChain"]))
check("rag.summarizer",
      lambda: __import__("rag.summarizer",
                         fromlist=["run_full_summary"]))

# ── UI ─────────────────────────────────────────────────────────
print("\n[UI] UI Modules")
check("ui.theme",
      lambda: __import__("ui.theme",
                         fromlist=["inject_theme"]))
check("ui.components",
      lambda: __import__("ui.components",
                         fromlist=["page_header"]))
check("ui.pages.login_page",
      lambda: __import__("ui.pages.login_page",
                         fromlist=["render_login_page"]))
check("ui.pages.chat_page",
      lambda: __import__("ui.pages.chat_page",
                         fromlist=["render_chat_page"]))
check("ui.pages.upload_page",
      lambda: __import__("ui.pages.upload_page",
                         fromlist=["render_upload_page"]))
check("ui.pages.summary_page",
      lambda: __import__("ui.pages.summary_page",
                         fromlist=["render_summary_page"]))
check("ui.pages.compare_page",
      lambda: __import__("ui.pages.compare_page",
                         fromlist=["render_compare_page"]))

# ── NLTK Data check ────────────────────────────────────────────
print("\n[NLTK] NLTK Data")
try:
    from nltk.corpus import stopwords
    stopwords.words("english")
    print("  ✅  stopwords")
except Exception as e:
    print(f"  ❌  stopwords: {e}")
    errors.append(("nltk.stopwords", str(e)))

try:
    import nltk
    nltk.data.find("tokenizers/punkt")
    print("  ✅  punkt")
except Exception as e:
    print(f"  ❌  punkt: {e}")
    errors.append(("nltk.punkt", str(e)))

# ── MongoDB check ──────────────────────────────────────────────
print("\n[DB] MongoDB Connection")
try:
    from utils.config import MONGODB_URI, MONGODB_DB
    from pymongo import MongoClient
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=4000)
    client.admin.command("ping")
    print(f"  ✅  MongoDB connected: {MONGODB_DB}")
    client.close()
except Exception as e:
    print(f"  ⚠️   MongoDB: {e}")
    warnings.append("MongoDB not connected — auth will be unavailable")

# ── Groq check ─────────────────────────────────────────────────
print("\n[LLM] Groq API")
try:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("GROQ_API_KEY", "")
    if key.startswith("gsk_"):
        print("  ✅  GROQ_API_KEY found")
    else:
        print("  ⚠️   GROQ_API_KEY missing or invalid in .env")
        warnings.append("GROQ_API_KEY not set")
except Exception as e:
    print(f"  ❌  Groq check: {e}")

# ── Final report ───────────────────────────────────────────────
print("\n" + "="*55)
if not errors:
    print("  🎉  ALL CHECKS PASSED")
    print("  Run: streamlit run app.py")
else:
    print(f"  ❌  {len(errors)} error(s) found:")
    for label, err in errors:
        print(f"      • {label}: {err[:80]}")
    print("\n  Fix the errors above before running app.py")

if warnings:
    print(f"\n  ⚠️  {len(warnings)} warning(s):")
    for w in warnings:
        print(f"      • {w}")

print("="*55 + "\n")