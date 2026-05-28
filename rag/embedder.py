# rag/embedder.py  — Production v2.0  (embedding cache + retrieval cache)
import os, json, pickle, hashlib, time, threading
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
VECTORSTORE_DIR      = "data/vectorstore"
FAISS_INDEX_FILE     = "faiss_index.bin"
METADATA_FILE        = "chunks_metadata.pkl"
CONFIG_FILE          = "vectorstore_config.json"
EMBED_CACHE_FILE     = "embed_cache.pkl"     # text_hash → vector


class ResearchEmbedder:
    """
    FAISS vector store with:
    - Persistent embedding cache (skip re-embedding known texts)
    - In-process retrieval cache (same query → instant result)
    - Incremental add_chunks for new uploads
    """

    def __init__(self, vectorstore_dir: str = VECTORSTORE_DIR):
        self.vectorstore_dir = Path(vectorstore_dir)
        self.vectorstore_dir.mkdir(parents=True, exist_ok=True)
        self.index_path      = self.vectorstore_dir / FAISS_INDEX_FILE
        self.metadata_path   = self.vectorstore_dir / METADATA_FILE
        self.config_path     = self.vectorstore_dir / CONFIG_FILE
        self.embed_cache_path= self.vectorstore_dir / EMBED_CACHE_FILE

        self.index     = None
        self.chunks    = []
        self.model     = None
        self.dimension = 384
        self._lock     = threading.Lock()

        # Persistent embedding cache: text_hash → np.float32 vector
        self._embed_cache: dict[str, np.ndarray] = self._load_embed_cache()

        # In-process retrieval cache: (query_hash, paper, section, k) → list[dict]
        self._retrieval_cache: dict[str, tuple[list[dict], float]] = {}
        self._retrieval_ttl = 600   # 10 min
        
        # In-process query embedding cache: query_string → np.float32 vector
        self._query_cache: dict[str, np.ndarray] = {}

        print(f"📦 ResearchEmbedder | {self.vectorstore_dir} | "
              f"embed_cache={len(self._embed_cache)} entries")
              
        # Preload model to avoid cold starts on first user query
        self.load_model()

    # ── Embedding cache helpers ───────────────────────────────

    def _load_embed_cache(self) -> dict:
        try:
            if self.embed_cache_path.exists():
                with open(self.embed_cache_path, "rb") as f:
                    return pickle.load(f)
        except Exception:
            pass
        return {}

    def _save_embed_cache(self):
        try:
            with open(self.embed_cache_path, "wb") as f:
                pickle.dump(self._embed_cache, f)
        except Exception as e:
            print(f"⚠️  embed_cache save error: {e}")

    @staticmethod
    def _text_hash(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    # ── Model loading ─────────────────────────────────────────

    def load_model(self):
        if self.model is not None:
            return
        print(f"\n🤖 Loading embedding model: {EMBEDDING_MODEL_NAME}")
        self.model     = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"   ✅ Embedding dim: {self.dimension}")

    # ── Embed texts (with cache) ──────────────────────────────

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        self.load_model()
        hashes  = [self._text_hash(t) for t in texts]
        vectors = np.zeros((len(texts), self.dimension), dtype=np.float32)

        miss_indices = []
        for i, h in enumerate(hashes):
            if h in self._embed_cache:
                vectors[i] = self._embed_cache[h]
            else:
                miss_indices.append(i)

        cache_hits = len(texts) - len(miss_indices)
        if miss_indices:
            miss_texts = [texts[i] for i in miss_indices]
            print(f"   Embedding {len(miss_texts)} new texts "
                  f"({cache_hits} from cache)")
            new_vecs = self.model.encode(
                miss_texts, batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype(np.float32)

            for local_i, global_i in enumerate(miss_indices):
                h = hashes[global_i]
                vectors[global_i]      = new_vecs[local_i]
                self._embed_cache[h]   = new_vecs[local_i]

            self._save_embed_cache()
        else:
            print(f"   ✅ All {len(texts)} texts from embedding cache")

        return vectors

    # ── Index build / add / load / save ──────────────────────

    def build_index(self, chunks: list[dict]) -> None:
        if not chunks:
            raise ValueError("No chunks provided to build index!")
        print(f"\n🔨 Building FAISS index from {len(chunks)} chunks...")
        vectors = self.embed_texts([c["text"] for c in chunks])
        with self._lock:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(vectors)
            self.chunks = chunks
            self._retrieval_cache.clear()
            print(f"   ✅ {self.index.ntotal} vectors indexed")
            self._save()

    def add_chunks(self, new_chunks: list[dict]) -> None:
        if self.index is None:
            raise RuntimeError("No index. Call build_index() first.")
        print(f"\n➕ Adding {len(new_chunks)} chunks to existing index...")
        vectors = self.embed_texts([c["text"] for c in new_chunks])
        with self._lock:
            self.index.add(vectors)
            self.chunks.extend(new_chunks)
            self._retrieval_cache.clear()
            print(f"   ✅ Index now has {self.index.ntotal} vectors")
            self._save()

    def _save(self) -> None:
        faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.chunks, f)
        config = {
            "model_name"   : EMBEDDING_MODEL_NAME,
            "dimension"    : self.dimension,
            "total_vectors": self.index.ntotal,
            "total_chunks" : len(self.chunks),
            "papers"       : list(set(c["paper_name"] for c in self.chunks)),
            "sections"     : list(set(c["section"]    for c in self.chunks)),
        }
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"   💾 Saved: {self.index.ntotal} vectors")

    def load_index(self) -> bool:
        if not self.index_path.exists() or not self.metadata_path.exists():
            print("   ⚠️  No existing index on disk.")
            return False
        print(f"\n📂 Loading vectorstore from disk...")
        with self._lock:
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.metadata_path, "rb") as f:
                    self.chunks = pickle.load(f)
                if self.config_path.exists():
                    with open(self.config_path) as f:
                        cfg = json.load(f)
                    print(f"   Model: {cfg.get('model_name')} | "
                          f"Vectors: {cfg.get('total_vectors')} | "
                          f"Papers: {cfg.get('papers')}")
                print(f"   ✅ {self.index.ntotal} vectors, {len(self.chunks)} chunks")
            except Exception as e:
                print(f"   ❌ FATAL: Index corruption detected ({e}). Initiating self-healing...")
                # Release lock before calling delete_index to prevent deadlock, or just inline the deletion
                for f in [self.index_path, self.metadata_path, self.config_path, self.embed_cache_path]:
                    if f.exists(): f.unlink()
                self.index  = None
                self.chunks = []
                self._embed_cache.clear()
                self._retrieval_cache.clear()
                print("   🩹 Self-healing complete. Index cleared.")
                return False
        return True

    # ── PDF path resolution ─────────────────────────────────────

    def _resolve_pdf_path(self, paper_name: str) -> str:
        """Resolve paper_name → actual PDF file path in data/papers/."""
        papers_dir = self.vectorstore_dir.parent / "papers"
        # Direct match
        pdf_path = papers_dir / f"{paper_name}.pdf"
        if pdf_path.exists():
            return str(pdf_path)
        # Fallback: search by stem
        for f in papers_dir.glob("*.pdf"):
            if f.stem == paper_name:
                return str(f)
        return str(pdf_path)  # Return expected path even if not found

    # ── Search (with retrieval cache) ─────────────────────────

    def search(self, query: str, top_k: int = 5,
               paper_filter: str = None,
               section_filter: str = None) -> list[dict]:
        if self.index is None:
            raise RuntimeError("Index not loaded.")
        if self.index.ntotal == 0:
            raise RuntimeError("Index is empty.")

        # Retrieval cache key
        rkey = hashlib.md5(
            f"{query}|{paper_filter}|{section_filter}|{top_k}".encode()
        ).hexdigest()
        cached, ts = self._retrieval_cache.get(rkey, (None, 0))
        if cached is not None and (time.time() - ts) < self._retrieval_ttl:
            print(f"   🔍 Retrieval cache HIT")
            return cached

        if query in self._query_cache:
            qvec = self._query_cache[query]
        else:
            qvec = self.model.encode(
                [query], convert_to_numpy=True,
                normalize_embeddings=True
            ).astype(np.float32)
            self._query_cache[query] = qvec

        fetch_k = self.index.ntotal if (paper_filter or section_filter) else top_k
        fetch_k = min(fetch_k, self.index.ntotal)
        scores, indices = self.index.search(qvec, fetch_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk = {**self.chunks[idx], "score": float(score)}
            # Attach PDF file path for the viewer
            chunk["file_path"] = self._resolve_pdf_path(chunk["paper_name"])
            if paper_filter and chunk["paper_name"].lower() != paper_filter.lower():
                continue
            if section_filter and chunk["section"].lower() != section_filter.lower():
                continue
            results.append(chunk)
            if len(results) >= top_k:
                break

        self._retrieval_cache[rkey] = (results, time.time())
        return results

    # ── Utility ───────────────────────────────────────────────

    def index_exists(self) -> bool:
        return self.index_path.exists() and self.metadata_path.exists()

    def get_stats(self) -> dict:
        if self.index is None:
            return {"status": "not loaded"}
        return {
            "total_vectors"     : self.index.ntotal,
            "total_chunks"      : len(self.chunks),
            "papers"            : sorted(set(c["paper_name"] for c in self.chunks)),
            "sections"          : sorted(set(c["section"]    for c in self.chunks)),
            "dimension"         : self.dimension,
            "embed_cache_size"  : len(self._embed_cache),
            "retrieval_cache_sz": len(self._retrieval_cache),
        }

    def get_papers(self) -> list[str]:
        return sorted(set(c["paper_name"] for c in self.chunks))

    def get_sections(self) -> list[str]:
        return sorted(set(c["section"] for c in self.chunks))

    def delete_index(self) -> None:
        with self._lock:
            for f in [self.index_path, self.metadata_path,
                      self.config_path, self.embed_cache_path]:
                if f.exists():
                    f.unlink()
            self.index  = None
            self.chunks = []
            self._embed_cache.clear()
            self._retrieval_cache.clear()
            print("🗑️  Index deleted.")

    def clear_retrieval_cache(self):
        with self._lock:
            self._retrieval_cache.clear()