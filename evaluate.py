#!/usr/bin/env python3
"""
DocuMind Evaluation CLI
=======================
Usage:
    cd DocuMind-AI-main/backend
    python ../evaluate.py                        # run all questions
    python ../evaluate.py --doc-id <uuid>        # restrict to one document
    python ../evaluate.py --out results.json     # save detailed results
    python ../evaluate.py --verbose              # print per-question detail

Requires the backend to be importable (run from backend/ or set PYTHONPATH).
"""

import sys
import os
import json
import argparse
from typing import List, Dict

# ── path bootstrap ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

# ── imports ─────────────────────────────────────────────────────────────────
from core.config import config
from services.retrieval import load_vector_store, load_chunks, search_multiple
from services.reranking import rerank
from services.generation import answer_question
from evaluation.dataset import EVAL_DATASET
from evaluation.metrics import score_sample


# ── helpers ─────────────────────────────────────────────────────────────────

def _discover_doc_ids() -> List[str]:
    """Return all doc IDs that have both an index and a chunk file."""
    index_dir = os.path.join(BACKEND_DIR, config.index_dir)
    chunk_dir  = os.path.join(BACKEND_DIR, config.chunk_dir)

    if not os.path.isdir(index_dir):
        return []

    doc_ids = []
    for fname in os.listdir(index_dir):
        if fname.endswith(".index"):
            doc_id = fname[:-6]
            if os.path.exists(os.path.join(chunk_dir, f"{doc_id}.json")):
                doc_ids.append(doc_id)
    return doc_ids


def _bar(value: float, width: int = 20) -> str:
    filled = int(round(value * width))
    return "[" + "█" * filled + "░" * (width - filled) + f"] {value:.2%}"


def _print_summary(results: List[Dict]) -> None:
    if not results:
        print("⚠  No results to summarise.")
        return

    metrics = ["context_precision", "context_recall", "answer_correctness", "faithfulness"]
    averages = {}
    for m in metrics:
        vals = [r[m] for r in results if r.get(m) is not None]
        averages[m] = sum(vals) / len(vals) if vals else None

    print("\n" + "═" * 60)
    print("  DocuMind Evaluation Report")
    print("═" * 60)
    print(f"  Questions evaluated : {len(results)}")
    print()
    for m in metrics:
        label = m.replace("_", " ").title().ljust(22)
        if averages[m] is None:
            print(f"  {label} skipped (dry-run)")
        else:
            print(f"  {label} {_bar(averages[m])}")
    print("═" * 60)

    # overall score (equal weight)
    valid = [v for v in averages.values() if v is not None]
    overall = sum(valid) / len(valid) if valid else 0.0
    print(f"\n  Overall Score        {_bar(overall)}")

    # grade
    if overall >= 0.80:
        grade = "🏆 Excellent"
    elif overall >= 0.65:
        grade = "✅ Good"
    elif overall >= 0.50:
        grade = "⚠️  Fair — consider tuning chunking or retrieval"
    else:
        grade = "❌ Needs work — check your document coverage"
    print(f"  Grade                {grade}\n")


# ── main ────────────────────────────────────────────────────────────────────

def run_evaluation(
    doc_ids: List[str],
    verbose: bool = False,
    out_path: str = None,
    dry_run: bool = False,
) -> List[Dict]:

    results = []

    results = []

    # ── Build dataset (auto or manual) ────────────────────────────────
    from evaluation.dataset import AUTO_GENERATE, EVAL_DATASET, build_auto_dataset

    if AUTO_GENERATE:
        print("  ⚙  Auto-generating questions from your documents...")
        # Load a sample of real chunks to ground the questions
        all_sample_chunks = []
        for doc_id in doc_ids[:5]:   # sample first 5 docs
            chunks = load_chunks(doc_id)
            if chunks:
                all_sample_chunks.extend(chunks[:10])
        eval_data = build_auto_dataset(all_sample_chunks)
        if not eval_data:
            print("❌  Could not build auto dataset — no chunks found.")
            return results
        print(f"  ✅  Generated {len(eval_data)} questions from document content.\n")
    else:
        eval_data = EVAL_DATASET

    total = len(eval_data)
    for i, sample in enumerate(eval_data, 1):
        question   = sample["question"]
        gt_answer  = sample["ground_truth_answer"]
        gt_context = sample["ground_truth_contexts"]

        print(f"\n[{i}/{total}] {question}")

        # ── Retrieve ──────────────────────────────────────────────────
        # If question is tied to a specific doc, search only that doc
        search_ids = [sample["doc_hint"]] if sample.get("doc_hint") else doc_ids
        raw_chunks = search_multiple(search_ids, question, k=config.RETRIEVAL_TOP_K * 2)

        if not raw_chunks:
            print("  ⚠  No chunks retrieved — skipping.")
            continue

        # ── Rerank ────────────────────────────────────────────────────
        reranked = rerank(question, raw_chunks, top_n=config.RERANK_TOP_N)

        # ── Generate ──────────────────────────────────────────────────
        if dry_run:
            generated_answer = " ".join(
                c.get("text", "")[:80] for c in reranked
            )
            gen = {"query_type": "dry-run"}
        else:
            gen = answer_question(question, reranked)
            generated_answer = gen["answer"]

        # ── Score ─────────────────────────────────────────────────────
        scores = score_sample(
            question=question,
            generated_answer=generated_answer,
            retrieved_chunks=reranked,
            ground_truth_answer=gt_answer,
            ground_truth_contexts=gt_context,
            dry_run=dry_run,
        )
        scores["generated_answer"] = generated_answer
        scores["query_type"]       = gen.get("query_type", "unknown")
        scores["chunks_retrieved"] = len(reranked)
        results.append(scores)

        if verbose:
            print(f"  Query type  : {scores['query_type']}")
            print(f"  Chunks used : {scores['chunks_retrieved']}")
            print(f"  Answer      : {generated_answer[:120]}...")
            print(f"  Precision   : {scores['context_precision']:.2%}")
            print(f"  Recall      : {scores['context_recall']:.2%}")
            print(f"  Correctness : {scores['answer_correctness']:.2%}")
            print(f"  Faithfulness: {scores['faithfulness']:.2%}")

    _print_summary(results)

    if out_path:
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Detailed results saved to: {out_path}\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="DocuMind RAG Evaluation CLI")
    parser.add_argument(
        "--doc-id", dest="doc_id", default=None,
        help="Evaluate against a specific document ID (default: all documents)"
    )
    parser.add_argument(
        "--out", dest="out", default=None,
        help="Save full results to a JSON file (e.g. results.json)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print per-question detail"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip LLM generation — only measures retrieval metrics (free)"
    )
    args = parser.parse_args()

    # resolve doc IDs
    if args.doc_id:
        doc_ids = [args.doc_id]
    else:
        doc_ids = _discover_doc_ids()

    if not doc_ids:
        print("\n❌  No documents found in storage.")
        print("   Upload at least one PDF via the app before running evaluation.\n")
        sys.exit(1)

    print(f"\n🔍 DocuMind Evaluation — {len(doc_ids)} document(s) loaded")
    run_evaluation(doc_ids, verbose=args.verbose, out_path=args.out, dry_run=args.dry_run)


if __name__ == "__main__":
    main()