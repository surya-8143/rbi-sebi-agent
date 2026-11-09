import argparse
import csv
from pathlib import Path

from evals.schema import validate_questions
from src.io import read_jsonl

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--questions", default="evals/questions.jsonl")
    p.add_argument("--manifest", default="data/manifest.csv")
    p.add_argument("--fixture", action="store_true")
    p.add_argument("--allow-ai-reviewed", action="store_true")
    a = p.parse_args()
    manifest = None if a.fixture else {r["doc_id"]: r for r in csv.DictReader(Path(a.manifest).open(encoding="utf-8-sig"))}
    questions = validate_questions(read_jsonl(a.questions), manifest, full=not a.fixture, allow_ai_reviewed=a.allow_ai_reviewed)
    print(f"Validated {len(questions)} questions")
