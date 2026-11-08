import re

INJECTION = re.compile(
    r"(?:ignore|disregard|forget)\s+(?:(?:all|any)\s+)?(?:previous|prior|earlier|above)\s+(?:instructions|rules)"
    r"|(?:note|message|instruction)s?\s+(?:to|for)\s+(?:the\s+)?(?:ai|assistant|model|llm)"
    r"|you\s+must\s+now|reply\s+only\s+with|system\s+prompt|assistant\s*:", re.I)
VERDICT = re.compile(r"\b(?:you are|is|are) (?:fully )?compliant\b|\byou should (?:buy|sell)\b", re.I)


def quarantine(text):
    sentences = re.split(r"(?<=[.!?])\s+|\n", text)
    kept = [s for s in sentences if not INJECTION.search(s)]
    return "\n".join(kept), len(sentences) - len(kept)


def output_guard(text, system):
    if re.search(r"CANARY-[A-Z]+-\d+", text, re.I):
        return "blocked_decoy"
    # Require a substantial exact overlap; short benign answers cannot match by accident.
    words = " ".join(system.lower().split()).split()
    normalized = " ".join(text.lower().split())
    if any(" ".join(words[i:i + 24]) in normalized for i in range(max(0, len(words) - 23))):
        return "blocked_prompt_leak"
    if VERDICT.search(text):
        return "blocked_verdict"
    return None


def unknown_reference(question, manifest):
    refs = re.findall(r"\b(?:circular|direction)\s+(?:no\.?\s*)?([A-Z0-9][A-Z0-9./_-]*\d[A-Z0-9./_-]*)", question, re.I)
    known = {m.get("reference_no", "").strip().lower().rstrip(".") for m in manifest.values()}
    for ref in refs:
        if ref.lower().rstrip(".") not in known:
            return True
    titles = re.findall(r'(?:circular|direction)\s+["“]([^"”]+)["”]', question, re.I)
    return any(not any(title.lower() in m["title"].lower() for m in manifest.values()) for title in titles)
