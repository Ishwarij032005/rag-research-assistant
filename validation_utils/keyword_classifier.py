# validators/keyword_classifier.py

import re

# Strong academic signals — presence of these strongly
# suggests a research paper
STRONG_ACADEMIC_KEYWORDS = [
    # Research language
    "we propose", "we present", "we introduce", "we demonstrate",
    "in this paper", "this paper presents", "this work",
    "our approach", "our model", "our method", "our framework",
    "state-of-the-art", "state of the art", "baseline",
    "outperforms", "surpasses", "benchmark",
    # Technical
    "neural network", "deep learning", "machine learning",
    "transformer", "attention mechanism", "embedding",
    "algorithm", "dataset", "training", "inference",
    "classification", "regression", "accuracy", "precision",
    "recall", "f1 score", "loss function", "gradient",
    "epoch", "batch size", "learning rate", "hyperparameter",
    # Research methodology
    "hypothesis", "empirical", "quantitative", "qualitative",
    "statistical significance", "p-value", "confidence interval",
    "ablation study", "cross-validation", "ground truth",
    "annotation", "labeled data", "corpus",
]

# Weak signals — could appear in non-papers but still academic
WEAK_ACADEMIC_KEYWORDS = [
    "figure", "table", "equation", "theorem", "proof",
    "experiment", "evaluation", "analysis", "comparison",
    "performance", "result", "conclusion", "abstract",
    "introduction", "methodology", "implementation",
    "contribution", "limitation", "future work",
]

# Strong NON-paper signals — presence reduces score heavily
NON_PAPER_KEYWORDS = [
    # Resume
    "curriculum vitae", "resume", "work experience",
    "references available", "skills:", "hobbies:",
    # Book
    "chapter one", "chapter 1:", "table of contents",
    "all rights reserved", "isbn", "publisher:",
    # Invoice/legal
    "invoice", "billing", "payment due", "terms and conditions",
    "hereby agrees", "legal notice",
]


def classify_academic_keywords(text: str) -> dict:
    """
    Score the text based on academic keyword presence.

    Returns:
        {
            "academic_score"    : 0.72,
            "strong_hits"       : 8,
            "weak_hits"         : 15,
            "non_paper_hits"    : 0,
            "is_likely_paper"   : True,
            "keywords_found"    : [...]
        }
    """
    text_lower = text.lower()

    strong_hits = sum(
        1 for kw in STRONG_ACADEMIC_KEYWORDS
        if kw in text_lower
    )
    weak_hits = sum(
        1 for kw in WEAK_ACADEMIC_KEYWORDS
        if kw in text_lower
    )
    non_hits = sum(
        1 for kw in NON_PAPER_KEYWORDS
        if kw in text_lower
    )

    keywords_found = [
        kw for kw in STRONG_ACADEMIC_KEYWORDS
        if kw in text_lower
    ][:10]

    # Score formula:
    # Strong keywords carry 3x weight
    # Non-paper keywords heavily penalize
    raw_score = (strong_hits * 3 + weak_hits) / \
                (len(STRONG_ACADEMIC_KEYWORDS) * 3 +
                 len(WEAK_ACADEMIC_KEYWORDS))
    penalty   = non_hits * 0.15
    score     = max(0.0, min(1.0, raw_score - penalty))

    return {
        "academic_score" : round(score, 3),
        "strong_hits"    : strong_hits,
        "weak_hits"      : weak_hits,
        "non_paper_hits" : non_hits,
        "is_likely_paper": score >= 0.15 and non_hits == 0,
        "keywords_found" : keywords_found,
    }