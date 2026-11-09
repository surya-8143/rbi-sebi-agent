"""Dev-only threshold selection and optional judge agreement analysis."""
import argparse
import json

from src.io import digest, read_jsonl, write_json
from src.retrieval.search import Searcher


def tune_tau(searcher, questions):
    if any(q["split"] != "dev" for q in questions):
        raise ValueError("Threshold tuning must use dev only")
    scored = [(q, searcher.search(q["question"], k=1)) for q in questions]
    positive = sorted(hits[0][1] for q, hits in scored if not q["must_refuse"] and hits)
    if not positive or not any(q["must_refuse"] for q in questions):
        raise ValueError("Need answerable and refusal examples")
    tau = positive[int(.1 * (len(positive) - 1))]
    return {"tau": tau, "mode": searcher.mode, "reranker": searcher.reranker is not None,
            "dataset_hash": digest(questions), "corpus_hash": digest(searcher.chunks),
            "refusal_cases_below": sum(not hits or hits[0][1] < tau for q, hits in scored if q["must_refuse"]),
            "refusal_cases": sum(q["must_refuse"] for q in questions)}


def cohen_kappa(human, judge):
    if len(human) != len(judge) or not human:
        raise ValueError("Labels must be nonempty and aligned")
    labels = set(human) | set(judge)
    agreement = sum(a == b for a, b in zip(human, judge)) / len(human)
    expected = sum(human.count(label) * judge.count(label) / len(human) ** 2 for label in labels)
    return {"n": len(human), "agreement": agreement, "kappa": (agreement - expected) / (1 - expected) if expected < 1 else None}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--questions", default="evals/questions.jsonl")
    p.add_argument("--index", default="index")
    p.add_argument("--out", default="results/calibration.json")
    p.add_argument("--rerank", action="store_true")
    a = p.parse_args()
    result = tune_tau(Searcher(a.index, rerank=a.rerank), [q for q in read_jsonl(a.questions) if q["split"] == "dev"])
    write_json(a.out, result)
    print(json.dumps(result, indent=2))
