import copy

import pytest
from conftest import valid_answer

from evals.calibrate import cohen_kappa
from evals.run import evaluate
from evals.schema import validate_questions
from evals.score import aggregate, is_hit, key_facts_ok, score_question, wilson
from src.io import ROOT, read_jsonl


def test_fact_boundaries_and_forbidden():
    assert key_facts_ok("30 days and 10,00,000", [["30 days"], ["1000000"]])[0]
    assert not key_facts_ok("130 days", [["30 days"]])[0]
    assert not key_facts_ok("30 days or 20 days", [["30 days"]], ["20 days"])[0]


def test_gold_pages_are_enforced():
    assert not is_hit({"doc_id": "x", "page": 2, "text": "a fact"}, {"doc_id": "x", "pages": [1], "evidence": "a fact"})


def test_wilson_and_empty_metrics():
    low, high = wilson(5, 10)
    assert .23 < low < .24 and .76 < high < .77
    assert wilson(0, 0) == [None, None]
    assert aggregate([])["metrics"]["citation_valid"]["rate"] is None


def test_errors_not_counted_as_correct_refusals():
    q = {"id": "x", "category": "unanswerable", "key_facts": [], "gold": [], "must_refuse": True}
    row = score_question(q, {"status": "error", "answer": {}})
    assert not row["refusal_correct"] and row["error"]


def test_question_validation():
    rows = read_jsonl(ROOT / "tests/fixtures/questions.jsonl")
    validate_questions(rows)
    with pytest.raises(ValueError, match="Duplicate"):
        validate_questions(rows + [rows[0]])
    with pytest.raises(ValueError):
        validate_questions(rows, full=True)


def test_resume_and_changed_config_rejected(tmp_path, agent_factory, monkeypatch):
    monkeypatch.chdir(tmp_path)
    questions = [q for q in read_jsonl(ROOT / "tests/fixtures/questions.jsonl") if q["id"] == "fixture_02_1"]
    agent, chat = agent_factory([{"content": "IN_SCOPE"}, {"content": "Ready"}, valid_answer()])
    out = tmp_path / "run.json"
    result = evaluate(agent, questions, out, fixture=True)
    assert result["metrics"]["key_fact_strict"]["k"] == 1
    evaluate(agent, questions, out, fixture=True)
    assert len(chat.calls) == 3
    changed = copy.deepcopy(questions)
    changed[0]["question"] += " Changed"
    with pytest.raises(ValueError, match="fingerprint"):
        evaluate(agent, changed, out, fixture=True)


def test_kappa():
    assert cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0])["kappa"] == 1
    assert cohen_kappa([1, 1], [1, 1])["kappa"] is None
