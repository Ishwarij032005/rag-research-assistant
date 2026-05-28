# rag/llm_chain.py  — Production v3.0
import os, re, time, random, hashlib, threading
from typing import Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL_FAST     = "llama-3.1-8b-instant"
MODEL_HEAVY    = "llama-3.3-70b-versatile"
MAX_TOKENS_QA  = 800
MAX_TOKENS_SUM = 1200
MAX_TOKENS_CMP = 1800
MAX_TOKENS_SYN = 900
TEMPERATURE    = 0.2
MAX_CHARS      = 550
TOKEN_BUDGET_QA         = 3500
TOKEN_BUDGET_SUM_FAST   = 800
TOKEN_BUDGET_SUM_DETAIL = 2500
COOLDOWN       = 2
MAX_RETRIES    = 3
BACKOFF_BASE   = 4
MAX_PARALLEL_WORKERS = 5

_api_lock = threading.Lock()
_last_t: list[float] = [0.0]

# ── Prompt templates ──────────────────────────────────────────
QA_SYS = (
    "You are an expert research assistant. Answer ONLY from context. "
    "Be precise and academic. Never fabricate."
)
QA_USR = "CONTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER:"

SUM_SYS = (
    "You are an expert at summarizing academic papers clearly and concisely."
)
SUM_USR = (
    "Summarize '{paper_name}' from these excerpts.\n\n"
    "EXCERPTS:\n{context}\n\n"
    "Sections: **Main Contribution**, **Methodology**, **Key Results**, "
    "**Conclusion**, **Significance**\n\nSUMMARY:"
)

CMP_SYS = "You are an expert at comparing academic papers."
CMP_USR = (
    "Compare these papers from the excerpts.\n\nPAPERS:\n{context}\n\n"
    "Cover: Research Goals, Methodology, Results, Strengths & Weaknesses, "
    "Overall Verdict.\n\nCOMPARISON:"
)

SYN_SYS = SUM_SYS
SYN_USR = (
    "Based on these summaries, provide a combined synthesis covering: "
    "common themes, relationships, collective contribution, key differences."
    "\n\nSUMMARIES:\n{context}\n\nSYNTHESIS:"
)


# ── Token utilities ───────────────────────────────────────────
def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def trim_to_budget(chunks: list[dict], budget: int) -> list[dict]:
    """Select chunks fitting token budget; deduplicate by text fingerprint."""
    out, used, seen = [], 0, set()
    for c in chunks:
        txt = c["text"][:MAX_CHARS]
        fp  = hashlib.md5(txt[:128].encode()).hexdigest()
        if fp in seen:
            continue
        seen.add(fp)
        toks = estimate_tokens(txt)
        if used + toks > budget:
            break
        out.append({**c, "text": txt})
        used += toks
    return out

def filter_essential_chunks(chunks: list[dict]) -> list[dict]:
    """Aggressively filter chunks for Fast Mode, prioritizing highly representative sections."""
    essential = []
    for c in chunks:
        s = c["section"].lower()
        if "abstract" in s or "conclusion" in s or "result" in s or "method" in s or "intro" in s:
            essential.append(c)
    return essential if essential else chunks  # Fallback if paper lacks standard headers


def build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant context found."
    lines = []
    for i, c in enumerate(chunks, 1):
        txt = c["text"][:MAX_CHARS]
        lines += [f"[{i}] {c['paper_name']} p.{c['page_number']} §{c['section']}", txt, ""]
    return "\n".join(lines)


def build_sources(chunks: list[dict]) -> list[dict]:
    return [{
        "source_num" : i,
        "paper_name" : c["paper_name"],
        "page_number": c["page_number"],
        "section"    : c["section"],
        "snippet"    : c["text"][:300] + ("…" if len(c["text"]) > 300 else ""),
        "score"      : round(c.get("score", 0.0), 4),
        "file_path"  : c.get("file_path", ""),
    } for i, c in enumerate(chunks, 1)]


