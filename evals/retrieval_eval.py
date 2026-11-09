import argparse
import statistics
import time

from evals.schema import validate_questions
from evals.score import is_hit
from src.io import digest, read_jsonl, write_json
from src.retrieval.search import Searcher


def evaluate(searcher, questions, mode="bm25", ks=(1, 3, 5, 10)):
    rows = []
    for q in questions:
        if q["must_refuse"]:
            continue
        started = time.perf_counter()
        chunks = [c for c, _ in searcher.search(q["question"], k=max(ks), mode=mode)]
        rank = next((i for i, c in enumerate(chunks, 1) if any(is_hit(c, g) for g in q["gold"])), None)
        rows.append({"id": q["id"], "rank": rank, "seconds": time.perf_counter() - started,
                     "all_gold_at_5": all(any(is_hit(c, g) for c in chunks[:5]) for g in q["gold"])})
    if not rows:
        raise ValueError("No answerable questions")
    return {"n": len(rows), **{f"recall@{k}": sum(r["rank"] is not None and r["rank"] <= k for r in rows) / len(rows) for k in ks},
            "mrr": sum(1 / r["rank"] if r["rank"] else 0 for r in rows) / len(rows),
            "all_gold_at_5": sum(r["all_gold_at_5"] for r in rows) / len(rows),
            "median_seconds": statistics.median(r["seconds"] for r in rows), "rows": rows}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--index", default="index")
    p.add_argument("--questions", default="evals/questions.jsonl")
    p.add_argument("--out", default="results/retrieval.json")
    p.add_argument("--fixture", action="store_true")
    p.add_argument("--rerank", action="store_true")
    p.add_argument("--allow-draft", action="store_true", help="Exploratory dev measurements; never a verified benchmark")
    p.add_argument("--allow-ai-reviewed", action="store_true")
    a = p.parse_args()
    searcher = Searcher(a.index)
    qs = [q for q in read_jsonl(a.questions) if q["split"] == "dev"]
    validate_questions(qs, {c["doc_id"] for c in searcher.chunks})
    draft = any(q["label_status"] == "draft" for q in qs)
    if draft and not a.allow_draft:
        raise ValueError("Unverified labels require explicit --allow-draft")
    permitted = {"verified", "ai_reviewed"} if a.allow_ai_reviewed else {"verified"}
    if not a.fixture and not a.allow_draft and any(q["label_status"] not in permitted for q in qs):
        raise ValueError("Official benchmark requires verified labels")
    modes = ["bm25", "dense", "hybrid"] if searcher.vector is not None else ["bm25"]
    setups = {mode: evaluate(searcher, qs, mode) for mode in modes}
    if a.rerank:
        setups["hybrid_reranked"] = evaluate(Searcher(a.index, rerank=True), qs, "hybrid")
    write_json(a.out, {"kind": "retrieval", "meta": {"fixture": a.fixture, "exploratory": draft,
               "label_status": "draft" if draft else "synthetic" if a.fixture else "ai_reviewed" if any(q["label_status"] == "ai_reviewed" for q in qs) else "verified",
               "split": "dev", "dataset_hash": digest(qs), "corpus_hash": digest(searcher.chunks)}, "setups": setups})
    print({name: {k: v for k, v in metrics.items() if k != "rows"} for name, metrics in setups.items()})
