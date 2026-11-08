"""One-command fixture setup. Full mode additionally installs semantic retrieval."""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--full", action="store_true")
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    env = root / ".venv"
    if not env.exists():
        subprocess.run([sys.executable, "-m", "venv", str(env)], check=True)
    python = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    def run(*args):
        subprocess.run([str(python), *args], cwd=root, check=True)
    run("-m", "pip", "install", "-r", "requirements-ci.txt")
    if a.full:
        run("-m", "pip", "install", "-r", "requirements-retrieval.txt")
    run("-m", "scripts.create_fixtures")
    run("-m", "scripts.create_attacks")
    run("-m", "src.retrieval.index", "--chunks", "tests/fixtures/chunks.jsonl", *(["--dense"] if a.full else []))
    run("-m", "src.retrieval.index", "--chunks", "tests/fixtures/attack_chunks.jsonl", "--out", "index_attack")
    run("-m", "pytest", "-q")
    run("-m", "evals.retrieval_eval", "--questions", "tests/fixtures/questions.jsonl", "--fixture", "--out", "results/fixture_retrieval.json")
    run("-m", "scripts.build_dashboard")
    print("Ready. Open docs/index.html. For model answers: ollama pull qwen3:4b, then use python -m src.cli.")


if __name__ == "__main__":
    main()
