import copy

import pytest

from evals.run import evaluate
from scripts.review_labels import apply_review, export, packet
from src.io import ROOT, read_jsonl


def sample(chunks):
    qs = [q for q in read_jsonl(ROOT / "tests/fixtures/questions.jsonl") if q["id"] == "fixture_02_1"]
    qs[0]["label_status"] = "draft"
    enriched = [{"version_date": c["date_issued"], "sha256": "fixture", "source_url": "fictional", **c} for c in chunks]
    return qs, enriched


def test_review_needs_identity_and_matching_sources(tmp_path, chunks):
    qs, cs = sample(chunks)
    p = packet(qs, cs)
    review = {"dataset_hash": p["dataset_hash"], "corpus_hash": p["corpus_hash"], "reviewer": "", "reviewed_at": "2026-11-08", "decisions": [{"id": qs[0]["id"], "decision": "accept", "notes": "test"}]}
    with pytest.raises(ValueError, match="identity"):
        apply_review(review, qs, cs, tmp_path / "verified.jsonl")
    review["reviewer"] = "unit-test reviewer"
    changed = copy.deepcopy(cs)
    changed[0]["text"] += " changed"
    with pytest.raises(ValueError, match="fingerprint"):
        apply_review(review, qs, changed, tmp_path / "verified.jsonl")
    assert apply_review(review, qs, cs, tmp_path / "verified.jsonl") == 1
    assert qs[0]["label_status"] == "draft"
    with pytest.raises(ValueError, match="overwritten"):
        apply_review(review, qs, cs, tmp_path / "verified.jsonl")


def test_review_packet_escapes_source_script(tmp_path, chunks):
    qs, cs = sample(chunks)
    qs[0]["question"] += " </script><script>alert(1)</script>"
    page = export(qs, cs, tmp_path / "review.html").read_text(encoding="utf-8")
    assert "</script><script>alert(1)" not in page
    assert 'value="pending"' in page


def test_drafts_are_not_silently_evaluated(agent_factory, tmp_path):
    questions = read_jsonl(ROOT / "tests/fixtures/questions.jsonl")[:1]
    questions[0]["label_status"] = "draft"
    agent, chat = agent_factory([])
    with pytest.raises(ValueError, match="verified"):
        evaluate(agent, questions, tmp_path / "result.json")
    with pytest.raises(ValueError, match="dev"):
        evaluate(agent, questions, tmp_path / "result.json", fixture=True, allow_draft=True)
    assert not chat.calls
