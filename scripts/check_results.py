import argparse
import json
import math
from pathlib import Path

from evals.score import aggregate


def check(new, base, tolerance=.03):
    for field in ("dataset_hash", "corpus_hash", "split", "fixture"):
        if new["meta"][field] != base["meta"][field]:
            raise ValueError(f"Incomparable result field: {field}")
    if new["meta"].get("label_status") != base["meta"].get("label_status"):
        raise ValueError("Label review tiers differ")
    if {r["id"] for r in new["rows"]} != {r["id"] for r in base["rows"]}:
        raise ValueError("Evaluation IDs differ")
    for result in (new, base):
        if result["meta"].get("exploratory") or result["meta"].get("label_status") == "draft":
            raise ValueError("Draft-label results cannot pass a benchmark regression gate")
        if not result["meta"].get("complete") or len({r["id"] for r in result["rows"]}) != len(result["rows"]):
            raise ValueError("Incomplete or duplicate results")
        recomputed = aggregate(result["rows"])
        if result["metrics"] != recomputed["metrics"]:
            raise ValueError("Recorded metrics do not match rows")
        if recomputed["metrics"]["error"]["k"]:
            raise ValueError("Operational errors invalidate the benchmark")
    failures = []
    for metric in ("key_fact_strict", "refusal_correct", "citation_valid"):
        n, b = new["metrics"][metric]["rate"], base["metrics"][metric]["rate"]
        if n is None or b is None or not math.isfinite(n) or not math.isfinite(b):
            raise ValueError(f"No evaluable denominator: {metric}")
        if n < b - tolerance:
            failures.append(metric)
    if new["metrics"]["false_refusal"]["rate"] > base["metrics"]["false_refusal"]["rate"] + tolerance:
        failures.append("false_refusal")
    return failures


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--latest", default="results/latest_test.json")
    p.add_argument("--baseline", default="results/baseline_test.json")
    p.add_argument("--allow-missing", action="store_true")
    a = p.parse_args()
    if not Path(a.latest).exists() and not Path(a.baseline).exists() and a.allow_missing:
        print("NOT RUN: real baseline and final results do not exist. Software tests are not a benchmark.")
    else:
        failures = check(json.loads(Path(a.latest).read_text()), json.loads(Path(a.baseline).read_text()))
        if failures:
            raise SystemExit("REGRESSION: " + ", ".join(failures))
        print("Recorded result gate passed")
