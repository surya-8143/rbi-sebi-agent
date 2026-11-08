import ast
import json
import math
import operator
import re
import time
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.agent.guard import quarantine

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Mod: operator.mod}


def calculate(expression):
    def evaluate(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = evaluate(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
            value = OPS[type(node.op)](evaluate(node.left), evaluate(node.right))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            if node.func.id == "days_between" and len(node.args) == 2:
                if not all(isinstance(a, ast.Constant) and isinstance(a.value, str) and len(a.value) == 10 for a in node.args):
                    raise ValueError("ISO dates required")
                value = (date.fromisoformat(node.args[1].value) - date.fromisoformat(node.args[0].value)).days
            else:
                funcs = {"round": round, "min": min, "max": max, "abs": abs}
                if node.func.id not in funcs or not 1 <= len(node.args) <= 8:
                    raise ValueError("Function not permitted")
                args = [evaluate(a) for a in node.args]
                if node.func.id == "round" and len(args) == 2 and (type(args[1]) is not int or abs(args[1]) > 12):
                    raise ValueError("Precision out of bounds")
                value = funcs[node.func.id](*args)
        else:
            raise ValueError("Operation not permitted")
        if not math.isfinite(value) or abs(value) > 1e15:
            raise ValueError("Result out of bounds")
        return value

    try:
        if not isinstance(expression, str) or len(expression) > 200:
            raise ValueError("Expression too long")
        tree = ast.parse(expression, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 80:
            raise ValueError("Expression too complex")
        return {"result": evaluate(tree.body)}
    except (ValueError, SyntaxError, TypeError, ZeroDivisionError, OverflowError, RecursionError):
        return {"error": "Expression is invalid or outside the calculator limits"}


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchArgs(Args):
    query: str = Field(min_length=1, max_length=300)
    issuer: str | None = Field(default=None, pattern=r"^(RBI|SEBI|FRA)$")
    top_k: int = Field(default=5, ge=1, le=8)


class SectionArgs(Args):
    doc_id: str = Field(pattern=r"^[a-z0-9_]{3,80}$")
    section: str = Field(pattern=r"^[0-9A-Za-z .()-]{1,70}$")


class ListArgs(Args):
    issuer: str | None = Field(default=None, pattern=r"^(RBI|SEBI|FRA)$")
    keyword: str | None = Field(default=None, max_length=100)


class CalculateArgs(Args):
    expression: str = Field(min_length=1, max_length=200)


SCHEMAS = {"search_circulars": SearchArgs, "get_section": SectionArgs,
           "list_documents": ListArgs, "calculate": CalculateArgs}
DESCRIPTIONS = {"search_circulars": "Search loaded circular passages for evidence. Only loaded sources are available.",
                "get_section": "Read a numbered section from a known document ID.",
                "list_documents": "List available documents and dates, optionally filtered.",
                "calculate": "Bounded arithmetic and days_between(ISO date, ISO date). No code execution."}
TOOLS = [{"type": "function", "function": {"name": name, "description": DESCRIPTIONS[name],
          "parameters": schema.model_json_schema()}} for name, schema in SCHEMAS.items()]


class ToolSet:
    def __init__(self, searcher, defense=5):
        self.searcher, self.defense = searcher, defense
        self.manifest = {c["doc_id"]: {k: c.get(k, "") for k in
                         ("doc_id", "title", "issuer", "date_issued", "reference_no", "source_url")}
                         for c in searcher.chunks}

    def _passages(self, chunks):
        output = []
        for chunk, score in chunks:
            text = chunk["text"][:2800]
            removed = 0
            if self.defense >= 3:
                text, removed = quarantine(text)
            item = {**{k: chunk[k] for k in ("chunk_id", "doc_id", "title", "issuer", "date_issued", "page", "section_path")},
                    "score": score, "quarantined_sentences": removed}
            room = 5800 - len(json.dumps(output)) - len(json.dumps(item))
            if room < 100:
                break
            item["text"] = text[:room]
            output.append(item)
        return output

    def run(self, name, arguments):
        started = time.perf_counter()
        try:
            if name not in SCHEMAS or not isinstance(arguments, str) or len(arguments) > 2000:
                raise ValueError("Unknown tool or oversized arguments")
            args = SCHEMAS[name].model_validate_json(arguments)
            if name == "calculate":
                result = calculate(args.expression)
            elif name == "search_circulars":
                result = self._passages(self.searcher.search(args.query, k=args.top_k, issuer=args.issuer))
            elif name == "get_section":
                if args.doc_id not in self.manifest:
                    raise ValueError("Unknown document ID")
                hits = [c for c in self.searcher.chunks if c["doc_id"] == args.doc_id and
                        (c["section_path"] == args.section or c["section_path"].startswith(args.section + "."))]
                result = self._passages([(c, None) for c in hits[:4]])
            else:
                result = [m for m in self.manifest.values() if
                          (not args.issuer or m["issuer"] == args.issuer) and
                          (not args.keyword or args.keyword.lower() in m["title"].lower())][:20]
        except (ValidationError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            result = {"error": "Unknown tool, document, or invalid arguments"}
        return result, time.perf_counter() - started


def display_result(result, defense):
    if defense < 1 or not isinstance(result, list):
        return result
    return [{**r, "text": "<document>\n" + re.sub(r"</?document[^>]*>", "", r["text"], flags=re.I) + "\n</document>"}
            if "text" in r else r for r in result]
