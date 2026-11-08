import re

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    chunk_id: str = Field(min_length=1, max_length=100)
    quote: str = Field(min_length=1, max_length=250)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1, max_length=1500)
    citations: list[Citation] = Field(min_length=1, max_length=8)


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    can_answer: bool
    claims: list[Claim] = Field(max_length=8)


def normalized(text):
    return re.sub(r"\s+", " ", text).strip()


def verify(answer, seen):
    errors = []
    if answer["can_answer"] and not answer["claims"]:
        errors.append("No supported claims")
    for claim in answer["claims"]:
        if not claim["citations"]:
            errors.append("Claim has no citation")
        for citation in claim["citations"]:
            quote = normalized(citation["quote"])
            source = seen.get(citation["chunk_id"])
            if source is None:
                errors.append("Citation was not retrieved")
            elif not quote or quote not in normalized(source["text"]):
                errors.append("Quote is not an exact source substring")
            if len(quote.split()) > 12:
                errors.append("Quote exceeds 12 words")
    return errors
