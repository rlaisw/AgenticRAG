"""Deliberative reflection loop (Franc-System 2): plan -> route -> retrieve ->

sufficiency -> loop (bounded) -> synthesize with provenance (FR-013..FR-017).
Pure-Python graph; LangGraph-compatible interface kept separate for swap-in.
"""

from __future__ import annotations

from ..errors import SufficiencyExhausted
from ..routing.planner import decompose
from .sufficiency import assess


class ReflectionAgent:
    def __init__(self, tools: dict, max_iterations: int = 5) -> None:
        self._tools = tools          # name -> callable(query) -> list[dict]
        self._budget = max_iterations

    def run(self, question: str) -> dict:
        available = [t for t in ("vector_search", "sql_query", "web_search", "graphify")
                     if t in self._tools]
        tasks = decompose(question, available)
        trace: list[dict] = []
        evidence: list[dict] = []
        iterations = 0
        suff = {"outcome": "continue", "reason": "start"}

        while iterations < self._budget and suff["outcome"] == "continue":
            for task in tasks:
                tool = self._tools.get(task["tool"])
                if not tool:
                    continue
                try:
                    hits = tool(task["input"]) or []
                except Exception as exc:  # noqa: BLE001 - tool isolation
                    hits = []
                    task["error"] = str(exc)
                trace.append({"tool": task["tool"], "query": task["input"], "hits": len(hits)})
                task["results"] = hits
                evidence.extend(hits)
            iterations += 1
            suff = assess(question, evidence, iterations, self._budget)
            if suff["outcome"] == "continue":
                # reformulate: widen each sub-task query once
                tasks = [
                    {"id": t["id"], "tool": t["tool"], "input": f"{t['input']} details"}
                    for t in tasks
                ]

        confidence = "normal" if suff["outcome"] == "satisfied" else "low"
        error = None
        if suff["outcome"] == "exhausted":
            error = SufficiencyExhausted("iteration budget exhausted").to_result()

        answer = self._synthesize(question, evidence, confidence)
        return {
            "answer": answer,
            "confidence": confidence,
            "classification": "deliberative",
            "iterations": iterations,
            "sufficiency": suff["outcome"],
            "trace": trace,
            "citations": self._citations(evidence),
            "error": error,
            "plan": [{"id": t["id"], "tool": t["tool"], "input": t["input"]} for t in tasks],
        }

    def _synthesize(self, question: str, evidence: list[dict], confidence: str) -> str:
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

    def _citations(self, evidence: list[dict]) -> list[dict]:
        out = []
        for hit in evidence:
            if "url" in hit:
                out.append({"kind": "web", "ref": hit["url"], "title": hit.get("title", "")})
            elif "document_id" in hit:
                out.append(
                    {"kind": "document", "ref": hit["document_id"], "title": hit.get("title", "")}
                )
        # de-duplicate while preserving order
        seen, uniq = set(), []
        for c in out:
            if c["ref"] not in seen:
                seen.add(c["ref"])
                uniq.append(c)
        return uniq
