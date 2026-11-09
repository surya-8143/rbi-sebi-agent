"""Validate a local corpus manifest, parse PDFs, and produce auditable chunks."""
import argparse
import csv
import hashlib
import re
import statistics
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from src.io import write_json, write_jsonl
from src.retrieval.chunk import chunk_doc
from src.retrieval.html import parse_html
from src.retrieval.parse import parse_pdf


def ingest(manifest="data/manifest.csv", raw="data/raw", out="data/processed"):
    root, output = Path(raw).resolve(), Path(out)
    rows = list(csv.DictReader(Path(manifest).open(encoding="utf-8-sig")))
    if not rows:
        raise ValueError("Manifest is empty. Add your official PDFs and metadata first.")
    ids, chunks, all_pages, documents = set(), [], [], []
    for row in rows:
        doc_id = row["doc_id"]
        if not re.fullmatch(r"[a-z0-9_]{3,80}", doc_id) or doc_id in ids:
            raise ValueError("Invalid or duplicate doc_id")
        ids.add(doc_id)
        if row["issuer"] not in {"RBI", "SEBI"}:
            raise ValueError("Official corpus issuer must be RBI or SEBI")
        date.fromisoformat(row["date_issued"])
        url = urlparse(row["source_url"])
        domain = "rbi.org.in" if row["issuer"] == "RBI" else "sebi.gov.in"
        if url.scheme != "https" or not (url.hostname == domain or (url.hostname or "").endswith("." + domain)):
            raise ValueError("Source must be an official HTTPS URL")
        path = (root / row["filename"]).resolve()
        source_format = row.get("source_format") or "pdf"
        expected_suffix = ".html" if source_format == "html" else ".pdf"
        if source_format not in {"html", "pdf"} or not path.is_relative_to(root) or path.suffix.lower() != expected_suffix:
            raise ValueError("Invalid source format or path escapes data/raw")
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if row.get("sha256") and row["sha256"] != sha:
            raise ValueError(f"Source hash mismatch for {doc_id}")
        pages = parse_html(path) if source_format == "html" else parse_pdf(path)
        row.update(sha256=sha, pages=str(0 if source_format == "html" else len(pages)))
        doc_chunks = chunk_doc(row, pages)
        documents.append({"doc_id": doc_id, "source_format": source_format, "pages": int(row["pages"]), "chunks": len(doc_chunks),
                          "mean_characters_per_page": statistics.mean(len(p["text"]) for p in pages),
                          "review_needed": any(len(p["text"]) < 100 for p in pages)})
        all_pages.append((doc_id, pages))
        chunks.extend(doc_chunks)
    # Write only after the entire manifest passes validation.
    for doc_id, pages in all_pages:
        write_jsonl(output / f"{doc_id}.pages.jsonl", pages)
    write_jsonl(output / "chunks.jsonl", chunks)
    with Path(manifest).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lengths = [len(c["text"]) for c in chunks]
    report = {"documents": documents, "document_count": len(rows), "chunk_count": len(chunks),
              "median_chunk_characters": statistics.median(lengths),
              "under_300": sum(n < 300 for n in lengths), "over_2800": sum(n > 2800 for n in lengths)}
    write_json(output / "data_report.json", report)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default="data/manifest.csv")
    p.add_argument("--raw", default="data/raw")
    p.add_argument("--out", default="data/processed")
    args = p.parse_args()
    print(ingest(args.manifest, args.raw, args.out))
