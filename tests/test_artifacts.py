import json

import pytest

from scripts.check_results import check
from src.io import ROOT


def test_notebooks_have_valid_python_and_no_saved_outputs():
    for path in (ROOT / "notebooks").glob("*.ipynb"):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        assert notebook["nbformat"] == 4
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), str(path), "exec")
                assert cell["outputs"] == []


def test_results_gate_rejects_different_corpus():
    base = {"meta": {"dataset_hash": "a", "corpus_hash": "b", "split": "test", "fixture": True}}
    new = {"meta": base["meta"] | {"corpus_hash": "c"}}
    with pytest.raises(ValueError, match="corpus_hash"):
        check(new, base)
