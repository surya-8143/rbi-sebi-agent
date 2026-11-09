"""Local Ollama transport; native API gives explicit thinking control."""
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4


def native_messages(messages):
    output, names = [], {}
    for message in messages:
        item = {"role": message["role"], "content": message.get("content") or ""}
        if message.get("tool_calls"):
            calls = []
            for call in message["tool_calls"]:
                fn = call["function"]
                names[call["id"]] = fn["name"]
                args = fn["arguments"]
                calls.append({"type": "function", "function": {"name": fn["name"], "arguments": json.loads(args) if isinstance(args, str) else args}})
            item["tool_calls"] = calls
        if message["role"] == "tool":
            item["tool_name"] = names.get(message.get("tool_call_id"), "unknown")
        output.append(item)
    return output


def wire_message(message):
    result = {"role": "assistant", "content": message.get("content") or ""}
    if message.get("tool_calls"):
        result["tool_calls"] = [{"id": "call_" + uuid4().hex, "type": "function", "function": {
            "name": c["function"]["name"], "arguments": json.dumps(c["function"]["arguments"])}}
            for c in message["tool_calls"]]
    return result


def clean(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()


def structured_content(text):
    """Accept the leading complete JSON object; never mine prose for a payload."""
    value = clean(text)
    if not value.startswith("{"):
        return value, False
    try:
        parsed, end = json.JSONDecoder().raw_decode(value)
    except ValueError:
        return value, False
    return json.dumps(parsed), bool(value[end:].strip())


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
        endpoint = self.config.base_url.rstrip("/") + "/chat/completions"
        if self.config.protocol == "native":
            url = urlsplit(self.config.base_url)
            endpoint = f"{url.scheme}://{url.netloc}/api/chat"
            body = {"model": self.config.model, "messages": native_messages(messages), "stream": False,
                    "think": False, "options": {"temperature": 0, "seed": 7, "num_predict": max_tokens, "num_ctx": 8192}}
            if self.config.model.startswith("qwen3"):
                # Legacy Qwen templates may still open <think> despite think=False.
                for message in reversed(body["messages"]):
                    if message["role"] == "user":
                        message["content"] += "\n/no_think"
                        break
            if tools:
                body["tools"] = tools
            if schema:
                body["format"] = "json"
                body["messages"].insert(0, {"role": "system", "content": "Return a JSON INSTANCE matching this schema, never the schema itself. No prose. " + json.dumps(schema)})
        req = Request(endpoint,
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
        if self.config.protocol == "native":
            message = wire_message(result["message"])
            discarded = False
            if schema:
                message["content"], discarded = structured_content(message["content"])
            return {"message": message, "transport": {"trailing_text_discarded": discarded, "schema_mode": "json_with_local_validation" if schema else None},
                    "tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                    "seconds": time.perf_counter() - started}
        return {"message": result["choices"][0]["message"],
                "tokens": result.get("usage", {}).get("total_tokens", 0),
                "seconds": time.perf_counter() - started}
