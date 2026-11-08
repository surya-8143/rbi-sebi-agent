"""Run local checks and write an evidence-based software validation record."""
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from src.io import ROOT, write_json


def main():
    output = ROOT / "runs/pytest.xml"
    output.parent.mkdir(exist_ok=True)
    subprocess.run([sys.executable, "-m", "ruff", "check", "."], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "pytest", "-q", f"--junitxml={output}"], cwd=ROOT, check=True)
    suite = ET.parse(output).getroot().find("testsuite")
    total = int(suite.attrib["tests"])
    failed = int(suite.attrib["failures"]) + int(suite.attrib["errors"])
    skipped = int(suite.attrib["skipped"])
    write_json(ROOT / "results/software_validation.json", {"kind": "validation", "date": datetime.now(timezone.utc).isoformat(),
               "environment": f"{platform.system()} / Python {platform.python_version()}",
               "summary": f"{total - failed - skipped} software checks passed; {failed} failed; {skipped} skipped. Ruff passed.",
               "tests": total, "failed": failed, "skipped": skipped,
               "scope": "Offline software tests; scripted model control flow, not LLM accuracy"})


if __name__ == "__main__":
    main()
