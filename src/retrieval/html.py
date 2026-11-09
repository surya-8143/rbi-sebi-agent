"""Read RBI's published HTML body with section locators, never synthetic PDF pages."""
import re
from html.parser import HTMLParser
from pathlib import Path


class OfficialBody(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts = []
        self.complete = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            if self.depth:
                self.depth += 1
            elif not self.complete and "tablecontent2" in attrs.get("class", "").split():
                self.depth = 1
        if self.depth and tag in {"p", "br", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.depth and tag in {"p", "li", "tr"}:
            self.parts.append("\n")
        if self.depth and tag == "tr":
            self.depth -= 1
            if not self.depth:
                self.complete = True

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)


def parse_html(path):
    parser = OfficialBody()
    parser.feed(Path(path).read_text(encoding="utf-8"))
    text = "\n".join(re.sub(r"[ \t\r\xa0]+", " ", line).strip() for line in "".join(parser.parts).splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not parser.complete or len(text) < 300:
        raise ValueError("Official HTML body missing or incomplete")
    return [{"page": None, "text": text}]
