# Graph Report - AgenticRAG  (2026-10-08)

## Corpus Check
- 142 files · ~93,196 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .code-workspace 1)

## Summary
- 912 nodes · 1812 edges · 61 communities (40 shown, 21 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 200 edges (avg confidence: 0.92)
- Token cost: 31,000 input · 5,200 output

## Community Hubs (Navigation)
- Spec-Kit Bash Prerequisites
- Web Search Provider Adapters
- Spec 002 Contracts & Checklists
- System 1 Decision Node
- Content Dedup Pipeline
- Error Taxonomy
- Spec-Kit Shell Libraries
- Reflexion Graph Core
- Graphify Search Layer
- Episodic Memory
- MCP Server Construction
- Source Sync & Watchers
- Reflexion Graph Tests
- Laya Model Utilities
- Rule-Based Evaluator
- HTTP/SSE Entry Scripts
- Fallback Provenance Tests
- Dify Sidecar Server
- Web Tool Contracts
- Laya Inference API
- Spec-Kit PowerShell Helpers
- Spec-Kit Templates & Spec 001
- MCP Tool Surface
- Speckit Workflow Commands
- Speckit Slash Commands
- Vector Store Chunking
- Ingestion Data Model
- Ingestion Pipeline
- Decision Routing Tests
- Deployment & Docs
- MCP Contract Tests
- Laya Sequence Building
- Sub-Task Planner
- RLAgent Inference Core
- End-to-End Tests
- Ask Contract Tests
- Test Fixtures & Pins
- System 2 Design Docs
- Reflexion Conditioning Tests
- Success Criteria Suite
- Decision Model Architecture
- Shared Test Fixtures
- SQLite Source Connector
- RL Training Targets
- Reflexion Honesty Tests
- Feature Branch Script
- Graphify Layer Docs
- Indexing Skill Config
- FastMCP Framework Decision
- Package Root

## God Nodes (most connected - your core abstractions)
1. `build_server()` - 41 edges
2. `ProviderError` - 29 edges
3. `Config` - 22 edges
4. `StateStore` - 22 edges
5. `resolve_template_content()` - 20 edges
6. `EpisodicMemory` - 18 edges
7. `TemplateResolutionError` - 17 edges
8. `GraphifySearch` - 17 edges
9. `ReflexionAgent` - 16 edges
10. `SourceAuthError` - 16 edges

## Surprising Connections (you probably didn't know these)
- `test_no_evidence_answer_is_honest_never_fabricated()` --uses--> `ReflexionAgent`  [INFERRED]
  tests/unit/test_reflexion.py → src/agentic_rag_mcp/agents/reflexion.py
- `LangGraph reflexion graph (Actor - Evaluator - Self-Reflector - Episodic Memory)` --semantically_similar_to--> `LangGraph ReAct System 2 deliberative loop`  [INFERRED] [semantically similar]
  README.md → specs/001-agentic-rag-mcp/plan.md
- `_rec()` --uses--> `ReflectionRecord`  [INFERRED]
  tests/unit/test_memory.py → src/agentic_rag_mcp/agents/memory.py
- `test_memory_starts_empty_per_request()` --uses--> `EpisodicMemory`  [INFERRED]
  tests/unit/test_memory.py → src/agentic_rag_mcp/agents/memory.py
- `test_budget_exhaustion_low_confidence_and_full_memory()` --uses--> `ReflexionAgent`  [INFERRED]
  tests/unit/test_reflexion_graph.py → src/agentic_rag_mcp/agents/reflexion.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Problem-Solving Ladder (KB ask, then web_search, then fetch_url, then synthesize)** — dify_chatflow_basic__agenticrag_agent__agentic_strategy, specs_001_agentic_rag_mcp_contracts_mcp_tools_ask, dify_chatflow_basic__agenticrag_agent__web_search_tool, dify_chatflow_basic__agenticrag_agent__fetch_url_tool [EXTRACTED 1.00]
- **Incremental ingestion pipeline (CocoIndex change detection into LanceDB chunks with dedup by content hash)** — specs_001_agentic_rag_mcp_plan_cocoindex_pipeline, specs_001_agentic_rag_mcp_plan_lancedb_vector_store, specs_001_agentic_rag_mcp_data_model_document, specs_001_agentic_rag_mcp_data_model_chunk, specs_001_agentic_rag_mcp_data_model_source [INFERRED 0.95]
- **System 1/System 2 question routing (Laya decision layer steering between fast retrieval and the LangGraph deliberative loop)** — specs_001_agentic_rag_mcp_research_d5_laya_routing, specs_001_agentic_rag_mcp_plan_langgraph_deliberative_loop, specs_001_agentic_rag_mcp_contracts_mcp_tools_ask, specs_001_agentic_rag_mcp_spec_fr_012 [INFERRED 0.95]
- **System 2 Reflexion Loop: Actor → Evaluator → Self-Reflector → Episodic Memory** — specs_002_laya_reflexion_nodes_spec_actor_stage, specs_002_laya_reflexion_nodes_spec_evaluator_stage, specs_002_laya_reflexion_nodes_spec_self_reflector_stage, specs_002_laya_reflexion_nodes_data_model_episodicmemory, specs_002_laya_reflexion_nodes_spec_system_2_reflexion_graph [EXTRACTED 1.00]
- **Dual-System Request Flow: System 1 decision → FR-005 route mapping → execution path → ask response contract** — specs_002_laya_reflexion_nodes_spec_system_1_decision_node, specs_002_laya_reflexion_nodes_spec_fr005_route_mapping, specs_002_laya_reflexion_nodes_spec_system_2_reflexion_graph, specs_002_laya_reflexion_nodes_contracts_ask_response_ask_tool_contract [EXTRACTED 1.00]
- **Supersedes Replacement Scope: OLD components → NEW dual-system design** — specs_002_laya_reflexion_nodes_spec_single_label_classifier, specs_002_laya_reflexion_nodes_spec_keyword_heuristic_fallback, specs_002_laya_reflexion_nodes_spec_monolithic_deliberation_loop, specs_002_laya_reflexion_nodes_spec_hit_count_sufficiency_gate, specs_002_laya_reflexion_nodes_spec_system_1_decision_node, specs_002_laya_reflexion_nodes_spec_system_2_reflexion_graph, specs_002_laya_reflexion_nodes_spec_evaluator_stage [EXTRACTED 1.00]

## Communities (61 total, 21 thin omitted)

### Community 0 - "Spec-Kit Bash Prerequisites"
Cohesion: 0.06
Nodes (60): Args, _available_docs(), _check_dir(), _check_file(), _dir_has_entries(), _json_line(), main(), _parse_args() (+52 more)

### Community 1 - "Web Search Provider Adapters"
Cohesion: 0.07
Nodes (26): ProviderError, SourceAuthError, build_providers(), ExaProvider, SearxngProvider, TavilyProvider, GraphAuth, GraphBase (+18 more)

### Community 2 - "Spec 002 Contracts & Checklists"
Cohesion: 0.07
Nodes (41): Specification Quality Checklist: Dual-System Workflow, ask MCP Tool Response Contract (preserved fields + decision/reflections extensions), Pre-existing Contract Test Suite (tests/contract/), Dify Chatflow (client consumer of the ask tool), Contract: ask Tool Response, decide(question) → DecisionResult (System 1 decision node operation), Decision Primitives: choice, score, noul (one-pass three-question batch), Contract: System 1 Decision Schema (+33 more)

### Community 3 - "System 1 Decision Node"
Cohesion: 0.06
Nodes (27): Config, decide(), DecisionResult, fallback_route(), map_model_output(), _questions(), _test_cfg(), validate_output() (+19 more)

### Community 4 - "Content Dedup Pipeline"
Cohesion: 0.08
Nodes (14): content_hash(), normalize(), _now(), StateStore, call(), server(), test_budget_exhaustion_low_confidence(), test_concurrent_queries_consistent() (+6 more)

### Community 5 - "Error Taxonomy"
Cohesion: 0.11
Nodes (19): DecisionLayerUnavailable, Err, ErrorCode, IngestionError, Ok, RagError, SufficiencyExhausted, wrap() (+11 more)

### Community 6 - "Spec-Kit Shell Libraries"
Cohesion: 0.13
Nodes (29): check-prerequisites.sh script, check_dir(), check_file(), find_specify_root(), format_speckit_command(), get_current_branch(), get_feature_paths(), get_invoke_separator() (+21 more)

### Community 7 - "Reflexion Graph Core"
Cohesion: 0.14
Nodes (10): ReflectionRecord, _actor(), _after_evaluator(), _after_memory(), _build_graph(), _evaluator(), _memory_node(), _self_reflector() (+2 more)

### Community 8 - "Graphify Search Layer"
Cohesion: 0.13
Nodes (7): FeatureDisabledError, GraphifySearch, test_cli_failure_is_provider_error(), test_disabled_by_default(), test_enabled_but_graph_missing(), test_explain_shells_out(), test_stats_reads_graph()

### Community 10 - "Episodic Memory"
Cohesion: 0.14
Nodes (8): EpisodicMemory, _rec(), test_append_ordering_preserved(), test_memory_starts_empty_per_request(), test_no_cross_request_leakage(), test_record_serializes_all_fields(), test_union_deduplicates_terms_in_first_appearance_order(), test_union_missing_focus_is_full_history_not_latest()

### Community 11 - "MCP Server Construction"
Cohesion: 0.14
Nodes (13): make_vector_tool(), make_web_tool(), build_server(), ask(), degraded_sources(), fetch_url(), graph_query(), route_question() (+5 more)

### Community 12 - "Source Sync & Watchers"
Cohesion: 0.13
Nodes (8): make_sql_tool(), Watcher, loop(), Embedder, test_sql_tool_no_text_column(), test_sql_tool_reads_rows(), test_watcher_isolates_bad_source(), test_watcher_sync_once_local()

### Community 13 - "Reflexion Graph Tests"
Cohesion: 0.15
Nodes (8): ReflexionAgent, test_budget_exhaustion_low_confidence_and_full_memory(), test_contract_fields_present(), test_fail_triggers_reflector_memory_and_conditioned_retry(), test_full_history_conditions_each_trial_no_regression(), test_graph_runs_until_pass_and_stops(), fake_vector(), test_web_first_orders_web_tools_in_first_trial()

### Community 14 - "Laya Model Utilities"
Cohesion: 0.14
Nodes (6): aurc(), auroc(), ece_score(), make_token_batches(), pack_groups(), spearman()

### Community 15 - "Rule-Based Evaluator"
Cohesion: 0.18
Nodes (9): evaluate(), _terms(), _ev(), test_full_coverage_with_citations_passes_with_high_score(), test_hit_count_is_scoring_input_not_verdict_gate(), test_identical_inputs_identical_outputs(), test_no_citable_evidence_caps_score_and_fails(), test_partial_coverage_fails_and_names_missing_terms() (+1 more)

### Community 16 - "HTTP/SSE Entry Scripts"
Cohesion: 0.14
Nodes (4): _get(), init_config(), load_config(), main()

### Community 17 - "Fallback Provenance Tests"
Cohesion: 0.18
Nodes (9): call(), _live_cfg(), _median(), server(), test_fallback_latency_within_budget(), test_no_third_provenance_value(), test_outage_routes_via_fallback_and_marks_it(), test_recovery_next_request_uses_decision_node() (+1 more)

### Community 19 - "Web Tool Contracts"
Cohesion: 0.18
Nodes (12): fetch_url MCP tool (live page fetch with date_utc clock), web_search MCP tool (live web via SearXNG/Tavily/Exa), MCP typed error surface, Question session entity (deliberative trace), SubTask entity (per-tool provenance unit), Scenario 4 - Web search fallback (P3), FR-011: Real-time internet search via pluggable providers, FR-016: Per-answer provenance (+4 more)

### Community 20 - "Laya Inference API"
Cohesion: 0.16
Nodes (4): amp_dtype(), build_model(), collate_items(), predict_items()

### Community 21 - "Spec-Kit PowerShell Helpers"
Cohesion: 0.22
Nodes (10): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-Python3Command(), Get-RepoRoot(), Resolve-SpecifyInitDir() (+2 more)

### Community 22 - "Spec-Kit Templates & Spec 001"
Cohesion: 0.24
Nodes (12): Spec-kit plan template, Spec-kit feature specification template, Spec-kit task list template, Specification Quality Checklist: Agentic RAG MCP Server, MCP Tool Contracts (stdio transport), Data Model: Agentic RAG MCP Server, Implementation Plan: Agentic RAG MCP Server, Quickstart: Agentic RAG MCP Server (validation scenarios) (+4 more)

### Community 23 - "MCP Tool Surface"
Cohesion: 0.35
Nodes (13): Agentic Strategy node (FunctionCalling agent), MCP tool: ask (agentic Q&A with citations), MCP tool: search (direct vector retrieval), MCP tool: sources.add (register source), MCP tool: sources.list (sources with health), MCP tool: sources.remove (drop source), MCP tool: sources.sync (incremental sync), MCP tool: status (server health) (+5 more)

### Community 24 - "Speckit Workflow Commands"
Cohesion: 0.41
Nodes (13): Speckit Analyze Workflow, Speckit Checklist Workflow, Speckit Clarify Workflow, Speckit Constitution Workflow, Speckit Converge Workflow, Speckit Implement Workflow, Speckit Plan Workflow, Speckit Specify Workflow (+5 more)

### Community 25 - "Speckit Slash Commands"
Cohesion: 0.50
Nodes (12): speckit.analyze Command, speckit.checklist Command, speckit.clarify Command, speckit.constitution Command, Project Constitution, speckit.converge Command, speckit.implement Command, speckit.plan Command (+4 more)

### Community 27 - "Ingestion Data Model"
Cohesion: 0.24
Nodes (9): Chunk entity (embedded segment, row in LanceDB), Document entity (canonical ingested item, deduplicated by content), OriginRef entity (one physical location of a Document), CocoIndex [full] incremental pipeline, LanceDB embedded vector store, Scenario 2 - Incremental update (P1), FR-004: Incremental updates without full rebuild, FR-006: Content-identical dedup across sources (+1 more)

### Community 29 - "Decision Routing Tests"
Cohesion: 0.29
Nodes (7): call(), direct_output(), server(), test_decision_contains_only_structured_values(), test_direct_route_served_in_one_step(), test_forced_mode_still_records_decision(), test_source_management_route_gives_guidance_without_operations()

### Community 30 - "Deployment & Docs"
Cohesion: 0.27
Nodes (8): Chatflow Basic (AgenticRAG Agent), AgenticRAG MCP sidecar (Dify compose service), AgenticRAG MCP sidecar (standalone compose), Agentic RAG MCP Server, Local sentence-transformers embeddings (all-MiniLM-L6-v2), MSAL per-user delegated OAuth (OneDrive/SharePoint), FR-003: OneDrive/SharePoint ingestion via per-user delegated authorization, FR-012: Question classification with fast/deliberative routing and heuristic fallback

### Community 31 - "MCP Contract Tests"
Cohesion: 0.31
Nodes (7): call(), server(), test_ask_no_documents_returns_no_fabrication(), test_bad_source_type_raises_not_found(), test_graph_query_disabled_by_default(), test_status_shape(), test_unknown_source_remove_is_graceful()

### Community 32 - "Laya Sequence Building"
Cohesion: 0.25
Nodes (5): build_sequence(), encode_record(), episode_prefix_lengths(), render_options(), serialize_state()

### Community 33 - "Sub-Task Planner"
Cohesion: 0.31
Nodes (4): decompose(), test_planner_default_vector(), test_planner_multi_part(), test_planner_sql_keyword_routes_sql()

### Community 34 - "RLAgent Inference Core"
Cohesion: 0.25
Nodes (3): RLAgent, confidence_from_probs(), temp_bucket()

### Community 35 - "End-to-End Tests"
Cohesion: 0.33
Nodes (6): call(), server(), test_deep_path_budget_exhaustion_marks_low_confidence(), test_deep_path_multi_tool_trace(), test_full_flow_ingest_and_ask(), test_incremental_add_update_delete()

### Community 36 - "Ask Contract Tests"
Cohesion: 0.32
Nodes (4): call(), server(), test_all_fields_present_on_every_response(), test_decision_invariants_on_both_provenances()

### Community 37 - "Test Fixtures & Pins"
Cohesion: 0.29
Nodes (6): broken.pdf fixture (corrupt file, skip-with-reason path), Test fixture corpus (PDF/DOCX/XLSX/PPTX/SQLite/audio), notes.sqlite3 fixture (SQLite source connector), audio/silence.wav fixture (no-speech path), faster-whisper local audio transcription, FR-002: Ingest rows/records from a configured SQLite database

### Community 38 - "System 2 Design Docs"
Cohesion: 0.29
Nodes (5): Scenario 3 - Multi-source deep research (P2), FR-013: Sub-task decomposition and tool routing, FR-014: Sufficiency evaluation with bounded iteration budget, FR-015: ReAct (Reason + Act) loop with LLM during deliberative research, US3: Deep research on complex questions (P2)

### Community 39 - "Reflexion Conditioning Tests"
Cohesion: 0.32
Nodes (4): call(), server(), test_live_web_route_leads_with_web_tools(), test_multi_part_question_covers_all_parts_with_reflections()

### Community 40 - "Success Criteria Suite"
Cohesion: 0.36
Nodes (4): call(), server(), test_sc001_002_003_over_100_questions(), test_sc005_budget_exhausted_always_flagged_low()

### Community 44 - "SQLite Source Connector"
Cohesion: 0.60
Nodes (3): NotFoundError, sources_add(), SqliteSource

### Community 48 - "Graphify Layer Docs"
Cohesion: 0.50
Nodes (3): MCP tool: graph.query (Graphify layer), Graphify optional graph-search layer, FR-010: Optional graph-based semantic search layer

### Community 49 - "Indexing Skill Config"
Cohesion: 0.67
Nodes (3): CocoIndex Code Settings, graphify Command, graphify Skill

## Knowledge Gaps
- **19 isolated node(s):** `common.sh script`, `agentic-rag-mcp`, `CocoIndex Code Settings`, `graphify Command`, `GitHub MCP Server` (+14 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 267 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_server()` connect `MCP Server Construction` to `Web Search Provider Adapters`, `System 1 Decision Node`, `Content Dedup Pipeline`, `Ask Contract Tests`, `End-to-End Tests`, `Reflexion Conditioning Tests`, `Graphify Search Layer`, `Agent Tool Factories`, `Success Criteria Suite`, `SQLite Source Connector`, `Reflexion Graph Tests`, `Source Sync & Watchers`, `HTTP/SSE Entry Scripts`, `Fallback Provenance Tests`, `Vector Store Chunking`, `Ingestion Pipeline`, `Decision Routing Tests`, `MCP Contract Tests`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `ReflexionAgent` connect `Reflexion Graph Tests` to `Error Taxonomy`, `Reflexion Graph Core`, `Agent Tool Factories`, `Episodic Memory`, `MCP Server Construction`, `Reflexion Honesty Tests`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `StateStore` connect `Content Dedup Pipeline` to `Agent Tool Factories`, `MCP Server Construction`, `Source Sync & Watchers`, `Web Search Provider Adapters`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `build_server()` (e.g. with `Config` and `_fetch_url()`) actually correct?**
  _`build_server()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `ProviderError` (e.g. with `GraphifySearch` and `build_providers()`) actually correct?**
  _`ProviderError` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `Config` (e.g. with `decide()` and `get_agent()`) actually correct?**
  _`Config` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `StateStore` (e.g. with `test_cross_source_duplicate_collapses()` and `test_expired_credential_marks_source_degraded()`) actually correct?**
  _`StateStore` has 6 INFERRED edges - model-reasoned connections that need verification._