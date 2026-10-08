"""Draft synthesis + citation extraction (moved from the retired monolithic loop).

Used by the direct path in server.py and by the Actor stage of the reflexion graph.
"""

from __future__ import annotations


def synthesize(question: str, evidence: list[dict], confidence: str) -> str:
    if not evidence:
        return ("I could not find sufficient information to answer that question "
                "from the available sources.")
    seen, lines = set(), []
    for hit in evidence[:8]:
        text = (hit.get("snippet") or hit.get("content") or "").strip()
        if text and text not in seen:
            seen.add(text)
            lines.append(f"- {text[:400]}")
    header = ("Answer (best available evidence; confidence LOW):"
              if confidence == "low" else "Answer:")
    return f"{header}\n" + "\n".join(lines)


def citations(evidence: list[dict]) -> list[dict]:
    out = []
    for hit in evidence:
        if "url" in hit:
            out.append({"kind": "web", "ref": hit["url"], "title": hit.get("title", "")})
        elif "document_id" in hit:
            out.append({"kind": "document", "ref": hit["document_id"], "title": hit.get("title", "")})
    seen, uniq = set(), []
    for c in out:  # de-duplicate, preserve order
        if c["ref"] not in seen:
            seen.add(c["ref"])
            uniq.append(c)
    return uniq
