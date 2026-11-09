"""Small real-source CPU model smoke run, explicitly using unverified draft labels."""
import argparse

from evals.run import evaluate
from src.agent.config import Config
from src.agent.graph import Agent
from src.io import read_jsonl
from src.retrieval.search import Searcher

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--index", default="index/official_bm25")
    p.add_argument("--out", default="results/official_draft_smoke.json")
    a = p.parse_args()
    questions = [q for q in read_jsonl("evals/questions.draft.jsonl") if q["id"] in {"draft_001", "draft_034", "draft_037"}]
    result = evaluate(Agent(Searcher(a.index), Config.from_env()), questions, a.out, allow_draft=True)
    print(result["metrics"])
