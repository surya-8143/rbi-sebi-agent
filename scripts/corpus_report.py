"""Publish corpus metadata and inspection findings, never regulator source text."""
import csv
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.io import digest, read_jsonl, write_json

if __name__ == "__main__":
    manifest = list(csv.DictReader(Path("data/manifest.csv").open(encoding="utf-8")))
    chunks = read_jsonl("data/processed/chunks.jsonl")
    if digest(chunks) != "1a1ea73681194aeb4ad5fc6c9567bfbd7a388ba17a780710c0c276102a1bb9cc":
        raise ValueError("Recorded inspection is bound to chunker-v2 corpus; inspect the new snapshot before updating it")
    questions = read_jsonl("evals/questions.draft.jsonl")
    report = json.loads(Path("data/processed/data_report.json").read_text(encoding="utf-8"))
    # These findings refer to the seed-7, 30-chunk inspection of chunker v2.
    context_needed = {1, 6, 8, 10, 11, 16, 19, 21, 30}
    sample = random.Random(7).sample(chunks, 30)
    record = {"kind": "corpus", "date": datetime.now(timezone.utc).isoformat(),
              "documents": len(manifest), "issuers": dict(Counter(r["issuer"] for r in manifest)),
              "formats": dict(Counter(r["source_format"] for r in manifest)),
              "pdf_pages": sum(int(r["pages"]) for r in manifest), "chunks": len(chunks),
              "corpus_hash": digest(chunks), "draft_questions": len(questions), "verified_questions": 0,
              "median_chunk_characters": report["median_chunk_characters"],
              "short_chunks_under_300": report["under_300"], "oversized_chunks": report["over_2800"],
              "inspection": {"reviewer": "AI-assisted text inspection; not independent human validation", "seed": 7,
                  "sample_size": 30, "needs_surrounding_context": len(context_needed),
                  "findings": "Remaining headings, table/form labels and cross-page fragments need surrounding context. Flattened table relationships are not guaranteed.",
                  "rows": [{"chunk_id": c["chunk_id"], "page": c["page"], "section_path": c["section_path"],
                            "finding": "needs surrounding context" if i in context_needed else "readable text; applicability not verified"}
                           for i, c in enumerate(sample, 1)]},
              "limits": ["49 HTML captures cite sections, not PDF pages", "All source metadata remains draft",
                         "Current captures cannot reconstruct unreviewed historical versions", "No human-verified labels or frozen test split"]}
    write_json("results/official_corpus.json", record)
    print({k: v for k, v in record.items() if k not in {"inspection", "limits"}})
