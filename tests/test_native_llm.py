import json

import pytest
from pydantic import ValidationError

from src.agent.llm import native_messages, structured_content, wire_message
from src.agent.verify import Citation


def test_native_tool_messages_preserve_pairing():
    message = wire_message({"content": "", "tool_calls": [
        {"function": {"name": "calculate", "arguments": {"expression": "3*500"}}},
        {"function": {"name": "search_circulars", "arguments": {"query": "retention"}}}]})
    calls = message["tool_calls"]
    assert calls[0]["id"] != calls[1]["id"]
    assert json.loads(calls[0]["function"]["arguments"])["expression"] == "3*500"
    result = native_messages([message, {"role": "tool", "tool_call_id": calls[0]["id"], "content": "1500"}])
    assert result[0]["tool_calls"][0]["function"]["arguments"] == {"expression": "3*500"}
    assert result[1] == {"role": "tool", "tool_name": "calculate", "content": "1500"}


def test_quote_word_limit_in_generation_schema():
    assert "pattern" in Citation.model_json_schema()["properties"]["quote"]
    Citation(chunk_id="x", quote=" ".join(["word"] * 12))
    with pytest.raises(ValidationError):
        Citation(chunk_id="x", quote=" ".join(["word"] * 13))


def test_json_tail_is_logged_but_prose_is_not_mined():
    content, discarded = structured_content('{"ok": true}\n</think>\nextra text')
    assert json.loads(content) == {"ok": True} and discarded
    content, discarded = structured_content('prose {"ok": true}')
    assert content.startswith("prose") and not discarded


def test_structured_answer_uses_one_post_retrieval_call(agent_factory):
    from conftest import valid_answer
    answer = json.loads(valid_answer()["content"])
    decision = {"action": "answer", "tool": "none", "arguments": "{}", "answer": answer}
    agent, chat = agent_factory([{"content": "IN_SCOPE"}, {"content": json.dumps(decision)}])
    result = agent.invoke("What is the FRA KYC retention period?")
    assert result["status"] == "answered"
    assert len(chat.calls) == 2


def test_structured_tool_route_validates_arguments(agent_factory):
    from conftest import valid_answer
    decision = {"action": "tool", "tool": "calculate", "arguments": '{"expression":"__import__(1)"}', "answer": None}
    agent, _ = agent_factory([{"content": "IN_SCOPE"}, {"content": json.dumps(decision)}, valid_answer()], max_steps=1)
    result = agent.invoke("What is the FRA KYC retention period?")
    tools = [e for e in result["trace"] if e["kind"] == "tool"]
    assert "error" in tools[-1]["result"]


def test_long_exact_quote_is_split_losslessly_but_invention_is_not():
    from src.agent.verify import split_exact_quotes
    text = "These transaction records must be kept for at least five years after the transaction date."
    answer = {"can_answer": True, "claims": [{"text": "Five years.", "citations": [{"chunk_id": "x", "quote": text}]}]}
    result, repairs = split_exact_quotes(answer, {"x": {"text": text}})
    citations = result["claims"][0]["citations"]
    assert repairs == 1 and all(len(c["quote"].split()) <= 12 for c in citations)
    assert " ".join(c["quote"] for c in citations) == text
    fabricated, repairs = split_exact_quotes(answer, {"x": {"text": "Different source"}})
    assert repairs == 0 and fabricated == answer


