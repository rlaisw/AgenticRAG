"""FastMCP stdio server: ask, search, sources.*, status, graph.query."""

from __future__ import annotations

import argparse
import logging
import uuid
from pathlib import Path

import httpx

from mcp.server.fastmcp import FastMCP

from .agents import synthesis
from .agents.reflexion import ReflexionAgent
from .agents.tools import make_sql_tool, make_vector_tool, make_web_tool
from .config import Config, init_config, load_config
from .errors import FeatureDisabledError, NotFoundError, RagError
from .ingestion.pipeline import IngestionPipeline
from .ingestion.watchers import Watcher
from .routing import decision as decision_mod
from .search.embeddings import Embedder
from .search.graphify_search import GraphifySearch
from .search.web.base import build_providers, search_all
from .sources.sqlite_source import SqliteSource
from .store.state import StateStore
from .store.vectordb import VectorStore

log = logging.getLogger("agentic_rag_mcp")


def _fetch_url(url: str, max_chars: int = 4000) -> dict:
    """Fetch a live web page (httpx). Shared by the MCP tool and the deep loop."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must be http(s)")
    resp = httpx.get(url, timeout=20.0, follow_redirects=True,
                     headers={"User-Agent": "agentic-rag-mcp/0.1"})
    return {
        "url": str(resp.url),
        "status": resp.status_code,
        "date_utc": resp.headers.get("date", ""),
        "text": resp.text[:max_chars],
    }


def build_server(cfg: Config | None = None, **fastmcp_kwargs) -> FastMCP:
    """Build the MCP server. `fastmcp_kwargs` override FastMCP settings
    (e.g. stateless_http=True for Dify's streamable-HTTP client)."""
    cfg = cfg or load_config()
    state = StateStore(cfg.state_db)
    vectors = VectorStore(cfg.vector_dir)
    embedder = Embedder(cfg.embedding_model, cfg.embedding_device)
    pipeline = IngestionPipeline(state, vectors, embedder)
    watcher = Watcher(pipeline, state)
    watcher.start()

    web_providers = build_providers(cfg)
    graphify = GraphifySearch(Path("graphify-out/graph.json"), enabled=cfg.graphify_enabled)

    def _web_evidence(query: str, limit: int = 3) -> list[dict]:
        """FR-012: grouped web content as reflexion evidence (internal shape) —
        the snippet field carries the bounded, grouped page text so synthesis
        and citations consume it unchanged; document_id = url for citations."""
        from .search.web.research import render_page, research_pages, sections_to_text

        hits, _, _ = search_all(web_providers, query, limit)
        scrapes = research_pages(
            hits, t0=__import__("time").perf_counter(),
            fetch_timeout_s=cfg.research_fetch_timeout_s,
            per_page_chars=cfg.research_per_page_chars,
            overall_timeout_s=cfg.research_overall_timeout_s,
            max_concurrent=cfg.research_max_concurrent,
        )
        out = []
        for h in hits:
            scrape = scrapes.get(h["url"])
            content = (sections_to_text(scrape["sections"])
                       if scrape and scrape["status"] == "ok" and scrape["sections"]
                       else h["snippet"])
            if content:
                out.append({"title": h["title"], "url": h["url"], "snippet": content,
                            "document_id": h["url"]})
        return out

    agent_tools = {
        "vector_search": make_vector_tool(vectors, embedder),
        "web_search": _web_evidence,
        "fetch_url": _fetch_url,
    }
    if cfg.graphify_enabled:
        agent_tools["graphify"] = lambda q, limit=5: [
            {"content": graphify.explain(q)["answer"], "title": f"graph:{q}",
             "document_id": f"graphify:{q}"}
        ]
    agent = ReflexionAgent(agent_tools, cfg.max_iterations)

    fastmcp_kwargs.setdefault("host", cfg.mcp_host)
    fastmcp_kwargs.setdefault("port", cfg.mcp_port)
    mcp = FastMCP("agentic-rag-mcp", **fastmcp_kwargs)
    mcp._cfg = cfg  # live config handle for tests/ops (recovery toggles, status probes)
    if cfg.decider_enabled:
        from .routing import laya_runtime

        laya_runtime.warm_up(cfg)  # pre-load the decision model in the background

    def degraded_sources() -> list[str]:
        return [s["id"] for s in state.list_sources() if s["health"] != "healthy"]

    def route_question(question: str):
        """FR-001/FR-003: the decision node is primary; keyword heuristic only on outage."""
        if cfg.decider_enabled:
            d = decision_mod.decide(question, cfg)
            if d.valid:
                return d
        return decision_mod.fallback_route(question)

    @mcp.tool()
    def ask(question: str, collections: list[str] | None = None, mode: str = "auto",
            max_iterations: int | None = None) -> dict:
        """Answer a question with agentic retrieval and per-source citations."""
        request_id = uuid.uuid4().hex[:8]
        log.info("ask[%s]: %s", request_id, question[:120])
        d = route_question(question)
        # forced modes override execution, not the decision itself (FR-001: every request decided)
        if mode == "fast":
            exec_route, classifier = "direct_retrieval", "forced"
        elif mode == "deep":
            exec_route, classifier = "deliberative_reasoning", "forced"
        else:
            exec_route = d.route
            classifier = d.provenance  # "decision_node" | "fallback"
        agent._budget = max_iterations or cfg.max_iterations
        if exec_route in ("direct_retrieval", "source_management"):
            if exec_route == "source_management":
                # FR-005: guidance only, never operations. Misroute safety: a strong KB
                # match (Lance distance <= 1.0; measured 0.7 real vs 1.9 fuzzy) means
                # this was actually a knowledge question — answer it from the KB.
                hits = make_vector_tool(vectors, embedder)(question)
                if hits and hits[0].get("score", 99) <= 1.0:
                    answer = synthesis.synthesize(question, hits, "normal")
                    citations = synthesis.citations(hits)
                else:
                    answer = ("This looks like a source-management request. Use the sources_list, "
                              "sources_add, sources_sync, or sources_remove tools to manage the "
                              "knowledge base — they perform the actual operations.")
                    citations = []
            else:
                hits = make_vector_tool(vectors, embedder)(question)
                if hits:
                    answer = synthesis.synthesize(question, hits, "normal")
                    citations = synthesis.citations(hits)
                else:
                    answer = "No relevant information was found in the available sources."
                    citations = []
            if exec_route == "source_management":
                suff, plan = "satisfied", []
            else:
                suff = "satisfied" if hits else "exhausted"
                plan = [{"id": "t1", "tool": "vector_search", "input": question}]
            result = {
                "answer": answer, "confidence": "normal", "classification": "fast",
                "classifier": classifier, "citations": citations, "iterations": 0,
                "sufficiency": suff, "error": None, "plan": plan, "reflections": [],
                "trace": [{"tool": "vector_search", "query": question, "hits": len(hits)}],
                "degraded_sources": degraded_sources(),
            }
        else:
            result = agent.run(question, web_first=(exec_route == "live_web"))
            result["classifier"] = classifier
            result["degraded_sources"] = degraded_sources()
        result["decision"] = d.to_dict()  # FR-014: full System 1 trace on every response
        state.save_session({"question": question, "classification": result.get("classification"),
                            "classifier": classifier, "plan": result.get("plan", []),
                            "iterations": result.get("iterations", 0),
                            "sufficiency": result.get("sufficiency"),
                            "answer": result["answer"], "confidence": result.get("confidence"),
                            "citations": result.get("citations", [])})
        return result

    @mcp.tool()
    def search(query: str, collections: list[str] | None = None, limit: int = 5) -> list[dict]:
        """Direct vector search without synthesis."""
        return make_vector_tool(vectors, embedder)(query, limit=limit)

    @mcp.tool()
    def web_search(query: str, limit: int = 5) -> list[dict]:
        """Live web search via configured providers (SearXNG first; falls back to Tavily/Exa). Returns [{title, url, snippet}]."""
        return make_web_tool(web_providers)(query, limit=limit)

    @mcp.tool()
    def specialty_profiles() -> dict:
        """List available specialty search profiles with their sites and descriptions.
        Call this first to discover which profiles exist, then use specialty_search."""
        from .search.web.specialty import load_profiles

        path = cfg.specialty_profiles_file or None
        profiles, error = load_profiles(path, return_error=True)
        if error:
            return {"error": error, "profiles": {}}
        return profiles

    @mcp.tool()
    def specialty_search(query: str, profile: str, limit: int = 5) -> list[dict] | dict:
        """Domain-scoped web search: results only from the profile's configured sites.
        The domain restriction is a hard filter (site: operator + post-filter)."""
        from .search.web.specialty import (
            construct_scoped_query, filter_by_domains, load_profiles, resolve_profile,
        )

        path = cfg.specialty_profiles_file or None
        profiles, file_error = load_profiles(path, return_error=True)
        if file_error:
            return {"error": file_error}                         # FR-004
        resolved = resolve_profile(profiles, profile)
        if "error" in resolved:
            return resolved                                      # FR-007/008
        scoped_query = construct_scoped_query(resolved["sites"], query)
        hits, _, _ = search_all(web_providers, scoped_query, limit)
        return filter_by_domains(hits, resolved["sites"])       # FR-006

    @mcp.tool()
    def web_research(query: str, limit: int = 3) -> dict:
        """Grouped web research: multi-engine search via the provider chain, then a
        per-page outline-preserving scrape (sections keep text + belonging image in
        document order), bounded for the LLM, with honest snippet fallbacks and a
        standalone rendered HTML artifact per page (spec 003, FR-011)."""
        import time as _time

        from .search.web.research import render_page, research_pages, sections_to_text

        limit = max(1, min(limit, cfg.research_max_pages))
        started = _time.perf_counter()
        hits, engines_used, error = search_all(web_providers, query, limit)
        scrapes = research_pages(
            hits, t0=started, fetch_timeout_s=cfg.research_fetch_timeout_s,
            per_page_chars=cfg.research_per_page_chars,
            overall_timeout_s=cfg.research_overall_timeout_s,
            max_concurrent=cfg.research_max_concurrent,
        )
        out_hits = []
        for h in hits:
            scrape = scrapes.get(h["url"], {"url": h["url"], "sections": [],
                                            "truncated": False, "status": "failed",
                                            "status_reason": "not-attempted"})
            ok = scrape["status"] == "ok" and scrape["sections"]
            # honest content (FR-008/SC-004): grouped sections when ok, else the snippet
            content = sections_to_text(scrape["sections"]) if ok else h["snippet"]
            render = (render_page(scrape["sections"], h["url"], h["title"]) if ok
                      else render_page([], h["url"], h["title"],
                                       fallback_snippet=h["snippet"] or None))
            out_hits.append({**h, "scrape": scrape, "content": content,
                             "render_html": render})
        return {
            "query": query,
            "engines_used": engines_used,
            "elapsed_ms": int((_time.perf_counter() - started) * 1000),
            "error": error,
            "hits": out_hits,
        }

    @mcp.tool()
    def fetch_url(url: str, max_chars: int = 4000) -> dict:
        """Fetch a live web page. Returns page text plus the server's `date_utc`
        (HTTP Date header = live UTC clock) — use it for current time/date
        questions instead of trusting cached search snippets."""
        return _fetch_url(url, max_chars)

    @mcp.tool()
    def sources_add(type: str, config: dict) -> dict:
        """Register a source. Types: local_folder, sqlite, onedrive."""
        if type == "local_folder":
            source_id = state.add_source(type, config)
            stats = pipeline.sync_local_folder(source_id, config["path"])
        elif type == "sqlite":
            source_id = state.add_source(type, config)
            stats = pipeline.sync_sqlite(
                source_id, SqliteSource(config["db_path"], config["table"],
                                        config.get("template", "{row}")))
        elif type == "onedrive":
            from pathlib import Path as _P
            from .sources.graph_auth import GraphAuth
            from .sources.onedrive import OneDriveSource

            if not config.get("client_id"):
                raise NotFoundError("onedrive source requires config.client_id")
            source_id = state.add_source(type, {
                "client_id": config["client_id"],
                "folder_path": config.get("folder_path", "/"),
                "include_subfolders": config.get("include_subfolders", True),
                "max_file_size_mb": config.get("max_file_size_mb", 50),
            })
            token_path = _P.home() / ".config/agentic-rag-mcp/tokens" / f"{source_id}.json"
            auth = GraphAuth(config["client_id"], token_path)
            try:
                auth.token()  # check for existing valid token (FR-002)
            except Exception:  # noqa: BLE001 — no token yet is expected for new sources
                state.set_health(source_id, "degraded", "needs sign-in")
                return {"source_id": source_id, "status": "needs_auth",
                        "message": "Call sources_auth to complete Microsoft sign-in."}
            source = OneDriveSource(auth, config)
            try:
                stats = pipeline.sync_onedrive(source_id, source)
            except Exception as exc:  # noqa: BLE001 — sync failure marks degraded, doesn't crash
                state.set_health(source_id, "degraded", str(exc))
                return {"source_id": source_id, "status": "ok", "sync": {"error": str(exc)}}
        else:
            raise NotFoundError(f"unsupported source type for manual add: {type}")
        return {"source_id": source_id, "status": "ok", "sync": stats}

    @mcp.tool()
    def sources_auth(source_id: str) -> dict:
        """Complete Microsoft sign-in for a OneDrive source (device code flow).
        Returns the sign-in URL and user code; the connection completes in the
        background after the user signs in. Call again to check status."""
        import threading
        from pathlib import Path as _P
        from .sources.graph_auth import GraphAuth

        sources = state.get_source(source_id)
        if not sources:
            raise NotFoundError(f"source not found: {source_id}")
        if sources["type"] != "onedrive":
            raise NotFoundError(f"source {source_id} is not a onedrive source")
        client_id = sources["config"]["client_id"]
        token_path = _P.home() / ".config/agentic-rag-mcp/tokens" / f"{source_id}.json"
        auth = GraphAuth(client_id, token_path)

        try:
            auth.token()  # already authenticated (FR-003: already_authenticated)
            return {"status": "already_authenticated",
                    "message": "This source has a valid token."}
        except Exception:  # noqa: BLE001 — needs sign-in
            pass

        # initiate device flow non-blocking (research.md D3)
        def _complete_sign_in():
            try:
                auth.device_sign_in()
                state.set_health(source_id, "healthy", None)
                # trigger a sync after successful auth
                from .sources.onedrive import OneDriveSource
                source = OneDriveSource(auth, sources["config"])
                try:
                    pipeline.sync_onedrive(source_id, source)
                except Exception:  # noqa: BLE001 — best-effort sync after auth
                    pass
            except Exception as exc:  # noqa: BLE001
                state.set_health(source_id, "degraded", str(exc))

        # start the flow to get the URL+code
        try:
            flow = auth._app.initiate_device_flow(scopes=auth.__class__.SCOPES
                                                    if hasattr(auth.__class__, "SCOPES")
                                                    else ["Files.Read"])
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "message": f"failed to start sign-in: {exc}"}

        if "user_code" not in flow:
            return {"status": "error", "message": "device flow failed to start"}

        # return URL+code immediately; background thread waits for completion
        threading.Thread(target=_complete_sign_in, daemon=True).start()
        return {
            "status": "sign_in_required",
            "sign_in_url": flow.get("verification_uri", "https://microsoft.com/devicelogin"),
            "user_code": flow["user_code"],
            "message": "Visit the URL, enter the code, and sign in with your Microsoft "
                       "account. The connection completes automatically.",
        }

    @mcp.tool()
    def sources_list() -> list[dict]:
        """List sources with health and sync metadata."""
        return [
            {"id": s["id"], "type": s["type"], "health": s["health"],
             "health_reason": s["health_reason"], "last_sync_at": s["last_sync_at"],
             "doc_hint": s["config"]}
            for s in state.list_sources()
        ]

    @mcp.tool()
    def sources_remove(source_id: str) -> dict:
        """Remove a source; drops documents whose last origin was this source."""
        deleted = state.remove_source(source_id)
        for doc_id in deleted:
            vectors.delete_document(vectors.default_collection(), doc_id)
        return {"removed": source_id, "documents_deleted": len(deleted)}

    @mcp.tool()
    def sources_sync(source_id: str | None = None) -> dict:
        """Manually trigger incremental sync."""
        results = watcher.sync_once()
        if source_id:
            return {source_id: results.get(source_id, {"error": "unknown source"})}
        return results

    @mcp.tool()
    def graph_query(query: str) -> dict:
        """Optional graph search (Graphify layer); disabled by default."""
        if not cfg.graphify_enabled:
            raise FeatureDisabledError("graphify layer disabled; enable in config.features")
        return graphify.explain(query)

    @mcp.tool()
    def status() -> dict:
        """Server health: decision node, per-source health, index counters."""
        probe = route_question("status probe")
        decider = probe.provenance  # "decision_node" | "fallback"
        stats = vectors.stats()
        return {
            "version": "0.1.0",
            "decision_layer": decider,
            "sources": sources_list(),
            "index": {"documents": state.doc_count(), "chunks": stats["chunks"],
                      "collections": stats["collections"]},
        }

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(prog="agentic-rag-mcp")
    parser.add_argument("--init", action="store_true", help="write default config and exit")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8811)
    args, _unknown = parser.parse_known_args()
    if args.init:
        path = init_config()
        print(f"config written: {path}")
        return
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    mcp = build_server(cfg)
    if args.transport == "streamable-http":
        print(f"agentic-rag-mcp MCP endpoint: http://{cfg.mcp_host}:{cfg.mcp_port}/mcp")
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
