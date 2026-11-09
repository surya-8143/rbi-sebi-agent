"""Check local runtime/schema compatibility before expensive benchmark runs."""
from src.agent.config import Config
from src.agent.graph import Decision
from src.agent.llm import OllamaChat

if __name__ == "__main__":
    result = OllamaChat(Config.from_env())([
        {"role": "system", "content": "Return only the requested JSON. Quote exactly four words."},
        {"role": "user", "content": 'Use action answer, tool none, arguments empty string. In answer use can_answer true with one claim: The number is seven. Cite chunk_id demo:1 with quote The number is seven.'}],
        schema=Decision.model_json_schema(), max_tokens=220)
    print(result)
    Decision.model_validate_json(result["message"]["content"])
