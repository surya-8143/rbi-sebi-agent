import math
import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Config:
    model: str = "qwen3:4b"
    base_url: str = "http://127.0.0.1:11434/v1"
    timeout: float = 120
    max_steps: int = 5
    max_tool_calls: int = 12
    defense: int = 5
    tau: float | None = None
    fixture: bool = False
    redteam: bool = False

    def __post_init__(self):
        url = urlparse(self.base_url)
        if url.hostname not in {"localhost", "127.0.0.1", "::1"} or url.scheme != "http":
            raise ValueError("This project uses a local Ollama endpoint only")
        if not 0 <= self.defense <= 5 or not 1 <= self.max_steps <= 5:
            raise ValueError("Invalid defense level or step budget")
        if not 1 <= self.max_tool_calls <= 12 or not 1 <= self.timeout <= 600:
            raise ValueError("Tool budget or request timeout is outside permitted limits")
        if self.tau is not None and not math.isfinite(self.tau):
            raise ValueError("Retrieval threshold must be finite")

    @classmethod
    def from_env(cls, **overrides):
        values = {"model": os.getenv("LLM_MODEL", "qwen3:4b"),
                  "base_url": os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
                  "timeout": float(os.getenv("LLM_TIMEOUT", "120"))}
        if os.getenv("RETRIEVAL_TAU"):
            values["tau"] = float(os.environ["RETRIEVAL_TAU"])
        return cls(**(values | overrides))