# ── Main class ────────────────────────────────────────────────
class ResearchLLMChain:
    def __init__(self):
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY missing from .env")
        self.client = Groq(api_key=key, max_retries=0)
        print(f"🤖 LLM Chain ready (Stateless Routing)")

    def _cooldown(self):
        with _api_lock:
            elapsed = time.time() - _last_t[0]
            if elapsed < COOLDOWN:
                time.sleep(COOLDOWN - elapsed)
            _last_t[0] = time.time()

    def _call_llm(self, sys_p: str, usr_p: str,
                  primary_model: str, fallback_model: str,
                  max_tok: int = MAX_TOKENS_QA) -> str:
        model = primary_model
        for attempt in range(MAX_RETRIES + 1):
            self._cooldown()
            try:
                r = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": sys_p},
                               {"role": "user",   "content": usr_p}],
                    temperature=TEMPERATURE,
                    max_tokens=max_tok,
                )
                return r.choices[0].message.content
            except Exception as e:
                err = str(e)
                if "429" in err or "rate_limit" in err:
                    if attempt >= 1 and primary_model != fallback_model:
                        model = fallback_model
                        max_tok = max(int(max_tok * 0.8), 64)
                        print(f"⚡ Switched to fallback: {fallback_model} with max_tokens={max_tok}")
                    elif attempt >= 1:
                        max_tok = max(int(max_tok * 0.75), 64)
                        print(f"⚡ Retrying {model} with reduced tokens={max_tok}")

                    m = re.search(r"try again in ([\d.]+)s", err)
                    wait = int(float(m.group(1))) + 1 if m else (
                        BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 2))
                    print(f"⏳ Rate limit. Waiting {wait:.0f}s (retry {attempt+1})")
                    time.sleep(wait)
                elif "401" in err or "invalid_api_key" in err:
                    return "❌ Invalid Groq API key."
                elif "503" in err or "unavailable" in err:
                    time.sleep(BACKOFF_BASE * (2 ** attempt))
                else:
                    return f"❌ LLM Error: {err}"
        return "⚠️ Rate limit persists. Please wait and retry."

    def _call_llm_streaming(self, sys_p: str, usr_p: str,
                             primary_model: str, fallback_model: str,
                             max_tok: int = MAX_TOKENS_QA,
                             usr_p_fallback: str = None,
                             meta_out: list = None) -> Generator[str, None, None]:
        self._cooldown()
        if meta_out is not None:
            meta_out[0] = primary_model

        try:
            stream = self.client.chat.completions.create(
                model=primary_model,
                messages=[{"role": "system", "content": sys_p},
                           {"role": "user",   "content": usr_p}],
                temperature=TEMPERATURE,
                max_tokens=max_tok,
                stream=True,
            )
            for chunk in stream:
                d = chunk.choices[0].delta
                if d and d.content:
                    yield d.content
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err:
                if meta_out is not None:
                    meta_out[0] = fallback_model

                if primary_model != fallback_model:
                    yield (
                        "\n\n> [!WARNING]\n"
                        f"> 🔄 **API Rate Limit Exceeded.** Switching from `{primary_model}` to fallback model `{fallback_model}` "
                        "to ensure delivery. Retrying...\n\n"
                    )
                else:
                    yield (
                        "\n\n> [!WARNING]\n"
                        f"> ⏳ **API Rate Limit Exceeded.** Dynamically shrinking context by 30% to fit strict limits "
                        f"on `{fallback_model}`. Retrying...\n\n"
                    )

                wait_time = 4
                m = re.search(r"try again in ([\d.]+)s", err)
                if m:
                    wait_time = int(float(m.group(1))) + 1
                time.sleep(wait_time)

                final_usr_p = usr_p_fallback if usr_p_fallback else usr_p
                fallback_max_tok = max(int(max_tok * 0.75), 64)

                for attempt in range(MAX_RETRIES):
                    try:
                        stream = self.client.chat.completions.create(
                            model=fallback_model, stream=True,
                            messages=[{"role": "system", "content": sys_p},
                                       {"role": "user",   "content": final_usr_p}],
                            temperature=TEMPERATURE, max_tokens=fallback_max_tok,
                        )
                        for chunk in stream:
                            d = chunk.choices[0].delta
                            if d and d.content:
                                yield d.content
                        return
                    except Exception as fallback_err:
                        fallback_err_str = str(fallback_err)
                        if "429" in fallback_err_str or "rate_limit" in fallback_err_str:
                            if attempt < MAX_RETRIES - 1:
                                retry_wait = BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 2)
                                yield (
                                    "\n\n> [!WARNING]\n"
                                    f"> ⚡ Fallback model `{fallback_model}` is still rate-limited. Retrying in {int(retry_wait)}s...\n\n"
                                )
                                time.sleep(retry_wait)
                                continue
                            yield f"\n\n❌ Fallback also failed after retries: {fallback_err_str}"
                        else:
                            yield f"\n\n❌ Fallback also failed: {fallback_err_str}"
                        return
            else:
                yield f"\n\n❌ Stream error: {err}"

    # ── Q&A ───────────────────────────────────────────────────
    def answer_question(self, question: str, retrieved_chunks: list[dict],
                        stream: bool = False) -> dict:
        selected = trim_to_budget(retrieved_chunks, TOKEN_BUDGET_QA)
        ctx      = build_context(selected)
        usr_p    = QA_USR.format(context=ctx, question=question)
        
        reduced_budget = int(TOKEN_BUDGET_QA * 0.7)
        fallback_sel   = trim_to_budget(retrieved_chunks, reduced_budget)
        fallback_ctx   = build_context(fallback_sel)
        usr_p_fallback = QA_USR.format(context=fallback_ctx, question=question)

        print(f"💬 Q&A | {len(selected)} chunks | ~{estimate_tokens(usr_p)} tok")
        
        meta = [MODEL_FAST]
        answer = (self._call_llm_streaming(QA_SYS, usr_p, MODEL_FAST, MODEL_FAST, MAX_TOKENS_QA, usr_p_fallback, meta)
                  if stream else
                  self._call_llm(QA_SYS, usr_p, MODEL_FAST, MODEL_FAST, MAX_TOKENS_QA))
                  
        return {
            "answer"           : answer,
            "sources"          : build_sources(selected),
            "question"         : question,
            "num_sources_used" : len(selected),
            "tokens_estimated" : estimate_tokens(usr_p),
            "meta_ref"         : meta,
            "mode_label"       : "⚡ Fast Mode",
        }

    # ── Single-paper summary ──────────────────────────────────
    def summarize_paper(self, paper_name: str, chunks: list[dict],
                        section: str = None, stream: bool = False,
                        mode: str = "fast") -> dict:
        pc = [c for c in chunks if c["paper_name"] == paper_name]
        if section:
            sc = [c for c in pc if c["section"].lower() == section.lower()]
            pc = sc or pc
            
        if mode == "fast":
            pc = filter_essential_chunks(pc)
            budget = TOKEN_BUDGET_SUM_FAST
            model_target = MODEL_FAST
            label = "⚡ Fast Mode"
        else:
            budget = TOKEN_BUDGET_SUM_DETAIL
            model_target = MODEL_HEAVY
            label = "📚 Detailed Mode"
            
        if not pc:
            return {"paper_name": paper_name, "section": section or "All",
                    "summary": f"No content found for '{paper_name}'", "sources": []}
                    
        selected = trim_to_budget(pc, budget)
        ctx      = build_context(selected)
        usr_p    = SUM_USR.format(paper_name=paper_name +
                                   (f" §{section}" if section else ""), context=ctx)
        print(f"📝 Summary | {paper_name} | {len(selected)} chunks | {label}")
        
        meta = [model_target]
        summary = (self._call_llm_streaming(SUM_SYS, usr_p, model_target, MODEL_FAST, MAX_TOKENS_SUM, None, meta)
                   if stream else
                   self._call_llm(SUM_SYS, usr_p, model_target, MODEL_FAST, MAX_TOKENS_SUM))
                   
        return {"paper_name": paper_name, "section": section or "All Sections",
                "summary": summary, "sources": build_sources(selected),
                "meta_ref": meta, "mode_label": label}

    # ── Parallel all-papers summary (Generator) ───────────────────
    def summarize_all_papers(self, chunks: list[dict], mode: str = "fast") -> Generator[dict, None, None]:
        names = sorted(set(c["paper_name"] for c in chunks))
        workers = min(len(names), MAX_PARALLEL_WORKERS)
        print(f"\n📚 Parallel summarize | {len(names)} papers | workers={workers} | {mode}")
        
        individual: dict[str, dict] = {}
        t0 = time.time()

        def _one(name):
            return name, self.summarize_paper(name, chunks, stream=False, mode=mode)

        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_one, n): n for n in names}
            for fut in as_completed(futures):
                name = futures[fut]
                try:
                    pname, res = fut.result()
                    individual[pname] = res
                except Exception as exc:
                    res = {"paper_name": name, "section": "All", "summary": f"❌ Error: {exc}", "sources": []}
                    individual[name] = res
                
                done += 1
                yield {"type": "paper", "paper_name": name, "result": res, "done": done, "total": len(names)}

        elapsed = int((time.time() - t0) * 1000)
        print(f"✅ Parallel done in {elapsed}ms")

        # Synthesis
        ctx_parts = []
        for i, (n, r) in enumerate(individual.items(), 1):
            txt = r["summary"] if isinstance(r["summary"], str) else "(unavailable)"
            ctx_parts.append(f"=== PAPER {i}: {n} ===\n{txt[:1200]}")
        syn_ctx = "\n\n".join(ctx_parts)
        
        model_target = MODEL_FAST if mode == "fast" else MODEL_HEAVY
        label = "⚡ Fast Mode" if mode == "fast" else "📚 Detailed Mode"
        
        combined = self._call_llm(SYN_SYS, SYN_USR.format(context=syn_ctx), model_target, MODEL_FAST, MAX_TOKENS_SYN)

        final_res = {"individual_summaries": individual, "combined_summary": combined,
                     "paper_names": names, "parallel_time_ms": elapsed, 
                     "mode_label": label, "meta_ref": [model_target]}
                     
        yield {"type": "synthesis", "result": final_res}

    # ── Compare papers ────────────────────────────────────────
    def compare_papers(self, paper_names: list[str], chunks: list[dict],
                       aspect: str = "overall", stream: bool = False) -> dict:
        print(f"⚖️  Compare | {len(paper_names)} papers | {aspect}")
        all_sel, parts = [], []
        per_budget = TOKEN_BUDGET_QA // max(len(paper_names), 1)
        for name in paper_names:
            pc = [c for c in chunks if c["paper_name"] == name]
            if aspect == "methodology":
                pc = [c for c in pc if "method" in c["section"].lower()] or pc
            elif aspect == "results":
                pc = [c for c in pc if c["section"].lower()
                      in ("results", "experiments")] or pc
            sel = trim_to_budget(pc, per_budget)
            all_sel.extend(sel)
            parts.append(f"\n{'='*40}\nPAPER: {name}\n{'='*40}\n{build_context(sel)}")
        usr_p = CMP_USR.format(context="\n".join(parts))
        
        meta = [MODEL_HEAVY]
        cmp = (self._call_llm_streaming(CMP_SYS, usr_p, MODEL_HEAVY, MODEL_FAST, MAX_TOKENS_CMP, None, meta)
               if stream else
               self._call_llm(CMP_SYS, usr_p, MODEL_HEAVY, MODEL_FAST, MAX_TOKENS_CMP))
               
        return {"comparison": cmp, "paper_names": paper_names,
                "aspect": aspect, "sources": build_sources(all_sel[:10]),
                "meta_ref": meta, "mode_label": "🧠 Deep Compare"}

    # ── Health check ──────────────────────────────────────────
    def health_check(self) -> dict:
        t0 = time.time()
        try:
            self.client.chat.completions.create(
                model=MODEL_FAST,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            return {"ok": True, "model": MODEL_FAST,
                    "latency_ms": int((time.time()-t0)*1000), "error": None}
        except Exception as e:
            return {"ok": False, "model": MODEL_FAST,
                    "latency_ms": int((time.time()-t0)*1000), "error": str(e)}