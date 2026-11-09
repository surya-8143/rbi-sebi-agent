"""Create a separate non-thinking Qwen3 profile; retain the original base model."""
import argparse
import json
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen


def prepare(create=False):
    request = Request("http://127.0.0.1:11434/api/show", data=json.dumps({"model": "qwen3:4b"}).encode(), headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=30) as response:
        info = json.load(response)
    template = info["template"]
    opening = '{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant\n<think>\n'
    if template.count(opening) != 1:
        raise ValueError("Base model template differs; review it before creating the profile")
    template = template.replace(opening, opening + '\n</think>\n\n')
    path = Path("models/Modelfile")
    path.parent.mkdir(exist_ok=True)
    path.write_text('FROM qwen3:4b\nTEMPLATE """' + template + '"""\nPARAMETER temperature 0\nPARAMETER num_ctx 8192\n', encoding="utf-8")
    if create:
        subprocess.run(["ollama", "create", "rbi-sebi-qwen3:4b", "-f", str(path)], check=True)
    return path


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--create", action="store_true")
    print(prepare(p.parse_args().create))
