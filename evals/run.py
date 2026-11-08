"""Resumable evaluation; configuration and corpus fingerprints prevent mixed runs."""
import argparse
import json
import os
import platform
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from evals.schema import validate_questions
from evals.score import aggregate, score_question
from src.agent.config import Config
from src.agent.graph import Agent
from src.io import digest, git_sha, read_jsonl, source_hash, write_json
from src.retrieval.search import Searcher
from src.tracing import save_trace


def evaluate(agent, questions, out, split="dev", fixture=False):
    validate_questions(questions, agent.tools.manifest)
    selected = [q for q in questions if q["split"] == split]
    if not selected:
        raise ValueError("No questions in requested split")
    if not fixture and any(q["label_status"] != "verified" for q in selected):
        raise ValueError("Official evaluation requires verified labels")
    identity = {"schema": 1, "config": asdict(agent.config), "prompt_hash": agent.prompt_hash,
                "dataset_hash": digest(questions), "corpus_hash": digest(agent.tools.searcher.chunks),
                "split": split, "fixture": fixture, "git_sha": git_sha(), "source_hash": source_hash(), "python": platform.python_version()}
    fingerprint = digest(identity)
    partial = Path(str(out) + ".partial.jsonl")
    partial.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    if partial.exists():
        # A torn last write is discarded; other malformed lines fail loudly.
        lines = partial.read_bytes().splitlines(keepends=True)
        if lines and not lines[-1].endswith(b"\n"):
            partial.write_bytes(b"".join(lines[:-1]))
        rows = read_jsonl(partial)
        if any(r["fingerprint"] != fingerprint for r in rows):
            raise ValueError("Resume fingerprint mismatch; choose a new output path")
        if len({r["id"] for r in rows}) != len(rows):
            raise ValueError("Duplicate IDs in partial run")
    done = {r["id"] for r in rows}
    with partial.open("a", encoding="utf-8") as f:
        for question in selected:
            if question["id"] in done:
                continue
            state = agent.invoke(question["question"])
            trace_id = save_trace(state)
            row = score_question(question, state) | {"fingerprint": fingerprint, "trace_id": trace_id}
            f.write(json.dumps(row) + "\n")
            f.flush()
            os.fsync(f.fileno())
            rows.append(row)
            print(question["id"], state["status"], state.get("reason", ""), flush=True)
    if {r["id"] for r in rows} != {q["id"] for q in selected}:
        raise ValueError("Partial file IDs differ from evaluation split")
    result = {"kind": "evaluation", "meta": identity | {"date": datetime.now(timezone.utc).isoformat(),
              "model": agent.config.model, "fingerprint": fingerprint, "complete": True},
              "rows": rows, **aggregate(rows)}
    write_json(out, result)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--questions", default="evals/questions.jsonl")
    p.add_argument("--index", default="index")
    p.add_argument("--split", choices=["dev", "test"], default="dev")
    p.add_argument("--out", required=True)
    p.add_argument("--fixture", action="store_true")
    p.add_argument("--defense", type=int, default=5)
    args = p.parse_args()
    agent = Agent(Searcher(args.index), Config.from_env(fixture=args.fixture, defense=args.defense))
    evaluate(agent, read_jsonl(args.questions), args.out, args.split, args.fixture)


if __name__ == "__main__":
    main()
