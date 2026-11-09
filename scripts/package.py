"""Package distributable source, excluding models, real source text, secrets, and traces."""
from zipfile import ZIP_DEFLATED, ZipFile

from src.io import ROOT


def main():
    folders = ("src", "evals", "redteam", "scripts", "tests", "docs", "prompts", "notebooks", "models", ".github")
    filenames = ("README.md", "LICENSE", "pyproject.toml", "requirements.txt", "requirements-ci.txt",
                 "requirements-retrieval.txt", "requirements-lock.txt", ".gitignore", ".env.example", "data/manifest.csv",
                 "data/source_catalog.csv", "data/collection_report.json", "data/relationships.json")
    output = ROOT / "dist/rbi-sebi-agent.zip"
    output.parent.mkdir(exist_ok=True)
    paths = [ROOT / name for name in filenames]
    for folder in folders:
        paths.extend((ROOT / folder).rglob("*"))
    paths.extend((ROOT / "results").glob("*.json"))
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in paths:
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                archive.write(path, path.relative_to(ROOT))
    print(output)


if __name__ == "__main__":
    main()
