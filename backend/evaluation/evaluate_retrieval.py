"""
Retrieval & generation evaluation harness for the RAG pipeline.

This is a deliberately dependency-light alternative to Ragas/DeepEval
(Module 12 in the capstone spec). Ragas and DeepEval are excellent, but by
default they call an OpenAI-compatible judge LLM for several metrics,
which means: an API key, network egress, and per-run cost. That's a real
option once you have an OpenAI/Anthropic key wired up -- see the notes at
the bottom of this file for how to plug Ragas in as a drop-in upgrade.

What this script measures without any external API:
  - Hit Rate @ k       : did retrieval find the page containing the answer?
  - Mean Reciprocal Rank: how high up was the correct page?
  - Latency             : end-to-end wall-clock time per question.

Usage:
    1. Upload a document through the running API and note its document_id.
    2. Fill in a test set (see `example_test_set.json`) mapping questions
       to the PDF page number that contains the answer.
    3. Run:
         python evaluation/evaluate_retrieval.py \
             --base-url http://localhost:8000 \
             --token <your JWT access token> \
             --document-id 1 \
             --test-set evaluation/example_test_set.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

import urllib.request
import urllib.error


def _post(url: str, token: str, payload: dict) -> str:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8")


def evaluate(base_url: str, token: str, document_id: int, test_set: list[dict]):
    results = []

    for case in test_set:
        question = case["question"]
        expected_page = case["expected_page"]

        start = time.perf_counter()
        try:
            raw_response = _post(
                f"{base_url}/chat/",
                token,
                {"question": question, "document_id": document_id},
            )
        except urllib.error.URLError as e:
            print(f"[ERROR] Request failed for question '{question}': {e}", file=sys.stderr)
            continue
        latency = time.perf_counter() - start

        answer_text, citations = _split_answer_and_citations(raw_response)
        cited_pages = [c.get("page") for c in citations]

        hit = expected_page in cited_pages
        rank = (cited_pages.index(expected_page) + 1) if hit else None

        results.append(
            {
                "question": question,
                "expected_page": expected_page,
                "cited_pages": cited_pages,
                "hit": hit,
                "reciprocal_rank": (1 / rank) if rank else 0.0,
                "latency_seconds": round(latency, 3),
                "answer_preview": answer_text[:120],
            }
        )

    _print_report(results)
    return results


def _split_answer_and_citations(raw_response: str):
    delimiter = "\n\n[[CITATIONS]]"
    if delimiter in raw_response:
        answer, citation_json = raw_response.split(delimiter, 1)
        try:
            citations = json.loads(citation_json)
        except json.JSONDecodeError:
            citations = []
        return answer, citations
    return raw_response, []


def _print_report(results: list[dict]):
    if not results:
        print("No results to report.")
        return

    n = len(results)
    hit_rate = sum(r["hit"] for r in results) / n
    mrr = sum(r["reciprocal_rank"] for r in results) / n
    avg_latency = sum(r["latency_seconds"] for r in results) / n

    print("\n" + "=" * 60)
    print("RETRIEVAL EVALUATION REPORT")
    print("=" * 60)
    print(f"Test cases           : {n}")
    print(f"Hit Rate (page found) : {hit_rate:.1%}")
    print(f"Mean Reciprocal Rank  : {mrr:.3f}")
    print(f"Avg latency           : {avg_latency:.2f}s")
    print("-" * 60)

    for r in results:
        status = "PASS" if r["hit"] else "FAIL"
        print(f"[{status}] q='{r['question'][:50]}' expected_page={r['expected_page']} cited_pages={r['cited_pages']}")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the RAG chatbot's retrieval quality.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--token", required=True, help="JWT access token from /auth/login")
    parser.add_argument("--document-id", type=int, required=True)
    parser.add_argument("--test-set", required=True, help="Path to a JSON test-set file")
    args = parser.parse_args()

    test_set = json.loads(Path(args.test_set).read_text())
    evaluate(args.base_url, args.token, args.document_id, test_set)

# ---------------------------------------------------------------------------
# Upgrading to Ragas / DeepEval (optional, needs an LLM judge + API key):
#
#   pip install ragas deepeval
#
#   from ragas import evaluate as ragas_evaluate
#   from ragas.metrics import faithfulness, answer_relevancy, context_precision
#   # Build a HuggingFace `Dataset` with columns: question, answer,
#   # contexts (list[str]), ground_truth, then call ragas_evaluate(dataset,
#   # metrics=[faithfulness, answer_relevancy, context_precision]).
#   # This adds LLM-judged metrics on top of the deterministic ones above.
# ---------------------------------------------------------------------------
