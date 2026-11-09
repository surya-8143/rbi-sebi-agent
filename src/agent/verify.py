import re
from copy import deepcopy

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    chunk_id: str = Field(min_length=1, max_length=100)
    quote: str = Field(min_length=1, max_length=250, pattern=r"^[^ ]+( [^ ]+){0,11}$")


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


def split_exact_quotes(answer, seen):
    """Losslessly split an exact long quote; never salvage a fabricated quotation."""
    result = deepcopy(answer)
    splits = 0
    if not isinstance(result, dict) or not isinstance(result.get("claims"), list):
        return result, splits
    for claim in result["claims"]:
        if not isinstance(claim, dict) or not isinstance(claim.get("citations"), list):
            continue
        citations = []
        for citation in claim["citations"]:
            if not isinstance(citation, dict) or not isinstance(citation.get("quote"), str):
                citations.append(citation)
                continue
            quote = normalized(citation["quote"])
            source = seen.get(citation.get("chunk_id"))
            words = quote.split()
            if len(words) > 12 and source and quote in normalized(source["text"]):
                citations.extend(citation | {"quote": " ".join(words[i:i+12])} for i in range(0, len(words), 12))
                splits += 1
            else:
                citations.append(citation)
        claim["citations"] = citations
    return result, splits


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
