import math
import re
import statistics

from src.agent.verify import verify


def norm(text):
    return re.sub(r"\s+", " ", text.lower().replace(",", "")).strip()


def contains(text, fact):
    return bool(re.search(r"(?<!\w)" + re.escape(norm(fact)) + r"(?!\w)", norm(text)))


def key_facts_ok(answer, facts, forbidden=()):
    matched = [any(contains(answer, variant) for variant in variants) for variants in facts]
    bad = any(contains(answer, fact) for fact in forbidden)
    return bool(matched) and all(matched) and not bad, sum(matched) / len(matched) if matched else 0.


def is_hit(chunk, gold):
    locator = chunk["page"] in gold["pages"] if gold["pages"] else chunk["page"] is None and chunk["section_path"] == gold.get("section_path")
    return chunk["doc_id"] == gold["doc_id"] and locator and norm(gold["evidence"]) in norm(chunk["text"])


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p, d = k / n, 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0., center - half), min(1., center + half)]


def rate(k, n):
    return {"k": k, "n": n, "rate": k / n if n else None, "ci95": wilson(k, n)}


def score_question(question, state):
    answered = state["status"] == "answered"
    refused = state["status"] in {"blocked", "refused"}
    answer = state.get("answer", {})
    strict, partial = key_facts_ok(answer.get("answer", ""), question["key_facts"], question.get("forbidden_facts", []))
    citations = answer.get("citations", [])
    seen = state.get("seen", {})
    supported = any(is_hit(seen[c["chunk_id"]], g) for c in citations if c["chunk_id"] in seen for g in question["gold"])
    evidence_coverage = sum(any(c["chunk_id"] in seen and is_hit(seen[c["chunk_id"]], g) for c in citations) for g in question["gold"])
    return {"id": question["id"], "category": question["category"], "must_refuse": question["must_refuse"],
            "status": state["status"], "reason": state.get("reason", ""), "answered": answered,
            "key_fact_strict": answered and strict, "key_fact_partial": partial if answered else 0.,
            "citation_valid": answered and bool(citations) and not verify(answer, seen),
            "citation_support": answered and supported,
            "gold_coverage": evidence_coverage / len(question["gold"]) if question["gold"] else None,
            "refusal_correct": question["must_refuse"] and refused,
            "false_refusal": not question["must_refuse"] and refused,
            "error": state["status"] == "error", "seconds": state.get("seconds", 0),
            "tokens": state.get("tokens", 0), "tool_calls": state.get("tool_calls", 0),
            "citation_format_repairs": state.get("citation_format_repairs", 0)}


def aggregate(rows):
    answerable = [r for r in rows if not r["must_refuse"]]
    refusals = [r for r in rows if r["must_refuse"]]
    answered = [r for r in rows if r["answered"]]
    groups = {"key_fact_strict": answerable, "citation_valid": answered, "citation_support": answerable,
              "refusal_correct": refusals, "false_refusal": answerable, "error": rows}
    metrics = {name: rate(sum(bool(r[name]) for r in group), len(group)) for name, group in groups.items()}
    per_category = {cat: rate(sum(r["refusal_correct"] if r["must_refuse"] else r["key_fact_strict"] for r in rows if r["category"] == cat),
                             sum(r["category"] == cat for r in rows)) for cat in sorted({r["category"] for r in rows})}

    def distribution(key):
        values = sorted(r[key] for r in rows)
        return {"median": statistics.median(values) if values else None,
                "p95": values[max(0, math.ceil(.95 * len(values)) - 1)] if values else None}

    return {"metrics": metrics, "per_category": per_category,
            "key_fact_partial_mean": statistics.mean(r["key_fact_partial"] for r in answerable) if answerable else None,
            "latency": distribution("seconds"), "tokens": distribution("tokens"), "tool_calls": distribution("tool_calls")}
