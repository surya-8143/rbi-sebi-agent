"""Ollama's local OpenAI-compatible wire format, without API credentials."""
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def clean(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()


class OllamaChat:
    def __init__(self, config):
        self.config = config

    def __call__(self, messages, tools=None, schema=None, max_tokens=900):
        body = {"model": self.config.model, "messages": messages, "temperature": 0,
                "seed": 7, "max_tokens": max_tokens, "stream": False, "reasoning_effort": "none"}
        if tools:
            body["tools"] = tools
        if schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "schema": schema}}
        req = Request(self.config.base_url.rstrip("/") + "/chat/completions",
                      data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        started = time.perf_counter()
        try:
            with urlopen(req, timeout=self.config.timeout) as response:
                result = json.loads(response.read(2_000_000))
        except HTTPError as exc:
            detail = exc.read(500).decode("utf-8", errors="replace")
            raise RuntimeError(f"Local Ollama HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"Local model unavailable ({type(exc).__name__}); start Ollama and pull {self.config.model}") from exc
        return {"message": result["choices"][0]["message"],
                "tokens": result.get("usage", {}).get("total_tokens", 0),
                "seconds": time.perf_counter() - started}
