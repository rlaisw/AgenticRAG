# Test Fixtures

Generated sample documents for manual/automated testing of the AgenticRAG MCP server.
Not committed to git (binary) — regenerate with the snippet below.

| File | Purpose |
|---|---|
| `moon.docx` | Apollo 11 facts (DOCX parsing + RAG Q&A) |
| `physics.pdf` | physics constants (PDF parsing) |
| `cities.xlsx` | city populations (XLSX parsing) |
| `results.pptx` | quarterly review (PPTX parsing) |
| `broken.pdf` | corrupt file → skip-with-reason path |
| `notes.sqlite3` | `notes` table for the SQLite source connector |
| `audio/silence.wav` | 1 s silence (audio no-speech path) |

Ask things like "How tall is the speed of light?" (physics.pdf), "What happened in 1969?" (moon.docx), "Compare Tokyo and Delhi populations" (cities.xlsx + deep mode).
