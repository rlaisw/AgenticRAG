# Agentic RAG MCP Server

Agentic retrieval-augmented generation over stdio MCP. See `specs/001-agentic-rag-mcp/` for spec, plan, and contracts.

## Install

```bash
pipx install -e .
agentic-rag-mcp --init   # writes ~/.config/agentic-rag-mcp/config.toml
```

## MCP host config

```json
{ "mcpServers": { "agentic-rag": { "command": "agentic-rag-mcp" } } }
```

## System 1 decision node

Every `ask` request is routed by an embedded decision model (Laya, `convaiinnovations/laya`) in one pass — returning a route choice (`direct_retrieval` / `deliberative_reasoning` / `live_web` / `source_management`), a complexity score (1–10), and a knowledge-base-sufficiency boolean. No text is generated. Config in `config.toml`:

```toml
[decider]
enabled = true               # false => keyword heuristic routes (provenance: fallback)
model_repo = "convaiinnovations/laya"
model_dir = ""               # optional local checkpoint dir
timeout = 12.0               # exceeded => fallback routing
noul_threshold = 0.5
```

- First run downloads ~1.7 GB to the Hugging Face cache (~2 GB RAM loaded); the server pre-loads in the background at startup.
- Warm inference is hardware-dependent: ~140 ms on Apple Silicon, ~7.4 s on a small ARM cloud CPU — set `timeout` above your measured latency.
- Every response carries a `decision` object with `provenance` (`decision_node` | `fallback`) and `latency_ms`; when the decider is disabled/unavailable/timed-out, the keyword heuristic routes and responses are marked `provenance: "fallback"` (FR-003).
- Deliberative routes run the LangGraph reflexion graph (Actor → Evaluator → Self-Reflector → Episodic Memory); `reflections` in the response records each trial's score, verdict, and critique.

## Known pin

`faster-whisper==1.2.1` calls `av.open(..., metadata_errors="ignore")`, removed in PyAV 19. The vendored copy in `.venv` is patched; without the patch, unreadable audio files are skipped with a reason instead of crashing the batch (per FR edge-case). Upstream tracker: Pin PyAV<19 or upgrade faster-whisper when fixed.
