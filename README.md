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
