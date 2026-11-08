from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CATEGORY_COUNTS = {"single_fact": (16, 14), "multi_section": (10, 10), "numeric_date": (8, 7),
                   "cross_document": (6, 4), "unanswerable": (6, 14), "out_of_scope": (2, 8), "version_conflict": (2, 13)}


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doc_id: str
    pages: list[int] = Field(min_length=1)
    evidence: str = Field(min_length=1)

    @model_validator(mode="after")
    def check_evidence(self):
        if min(self.pages) < 1 or len(self.evidence.split()) > 12:
            raise ValueError("Evidence requires positive pages and at most 12 words")
        return self


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    split: Literal["dev", "test"]
    category: Literal["single_fact", "multi_section", "numeric_date", "cross_document", "unanswerable", "out_of_scope", "version_conflict"]
    question: str = Field(min_length=1)
    gold_answer: str
    key_facts: list[list[str]]
    forbidden_facts: list[str] = []
    gold: list[Evidence]
    must_refuse: bool
    label_status: Literal["synthetic", "draft", "verified"]
    notes: str = ""

    @model_validator(mode="after")
    def check_labels(self):
        if self.must_refuse and (self.gold or self.key_facts):
            raise ValueError("Refusal questions must have empty gold evidence and key facts")
        if not self.must_refuse and (not self.gold or not self.key_facts):
            raise ValueError("Answerable questions require evidence and key facts")
        if any(not variants or any(not v.strip() for v in variants) for variants in self.key_facts):
            raise ValueError("Empty key fact variant")
        return self


def validate_questions(rows, manifest=None, full=False):
    questions = [Question.model_validate(r) for r in rows]
    if len({q.id for q in questions}) != len(questions):
        raise ValueError("Duplicate question IDs")
    if not questions:
        raise ValueError("Question set is empty; add verified real-source labels or use the fixture set")
    if manifest is not None and any(g.doc_id not in manifest for q in questions for g in q.gold):
        raise ValueError("Unknown gold document")
    if full:
        counts = Counter((q.category, q.split) for q in questions)
        if any(counts[category, split] != count for category, pair in CATEGORY_COUNTS.items()
               for split, count in zip(("dev", "test"), pair)):
            raise ValueError("Question category/split counts differ from the 120-question protocol")
        if any(q.label_status != "verified" for q in questions):
            raise ValueError("Real benchmark labels require human verification")
    return questions
