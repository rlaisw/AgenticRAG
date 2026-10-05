# Feature Specification: Agentic RAG MCP Server

**Feature Branch**: `001-agentic-rag-mcp`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "Build an Agentic RAG MCP Server with: dynamic/real-time update and embedding of data into a vector database (LanceDB); support for local source data files (PDF, Microsoft Office documents — Word, Excel, PowerPoint — and audio files); SQLite DB as a data source; remote data sources OneDrive and Office 365 SharePoint Online; real-time internet search engines (Tavily, Exa, SearXNG); LanceDB paired with CocoIndex [full] for an incremental data transformation and vector search pipeline; Graphify for semantic search; Laya decision model and reflection agent loop (System 1 fast path, System 2 LangGraph complex research); dynamic reasoning loops that evaluate retrieval sufficiency and loop back to query more; autonomous planning & routing that breaks complex questions into sub-tasks and chooses the best tools; ReAct (Reason + Act) with LLMs; run Laya as a decision layer locally."

## Clarifications

### Session 2026-10-05

- Q: How should the Laya decision layer for System 1 / System 2 routing be implemented? → A: Run the actual Laya desktop app (https://laya.aay.sh/) locally and route decision-model requests through its local MCP/HTTP surface; the Laya app is a required runtime dependency.
- Q: What deployment and user scope must the server support? → A: Single-user, single-machine deployment only; multi-user/team serving is out of scope.
- Q: Where do embeddings run? → A: Embedding generation runs locally on the user's machine (local model); no hosted embedding API is required for the default configuration.
- Q: How should OneDrive/SharePoint Online authorization work? → A: Per-user delegated authorization (the connecting user's own Microsoft account), not app-only/daemon access.
- Q: How do MCP clients connect to the server? → A: stdio transport (the MCP host launches the server as a child process); no separate network listener required for v1.
- Q: Which languages, frameworks, and APIs are fixed for this project? → A: All 15 confirmed as binding user-specified constraints (see Technology Constraints section): Python 3.12; official MCP Python SDK over stdio; CocoIndex [full] incremental pipeline; LanceDB embedded vector store; Graphify as an optional graph-search layer; LangGraph for the System 2 loop; the Laya desktop app as the System 1 decision layer (heuristic fallback); sentence-transformers local embeddings; faster-whisper local transcription; pypdf/python-docx/openpyxl/python-pptx parsing; MSAL per-user delegated OAuth; Tavily/Exa/SearXNG web-search adapters; SQLite state store; pytest; pipx-packaged CLI.

## Technology Constraints (user-specified, binding)

The following choices are product requirements set by the user, not implementation proposals. Functional Requirements below are deliberately technology-agnostic; these constraints govern how they are realized:

1. **Language**: Python 3.12.
2. **MCP surface**: official MCP Python SDK, stdio transport.
3. **Incremental pipeline**: CocoIndex [full].
4. **Vector store**: LanceDB (embedded).
5. **Graph search**: Graphify (optional layer, off the fast path).
6. **Deliberative orchestration**: LangGraph (ReAct loop).
7. **Decision layer**: Laya desktop app local API; built-in heuristic fallback when unreachable.
8. **Embeddings**: sentence-transformers, local (`all-MiniLM-L6-v2` default).
9. **Audio transcription**: faster-whisper (local).
10. **Document parsing**: pypdf, python-docx, openpyxl, python-pptx.
11. **Microsoft authentication**: MSAL, per-user delegated OAuth 2.0.
12. **Web search APIs**: pluggable adapters — Tavily, Exa, self-hosted SearXNG.
13. **State store**: SQLite.
14. **Testing**: pytest.
15. **Packaging**: pipx-installable CLI entry point.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask a question and get a sourced answer (Priority: P1)

An AI client (agent host) connects to the MCP server and asks a natural-language question. The server classifies the question as simple, retrieves relevant documents from the local knowledge base, and returns an answer with citations to the sources used.

**Why this priority**: This is the core value of the product — retrieval-augmented answers over personal/organizational knowledge. Without it, every other capability is dead weight.

**Independent Test**: Can be fully tested by ingesting a small set of local documents, sending a question over MCP, and verifying the answer cites the correct source documents.

**Acceptance Scenarios**:

1. **Given** a set of ingested local documents, **When** a client asks a fact-based question answerable from those documents, **Then** the server returns an answer with references to the specific source documents used.
2. **Given** a question that cannot be answered from available sources, **When** retrieval finds nothing relevant, **Then** the server responds that no relevant information was found rather than fabricating an answer.

---

### User Story 2 - Keep the knowledge base up to date automatically (Priority: P1)

A user adds, edits, or deletes files in watched local folders, a connected SQLite database, OneDrive, or SharePoint. The knowledge base reflects those changes automatically — new content becomes searchable, changed content is re-embedded, and deleted content stops appearing in answers — without the user manually re-running an index.

**Why this priority**: Stale answers destroy trust — an incremental, near-real-time pipeline is a stated core differentiator over one-shot indexing.

**Independent Test**: Can be tested by adding a new document to a watched source, waiting for the ingestion cycle, and verifying a fresh question retrieves it — then deleting the document and verifying it no longer appears.

**Acceptance Scenarios**:

1. **Given** a watched local folder, **When** a new PDF is added, **Then** the document is parsed, embedded, and retrievable within a configurable freshness window.
2. **Given** a previously ingested document, **When** its content changes, **Then** subsequent answers reflect the new content, not the old.
3. **Given** a previously ingested document, **When** it is deleted from the source, **Then** it no longer appears in retrieval results.

---

### User Story 3 - Deep research on complex questions (Priority: P2)

A client asks a multi-part or ambiguous question that simple retrieval can't answer (e.g., requires combining local documents, structured data, and recent web information). The system decomposes the question into sub-tasks, routes each sub-task to the best source (vector search, SQL data, web search), evaluates whether results are sufficient, loops back to gather more if not, and synthesizes a well-supported answer.

**Why this priority**: This is the "agentic" differentiator — high-value research answers — but it depends on the retrieval substrate from Stories 1–2.

**Independent Test**: Can be tested with a question that requires at least two different source types, verifying the system plans sub-tasks, retrieves from each, and returns a synthesized answer showing which sources were used per sub-task.

**Acceptance Scenarios**:

1. **Given** a complex question spanning multiple sources, **When** the client submits it, **Then** the system produces a synthesized answer with per-sub-task provenance.
2. **Given** an initial retrieval that is insufficient, **When** the sufficiency check fails, **Then** the system reformulates and issues additional queries before answering, within a bounded number of iterations.

---

### User Story 4 - Search the live web alongside private data (Priority: P3)

A client asks about current events, recent documentation, or anything not yet in the local knowledge base. The system queries one or more internet search providers in real time, incorporates results into retrieval, and distinguishes external (web) sources from private/local sources in its answer.

**Why this priority**: Adds recency and breadth, but the system is still useful without it; it depends on the routing layer from Story 3.

**Independent Test**: Can be tested by asking a question about a recent public event with no matching local documents and verifying the answer cites web sources.

**Acceptance Scenarios**:

1. **Given** no relevant local documents, **When** a question requires current information, **Then** the system consults a configured web search provider and cites web URLs in the answer.
2. **Given** a configured web search provider is unreachable, **When** a question needs it, **Then** the system either falls back to another configured provider or reports that web search is unavailable, while still answering from local sources if possible.

---

### Edge Cases

- What happens when a source file is corrupt, encrypted, or password-protected? System skips it, logs the failure, and continues the ingestion cycle without blocking other documents.
- What happens when an audio file has no speech or unsupported language? It is marked as unprocessable with a reason, not silently dropped.
- What happens when the same document exists in two sources (e.g., local copy and OneDrive)? The system detects duplicates (by content identity) and does not return the same content twice.
- What happens when the reflection loop cannot reach sufficiency within its iteration budget? The system answers with the best evidence gathered and explicitly flags confidence as low.
- What happens when a remote source (OneDrive/SharePoint/web) credential expires mid-cycle? The affected source is marked degraded; ingestion from other sources continues; the client is informed the source needs re-authentication.
- What happens when two clients query concurrently? Answers remain consistent and ingestion is not corrupted by concurrent updates.
- What happens when the Laya decision-layer app is not running or unreachable? The system falls back to a built-in heuristic default (treat the question as deliberative), reports the degradation to the client, and continues answering normally.

## Requirements *(mandatory)*

### Functional Requirements

**Ingestion & Indexing**

- **FR-001**: System MUST ingest documents from watched local folders: PDF, Microsoft Word, Excel, PowerPoint, and common audio formats (at minimum MP3, WAV, M4A); parsing/embedding tooling per Technology Constraints #9–10.
- **FR-002**: System MUST ingest rows/records from a configured SQLite database as a data source.
- **FR-003**: System MUST ingest documents from OneDrive and SharePoint Online using per-user delegated authorization (the connecting user's own Microsoft account); app-only/daemon access is out of scope (see Technology Constraints #11).
- **FR-004**: System MUST support incremental updates: detecting added, changed, and deleted source items and reflecting those changes in the retrieval index without a full rebuild.
- **FR-005**: System MUST convert non-text sources into searchable text (document parsing for Office/PDF; transcription for audio) and embed them using a locally running embedding model before adding them to the index.
- **FR-006**: System MUST detect content-identical duplicates across sources and present each unique document at most once in retrieval results.
- **FR-007**: System MUST record the origin (source system, location/path, timestamp) of every ingested item so answers can cite sources.

**Retrieval & Answering**

- **FR-008**: System MUST expose its capabilities as an MCP server over stdio transport (the MCP host launches the server as a child process); a network listener is not required for v1.
- **FR-009**: System MUST provide semantic (vector) search over embedded content.
- **FR-010**: System SHOULD provide graph-based semantic search over the knowledge corpus as an optional layer (disabled bydefault ⇒ structured unavailable-response).
- **FR-011**: System MUST provide real-time internet search through at least one pluggable provider; provider selection and fallback order MUST be configurable.

**Agentic Decision & Reasoning**

- **FR-012**: System MUST classify each incoming question and route simple questions through a fast path (direct retrieval + answer) and complex questions through a deliberative research path, delegating the decision to the configured local decision layer (Technology Constraints #7) with a built-in heuristic fallback when it is unreachable.
- **FR-013**: System MUST decompose complex questions into structured sub-tasks and route each sub-task to the most appropriate tool (vector search, SQL query, web search, remote document source).
- **FR-014**: System MUST evaluate retrieval sufficiency after each step and, when results are insufficient, reformulate and issue additional queries up to a configurable iteration budget.
- **FR-015**: System MUST follow a Reason + Act (ReAct) loop with an LLM during deliberative research, recording intermediate reasoning/tool steps.
- **FR-016**: System MUST return per-answer provenance: which sources were consulted and which sub-task used them.
- **FR-017**: When a deliberative loop exhausts its iteration budget without sufficiency, the system MUST still answer from gathered evidence and flag the answer as low-confidence.

### Key Entities *(include if feature involves data)*

- **Document/Item**: A single ingested unit — file, database record, or remote file — with origin metadata (source type, path/URL, timestamps, hash), extracted text/transcript, and ingestion status.
- **Chunk/Embedding**: A text segment of a document with its vector representation, linked back to its parent document; subject to update/invalidation when the parent changes.
- **Collection**: A named logical grouping of documents within a vector store (e.g., one per source or domain), referenced in retrieval routing.
- **Source/Connector**: A configured ingestion channel (local folder, SQLite DB, OneDrive, SharePoint, web search provider) with credentials/config, sync state, and health status (healthy/degraded).
- **Question/Session**: A client question with classification (simple/complex), decomposition plan, tool-call trace, and final answer with citations.
- **Sufficiency assessment**: The outcome of evaluating retrieved evidence against the question, driving the dynamic reasoning loop.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Simple questions receive a sourced answer in under 10 seconds end-to-end on a typical local machine once sources are ingested.
- **SC-002**: A newly added or changed document becomes searchable within 5 minutes of the change occurring in its source (without manual reindex).
- **SC-003**: For a test corpus of mixed local documents, 90% of fact-based questions return answers citing the correct source document.
- **SC-004**: Complex multi-source questions complete within a bounded time budget (default iteration cap), and 100% of such answers report which sources were consulted.
- **SC-005**: When web search providers fail or credentials expire, answers from remaining healthy sources are still returned, with degraded sources clearly reported, in 100% of failure-injection tests.
- **SC-006**: A first-time user can connect the MCP client, point the server at a folder of documents, and receive a correct sourced answer within 30 minutes of setup.

## Assumptions

- Deployment target is a single-user local machine (macOS/Linux/Windows); multi-tenant serving is out of scope (confirmed).
- Embedding generation runs locally by default (local model on the user's machine); no hosted embedding API key is required for the default configuration (confirmed).
- MCP clients connect over stdio transport — the host launches the server as a child process (confirmed); an optional network listener may be added later.
- The Laya desktop app (https://laya.aay.sh/) running locally is a required runtime dependency for the default System 1/System 2 routing decision; users who do not run Laya get the built-in heuristic fallback (confirmed).
- The user has valid credentials/app registration for Microsoft Graph (OneDrive/SharePoint) using per-user delegated authorization (confirmed); app-only access is out of scope.
- Audio support means speech-to-text transcription; music/sound analysis is out of scope.
- LLM providers for the deliberative path can be local or API-based per user configuration; embedding remains local by default.
- The deliberative (System 2) path is built on a graph-orchestrated agent loop (see Technology Constraints #6); the fast (System 1) path needs no multi-step orchestration.
- Internet search is opt-in per configuration; no web-search API keys are bundled — user supplies their own, or self-hosts a search instance (see Technology Constraints #12).
