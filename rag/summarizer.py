# rag/summarizer.py

from rag.llm_chain import ResearchLLMChain
from rag.embedder  import ResearchEmbedder


def run_full_summary(embedder: ResearchEmbedder,
                     llm: ResearchLLMChain) -> dict:
    """Generate summaries for all papers in the index."""
    return llm.summarize_all_papers(embedder.chunks)


def run_paper_summary(paper_name: str,
                      embedder: ResearchEmbedder,
                      llm: ResearchLLMChain) -> dict:
    """Generate summary for a single paper."""
    return llm.summarize_paper(paper_name, embedder.chunks)


def run_section_summary(paper_name: str,
                        section: str,
                        embedder: ResearchEmbedder,
                        llm: ResearchLLMChain) -> dict:
    """Generate summary for one section of one paper."""
    return llm.summarize_paper(
        paper_name, embedder.chunks, section=section
    )


def run_comparison(paper_names: list,
                   aspect: str,
                   embedder: ResearchEmbedder,
                   llm: ResearchLLMChain) -> dict:
    """Compare multiple papers on a given aspect."""
    return llm.compare_papers(
        paper_names, embedder.chunks, aspect=aspect
    )