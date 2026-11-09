"""Acquire a finite official-source catalog; no recursive crawling or PDF publication."""
import argparse
import csv
import hashlib
import re
import ssl
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

import pymupdf

from src.io import ROOT, write_json

RBI_LIST = "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx"
SEBI_LIST = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&smid=0&ssid=6"
FIELDS = ["doc_id", "issuer", "doc_type", "title", "date_issued", "version_date", "source_url", "pdf_url",
          "filename", "sha256", "pages", "reference_no", "amends", "retrieved_at", "metadata_status", "notes", "source_format"]
MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE = re.compile(rf"\b({MONTH}\s+\d{{1,2}},?\s+20\d{{2}}|\d{{1,2}}\s+{MONTH},?\s+20\d{{2}})\b", re.I)


def parse_date(text):
    match = DATE.search(text)
    if not match:
        return ""
    value = re.sub(r"[,\s]+", " ", match.group()).strip()
    for fmt in ("%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


class Rows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.current, self.anchor = [], None, None
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.current = {"text": [], "links": []}
        if tag == "a":
            self.anchor = {"url": attrs.get("href", "").strip(), "text": []}
        for key in ("src", "href"):
            if ".pdf" in attrs.get(key, "").lower():
                self.assets.append(attrs[key])

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"].append(data)
        if self.anchor is not None:
            self.anchor["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor is not None:
            if self.current is not None:
                self.current["links"].append({"url": self.anchor["url"], "title": " ".join(" ".join(self.anchor["text"]).split())})
            self.anchor = None
        if tag == "tr" and self.current is not None:
            self.current["text"] = " ".join(" ".join(self.current["text"]).split())
            self.rows.append(self.current)
            self.current = None


def official_url(url):
    value = urlparse(url)
    return value.scheme == "https" and not value.username and any(
        value.hostname == d or (value.hostname or "").endswith("." + d) for d in ("rbi.org.in", "sebi.gov.in"))


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not official_url(newurl):
            raise ValueError("Redirect left the official HTTPS source domains")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    if not official_url(url):
        raise ValueError("Only official HTTPS source URLs are permitted")
    if sys.platform == "win32":
        import truststore
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    else:
        context = ssl.create_default_context()
    opener = build_opener(HTTPSHandler(context=context), OfficialRedirect())
    req = Request(url, headers={"User-Agent": "CircularResearch/0.1 (non-commercial local research)"})
    with opener.open(req, timeout=45) as response:
        content = response.read(30_000_001)
    if len(content) > 30_000_000:
        raise ValueError("Source exceeds the 30 MB download limit")
    return content


def discover():
    catalog = []
    for issuer, listing in (("RBI", RBI_LIST), ("SEBI", SEBI_LIST)):
        parser = Rows()
        parser.feed(fetch(listing).decode("utf-8"))
        current_date = ""
        for row in parser.rows:
            found = parse_date(row["text"])
            if found and len(row["text"]) < 40:
                current_date = found
            for link in row["links"]:
                url, title = urljoin(listing, link["url"]), link["title"]
                if issuer == "RBI":
                    if "viewmasdirections.aspx?id=" not in url.lower():
                        continue
                    if not any(t in title for t in ("Commercial Banks", "Internal Ombudsman", "Agency Banks", "Wholly Owned Subsidiaries", "Universal Banks")):
                        continue
                    if "2027" in title or not any(year in title for year in ("2023", "2025", "2026")):
                        continue
                    ident = parse_qs(urlparse(url).query).get("id", [""])[0]
                    pdfs = [urljoin(listing, link["url"]) for link in row["links"] if ".pdf" in link["url"].lower()]
                    pdf = pdfs[0] if pdfs else ""
                else:
                    if "/legal/master-circulars/" not in url:
                        continue
                    ident = re.search(r"_(\d+)\.html", url).group(1)
                    pdf = ""
                version = parse_date(title[title.lower().find("updated as on"):]) if "updated as on" in title.lower() else ""
                catalog.append({"doc_id": f"{issuer.lower()}_md_{ident}", "issuer": issuer,
                                "doc_type": "master_direction" if issuer == "RBI" else "master_circular",
                                "title": title, "date_issued": current_date if issuer == "RBI" else found,
                                "version_date": version, "source_url": url, "pdf_url": pdf})
    catalog.extend([
        {"doc_id": "sebi_mc_ra_2024", "issuer": "SEBI", "doc_type": "master_circular", "title": "Master Circular for Research Analysts", "date_issued": "2024-05-21", "version_date": "2024-05-21", "source_url": "https://www.sebi.gov.in/sebi_data/attachdocs/may-2024/1716290553655.pdf", "pdf_url": "https://www.sebi.gov.in/sebi_data/attachdocs/may-2024/1716290553655.pdf"},
        {"doc_id": "sebi_mc_dt_2024", "issuer": "SEBI", "doc_type": "master_circular", "title": "Master Circular for Debenture Trustees", "date_issued": "2024-05-16", "version_date": "2024-05-16", "source_url": "https://www.sebi.gov.in/sebi_data/attachdocs/may-2024/1715922862264.pdf", "pdf_url": "https://www.sebi.gov.in/sebi_data/attachdocs/may-2024/1715922862264.pdf"},
        {"doc_id": "sebi_mc_ia_2024", "issuer": "SEBI", "doc_type": "master_circular", "title": "Master Circular for Investment Advisers", "date_issued": "2024-05-21", "version_date": "2024-05-21", "source_url": "https://www.sebi.gov.in/legal/master-circulars/may-2024/master-circular-for-investment-advisers_83488.html", "pdf_url": ""},
    ])
    unique = {item["doc_id"]: item for item in catalog}
    write_csv(ROOT / "data/source_catalog.csv", list(unique.values()))
    return list(unique.values())


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def cover_metadata(text, source):
    """Read the circular's own cover, never a cited reference in the body."""
    cover = text[:500].split("\nTo")[0]
    reference = re.search(r"(?:SEBI/|HO/|RBI/)[A-Za-z0-9/()_-]+", cover)
    issued = re.search(r"Issued on:\s*([^\n]+)", cover, re.I)
    updated = re.search(r"Last updated on:\s*([^\n]+)", cover, re.I)
    return {
        "reference_no": reference.group() if reference else "",
        "date_issued": parse_date(issued.group(1)) if issued else source["date_issued"],
        "version_date": parse_date(updated.group(1)) if updated else source.get("version_date") or source["date_issued"],
    }


def refresh_metadata():
    path = ROOT / "data/manifest.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    for row in rows:
        if row.get("source_format", "pdf") == "pdf":
            with pymupdf.open(ROOT / "data/raw" / row["filename"]) as pdf:
                row.update(cover_metadata(pdf[0].get_text(), row))
    write_csv(path, rows, FIELDS)


def restore_manifest():
    """Rebuild the exact recorded corpus; fail on changed upstream snapshots."""
    raw = (ROOT / "data/raw").resolve()
    raw.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader((ROOT / "data/manifest.csv").open(encoding="utf-8")))
    failures = []
    for row in rows:
        try:
            path = (raw / row["filename"]).resolve()
            if not path.is_relative_to(raw):
                raise ValueError("Manifest path escapes data/raw")
            content = path.read_bytes() if path.exists() else fetch(row["source_url"] if row["source_format"] == "html" else row["pdf_url"])
            if hashlib.sha256(content).hexdigest() != row["sha256"]:
                raise ValueError("Snapshot hash differs; do not silently replace benchmark sources")
            if not path.exists():
                path.write_bytes(content)
            print(f"VERIFIED {row['doc_id']}", flush=True)
        except Exception as exc:
            failures.append({"doc_id": row["doc_id"], "reason": str(exc)})
            print(f"FAILED {row['doc_id']}: {exc}", flush=True)
    if failures:
        raise ValueError(f"{len(failures)} sources could not be restored exactly")


def acquire(catalog, min_pages=5, max_pages=150):
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    existing = ROOT / "data/manifest.csv"
    manifest = list(csv.DictReader(existing.open(encoding="utf-8"))) if existing.exists() else []
    excluded = []
    for source in catalog:
        try:
            pdf_url = source["pdf_url"]
            if not pdf_url:
                parser = Rows()
                parser.feed(fetch(source["source_url"]).decode("utf-8"))
                options = []
                for asset in parser.assets:
                    asset = urljoin(source["source_url"], asset)
                    candidate = parse_qs(urlparse(asset).query).get("file", [asset])[0]
                    candidate = urljoin(source["source_url"], candidate)
                    if official_url(candidate) and candidate.lower().endswith(".pdf"):
                        options.append(candidate)
                if not options:
                    raise ValueError("No linked official PDF found")
                pdf_url = options[0]
            path = raw / (source["doc_id"] + ".pdf")
            content = path.read_bytes() if path.exists() else fetch(pdf_url)
            if not content.startswith(b"%PDF-"):
                raise ValueError("Response is not a PDF")
            with pymupdf.open(stream=content, filetype="pdf") as pdf:
                pages = len(pdf)
                cover = " ".join(pdf[i].get_text() for i in range(min(2, pages)))
                sample = [len(pdf[i].get_text().strip()) for i in {0, pages // 2, pages - 1}]
            if not min_pages <= pages <= max_pages:
                raise ValueError(f"Outside page range: {pages}")
            if max(sample) < 300:
                raise ValueError("Insufficient selectable text")
            if not path.exists():
                path.write_bytes(content)
            issue = source["date_issued"] or parse_date(cover[:2500])
            if not issue:
                raise ValueError("Issue date needs manual metadata review")
            row = dict.fromkeys(FIELDS, "") | source | {"pdf_url": pdf_url, "date_issued": issue,
                "version_date": source.get("version_date") or issue, "filename": path.name,
                "sha256": hashlib.sha256(content).hexdigest(), "pages": str(pages),
                "retrieved_at": datetime.now(timezone.utc).isoformat(), "metadata_status": "draft", "source_format": "pdf",
                "notes": "Official PDF, local research copy. Metadata and applicability require review; not a claim of current law."}
            row.update(cover_metadata(cover, row))
            manifest = [r for r in manifest if r["doc_id"] != row["doc_id"]] + [row]
            print(f"OK {row['doc_id']} {pages} pages", flush=True)
        except Exception as exc:
            excluded.append({"doc_id": source["doc_id"], "source_url": source["source_url"], "reason": str(exc)})
            print(f"SKIP {source['doc_id']}: {exc}", flush=True)
        if manifest:
            write_csv(ROOT / "data/manifest.csv", manifest, FIELDS)
        write_json(ROOT / "data/collection_report.json", {"accepted": len(manifest), "excluded": excluded})
        time.sleep(.4)
    return manifest


def acquire_html(catalog, limit=55):
    from src.retrieval.html import parse_html
    existing = ROOT / "data/manifest.csv"
    manifest = list(csv.DictReader(existing.open(encoding="utf-8"))) if existing.exists() else []
    manifest = [{**dict.fromkeys(FIELDS, ""), **row, "source_format": row.get("source_format") or "pdf"} for row in manifest]
    failures = []
    for source in [s for s in catalog if s["issuer"] == "RBI"][:limit]:
        if any(r["doc_id"] == source["doc_id"] and r["source_format"] == "html" for r in manifest):
            continue
        path = ROOT / "data/raw" / (source["doc_id"] + ".html")
        try:
            if not path.exists():
                path.write_bytes(fetch(source["source_url"]))
            text = parse_html(path)[0]["text"]
            if len(text) > 450_000:
                raise ValueError("HTML source exceeds corpus size limit")
            ref = re.search(r"RBI/[A-Z0-9/-]+", text)
            row = dict.fromkeys(FIELDS, "") | source | {
                "source_format": "html", "filename": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "pages": "0", "reference_no": ref.group() if ref else "", "metadata_status": "draft",
                "version_date": source.get("version_date") or source["date_issued"],
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "notes": "Official HTML fallback: PDF host returned a browser challenge. Cite section and exact quote, not PDF page. Metadata/applicability need review."}
            manifest = [r for r in manifest if r["doc_id"] != row["doc_id"]] + [row]
            write_csv(existing, manifest, FIELDS)
            print(f"HTML {row['doc_id']} {len(text)} characters", flush=True)
        except Exception as exc:
            failures.append({"doc_id": source["doc_id"], "reason": str(exc)})
            print(f"SKIP HTML {source['doc_id']}: {exc}", flush=True)
        time.sleep(.4)
    report_path = ROOT / "data/collection_report.json"
    import json
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    pdf_failures = report.get("pdf_attempt_failures", report.get("excluded", []))
    accepted_ids = {r["doc_id"] for r in manifest}
    report.update(pdf_attempt_failures=pdf_failures, excluded=[r for r in pdf_failures if r["doc_id"] not in accepted_ids])
    report.update(accepted=len(manifest), formats={kind: sum(r["source_format"] == kind for r in manifest) for kind in ("pdf", "html")}, html_failures=failures)
    write_json(report_path, report)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--html-fallback", action="store_true")
    parser.add_argument("--refresh-metadata", action="store_true")
    parser.add_argument("--restore", action="store_true", help="Restore exact manifest snapshots with SHA-256 checks")
    args = parser.parse_args()
    if args.discover:
        catalog = discover()
        print(f"Catalogued {len(catalog)} candidate documents")
    else:
        catalog = list(csv.DictReader((ROOT / "data/source_catalog.csv").open(encoding="utf-8")))
    if args.download:
        accepted = acquire(catalog)
        print(f"Accepted {len(accepted)} documents")
    if args.html_fallback:
        print(f"Total local sources: {len(acquire_html(catalog))}")
    if args.refresh_metadata:
        refresh_metadata()
    if args.restore:
        restore_manifest()
