"""Read text PDFs; remove recurring margin lines, never recurring body provisions."""
import re
from collections import Counter

import pymupdf

PAGE_NO = re.compile(r"(?:page\s*)?\d+(?:\s*of\s*\d+)?", re.I)


def parse_pdf(path):
    pages, margins = [], Counter()
    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise ValueError("Encrypted PDFs are not supported")
        for number, page in enumerate(doc, 1):
            lines = []
            for block in page.get_text("dict", sort=True)["blocks"]:
                for line in block.get("lines", []):
                    text = "".join(s["text"] for s in line["spans"]).strip()
                    if text:
                        margin = line["bbox"][1] < page.rect.height * .08 or line["bbox"][3] > page.rect.height * .92
                        lines.append((text, margin))
            margins.update({text for text, margin in lines if margin})
            pages.append({"page": number, "lines": lines})
    for page in pages:
        text = "\n".join(t for t, m in page.pop("lines")
                         if not (m and (PAGE_NO.fullmatch(t) or margins[t] >= max(3, len(pages) * .3))))
        text = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", text)
        page["text"] = re.sub(r"[ \t]+", " ", text).strip()
    if not any(len(p["text"]) >= 80 for p in pages):
        raise ValueError("No usable text found; scanned PDFs require OCR, which is outside this project")
    return pages
