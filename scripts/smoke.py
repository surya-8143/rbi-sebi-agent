from src.agent.config import Config
from src.agent.llm import OllamaChat

if __name__ == "__main__":
    config = Config.from_env()
    result = OllamaChat(config)([{"role": "user", "content": "In one sentence, what does a master circular do?"}])
    print(config.model, result["message"]["content"], result["seconds"], "seconds")
