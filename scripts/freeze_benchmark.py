"""Freeze the current dataset and experiment protocol before any test-split run."""
import argparse
from datetime import datetime, timezone
from pathlib import Path

from evals.schema import validate_questions
from src.io import digest, git_sha, read_jsonl, source_hash, write_json

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    a = p.parse_args()
    path = Path("evals/benchmark_freeze.json")
    if path.exists():
        raise ValueError("Already frozen; version changes explicitly")
    questions = read_jsonl("evals/questions.jsonl")
    validate_questions(questions, full=True, allow_ai_reviewed=True)
    write_json(path, {"version": "ai-eval-v1", "frozen_at": datetime.now(timezone.utc).isoformat(),
        "dataset_hash": digest(questions), "dev_hash": digest([q for q in questions if q["split"] == "dev"]),
        "test_hash": digest([q for q in questions if q["split"] == "test"]),
        "source_hash": source_hash(), "git_sha": git_sha(), "model": a.model,
        "label_status": "ai_reviewed", "human_verified": False,
        "protocol": {"baseline": "D0, BM25", "final": "D5, hybrid retrieval with reranker",
                     "test_access": "No tuning on test outcomes; publish failures and all categories",
                     "redteam": "40 attacks at each of D0-D5; synthetic poisoned corpus",
                     "benign_cost": "Same 20 dev cases at each defense with BM25 held fixed",
                     "hardware": "Local CPU; no Colab/GPU latency claim",
                     "threshold": "Disabled: no reliable applicability or answerability inference from retrieval score alone",
                     "judge": "LLM judge skipped; no independent human labels or kappa claimed"}})
    print(path)
