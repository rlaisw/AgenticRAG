# Agentic RAG MCP Server

Agentic retrieval-augmented generation as an MCP server, with a **dual-system workflow**: an embedded structured **decision node** (System 1) routes every request, and a **LangGraph reflexion graph** (System 2) handles complex questions with self-correcting, memory-conditioned retries. 97 tests, contract-preserved responses, provenance on every decision.

Specs: [`specs/001-agentic-rag-mcp/`](specs/001-agentic-rag-mcp/) (server, ingestion, contracts) · [`specs/002-laya-reflexion-nodes/`](specs/002-laya-reflexion-nodes/) (dual-system replacement — supersedes 001's routing/loop design).

## Architecture

```
question ──► System 1: embedded Laya decision model (one pass, no text generation)
             choice (route) + score (complexity 1–10) + sufficiency boolean
                 ├─ direct_retrieval / source_management ─► single retrieval step
                 └─ deliberative_reasoning / live_web ─► System 2 reflexion graph:
                        Actor ─► Evaluator (score+verdict) ─► Self-Reflector ─► Episodic Memory
                        (loop gated ONLY by the evaluator; union of all reflections
                         conditions every retry; bounded by max_iterations)
```

Outage behavior: if the decision node is unavailable/invalid/timed-out, the keyword heuristic routes and responses are marked `provenance: "fallback"` (FR-003 of spec 002).

## MCP tools (10)

| Tool | Purpose |
|---|---|
| `ask` | Agentic Q&A with citations; every response carries `decision` (route, complexity, sufficiency, provenance, latency) and `reflections` (per-trial evaluator scores/verdicts/critiques) |
| `search` | Direct vector search over LanceDB |
| `web_search` | Live web via SearXNG (fallback chain: searxng → tavily → exa) |
| `fetch_url` | Fetch a live page; returns `date_utc` (HTTP Date header = live UTC clock) |
| `sources_add` / `sources_list` / `sources_remove` / `sources_sync` | Knowledge-base source management (local_folder, sqlite) |
| `graph_query` | Optional Graphify layer (enable `[features] graphify = true`; build with the graphify skill) |
| `status` | Decision-node provenance, source health, index counters |

## Install

```bash
pipx install -e .
agentic-rag-mcp --init   # writes ~/.config/agentic-rag-mcp/config.toml
```

## MCP host config (stdio)

```json
{ "mcpServers": { "agentic-rag": { "command": "agentic-rag-mcp" } } }
```

## Dify integration

A stateless-HTTP sidecar for Dify ships in [`dify/`](dify/): Dockerfile, compose fragments (Dify networks + HF-cache mount), and a ready-to-import 10-tool chatflow DSL (`dify/Chatflow Basic (AgenticRAG Agent).yml`). Build and run:

```bash
docker build -f dify/docker/mcp-server/Dockerfile -t agentic-rag-mcp:latest .
docker run -d --name agentic-rag --network <dify_network> \
  -v ~/.config/agentic-rag-mcp:/root/.config/agentic-rag-mcp \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -p 28080:8080 --restart always agentic-rag-mcp:latest
```

Dify UI → Tools → MCP → URL `http://agentic-rag:8080/mcp` (container-internal port stays 8080; the host publishes **28080**, so host-side checks use `http://localhost:28080/healthz`). Edit MCP servers by delete + re-add (Dify 1.17's edit path has an identifier-vs-UUID bug).

## Configuration

```toml
[decider]                   # System 1 (see "System 1 decision node" details below)
enabled = true              # false => keyword heuristic routes (provenance: fallback)
model_repo = "convaiinnovations/laya"
model_dir = ""              # optional local checkpoint dir
timeout = 12.0              # exceeded => fallback (~7.4s warm on ARM CPU)
noul_threshold = 0.5

[features]
graphify = false            # optional graph-search layer over graphify-out/graph.json
```

### System 1 decision node

Every `ask` request is routed by an embedded decision model (Laya, `convaiinnovations/laya`) in one pass — returning a route choice (`direct_retrieval` / `deliberative_reasoning` / `live_web` / `source_management`), a complexity score (1–10), and a knowledge-base-sufficiency boolean. No text is generated.

- First run downloads ~1.7 GB to the Hugging Face cache (~2 GB RAM loaded); the server pre-loads in the background at startup.
- Warm inference is hardware-dependent: ~140 ms on Apple Silicon, ~7.4 s on a small ARM cloud CPU — set `timeout` above your measured latency.
- Every response carries a `decision` object with `provenance` (`decision_node` | `fallback`) and `latency_ms`.
- Deliberative routes run the LangGraph reflexion graph (Actor → Evaluator → Self-Reflector → Episodic Memory); `reflections` in the response records each trial's score, verdict, and critique.

## Known pin

`faster-whisper==1.2.1` calls `av.open(..., metadata_errors="ignore")`, removed in PyAV 19. The vendored copy in `.venv` is patched; without the patch, unreadable audio files are skipped with a reason instead of crashing the batch (per FR edge-case). Upstream tracker: Pin PyAV<19 or upgrade faster-whisper when fixed.
