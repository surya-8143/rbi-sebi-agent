"""Build the explicitly AI-reviewed benchmark authorized by the project owner."""
from collections import Counter
from pathlib import Path

from evals.schema import validate_questions
from evals.score import key_facts_ok
from scripts.benchmark_specs import ROWS
from src.agent.verify import normalized
from src.io import digest, read_jsonl, write_json, write_jsonl


def build():
    chunks = read_jsonl("data/processed/chunks.jsonl")
    rows, counters, audit = [], Counter(), []
    for split, category, question, answer, facts, refs in ROWS:
        counters[split, category] += 1
        ident = f"ai_{split}_{category}_{counters[split, category]:02d}"
        gold, sources = [], []
        for doc_id, quote in refs:
            matches = [c for c in chunks if c["doc_id"] == doc_id and normalized(quote) in normalized(c["body"])]
            if not matches:
                raise ValueError(f"{ident}: missing source evidence: {doc_id}: {quote}")
            c = matches[0]
            gold.append({"doc_id": doc_id, "pages": [c["page"]] if c["page"] else [], "section_path": c["section_path"], "evidence": quote})
            sources.append({"doc_id": doc_id, "sha256": c["sha256"], "chunk_id": c["chunk_id"]})
        rows.append({"id": ident, "split": split, "category": category, "question": question,
                     "gold_answer": answer, "key_facts": facts, "forbidden_facts": [], "gold": gold,
                     "must_refuse": category in {"unanswerable", "out_of_scope"}, "label_status": "ai_reviewed",
                     "notes": "AI-authored and AI-reviewed against captured sources. User authorized this substitution for human review on 2026-11-08. No independent human verification or legal applicability certification."})
        audit.append({"id": ident, "sources": sources, "quote_check": "exact normalized substring", "reviewer": "AI assistant", "human_verified": False})
    validate_questions(rows, {c["doc_id"] for c in chunks}, full=True, allow_ai_reviewed=True)
    for q in rows:
        if not q["must_refuse"] and not key_facts_ok(q["gold_answer"], q["key_facts"], q["forbidden_facts"])[0]:
            raise ValueError(f"Reference answer fails its own scoring facts: {q['id']}")
    # Refuse accidental replacement after freezing the evaluation.
    path = Path("evals/questions.jsonl")
    if Path("evals/benchmark_freeze.json").exists() and read_jsonl(path) != rows:
        raise ValueError("Benchmark frozen; use a separately versioned dataset for label corrections")
    write_jsonl(path, rows)
    write_json("evals/ai_label_audit.json", {"dataset_hash": digest(rows), "corpus_hash": digest(chunks),
               "human_verified": False, "label_method": "AI authoring and source review; exact quotes checked in software", "rows": audit,
               "visual_checks": [{"doc_id": "sebi_md_99571", "page": 89, "method": "Poppler rendering inspected by AI", "finding": "Individual RA application fee is Rs 2,000; table column alignment confirmed"}],
               "limitations": ["No independent annotator", "Related provisions recur across splits; questions are not independent samples",
                               "Version families and repetitive legal language can inflate scores", "Key-fact scoring is not a legal correctness judgment"]})
    print(len(rows), dict(counters))


if __name__ == "__main__":
    build()
