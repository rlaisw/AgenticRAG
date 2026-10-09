# Graph Report - AgenticRAG  (2026-10-09)

## Corpus Check
- 39 files · ~107,585 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1076 nodes · 1999 edges · 78 communities (41 shown, 37 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 172 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Spec-Kit Python Utilities
- Spec 002 Contracts & Checklists
- System 1 Decision Node
- System 2 Reflexion Graph
- Deployment Runbook & Skill
- SSRF Guard & Fetch
- Ingestion Dedup
- Web Research Pipeline (003)
- MCP Tool Surface
- Spec-Kit Shell Libraries
- Graph Connectors Auth
- Episodic Memory
- Graphify Search Layer
- Web Provider Chain
- HTTP/SSE Entry Scripts
- Error Taxonomy
- Rule-Based Evaluator
- Fallback Provenance Tests
- Web Research Integration Tests
- Spec-Kit PowerShell Helpers
- Spec-003 Research Decisions D1-D8
- Vector Store Chunking
- Laya Training Metrics
- SQL Tool
- Speckit Slash Commands
- Speckit Workflow Commands
- Document Parsers
- Source Watchers
- Web Research Contract Tests
- Dify Sidecar Server
- Content Dedup Pipeline
- Laya Model Metrics
- Decision Routing Tests
- Integration Fixture Server
- Shared Test Fixtures
- Laya Inference API
- Local Folder Source
- Spec-Kit Templates
- MCP Contract Tests
- Success Criteria Suite
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70

## God Nodes (most connected - your core abstractions)
1. `build_server()` - 39 edges
2. `Config` - 24 edges
3. `StateStore` - 24 edges
4. `resolve_template_content()` - 20 edges
5. `ProviderError` - 18 edges
6. `TemplateResolutionError` - 17 edges
7. `Agentic RAG MCP Server` - 17 edges
8. `GraphifySearch` - 15 edges
9. `main()` - 15 edges
10. `SourceAuthError` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Port Convention (host 28080 sidecar, 28888 SearXNG, container 8080)` --semantically_similar_to--> `Port Convention (NETWORK.md)`  [INFERRED] [semantically similar]
  DEPLOY.md → docs/NETWORK.md
- `test_network_error_is_provider_error()` --uses--> `ProviderError`  [INFERRED]
  tests/contract/test_graph_connectors.py → src/agentic_rag_mcp/errors.py
- `test_exa_timeout_raises_provider_error()` --uses--> `ProviderError`  [INFERRED]
  tests/contract/test_web_providers.py → src/agentic_rag_mcp/errors.py
- `test_unconfigured_provider_raises()` --uses--> `ProviderError`  [INFERRED]
  tests/contract/test_web_providers.py → src/agentic_rag_mcp/errors.py
- `test_codes()` --uses--> `ProviderError`  [INFERRED]
  tests/unit/test_errors.py → src/agentic_rag_mcp/errors.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Dual-System Request Flow: System 1 decision → FR-005 route mapping → execution path → ask response contract** — specs_002_laya_reflexion_nodes_spec_system_1_decision_node, specs_002_laya_reflexion_nodes_spec_fr005_route_mapping, specs_002_laya_reflexion_nodes_spec_system_2_reflexion_graph, specs_002_laya_reflexion_nodes_contracts_ask_response_ask_tool_contract [EXTRACTED 1.00]
- **Supersedes Replacement Scope: OLD components → NEW dual-system design** — specs_002_laya_reflexion_nodes_spec_single_label_classifier, specs_002_laya_reflexion_nodes_spec_keyword_heuristic_fallback, specs_002_laya_reflexion_nodes_spec_monolithic_deliberation_loop, specs_002_laya_reflexion_nodes_spec_hit_count_sufficiency_gate, specs_002_laya_reflexion_nodes_spec_system_1_decision_node, specs_002_laya_reflexion_nodes_spec_system_2_reflexion_graph, specs_002_laya_reflexion_nodes_spec_evaluator_stage [EXTRACTED 1.00]
- **System 2 Reflexion Loop: Actor → Evaluator → Self-Reflector → Episodic Memory** — specs_002_laya_reflexion_nodes_spec_actor_stage, specs_002_laya_reflexion_nodes_spec_evaluator_stage, specs_002_laya_reflexion_nodes_spec_self_reflector_stage, specs_002_laya_reflexion_nodes_data_model_episodicmemory, specs_002_laya_reflexion_nodes_spec_system_2_reflexion_graph [EXTRACTED 1.00]
- **Incremental ingestion pipeline (CocoIndex change detection into LanceDB chunks with dedup by content hash)** — specs_001_agentic_rag_mcp_plan_cocoindex_pipeline, specs_001_agentic_rag_mcp_plan_lancedb_vector_store, specs_001_agentic_rag_mcp_data_model_document, specs_001_agentic_rag_mcp_data_model_chunk, specs_001_agentic_rag_mcp_data_model_source [INFERRED 0.95]
- **System 1/System 2 question routing (Laya decision layer steering between fast retrieval and the LangGraph deliberative loop)** — specs_001_agentic_rag_mcp_research_d5_laya_routing, specs_001_agentic_rag_mcp_plan_langgraph_deliberative_loop [INFERRED 0.95]

## Communities (78 total, 37 thin omitted)

### Community 0 - "Spec-Kit Python Utilities"
Cohesion: 0.06
Nodes (60): Args, _available_docs(), _check_dir(), _check_file(), _dir_has_entries(), _json_line(), main(), _parse_args() (+52 more)

### Community 1 - "Spec 002 Contracts & Checklists"
Cohesion: 0.07
Nodes (41): Specification Quality Checklist: Dual-System Workflow, ask MCP Tool Response Contract (preserved fields + decision/reflections extensions), Pre-existing Contract Test Suite (tests/contract/), Dify Chatflow (client consumer of the ask tool), Contract: ask Tool Response, decide(question) → DecisionResult (System 1 decision node operation), Decision Primitives: choice, score, noul (one-pass three-question batch), Contract: System 1 Decision Schema (+33 more)

### Community 2 - "System 1 Decision Node"
Cohesion: 0.06
Nodes (27): Config, decide(), DecisionResult, fallback_route(), map_model_output(), _questions(), _test_cfg(), validate_output() (+19 more)

### Community 3 - "System 2 Reflexion Graph"
Cohesion: 0.06
Nodes (22): _actor(), _after_evaluator(), _after_memory(), _build_graph(), _evaluator(), _memory_node(), ReflexionAgent, _self_reflector() (+14 more)

### Community 4 - "Deployment Runbook & Skill"
Cohesion: 0.06
Nodes (49): agenticrag-deploy Skill, Deploy Steps 0-7, Port Convention (host 28080 sidecar, 28888 SearXNG, container 8080), Fresh-Host Deployment Runbook, SearXNG Service, SSRF Allowlist Step (SSRF_PROXY_ALLOW_PRIVATE_DOMAINS=agentic-rag), 5-Minute Verification Battery, Agentic Strategy Node (FunctionCalling) (+41 more)

### Community 5 - "SSRF Guard & Fetch"
Cohesion: 0.06
Nodes (23): mcp_get(), _assert_public_host(), extract_sections(), guarded_get(), render_page(), research_page(), ScrapeBlocked, _html() (+15 more)

### Community 6 - "Ingestion Dedup"
Cohesion: 0.06
Nodes (14): _now(), StateStore, call(), server(), test_budget_exhaustion_low_confidence(), test_concurrent_queries_consistent(), test_corrupt_and_encrypted_files_skipped_not_blocking(), test_cross_source_duplicate_collapses() (+6 more)

### Community 7 - "Web Research Pipeline (003)"
Cohesion: 0.07
Nodes (25): search_all(), research_pages(), sections_to_text(), build_server(), ask(), degraded_sources(), fetch_url(), route_question() (+17 more)

### Community 8 - "MCP Tool Surface"
Cohesion: 0.11
Nodes (35): ask MCP Tool, fetch_url MCP Tool, graph.query MCP Tool (Graphify layer), MCP Tool Contracts: Agentic RAG MCP Server, search MCP Tool, sources.list/add/remove/sync MCP Tools, Agentic RAG MCP Server Feature Specification, FR-008: MCP Server over stdio (+27 more)

### Community 9 - "Spec-Kit Shell Libraries"
Cohesion: 0.13
Nodes (29): check-prerequisites.sh script, check_dir(), check_file(), find_specify_root(), format_speckit_command(), get_current_branch(), get_feature_paths(), get_invoke_separator() (+21 more)

### Community 10 - "Graph Connectors Auth"
Cohesion: 0.11
Nodes (11): SourceAuthError, GraphAuth, GraphBase, OneDriveSource, SharePointSource, ExpiredAuth, FakeAuth, test_expired_token_propagates() (+3 more)

### Community 11 - "Episodic Memory"
Cohesion: 0.13
Nodes (9): EpisodicMemory, ReflectionRecord, _rec(), test_append_ordering_preserved(), test_memory_starts_empty_per_request(), test_no_cross_request_leakage(), test_record_serializes_all_fields(), test_union_deduplicates_terms_in_first_appearance_order() (+1 more)

### Community 12 - "Graphify Search Layer"
Cohesion: 0.13
Nodes (7): FeatureDisabledError, GraphifySearch, test_cli_failure_is_provider_error(), test_disabled_by_default(), test_enabled_but_graph_missing(), test_explain_shells_out(), test_stats_reads_graph()

### Community 13 - "Web Provider Chain"
Cohesion: 0.13
Nodes (8): build_providers(), ExaProvider, SearxngProvider, TavilyProvider, test_exa_timeout_raises_provider_error(), test_searxng_respects_limit(), test_tavily_normalizes_results(), test_unconfigured_provider_raises()

### Community 14 - "HTTP/SSE Entry Scripts"
Cohesion: 0.13
Nodes (4): _get(), init_config(), load_config(), main()

### Community 15 - "Error Taxonomy"
Cohesion: 0.16
Nodes (10): DecisionLayerUnavailable, Err, ErrorCode, IngestionError, Ok, RagError, SufficiencyExhausted, wrap() (+2 more)

### Community 16 - "Rule-Based Evaluator"
Cohesion: 0.20
Nodes (9): evaluate(), _terms(), _ev(), test_full_coverage_with_citations_passes_with_high_score(), test_hit_count_is_scoring_input_not_verdict_gate(), test_identical_inputs_identical_outputs(), test_no_citable_evidence_caps_score_and_fails(), test_partial_coverage_fails_and_names_missing_terms() (+1 more)

### Community 17 - "Fallback Provenance Tests"
Cohesion: 0.18
Nodes (9): call(), _live_cfg(), _median(), server(), test_fallback_latency_within_budget(), test_no_third_provenance_value(), test_outage_routes_via_fallback_and_marks_it(), test_recovery_next_request_uses_decision_node() (+1 more)

### Community 18 - "Web Research Integration Tests"
Cohesion: 0.24
Nodes (10): call(), FakeProvider, _hits_by_url(), _server(), test_ask_live_web_evidence_uses_grouped_content(), test_every_hit_yields_content_mixed_paths(), test_forbidden_page_falls_back_marked_http_403(), test_normal_page_scraped_with_grouped_content() (+2 more)

### Community 19 - "Spec-Kit PowerShell Helpers"
Cohesion: 0.22
Nodes (10): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-Python3Command(), Get-RepoRoot(), Resolve-SpecifyInitDir() (+2 more)

### Community 20 - "Spec-003 Research Decisions D1-D8"
Cohesion: 0.16
Nodes (14): D1: HTTP client — reuse httpx, D2: HTML parsing — beautifulsoup4 + lxml (the only new dependencies), D3: Parallel page fetching — bounded thread pool, D4: SSRF guard — per-hop address resolution + ipaddress check, D5: Grouping rules — reference algorithm + spec bounds, D8: Configuration surface — [web.research] block in config.toml, FR-005: Document-order grouped section extraction, FR-008: Honest snippet fallback — never silently missing, never fabricated (+6 more)

### Community 22 - "Laya Training Metrics"
Cohesion: 0.18
Nodes (3): encode_record(), episode_prefix_lengths(), pack_groups()

### Community 23 - "SQL Tool"
Cohesion: 0.19
Nodes (5): make_sql_tool(), make_vector_tool(), test_sql_tool_no_text_column(), test_sql_tool_reads_rows(), test_watcher_sync_once_local()

### Community 24 - "Speckit Slash Commands"
Cohesion: 0.50
Nodes (12): speckit.analyze Command, speckit.checklist Command, speckit.clarify Command, speckit.constitution Command, Project Constitution, speckit.converge Command, speckit.implement Command, speckit.plan Command (+4 more)

### Community 25 - "Speckit Workflow Commands"
Cohesion: 0.32
Nodes (12): Speckit Analyze Workflow, Speckit Checklist Workflow, Speckit Clarify Workflow, Speckit Constitution Workflow, Speckit Converge Workflow, Speckit Implement Workflow, Speckit Plan Workflow, Speckit Specify Workflow (+4 more)

### Community 26 - "Document Parsers"
Cohesion: 0.45
Nodes (8): _extract_docx(), _extract_pdf(), _extract_pptx(), extract_text(), _extract_xlsx(), media_type_for(), ParseSkipped, transcribe()

### Community 27 - "Source Watchers"
Cohesion: 0.21
Nodes (3): Watcher, loop(), SqliteSource

### Community 28 - "Web Research Contract Tests"
Cohesion: 0.35
Nodes (7): call(), FakeProvider, _server(), test_web_research_all_engines_down_honest_empty(), test_web_research_limit_capped_at_max_pages(), test_web_research_schema_v2(), test_web_search_stays_byte_identical_without_engine_field()

### Community 31 - "Laya Model Metrics"
Cohesion: 0.18
Nodes (6): aurc(), auroc(), confidence_from_probs(), ece_score(), make_token_batches(), spearman()

### Community 32 - "Decision Routing Tests"
Cohesion: 0.29
Nodes (7): call(), direct_output(), server(), test_decision_contains_only_structured_values(), test_direct_route_served_in_one_step(), test_forced_mode_still_records_decision(), test_source_management_route_gives_guidance_without_operations()

### Community 34 - "Shared Test Fixtures"
Cohesion: 0.24
Nodes (4): corpus(), call(), test_all_fields_present_on_every_response(), test_decision_invariants_on_both_provenances()

### Community 35 - "Laya Inference API"
Cohesion: 0.24
Nodes (4): RLAgent, build_sequence(), render_options(), serialize_state()

### Community 37 - "Spec-Kit Templates"
Cohesion: 0.36
Nodes (7): Spec-kit plan template, Spec-kit task list template, Data Model: Agentic RAG MCP Server, Implementation Plan: Agentic RAG MCP Server, Quickstart: Agentic RAG MCP Server (validation scenarios), Research: Agentic RAG MCP Server (15 decisions), Tasks: Agentic RAG MCP Server (T001-T050)

### Community 38 - "MCP Contract Tests"
Cohesion: 0.43
Nodes (6): call(), test_ask_no_documents_returns_no_fabrication(), test_bad_source_type_raises_not_found(), test_graph_query_disabled_by_default(), test_status_shape(), test_unknown_source_remove_is_graceful()

### Community 39 - "Success Criteria Suite"
Cohesion: 0.36
Nodes (4): call(), server(), test_sc001_002_003_over_100_questions(), test_sc005_budget_exhausted_always_flagged_low()

### Community 41 - "Community 41"
Cohesion: 0.29
Nodes (3): amp_dtype(), collate_items(), predict_items()

### Community 44 - "Community 44"
Cohesion: 0.29
Nodes (6): broken.pdf fixture (corrupt file, skip-with-reason path), Test fixture corpus (PDF/DOCX/XLSX/PPTX/SQLite/audio), notes.sqlite3 fixture (SQLite source connector), audio/silence.wav fixture (no-speech path), faster-whisper local audio transcription, Scenario 5 - Error handling assertions

### Community 45 - "Community 45"
Cohesion: 0.43
Nodes (6): make_web_tool(), ProviderError, test_web_tool_all_down_returns_empty(), search(), test_web_tool_fallback_order(), search()

### Community 46 - "Community 46"
Cohesion: 0.48
Nodes (5): call(), test_deep_path_budget_exhaustion_marks_low_confidence(), test_deep_path_multi_tool_trace(), test_full_flow_ingest_and_ask(), test_incremental_add_update_delete()

### Community 48 - "Community 48"
Cohesion: 0.47
Nodes (3): call(), test_live_web_route_leads_with_web_tools(), test_multi_part_question_covers_all_parts_with_reflections()

### Community 53 - "Community 53"
Cohesion: 0.67
Nodes (3): CocoIndex Code Settings, graphify Command, graphify Skill

## Knowledge Gaps
- **48 isolated node(s):** `common.sh script`, `Question session entity (deliberative trace)`, `SubTask entity (per-tool provenance unit)`, `Scenario 4 - Web search fallback (P3)`, `routing/fallback.py (DEMOTED: keyword heuristic, outage-only)` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 357 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `StateStore` connect `Ingestion Dedup` to `Web Research Pipeline (003)`, `HTTP/SSE Entry Scripts`, `Community 47`, `Community 49`, `SQL Tool`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `ReflexionAgent` connect `System 2 Reflexion Graph` to `HTTP/SSE Entry Scripts`, `Web Research Pipeline (003)`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `VectorStore` connect `Vector Store Chunking` to `SQL Tool`, `Community 47`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `build_server()` (e.g. with `Config` and `_web_evidence()`) actually correct?**
  _`build_server()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `Config` (e.g. with `decide()` and `get_agent()`) actually correct?**
  _`Config` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `StateStore` (e.g. with `test_cross_source_duplicate_collapses()` and `test_expired_credential_marks_source_degraded()`) actually correct?**
  _`StateStore` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `common.sh script`, `Question session entity (deliberative trace)`, `SubTask entity (per-tool provenance unit)` to the rest of the system?**
  _48 weakly-connected nodes found - possible documentation gaps or missing edges._