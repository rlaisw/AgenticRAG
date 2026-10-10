# Graph Report - AgenticRAG  (2026-10-10)

## Corpus Check
- 30 files · ~120,034 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1134 nodes · 2068 edges · 87 communities (48 shown, 39 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 170 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 54
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77

## God Nodes (most connected - your core abstractions)
1. `build_server()` - 39 edges
2. `Config` - 26 edges
3. `StateStore` - 22 edges
4. `resolve_template_content()` - 20 edges
5. `ProviderError` - 18 edges
6. `TemplateResolutionError` - 17 edges
7. `GraphifySearch` - 15 edges
8. `main()` - 15 edges
9. `SourceAuthError` - 14 edges
10. `get_feature_paths()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Dify Sidecar Server (aligned port 28080)` --implements--> `FR-001: Sidecar listens on 28080`  [EXTRACTED]
  dify/docker/mcp-server/server.py → specs/004-port-alignment/spec.md
- `test_codes()` --uses--> `SourceAuthError`  [INFERRED]
  tests/unit/test_errors.py → src/agentic_rag_mcp/errors.py
- `test_memory_starts_empty_per_request()` --uses--> `EpisodicMemory`  [INFERRED]
  tests/unit/test_memory.py → src/agentic_rag_mcp/agents/memory.py
- `test_explain_shells_out()` --uses--> `GraphifySearch`  [INFERRED]
  tests/unit/test_graphify_search.py → src/agentic_rag_mcp/search/graphify_search.py
- `test_stats_reads_graph()` --uses--> `GraphifySearch`  [INFERRED]
  tests/unit/test_graphify_search.py → src/agentic_rag_mcp/search/graphify_search.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Dual-System Request Flow: System 1 decision → FR-005 route mapping → execution path → ask response contract** — specs_002_laya_reflexion_nodes_spec_system_1_decision_node, specs_002_laya_reflexion_nodes_spec_fr005_route_mapping, specs_002_laya_reflexion_nodes_spec_system_2_reflexion_graph, specs_002_laya_reflexion_nodes_contracts_ask_response_ask_tool_contract [EXTRACTED 1.00]
- **Supersedes Replacement Scope: OLD components → NEW dual-system design** — specs_002_laya_reflexion_nodes_spec_single_label_classifier, specs_002_laya_reflexion_nodes_spec_keyword_heuristic_fallback, specs_002_laya_reflexion_nodes_spec_monolithic_deliberation_loop, specs_002_laya_reflexion_nodes_spec_hit_count_sufficiency_gate, specs_002_laya_reflexion_nodes_spec_system_1_decision_node, specs_002_laya_reflexion_nodes_spec_system_2_reflexion_graph, specs_002_laya_reflexion_nodes_spec_evaluator_stage [EXTRACTED 1.00]
- **System 2 Reflexion Loop: Actor → Evaluator → Self-Reflector → Episodic Memory** — specs_002_laya_reflexion_nodes_spec_actor_stage, specs_002_laya_reflexion_nodes_spec_evaluator_stage, specs_002_laya_reflexion_nodes_spec_self_reflector_stage, specs_002_laya_reflexion_nodes_data_model_episodicmemory, specs_002_laya_reflexion_nodes_spec_system_2_reflexion_graph [EXTRACTED 1.00]
- **Incremental ingestion pipeline (CocoIndex change detection into LanceDB chunks with dedup by content hash)** — specs_001_agentic_rag_mcp_plan_cocoindex_pipeline, specs_001_agentic_rag_mcp_plan_lancedb_vector_store, specs_001_agentic_rag_mcp_data_model_document, specs_001_agentic_rag_mcp_data_model_chunk, specs_001_agentic_rag_mcp_data_model_source [INFERRED 0.95]
- **System 1/System 2 question routing (Laya decision layer steering between fast retrieval and the LangGraph deliberative loop)** — specs_001_agentic_rag_mcp_research_d5_laya_routing, specs_001_agentic_rag_mcp_plan_langgraph_deliberative_loop [INFERRED 0.95]

## Communities (87 total, 39 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (60): Args, _available_docs(), _check_dir(), _check_file(), _dir_has_entries(), _json_line(), main(), _parse_args() (+52 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (33): make_web_tool(), DecisionLayerUnavailable, Err, ErrorCode, FeatureDisabledError, IngestionError, NotFoundError, Ok (+25 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (41): Specification Quality Checklist: Dual-System Workflow, ask MCP Tool Response Contract (preserved fields + decision/reflections extensions), Pre-existing Contract Test Suite (tests/contract/), Dify Chatflow (client consumer of the ask tool), Contract: ask Tool Response, decide(question) → DecisionResult (System 1 decision node operation), Decision Primitives: choice, score, noul (one-pass three-question batch), Contract: System 1 Decision Schema (+33 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (22): _actor(), _after_evaluator(), _after_memory(), _build_graph(), _evaluator(), _memory_node(), ReflexionAgent, _self_reflector() (+14 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (24): _assert_public_host(), extract_sections(), guarded_get(), render_page(), research_page(), research_pages(), ScrapeBlocked, sections_to_text() (+16 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (14): _now(), StateStore, call(), server(), test_budget_exhaustion_low_confidence(), test_concurrent_queries_consistent(), test_corrupt_and_encrypted_files_skipped_not_blocking(), test_cross_source_duplicate_collapses() (+6 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (35): ask MCP Tool, fetch_url MCP Tool, graph.query MCP Tool (Graphify layer), MCP Tool Contracts: Agentic RAG MCP Server, search MCP Tool, sources.list/add/remove/sync MCP Tools, Agentic RAG MCP Server Feature Specification, FR-008: MCP Server over stdio (+27 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (17): build_providers(), ExaProvider, search_all(), SearxngProvider, TavilyProvider, test_exa_timeout_raises_provider_error(), test_searxng_respects_limit(), test_tavily_normalizes_results() (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (29): check-prerequisites.sh script, check_dir(), check_file(), find_specify_root(), format_speckit_command(), get_current_branch(), get_feature_paths(), get_invoke_separator() (+21 more)

### Community 9 - "Community 9"
Cohesion: 0.11
Nodes (11): SourceAuthError, GraphAuth, GraphBase, OneDriveSource, SharePointSource, ExpiredAuth, FakeAuth, test_expired_token_propagates() (+3 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (9): EpisodicMemory, ReflectionRecord, _rec(), test_append_ordering_preserved(), test_memory_starts_empty_per_request(), test_no_cross_request_leakage(), test_record_serializes_all_fields(), test_union_deduplicates_terms_in_first_appearance_order() (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (11): evaluate(), _terms(), content_hash(), normalize(), _ev(), test_full_coverage_with_citations_passes_with_high_score(), test_hit_count_is_scoring_input_not_verdict_gate(), test_identical_inputs_identical_outputs() (+3 more)

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (4): _get(), init_config(), load_config(), main()

### Community 13 - "Community 13"
Cohesion: 0.13
Nodes (8): build_server(), ask(), degraded_sources(), fetch_url(), route_question(), sources_list(), status(), _fetch_url()

### Community 14 - "Community 14"
Cohesion: 0.14
Nodes (6): aurc(), auroc(), ece_score(), make_token_batches(), pack_groups(), spearman()

### Community 15 - "Community 15"
Cohesion: 0.18
Nodes (8): decide(), DecisionResult, fallback_route(), map_model_output(), _questions(), _test_cfg(), test_decider_timeout_yields_invalid(), test_malformed_model_output_yields_invalid()

### Community 16 - "Community 16"
Cohesion: 0.20
Nodes (8): call(), FakeProvider, _server(), test_case_insensitive_profile_lookup(), test_hot_reload_new_profile_immediately_usable(), test_missing_profiles_file_honest_error(), test_results_filtered_to_matching_domains(), test_zero_scoped_results_honest_empty()

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (12): Dify Chatflow with 13 MCP Tools, 13 MCP Tools, Dual-System Architecture, specialty_profiles MCP tool, specialty_search MCP tool, Specialty Search Tool Contract, ProfileFile (JSON, hot-reload), SpecialtyProfile entity (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.16
Nodes (10): construct_scoped_query(), filter_by_domains(), specialty_search(), profiles_file(), test_construct_scoped_query_multiple_sites(), test_construct_scoped_query_single_site(), test_filter_by_domains_empty_input(), test_filter_by_domains_no_matches() (+2 more)

### Community 19 - "Community 19"
Cohesion: 0.18
Nodes (9): call(), _live_cfg(), _median(), server(), test_fallback_latency_within_budget(), test_no_third_provenance_value(), test_outage_routes_via_fallback_and_marks_it(), test_recovery_next_request_uses_decision_node() (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.24
Nodes (10): call(), FakeProvider, _hits_by_url(), _server(), test_ask_live_web_evidence_uses_grouped_content(), test_every_hit_yields_content_mixed_paths(), test_forbidden_page_falls_back_marked_http_403(), test_normal_page_scraped_with_grouped_content() (+2 more)

### Community 22 - "Community 22"
Cohesion: 0.18
Nodes (3): RLAgent, confidence_from_probs(), temp_bucket()

### Community 23 - "Community 23"
Cohesion: 0.22
Nodes (10): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-Python3Command(), Get-RepoRoot(), Resolve-SpecifyInitDir() (+2 more)

### Community 24 - "Community 24"
Cohesion: 0.16
Nodes (14): D1: HTTP client — reuse httpx, D2: HTML parsing — beautifulsoup4 + lxml (the only new dependencies), D3: Parallel page fetching — bounded thread pool, D4: SSRF guard — per-hop address resolution + ipaddress check, D5: Grouping rules — reference algorithm + spec bounds, D8: Configuration surface — [web.research] block in config.toml, FR-005: Document-order grouped section extraction, FR-008: Honest snippet fallback — never silently missing, never fabricated (+6 more)

### Community 26 - "Community 26"
Cohesion: 0.19
Nodes (5): make_sql_tool(), make_vector_tool(), test_sql_tool_no_text_column(), test_sql_tool_reads_rows(), test_watcher_sync_once_local()

### Community 27 - "Community 27"
Cohesion: 0.22
Nodes (7): call(), FakeProvider, server(), test_existing_web_search_canary_unchanged(), test_specialty_profiles_returns_full_json(), test_specialty_search_invalid_profile_honest_error(), test_specialty_search_returns_only_matching_domains()

### Community 28 - "Community 28"
Cohesion: 0.30
Nodes (6): Config, get_agent(), _model_dir(), system_one(), _try_load(), warm_up()

### Community 29 - "Community 29"
Cohesion: 0.18
Nodes (9): AgenticRAG MCP sidecar (Dify compose service), Chunk entity (embedded segment, row in LanceDB), Document entity (canonical ingested item, deduplicated by content), OriginRef entity (one physical location of a Document), Source entity (connector config + health), CocoIndex [full] incremental pipeline, LanceDB embedded vector store, Local sentence-transformers embeddings (all-MiniLM-L6-v2) (+1 more)

### Community 30 - "Community 30"
Cohesion: 0.50
Nodes (12): speckit.analyze Command, speckit.checklist Command, speckit.clarify Command, speckit.constitution Command, Project Constitution, speckit.converge Command, speckit.implement Command, speckit.plan Command (+4 more)

### Community 31 - "Community 31"
Cohesion: 0.32
Nodes (12): Speckit Analyze Workflow, Speckit Checklist Workflow, Speckit Clarify Workflow, Speckit Constitution Workflow, Speckit Converge Workflow, Speckit Implement Workflow, Speckit Plan Workflow, Speckit Specify Workflow (+4 more)

### Community 32 - "Community 32"
Cohesion: 0.21
Nodes (3): Watcher, loop(), SqliteSource

### Community 33 - "Community 33"
Cohesion: 0.30
Nodes (8): validate_output(), _result(), test_complexity_must_be_integer(), test_complexity_out_of_range_is_invalid(), test_decider_mapping_from_model_output(), test_out_of_set_route_is_invalid(), test_provenance_only_two_values(), test_valid_result_passes()

### Community 34 - "Community 34"
Cohesion: 0.21
Nodes (9): _default_path(), load_profiles(), resolve_profile(), specialty_profiles(), test_load_profiles_malformed_json(), test_load_profiles_valid_file(), test_resolve_profile_case_insensitive(), test_resolve_profile_empty_sites_error() (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.35
Nodes (7): call(), FakeProvider, _server(), test_web_research_all_engines_down_honest_empty(), test_web_research_limit_capped_at_max_pages(), test_web_research_schema_v2(), test_web_search_stays_byte_identical_without_engine_field()

### Community 36 - "Community 36"
Cohesion: 0.29
Nodes (7): call(), direct_output(), server(), test_decision_contains_only_structured_values(), test_direct_route_served_in_one_step(), test_forced_mode_still_records_decision(), test_source_management_route_gives_guidance_without_operations()

### Community 37 - "Community 37"
Cohesion: 0.22
Nodes (9): Aligned Port Convention (28080:28080, 28888:28888), Sidecar Compose (28080:28080), Dify Sidecar Server (aligned port 28080), Network Topology (Dify ↔ AgenticRAG ↔ Host), PortSpec entity, Port Alignment Feature, FR-001: Sidecar listens on 28080, FR-003: Dify URL updated to :28080 (+1 more)

### Community 39 - "Community 39"
Cohesion: 0.31
Nodes (7): call(), server(), test_ask_no_documents_returns_no_fabrication(), test_bad_source_type_raises_not_found(), test_graph_query_disabled_by_default(), test_status_shape(), test_unknown_source_remove_is_graceful()

### Community 41 - "Community 41"
Cohesion: 0.25
Nodes (5): build_sequence(), encode_record(), episode_prefix_lengths(), render_options(), serialize_state()

### Community 42 - "Community 42"
Cohesion: 0.33
Nodes (6): call(), server(), test_deep_path_budget_exhaustion_marks_low_confidence(), test_deep_path_multi_tool_trace(), test_full_flow_ingest_and_ask(), test_incremental_add_update_delete()

### Community 43 - "Community 43"
Cohesion: 0.36
Nodes (7): Spec-kit plan template, Spec-kit task list template, Data Model: Agentic RAG MCP Server, Implementation Plan: Agentic RAG MCP Server, Quickstart: Agentic RAG MCP Server (validation scenarios), Research: Agentic RAG MCP Server (15 decisions), Tasks: Agentic RAG MCP Server (T001-T050)

### Community 44 - "Community 44"
Cohesion: 0.36
Nodes (4): heuristic_classify(), test_default_is_deliberative(), test_multi_part_question_deliberative(), test_simple_question_fast()

### Community 45 - "Community 45"
Cohesion: 0.32
Nodes (4): call(), server(), test_live_web_route_leads_with_web_tools(), test_multi_part_question_covers_all_parts_with_reflections()

### Community 46 - "Community 46"
Cohesion: 0.36
Nodes (4): call(), server(), test_sc001_002_003_over_100_questions(), test_sc005_budget_exhausted_always_flagged_low()

### Community 47 - "Community 47"
Cohesion: 0.29
Nodes (3): amp_dtype(), collate_items(), predict_items()

### Community 50 - "Community 50"
Cohesion: 0.29
Nodes (7): AgenticRAG Constitution, Contract Preservation (Principle I), Honest Answers (Principle IV), Minimal Dependencies (Principle III), Spec-Driven Replacement (Principle V), Tests-First (Principle II), Speckit Full SDD Cycle (specify - plan - tasks - implement)

### Community 51 - "Community 51"
Cohesion: 0.29
Nodes (6): broken.pdf fixture (corrupt file, skip-with-reason path), Test fixture corpus (PDF/DOCX/XLSX/PPTX/SQLite/audio), notes.sqlite3 fixture (SQLite source connector), audio/silence.wav fixture (no-speech path), faster-whisper local audio transcription, Scenario 5 - Error handling assertions

### Community 52 - "Community 52"
Cohesion: 0.38
Nodes (4): call(), server(), test_all_fields_present_on_every_response(), test_decision_invariants_on_both_provenances()

### Community 60 - "Community 60"
Cohesion: 0.67
Nodes (3): CocoIndex Code Settings, graphify Command, graphify Skill

## Knowledge Gaps
- **56 isolated node(s):** `agentic-rag-mcp`, `common.sh script`, `routing/fallback.py (DEMOTED: keyword heuristic, outage-only)`, `Pre-existing Contract Test Suite (tests/contract/)`, `Dify Chatflow (client consumer of the ask tool)` (+51 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 394 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `StateStore` connect `Community 5` to `Community 26`, `Community 54`, `Community 55`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `Config` connect `Community 28` to `Community 35`, `Community 36`, `Community 5`, `Community 39`, `Community 42`, `Community 12`, `Community 13`, `Community 45`, `Community 15`, `Community 16`, `Community 46`, `Community 19`, `Community 52`, `Community 20`, `Community 27`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `build_server()` (e.g. with `Config` and `_web_evidence()`) actually correct?**
  _`build_server()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `Config` (e.g. with `decide()` and `get_agent()`) actually correct?**
  _`Config` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `StateStore` (e.g. with `test_cross_source_duplicate_collapses()` and `test_expired_credential_marks_source_degraded()`) actually correct?**
  _`StateStore` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `agentic-rag-mcp`, `common.sh script`, `routing/fallback.py (DEMOTED: keyword heuristic, outage-only)` to the rest of the system?**
  _56 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05717852684144819 - nodes in this community are weakly interconnected._