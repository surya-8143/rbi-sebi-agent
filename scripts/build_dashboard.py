"""Build a standalone dashboard from measured result files, with honest empty states."""
import html
import json
from pathlib import Path

from src.io import ROOT


def build(results=None, out=None):
    results, out = Path(results or ROOT / "results"), Path(out or ROOT / "docs/index.html")
    runs = []
    for path in sorted(results.glob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if item.get("kind") in {"evaluation", "retrieval", "redteam", "validation", "corpus"}:
            runs.append({"file": path.name, **item})
    data = json.dumps(runs, ensure_ascii=False).replace("<", "\\u003c")
    template = (ROOT / "docs/dashboard.template.html").read_text(encoding="utf-8")
    page = template.replace("__RESULT_DATA__", data)
    out.parent.mkdir(parents=True, exist_ok=True)
    for name in ("eval_protocol", "redteam_report", "data_report", "writeup", "status"):
        path = ROOT / "docs" / (name + ".md")
        if path.exists():
            report = "<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Project report</title><style>body{max-width:900px;margin:60px auto;padding:24px;background:#f5f7fa;color:#17243a;font:17px/1.7 system-ui}pre{white-space:pre-wrap;font:inherit}a{color:#155b7d}</style><a href='index.html'>Back to dashboard</a><pre>" + html.escape(path.read_text(encoding="utf-8")) + "</pre>"
            (out.parent / (name + ".html")).write_text(report, encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"Built {out} from {len(runs)} recorded runs")


if __name__ == "__main__":
    build()
