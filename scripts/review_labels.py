"""Local review packet and explicit, provenance-checked human review import."""
import argparse
import json
from pathlib import Path

from evals.schema import validate_questions
from src.agent.verify import normalized
from src.io import digest, read_jsonl, write_json, write_jsonl


def packet(questions, chunks):
    validate_questions(questions, {c["doc_id"] for c in chunks})
    items = []
    for q in questions:
        context = []
        for gold in q["gold"]:
            matches = [c for c in chunks if c["doc_id"] == gold["doc_id"]
                       and (c["page"] in gold["pages"] if gold["pages"] else c["page"] is None and c["section_path"] == gold["section_path"])
                       and normalized(gold["evidence"]) in normalized(c["body"])]
            if not matches:
                raise ValueError(f"Missing exact source evidence: {q['id']}")
            c = matches[0]
            context.append({k: c[k] for k in ("doc_id", "title", "date_issued", "version_date", "source_url", "sha256", "page", "section_path", "body")})
        items.append({"question": q, "context": context})
    return {"dataset_hash": digest(questions), "corpus_hash": digest(chunks), "items": items}


def export(questions, chunks, out):
    data = json.dumps(packet(questions, chunks), ensure_ascii=False).replace("<", "\\u003c")
    page = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Official question review</title><style>body{max-width:1000px;margin:40px auto;padding:20px;background:#f4f6f8;color:#183047;font:16px/1.6 system-ui}article{background:white;border:1px solid #ccd6df;border-radius:10px;padding:22px;margin:24px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 system-ui}select,input,button,textarea{padding:10px;font:inherit}textarea{display:block;width:95%;margin-top:12px}summary{cursor:pointer}#save{position:sticky;bottom:12px;background:#0a6469;color:white;border:0;border-radius:6px}small{color:#526575}</style>
<h1>Review official-source question drafts</h1><p>These are AI drafts, not verified labels. Check each question, reference answer, scoring facts, exact quotation and surrounding source. Read the original document where context is incomplete. Accept only after your own review; leave uncertain cases pending or reject them. No decisions are preselected and nothing is sent to a server.</p>
<label>Reviewer name or identifier <input id="reviewer" autocomplete="off"></label><main id="items"></main><button id="save">Download review decisions</button><p id="status" role="status"></p>
<script>const packet=__DATA__;const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
document.getElementById('items').innerHTML=packet.items.map(({question:q,context},i)=>`<article><small>${esc(q.id)} · ${esc(q.category)} · DRAFT</small><h2>${esc(q.question)}</h2><p><b>Reference:</b> ${esc(q.gold_answer)}</p><p><b>Scoring facts:</b> ${esc(JSON.stringify(q.key_facts))}</p>${context.map(c=>`<details><summary>${esc(c.title)} · ${c.page?'PDF page '+c.page:'HTML section '+esc(c.section_path)}</summary><pre>${esc(c.body)}</pre><small>Issued ${esc(c.date_issued)} · revision ${esc(c.version_date)}<br>${esc(c.source_url)}<br>SHA-256 ${esc(c.sha256)}</small></details>`).join('')}<p><b>Evidence:</b> ${esc(q.gold.map(g=>g.evidence).join(' | '))}</p><label>Decision <select id="d${i}"><option value="pending">Pending</option><option value="accept">Accept after review</option><option value="reject">Reject / needs correction</option></select></label><textarea id="n${i}" placeholder="Review notes or correction needed"></textarea></article>`).join('');
document.getElementById('save').onclick=()=>{const reviewer=document.getElementById('reviewer').value.trim();if(!reviewer){document.getElementById('status').textContent='Enter a reviewer identifier first.';return}const result={dataset_hash:packet.dataset_hash,corpus_hash:packet.corpus_hash,reviewer,reviewed_at:new Date().toISOString(),decisions:packet.items.map(({question:q},i)=>({id:q.id,decision:document.getElementById('d'+i).value,notes:document.getElementById('n'+i).value}))};const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='official-label-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.getElementById('status').textContent='Saved review decisions. Import with scripts.review_labels --apply PATH. Pending/rejected labels remain unverified.'};</script>""".replace("__DATA__", data)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


def apply_review(review, questions, chunks, out):
    evidence = packet(questions, chunks)
    if any(review.get(k) != evidence[k] for k in ("dataset_hash", "corpus_hash")):
        raise ValueError("Review source or dataset fingerprint mismatch")
    if not str(review.get("reviewer", "")).strip() or not review.get("reviewed_at"):
        raise ValueError("Explicit reviewer identity and review date required")
    decisions = review.get("decisions", [])
    if len({d["id"] for d in decisions}) != len(decisions) or {d["id"] for d in decisions} != {q["id"] for q in questions}:
        raise ValueError("Review must contain each question exactly once")
    if any(d["decision"] not in {"accept", "reject", "pending"} for d in decisions):
        raise ValueError("Unknown review decision")
    accepted = {d["id"] for d in decisions if d["decision"] == "accept"}
    rows = [q | {"label_status": "verified", "notes": q["notes"] + f" Human reviewed by {review['reviewer']} on {review['reviewed_at']}."}
            for q in questions if q["id"] in accepted]
    if not rows:
        raise ValueError("No accepted labels")
    out = Path(out)
    if out.exists() or Path(str(out) + ".review.json").exists():
        raise ValueError("Choose a new output path; existing labels are never overwritten")
    validate_questions(rows)
    write_json(str(out) + ".review.json", review)
    write_jsonl(out, rows)
    return len(rows)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--questions", default="evals/questions.draft.jsonl")
    p.add_argument("--chunks", default="data/processed/chunks.jsonl")
    p.add_argument("--out", default="runs/official_label_review.html")
    p.add_argument("--apply", help="Human decisions JSON; --out must be a new JSONL path")
    a = p.parse_args()
    questions, chunks = read_jsonl(a.questions), read_jsonl(a.chunks)
    if a.apply:
        if Path(a.out).suffix != ".jsonl":
            raise ValueError("Use --out evals/questions.reviewed.jsonl when importing decisions")
        print(apply_review(json.loads(Path(a.apply).read_text(encoding="utf-8")), questions, chunks, a.out))
    else:
        print(export(questions, chunks, a.out))
