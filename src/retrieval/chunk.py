"""Page-local, bounded chunks with stable source metadata."""
import re

HEADING = re.compile(r"^(?:chapter|part|annex(?:ure)?|appendix|schedule)\b", re.I)
NUMBERED = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){0,3})(?:[.)])?\s+\S")


def chunk_doc(meta, pages, max_chars=2800, target_chars=1800):
    chunks, section = [], "Preamble"
    for page in pages:
        buf = ""
        heading_only = False

        def emit():
            nonlocal buf, heading_only
            if buf.strip():
                header = f"[{meta['issuer']} | {meta['title'][:160]} | {meta['date_issued']} | {section}]"
                if meta.get("version_date") and meta["version_date"] != meta["date_issued"]:
                    header += f" [revision {meta['version_date']}]"
                chunks.append({**meta, "chunk_id": f"{meta['doc_id']}:{len(chunks):04d}",
                               "page": page["page"], "section_path": section,
                               "body": buf.strip(), "text": header + "\n" + buf.strip()})
            buf = ""
            heading_only = False

        # Reserve enough room for metadata. Even one enormous input line is split.
        limit = max_chars - 300
        if limit < 100:
            raise ValueError("max_chars must be at least 400")
        for line in page["text"].splitlines():
            line = line.strip()
            if not line:
                continue
            numbered = NUMBERED.match(line)
            heading = bool(HEADING.match(line))
            if heading or numbered:
                if not heading_only:
                    emit()
                section = numbered.group(1) if numbered else line[:70]
            heading_only = heading and (not buf or heading_only)
            while line:
                room = limit - len(buf) - 1
                if room < 1:
                    emit()
                    continue
                cut = min(len(line), room)
                if cut < len(line):
                    space = line.rfind(" ", 0, cut)
                    if space > cut // 2:
                        cut = space
                buf += (" " if buf else "") + line[:cut]
                line = line[cut:].lstrip()
                if line or len(buf) >= target_chars:
                    emit()
        emit()
    return chunks
