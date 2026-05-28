#!/usr/bin/env bash
# setup.sh — One-shot setup for RAG Research Assistant
set -e

echo "═══════════════════════════════════════════"
echo "  RAG Research Assistant — Setup Script"
echo "═══════════════════════════════════════════"

# 1. Check Python
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
  echo "❌ Python 3.9+ required. Please install Python first."
  exit 1
fi
PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PY_VER found"

# 2. Create venv if not exists
if [ ! -d ".venv" ]; then
  echo "📦 Creating virtual environment..."
  $PYTHON -m venv .venv
fi

# 3. Activate venv
echo "🔧 Activating virtual environment..."
source .venv/bin/activate || source .venv/Scripts/activate 2>/dev/null

# 4. Upgrade pip
pip install --upgrade pip --quiet

# 5. Install dependencies
echo "📥 Installing dependencies (this may take 2-3 minutes)..."
pip install -r requirements.txt --quiet

# 6. Create .env from example if missing
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "⚠️  Created .env from template."
  echo "    ➜ Edit .env and set your GROQ_API_KEY before starting."
  echo ""
fi

# 7. Create required directories
mkdir -p data/papers data/vectorstore data/cache logs outputs

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Edit .env and add your GROQ_API_KEY"
echo "  2. (Optional) Start MongoDB for auth:"
echo "     mongod --dbpath ./data/mongodb"
echo "  3. Run the app:"
echo "     streamlit run app.py"
echo "═══════════════════════════════════════════"
