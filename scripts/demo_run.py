"""Three real-model smoke cases. Deliberately not a full evaluation benchmark."""
import argparse

from evals.run import evaluate
from src.agent.config import Config
from src.agent.graph import Agent
from src.io import ROOT, read_jsonl
from src.retrieval.search import Searcher

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results/fixture_model_smoke.json")
    args = parser.parse_args()
    questions = [q for q in read_jsonl(ROOT / "tests/fixtures/questions.jsonl")
                 if q["id"] in {"fixture_02_1", "fixture_refuse_1", "fixture_refuse_2"}]
    agent = Agent(Searcher(), Config.from_env(fixture=True))
    evaluate(agent, questions, args.out, fixture=True)
