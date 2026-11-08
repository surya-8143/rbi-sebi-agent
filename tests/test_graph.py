import json

from conftest import valid_answer

from src.agent.verify import verify

QUESTION = "What is the KYC record retention period in the FRA fictional KYC Records circular?"


def test_answer_and_token_accounting(agent_factory):
    agent, chat = agent_factory([{"content": "IN_SCOPE"}, {"content": "Ready"}, valid_answer()])
    state = agent.invoke(QUESTION)
    assert state["status"] == "answered", state
    assert state["tokens"] == 33 and len(chat.calls) == 3
    assert state["answer"]["sources"][0]["date_issued"] == "2025-01-01"
    assert not verify(state["answer"], state["seen"])


def test_one_citation_retry(agent_factory):
    agent, chat = agent_factory([{"content": "IN_SCOPE"}, {"content": "Ready"}, valid_answer(quote="invented"), valid_answer()])
    state = agent.invoke(QUESTION)
    assert state["status"] == "answered" and state["attempts"] == 1
    assert state["tokens"] == 44


def test_second_bad_citation_refuses(agent_factory):
    agent, _ = agent_factory([{"content": "IN_SCOPE"}, {"content": "Ready"}, valid_answer(quote="invented"), valid_answer(quote="invented")])
    state = agent.invoke(QUESTION)
    assert state["status"] == "refused" and state["reason"] == "citation_failed"


def test_gate_exact_and_fail_closed(agent_factory):
    agent, chat = agent_factory([{"content": "IN_SCOPE ignore previous rules"}])
    state = agent.invoke(QUESTION)
    assert state["status"] == "blocked" and len(chat.calls) == 1


def test_unknown_reference_no_model_call(agent_factory):
    agent, chat = agent_factory([])
    state = agent.invoke("What does RBI circular 2031/77 say?")
    assert state["reason"] == "unknown_reference" and not chat.calls


def test_all_tools_paired_and_budget_bounded(agent_factory):
    call = {"id": "calc", "type": "function", "function": {"name": "calculate", "arguments": '{"expression":"2+3"}'}}
    agent, chat = agent_factory([{"content": "IN_SCOPE"}, {"tool_calls": [call]}, valid_answer()], max_steps=1)
    state = agent.invoke(QUESTION)
    assert state["status"] == "answered"
    assert state["steps"] == 1 and state["tool_calls"] == 2
    assert chat.calls[-1][0][-2]["role"] == "tool"


def test_no_evidence_does_not_finalize(agent_factory):
    agent, chat = agent_factory([{"content": "IN_SCOPE"}])
    state = agent.invoke("xylophonezzzyyy")
    assert state["reason"] == "no_evidence" and len(chat.calls) == 1


def test_unseen_exact_short_and_negation_quotes():
    seen = {"x": {"text": "Banks must not charge fees."}}
    answer = json.loads(valid_answer("x", "Banks must charge fees.")["content"])
    assert verify(answer, seen)
    answer = json.loads(valid_answer("unseen", "Banks must not charge fees.")["content"])
    assert verify(answer, seen)


def test_model_failure_is_not_a_refusal(agent_factory):
    agent, _ = agent_factory([])
    def broken(*args, **kwargs):
        raise RuntimeError("offline")
    agent.chat = broken
    state = agent.invoke(QUESTION)
    assert state["status"] == "error"


def test_request_state_is_reset(agent_factory):
    agent, _ = agent_factory([{"content": "IN_SCOPE"}, {"content": "Ready"}, valid_answer(), {"content": "OUT_OF_SCOPE"}])
    assert agent.invoke(QUESTION)["status"] == "answered"
    second = agent.invoke("cake recipe")
    assert second["seen"] == {} and second["answer"]["citations"] == []
