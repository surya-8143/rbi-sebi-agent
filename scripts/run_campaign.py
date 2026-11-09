"""Execute frozen experiments sequentially; every result remains resumable."""
import argparse
import json
from pathlib import Path

from evals.run import evaluate
from redteam.run import run
from src.agent.config import Config
from src.agent.graph import Agent
from src.io import digest, read_jsonl
from src.retrieval.search import Searcher


def campaign(stages):
    freeze = json.loads(Path("evals/benchmark_freeze.json").read_text(encoding="utf-8"))
    questions = read_jsonl("evals/questions.jsonl")
    if digest(questions) != freeze["dataset_hash"]:
        raise ValueError("Frozen dataset changed")
    model = freeze["model"]
    attacks = read_jsonl("redteam/attacks.jsonl")
    # Fixed dev-only IDs; includes both supported and refusal cases.
    benign = [q for q in questions if q["split"] == "dev"]
    benign = [q for q in benign if q["must_refuse"]][:4] + [q for q in benign if not q["must_refuse"]][:16]
    for stage in stages:
        print("START", stage, flush=True)
        if stage in {"baseline_dev", "baseline_test", "latest_dev", "latest_test"}:
            final = stage.startswith("latest")
            searcher = Searcher("index/official" if final else "index/official_bm25", rerank=final)
            agent = Agent(searcher, Config.from_env(model=model, defense=5 if final else 0))
            result = evaluate(agent, questions, f"results/{stage}.json", stage.rsplit("_", 1)[1], allow_ai_reviewed=True)
            print("DONE", stage, result["metrics"], flush=True)
        elif stage.startswith("redteam_d"):
            level = int(stage[-1])
            config = Config.from_env(model=model, defense=level, fixture=True, redteam=True)
            agents = {"normal": Agent(Searcher("index"), config), "attack": Agent(Searcher("index_attack"), config)}
            result = run(agents, attacks, f"results/{stage}.json")
            print("DONE", stage, result["groups"], flush=True)
        elif stage.startswith("benign_d"):
            level = int(stage[-1])
            agent = Agent(Searcher("index/official_bm25"), Config.from_env(model=model, defense=level))
            evaluate(agent, benign, f"results/{stage}.json", allow_ai_reviewed=True)
        else:
            raise ValueError("Unknown campaign stage")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--stages", nargs="+", default=["baseline_dev", "latest_dev", "baseline_test", "latest_test"] +
                   [f"redteam_d{i}" for i in range(6)] + [f"benign_d{i}" for i in range(6)])
    campaign(p.parse_args().stages)
