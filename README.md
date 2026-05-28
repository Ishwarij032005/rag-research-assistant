# 🔬 RAG Research Assistant — Production v3.1

An AI-powered research paper workspace with split-screen PDF viewer, semantic search, citations, summaries, and paper comparison. Built with Streamlit, FAISS, Groq LLM, and MongoDB.

---

## ✨ Features

| Feature | Description |
|---|---|
| 💬 **Split-Screen Chat** | Ask questions, get cited answers, PDF opens alongside |
| 📄 **Embedded PDF Viewer** | Zoom, scroll, auto-navigate to cited pages |
| 📝 **Paper Summaries** | Per-paper, all-papers (parallel), section-wise |
| ⚖️ **Paper Comparison** | Side-by-side deep comparison |
| 📤 **Smart Upload** | Validates academic papers, auto-indexes in background |
| 🔐 **Auth + RBAC** | MongoDB-backed login, admin/user roles |
| 📊 **Analytics Dashboard** | Query stats, upload history (admin only) |
| ⚡ **Streaming Responses** | Real-time token streaming via Groq |
| 🗄️ **Persistent Cache** | SQLite-backed cache for answers + summaries |

---

## 🚀 Quick Start

### Requirements
- Python 3.9+
- MongoDB (optional — for user auth; app runs in demo mode without it)
- [Groq API key](https://console.groq.com) (free tier works)

### 1. Clone & Setup

```bash
git clone <repo>
cd rag-research-assistant
bash setup.sh
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and set:
#   GROQ_API_KEY=your_key_here
```

### 3. Run

```bash
# With virtual environment active:
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501)

---

## 📁 Project Structure

```
rag-research-assistant/
├── app.py                      # Streamlit entry point
├── requirements.txt
├── setup.sh                    # One-shot setup script
├── .env.example
│
├── rag/                        # Core RAG pipeline
│   ├── embedder.py             # FAISS + SentenceTransformer
│   ├── llm_chain.py            # Groq LLM (streaming, fallback, retry)
│   ├── pdf_loader.py           # PDF text + section extraction
│   ├── chunker.py              # Semantic chunking
│   └── summarizer.py
│
├── ui/
│   ├── theme.py                # Global dark-mode CSS
│   ├── components.py           # Reusable Streamlit components
│   ├── pdf_viewer.py           # Embedded PDF.js viewer (FIXED)
│   └── pages/
│       ├── chat_page.py        # Split-screen workspace (FIXED)
│       ├── upload_page.py      # Upload + auto-index (FIXED)
│       ├── summary_page.py
│       ├── compare_page.py
│       ├── analytics_page.py
│       └── login_page.py
│
├── auth/                       # Authentication
│   ├── auth_manager.py
│   ├── models.py
│   └── password_utils.py
│
├── analytics/
│   ├── tracker.py
│   └── dashboard.py
│
├── utils/
│   ├── config.py               # Central configuration
│   ├── disk_cache.py           # SQLite cache (FIXED)
│   ├── cache.py
│   └── logger.py
│
├── validation_utils/           # PDF academic validation
│   ├── pdf_validator.py
│   ├── citation_detector.py
│   ├── keyword_classifier.py
│   └── section_detector.py
│
└── data/                       # Runtime data (git-ignored)
    ├── papers/                 # Uploaded PDFs
    ├── vectorstore/            # FAISS index + metadata
    └── cache/                  # SQLite cache
```

---

## 🔧 Configuration (`.env`)

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | Get free at console.groq.com |
| `MONGODB_URI` | No | Default: `mongodb://localhost:27017/` |
| `MONGODB_DB` | No | Default: `research_assistant` |
| `SECRET_KEY` | No | Change in production |

---

## 🧪 Testing Checklist

- [ ] App starts without errors: `streamlit run app.py`
- [ ] Login/signup works (or "demo mode" if no MongoDB)
- [ ] Upload page accepts a research PDF and validates it
- [ ] Upload builds/extends the FAISS index
- [ ] Chat page: ask a question → streaming answer + source cards
- [ ] PDF viewer opens the cited paper automatically
- [ ] PDF viewer: zoom in/out works
- [ ] Paper selector appears when multiple papers cited
- [ ] Jump-to-page buttons navigate the PDF viewer
- [ ] Summary page: single paper + all papers
- [ ] Compare page: select 2+ papers → comparison
- [ ] Sidebar: cache stats, clear cache, logout
- [ ] Analytics dashboard (admin only)

---

## 🐛 Bugs Fixed in v3.1

1. **CRITICAL — Dead code in `render_pdf_viewer()`**: The entire PDF rendering block (PDF.js, base64 loading, zoom controls) was placed after a `return` statement due to an indentation error. The PDF viewer showed only the empty state regardless of whether a paper was loaded. **Fixed**: Restructured the if/else to properly handle empty vs. loaded states.

2. **CRITICAL — `st.session_state.pop()` not supported**: Streamlit's `SessionState` object does not implement `.pop()`. Calling it raised `AttributeError` on every user question that used "Quick Question" buttons, preventing any quick-fill question from working. **Fixed**: Replaced with `get()` + conditional `del`.

3. **Bug — Quick Question row variable collision**: Both rows of quick question buttons used the variable name `r1`, so the second row silently overwrote the first. `r2` was never used. **Fixed**: Use `row1` and `row2`.

4. **Bug — `prefill_q` in session defaults**: Setting `"prefill_q": ""` in `init_state()` defaults caused an empty string to be treated as a question on first load. **Fixed**: Removed from defaults; only set explicitly on button click.

5. **Bug — Background thread closure over loop variable**: In the upload page, the `_bg_index` thread was defined inside a `for` loop and closed over `dest` (a `Path` object). By the time the thread ran, `dest` may have been reassigned to the next loop iteration. **Fixed**: Pass `dest` as an explicit positional argument to the thread.

6. **Bug — `get_cache_stats()` missing key guard**: The stats dict was initialized at module level but could theoretically be missing keys if accessed before any operation. **Fixed**: Added `.get()` with defaults for all keys.

7. **Enhancement — `localStorage` blocked in iframes**: Browsers block `localStorage` access in cross-origin iframes (which Streamlit uses for `components.html()`). Zoom/scroll state was silently failing. **Fixed**: Switched to `sessionStorage` with a `try/catch` wrapper.

---

## ⚠️ Known Limitations

- PDF viewer requires a modern browser with JavaScript enabled (Chrome/Edge/Firefox)
- Very large PDFs (>20MB) may be slow to load in the viewer due to base64 encoding
- Background indexing happens in a daemon thread — if the app restarts before indexing completes, you'll need to re-upload
- MongoDB must be running locally for full auth features; without it the app runs in a degraded "no-auth" mode
- Groq API rate limits apply on the free tier (~30 req/min)

---

## 🔮 Future Improvements

- Highlight cited text passages directly in the PDF viewer
- Page-level citation jump (requires PDF.js text layer)
- Export chat as formatted PDF report
- Multi-user concurrent chat sessions
- RAG with web search fallback
- Docker + docker-compose for one-command deployment
