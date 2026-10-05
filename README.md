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

## Known pin

`faster-whisper==1.2.1` calls `av.open(..., metadata_errors="ignore")`, removed in PyAV 19. The vendored copy in `.venv` is patched; without the patch, unreadable audio files are skipped with a reason instead of crashing the batch (per FR edge-case). Upstream tracker: Pin PyAV<19 or upgrade faster-whisper when fixed.
