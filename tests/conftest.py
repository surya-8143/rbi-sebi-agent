import json

import pytest

from src.agent.config import Config
from src.agent.graph import Agent
from src.io import ROOT, read_jsonl
from src.retrieval.search import Searcher


class ScriptedChat:
    def __init__(self, messages):
        self.messages = iter(messages)
        self.calls = []

    def __call__(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        value = next(self.messages)
        return {"message": {"role": "assistant", **value}, "tokens": 11, "seconds": .01}


def valid_answer(chunk_id="fra_kyc:0001", quote="KYC records must be retained for 5 years.", text="Records are retained for 5 years."):
    return {"content": json.dumps({"can_answer": True, "claims": [{"text": text, "citations": [{"chunk_id": chunk_id, "quote": quote}]}]})}


@pytest.fixture
def chunks():
    return read_jsonl(ROOT / "tests/fixtures/chunks.jsonl")


@pytest.fixture
def searcher(chunks):
    return Searcher(chunks=chunks)


@pytest.fixture
def agent_factory(searcher):
    def make(messages, **kwargs):
        chat = ScriptedChat(messages)
        return Agent(searcher, Config(fixture=True, **kwargs), chat), chat
    return make
