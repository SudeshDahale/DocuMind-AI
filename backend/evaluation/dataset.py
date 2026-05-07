"""
Evaluation dataset for DocuMind.

Two modes:
  1. AUTO (default) : questions are generated from your actual documents at runtime
  2. MANUAL         : hard-code domain-specific Q&A pairs below for repeatable evals

To switch to manual, set AUTO_GENERATE = False and fill EVAL_DATASET.
"""

AUTO_GENERATE = False   # flip to False once you have manual pairs

# ── Manual dataset (used when AUTO_GENERATE = False) ──────────────────────
EVAL_DATASET = [
    # Example — replace with questions specific to YOUR documents:
    # {
    #     "question": "What SDGs does the platform target?",
    #     "ground_truth_answer": "The platform targets SDG 3 (Good Health) and SDG 4 (Quality Education).",
    #     "ground_truth_contexts": ["SDG", "health", "education", "platform"],
    #     "doc_hint": "",
    # },
    
    {
        "question": "What is the name of the person in the acknowledgement?",
        "ground_truth_answer": "Dr. P.N. Kathavate",
        "ground_truth_contexts": ["acknowledgement", "gratitude", "guidance", "Kathavate"],
        "doc_hint": "",
    },
    {
        "question": "What is the accuracy of Random Forest without negation handling?",
        "ground_truth_answer": "74% (83.5% with negation handling, which is an improvement of 9.5%, so without negation handling it is approximately 74%)",
        "ground_truth_contexts": ["random forest", "accuracy", "negation", "without"],
        "doc_hint": "",
    },
    {
        "question": "What is the accuracy of Random Forest with negation handling?",
        "ground_truth_answer": "83.5%",
        "ground_truth_contexts": ["random forest", "accuracy", "negation", "83.5"],
        "doc_hint": "",
    },
    {
        "question": "Which Machine Learning models are used in the paper?",
        "ground_truth_answer": "Naive Bayes, Random Forest, Logistic Regression, K-Nearest Neighbors (KNN), and Support Vector Machine (SVM)",
        "ground_truth_contexts": ["naive bayes", "random forest", "logistic regression", "knn", "svm"],
        "doc_hint": "",
    },
    {
        "question": "Which model performed the worst?",
        "ground_truth_answer": "K-Nearest Neighbors (KNN) with 68% accuracy",
        "ground_truth_contexts": ["knn", "worst", "68", "accuracy", "rank"],
        "doc_hint": "",
    },
    {
        "question": "Which model performed the best?",
        "ground_truth_answer": "Random Forest with 83.5% accuracy",
        "ground_truth_contexts": ["random forest", "best", "83.5", "accuracy", "rank"],
        "doc_hint": "",
    },
    {
        "question": "What is the name of the Author?",
        "ground_truth_answer": "Sudesh Dahale",
        "ground_truth_contexts": ["author", "sudesh", "dahale"],
        "doc_hint": "",
    },
]


# ── Auto-generation (runtime, uses your live documents) ───────────────────

QUESTION_TEMPLATES = [
    {
        "question_template": "What is the main topic or purpose described in this passage: '{snippet}'?",
        "gt_context_extractor": lambda text: text.lower().split()[:8],
    },
    {
        "question_template": "According to the document, what does this refer to: '{snippet}'?",
        "gt_context_extractor": lambda text: text.lower().split()[:8],
    },
]

AUTO_QUESTION_PROMPTS = [
    "What is the name of the person in the acknowledgement?",
    "What is the accuracy of Random forest without negation handling?",
    "What is the accuracy of Random forest with negation handling?",
    "Which Machine Learning models are used in the paper?",
    "Which model performed the worst?",
    "Which model performed the best?",
    "What is the name of Author?",
]


def build_auto_dataset(chunks_per_doc: list) -> list:
    """
    Build dataset by sampling one doc and grounding everything in it.
    Questions and ground truth come from the SAME document.
    """
    if not chunks_per_doc:
        return []

    # Pick the doc with the most chunks (most content = best eval target)
    from collections import defaultdict
    doc_chunks = defaultdict(list)
    for chunk in chunks_per_doc:
        doc_chunks[chunk.get("doc_id", "unknown")].append(chunk)

    # Pick doc with longest average chunk text (more content = better eval target)
    best_doc_id = max(
        doc_chunks,
        key=lambda d: sum(len(c.get("text","")) for c in doc_chunks[d])
    )
    best_chunks = doc_chunks[best_doc_id]

    step = max(1, len(best_chunks) // 7)
    sampled = best_chunks[::step][:7]

    dataset = []
    for prompt, chunk in zip(AUTO_QUESTION_PROMPTS, sampled):
        text = chunk.get("text", "")
        words = [
            w for w in text.lower().split()
            if len(w) > 5 and w.isalpha()
        ]
        from collections import Counter
        gt_keywords = [w for w, _ in Counter(words).most_common(8)]

        dataset.append({
            "question": prompt,
            "ground_truth_answer": text[:300],
            "ground_truth_contexts": gt_keywords,
            "doc_hint": best_doc_id,      # ← locked to one doc
        })

    return dataset