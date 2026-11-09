import json

import pytest

from evals.schema import Evidence
from evals.score import is_hit
from scripts.collect_sources import OfficialRedirect, Rows, cover_metadata, official_url, parse_date
from src.agent.tools import ToolSet
from src.retrieval.chunk import chunk_doc
from src.retrieval.html import parse_html
from src.retrieval.search import Searcher


def test_official_html_body_and_page_provenance(tmp_path, chunks):
    path = tmp_path / "official.html"
    path.write_text('<nav>Outside navigation</nav><table><tr class="tablecontent2"><td><p>1. ' + 'A source obligation must remain intact. ' * 15 + '</p><table><tr><td>Nested evidence</td></tr></table><p>2. Second section</p></td></tr></table><footer>Unrelated footer</footer>', encoding="utf-8")
    pages = parse_html(path)
    assert pages[0]["page"] is None
    assert "Nested evidence" in pages[0]["text"]
    assert "Outside navigation" not in pages[0]["text"]
    assert "Unrelated footer" not in pages[0]["text"]
    result = chunk_doc(chunks[0] | {"source_format": "html"}, pages)
    assert all(c["page"] is None for c in result)
    assert result[-1]["section_path"] == "2"


def test_html_gold_needs_explicit_section():
    with pytest.raises(ValueError):
        Evidence(doc_id="rbi", pages=[], evidence="a quote")
    gold = Evidence(doc_id="rbi", pages=[], section_path="3", evidence="a quote").model_dump()
    chunk = {"doc_id": "rbi", "page": None, "section_path": "3", "text": "a quote"}
    assert is_hit(chunk, gold)
    assert not is_hit(chunk | {"page": 1}, gold)
    assert not is_hit(chunk | {"section_path": "4"}, gold)


def test_revision_date_filters_prevent_future_snapshot(searcher):
    c = searcher.chunks[1] | {"date_issued": "2025-01-01", "version_date": "2026-10-01"}
    revised = Searcher(chunks=[c, searcher.chunks[4]])
    assert all(item["chunk_id"] != c["chunk_id"] for item, _ in revised.search("deposit notice", as_of="2026-01-01"))


@pytest.mark.parametrize("url", ["https://evil-rbi.org.in/a.pdf", "http://rbi.org.in/x", "https://rbi.org.in.evil.test/x", "https://user@rbi.org.in/x"])
def test_downloader_rejects_untrusted_hosts(url):
    assert not official_url(url)


def test_official_hosts_and_unquoted_links():
    assert official_url("https://rbidocs.rbi.org.in/rdocs/x.pdf")
    p = Rows()
    p.feed('<tr><td><a href=BS_ViewMasDirections.aspx?id=123>Document</a></td></tr>')
    assert p.rows[0]["links"][0]["url"] == "BS_ViewMasDirections.aspx?id=123"
    assert parse_date("Updated as on October 01, 2026") == "2026-10-01"
    assert parse_date("28 November 2025") == "2025-11-28"


def test_redirect_stays_official():
    with pytest.raises(ValueError, match="official"):
        OfficialRedirect().redirect_request(None, None, 302, "", {}, "https://example.com/file")


def test_unicode_tool_response_is_bounded(searcher):
    chunk = searcher.chunks[1] | {"text": "Circular " + "अ" * 2800}
    tools = ToolSet(Searcher(chunks=[chunk]))
    result = tools._passages([(chunk, .5)] * 8)
    assert len(json.dumps(result)) <= 6000


def test_index_without_supported_tokens_fails_clearly(chunks):
    with pytest.raises(ValueError, match="no searchable"):
        Searcher(chunks=[chunks[0] | {"text": "अ" * 100}])


def test_cover_metadata_uses_cover_not_referenced_circular():
    text = "MASTER CIRCULAR\nHO/49/14/15(3)2026-CFD-POD1/I/16178/2026\nIssued on: September 26, 2023\nLast updated on: July 14, 2026\nTo\nSEBI/old/2017"
    result = cover_metadata(text, {"date_issued": "2026-07-14"})
    assert result["reference_no"] == "HO/49/14/15(3)2026-CFD-POD1/I/16178/2026"
    assert result["date_issued"] == "2023-09-26"
    assert result["version_date"] == "2026-07-14"


def test_unreviewed_snapshot_is_not_historical_evidence(chunks):
    from src.retrieval.search import available_as_of
    c = chunks[0] | {"metadata_status": "draft", "retrieved_at": "2026-11-08T10:00:00Z", "version_date": "2025-01-01"}
    assert available_as_of(c) == "2026-11-08"


def test_heading_attaches_to_provision_and_year_is_not_section(chunks):
    pages = [{"page": 1, "text": "Chapter II Records\n3. The circular dated August 13,\n2025 shall stand rescinded.\n4. Retain records."}]
    result = chunk_doc(chunks[0], pages)
    assert len(result) == 2
    assert result[0]["section_path"] == "3"
    assert "Chapter II Records" in result[0]["body"]
    assert "2025 shall stand rescinded" in result[0]["body"]


def test_large_document_listing_is_bounded(chunks):
    many = [chunks[0] | {"doc_id": f"doc_{i}", "title": "अ" * 200} for i in range(30)]
    result, _ = ToolSet(Searcher(chunks=many)).run("list_documents", "{}")
    assert result and len(json.dumps(result)) <= 6000
