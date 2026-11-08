import pytest

from evals.retrieval_eval import evaluate
from src.io import ROOT, read_jsonl
from src.retrieval.chunk import chunk_doc
from src.retrieval.index import build
from src.retrieval.search import Searcher


def test_chunk_boundaries_and_long_lines(chunks):
    meta = chunks[0]
    result = chunk_doc(meta, [{"page": 1, "text": "1. " + "word " * 2000}, {"page": 2, "text": "2. Short provision."}])
    assert all(len(c["text"]) <= 2800 for c in result)
    assert len({c["chunk_id"] for c in result}) == len(result)
    assert result[-1]["page"] == 2 and result[-1]["section_path"] == "2"
    assert result[-1]["body"] == "2. Short provision."


def test_fixture_recall(searcher):
    report = evaluate(searcher, read_jsonl(ROOT / "tests/fixtures/questions.jsonl"))
    assert report["recall@5"] >= .8


def test_filters_are_applied_before_top_k(searcher):
    assert searcher.search("KYC", issuer="RBI") == []
    assert searcher.search("KYC", as_of="2024-01-01") == []
    assert len(searcher.search("FRA", k=2)) <= 2


def test_sparse_index_roundtrip_and_dense_failure(tmp_path):
    build(ROOT / "tests/fixtures/chunks.jsonl", tmp_path)
    searcher = Searcher(tmp_path)
    assert searcher.search("KYC retained")
    with pytest.raises(ValueError, match="Dense"):
        searcher.search("KYC", mode="dense")


def test_no_irrelevant_sparse_results(searcher):
    assert searcher.search("xylophonezzzyyy") == []


def test_parser_preserves_repeated_body_text(tmp_path):
    import pymupdf

    from src.retrieval.parse import parse_pdf
    path = tmp_path / "test.pdf"
    doc = pymupdf.open()
    for i in range(4):
        page = doc.new_page()
        page.insert_text((70, 30), "Repeated header")
        page.insert_text((70, 200), "Repeated mandatory body obligation must remain on each page.")
        page.insert_text((70, 230), f"Distinct paragraph {i} with sufficient useful text for the parser validation.")
    doc.save(path)
    doc.close()
    pages = parse_pdf(path)
    assert all("Repeated header" not in p["text"] for p in pages)
    assert all("Repeated mandatory" in p["text"] for p in pages)
