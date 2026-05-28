import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rag.embedder import ResearchEmbedder

e = ResearchEmbedder("data/vectorstore")
loaded = e.load_index()
print('load_ok:', loaded)
print('stats:', e.get_stats())
print('papers:', e.get_papers())
