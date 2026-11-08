"""Generate self-contained notebooks using an uploaded source archive."""
import json

from src.io import ROOT


def md(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source):
    return {"cell_type": "code", "metadata": {}, "source": source.splitlines(keepends=True), "outputs": [], "execution_count": None}


SETUP = [
    md("# Circular research agent in Colab\nRun the model and agent in this notebook's own runtime. No tunnels or web UI. Select a GPU runtime if available. The default documents are fictional and must not be used as regulatory guidance. Model downloads and inference use your runtime quota.\n"),
    code("import sys, subprocess\nprint(sys.version)\nassert (3, 11) <= sys.version_info[:2] < (3, 14), 'Use Python 3.11–3.13'\nsubprocess.run(['nvidia-smi'], check=False)\n"),
    md("## Upload the source ZIP\nUse the rbi-sebi-agent.zip produced by scripts/package.py. The notebook extracts it under /content/rbi-sebi-agent.\n"),
    code("from google.colab import files\nfrom pathlib import Path\nimport zipfile, io, os\nuploaded = files.upload()\narchive = next((name for name in uploaded if name.endswith('.zip')), None)\nassert archive, 'Upload the project ZIP'\nroot = Path('/content/rbi-sebi-agent').resolve()\nroot.mkdir(exist_ok=True)\nwith zipfile.ZipFile(io.BytesIO(uploaded[archive])) as z:\n    assert all((root / name).resolve().is_relative_to(root) for name in z.namelist()), 'Unsafe archive path'\n    z.extractall(root)\nos.chdir(root)\nsubprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements-ci.txt'], check=True)\n"),
    code("subprocess.run(['sudo', 'apt-get', 'update', '-qq'], check=True)\nsubprocess.run(['sudo', 'apt-get', 'install', '-y', 'pciutils', 'zstd'], check=True)\nsubprocess.run(['curl', '-fsSL', 'https://ollama.com/install.sh', '-o', '/content/install-ollama.sh'], check=True)\nsubprocess.run(['sh', '/content/install-ollama.sh'], check=True)\n"),
    code("import urllib.request, time\nos.environ['OLLAMA_HOST'] = '127.0.0.1:11434'\nlog = open('/content/ollama.log', 'w')\nserver = subprocess.Popen(['ollama', 'serve'], stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy())\nfor attempt in range(60):\n    try:\n        urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=2).close()\n        break\n    except OSError:\n        time.sleep(1)\nelse:\n    raise RuntimeError('Ollama did not start; inspect /content/ollama.log')\nos.environ['LLM_MODEL'] = 'qwen3:8b'\nos.environ['LLM_TIMEOUT'] = '180'\nsubprocess.run(['ollama', 'pull', os.environ['LLM_MODEL']], check=True)\nsubprocess.run([sys.executable, '-m', 'scripts.smoke'], check=True)\nsubprocess.run(['ollama', 'ps'], check=True)\n"),
    code("subprocess.run([sys.executable, '-m', 'src.retrieval.index', '--chunks', 'tests/fixtures/chunks.jsonl'], check=True)\nsubprocess.run([sys.executable, '-m', 'src.retrieval.index', '--chunks', 'tests/fixtures/attack_chunks.jsonl', '--out', 'index_attack'], check=True)\n"),
]


def main():
    evaluation = [md("# Resumable evaluation\nRun the setup cells above first. This example measures fictional dev questions, not official regulatory accuracy. Upload official PDFs and a verified manifest/question set before official evaluation.\n"),
                  code("subprocess.run([sys.executable, '-m', 'evals.run', '--questions', 'tests/fixtures/questions.jsonl', '--fixture', '--split', 'dev', '--out', 'results/colab_fixture_dev.json'], check=True)\n"),
                  code("# Explicitly run each defense level when ready; these jobs may take a long time.\n# subprocess.run([sys.executable, '-m', 'redteam.run', '--fixture', '--defense', '0', '--out', 'results/colab_redteam_d0.json'], check=True)\n# subprocess.run([sys.executable, '-m', 'redteam.run', '--fixture', '--defense', '5', '--out', 'results/colab_redteam_d5.json'], check=True)\n"),
                  code("import shutil\nshutil.make_archive('/content/results-and-traces', 'zip', '.', 'results')\nfiles.download('/content/results-and-traces.zip')\n# Also preserve raw traces before ending the runtime.\nshutil.make_archive('/content/traces', 'zip', '.', 'runs')\nfiles.download('/content/traces.zip')\n")]
    demo = [md("# Ask the fictional corpus\nInspect the status, source dates, exact quotes, and trace. The attack example uses a separate poisoned index.\n"),
            code("from src.agent.graph import Agent\nfrom src.agent.config import Config\nfrom src.retrieval.search import Searcher\nagent = Agent(Searcher('index'), Config.from_env(fixture=True))\ndef ask(question, chosen=agent):\n    state = chosen.invoke(question)\n    print('STATUS:', state['status'], state.get('reason', ''))\n    print(state['answer']['answer'])\n    for citation in state['answer']['citations']:\n        print(citation)\n    print('Seconds:', round(state['seconds'], 2), 'Tokens:', state['tokens'])\n    return state\n"),
            code("normal = ask('What is the KYC record retention period in the FRA fictional KYC Records circular?')\nrefusal = ask('What does RBI circular 2031/77 require?')\npoisoned = Agent(Searcher('index_attack'), Config.from_env(fixture=True))\nattack = ask('Explain FRA fictional KYC automated review note 1.', poisoned)\nprint('Quarantined sentences:', sum(item.get('quarantined_sentences', 0) for item in attack.get('seen', {}).values()))\n")]
    for name, cells in [("00_colab_setup", SETUP), ("10_run_eval", SETUP + evaluation), ("20_demo", SETUP + demo)]:
        notebook = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "cells": cells}
        for i, cell in enumerate(cells):
            cell["id"] = f"cell-{i:03d}"
        path = ROOT / "notebooks" / (name + ".ipynb")
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(notebook, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
