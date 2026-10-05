"""FastMCP stdio server: ask, search, sources.*, status, graph.query."""

from __future__ import annotations

import argparse
import logging
import uuid
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .agents.graph import ReflectionAgent
from .agents.tools import make_sql_tool, make_vector_tool, make_web_tool
from .config import Config, init_config, load_config
from .errors import DecisionLayerUnavailable, FeatureDisabledError, NotFoundError, RagError
from .ingestion.pipeline import IngestionPipeline
from .ingestion.watchers import Watcher
from .routing.laya import LayaDecisionLayer, heuristic_classify
from .search.embeddings import Embedder
from .search.graphify_search import GraphifySearch
from .search.web.base import build_providers
from .sources.sqlite_source import SqliteSource
from .store.state import StateStore
from .store.vectordb import VectorStore

log = logging.getLogger("agentic_rag_mcp")


def build_server(cfg: Config | None = None) -> FastMCP:
    cfg = cfg or load_config()
    state = StateStore(cfg.state_db)
    vectors = VectorStore(cfg.vector_dir)
    embedder = Embedder(cfg.embedding_model, cfg.embedding_device)
    pipeline = IngestionPipeline(state, vectors, embedder)
    watcher = Watcher(pipeline, state)
    watcher.start()

    laya = LayaDecisionLayer(cfg.laya_url, cfg.laya_token)
    web_providers = build_providers(cfg)
    graphify = GraphifySearch(Path("graphify-out/graph.json"), enabled=cfg.graphify_enabled)

    agent_tools = {
        "vector_search": make_vector_tool(vectors, embedder),
        "web_search": make_web_tool(web_providers),
    }
    if cfg.graphify_enabled:
        agent_tools["graphify"] = lambda q, limit=5: [
            {"content": graphify.explain(q)["answer"], "title": f"graph:{q}",
             "document_id": f"graphify:{q}"}
        ]
    agent = ReflectionAgent(tools=agent_tools, max_iterations=cfg.max_iterations)

    mcp = FastMCP("agentic-rag-mcp")

    def degraded_sources() -> list[str]:
        return [s["id"] for s in state.list_sources() if s["health"] != "healthy"]

    def classify(question: str) -> tuple[str, str]:
        try:
            return laya.classify(question), "laya"
        except DecisionLayerUnavailable:
            return heuristic_classify(question), "fallback"

    @mcp.tool()
    def ask(question: str, collections: list[str] | None = None, mode: str = "auto",
            max_iterations: int | None = None) -> dict:
        """Answer a question with agentic retrieval and per-source citations."""
        request_id = uuid.uuid4().hex[:8]
        log.info("ask[%s]: %s", request_id, question[:120])
        classification, classifier = (
            ("deliberative", "forced") if mode == "deep"
            else ("fast", "forced") if mode == "fast"
            else classify(question)
        )
        agent._budget = max_iterations or cfg.max_iterations
        if classification == "fast":
            hits = make_vector_tool(vectors, embedder)(question)
            if hits:
                answer = ReflectionAgent({}, 0)._synthesize(question, hits, "normal")
                citations = ReflectionAgent({}, 0)._citations(hits)
                confidence = "normal"
            else:
                answer = "No relevant information was found in the available sources."
                citations, confidence = [], "normal"
            result = {
                "answer": answer, "confidence": confidence, "classification": "fast",
                "classifier": classifier, "citations": citations,
                "trace": [{"tool": "vector_search", "query": question, "hits": len(hits)}],
                "degraded_sources": degraded_sources(),
            }
        else:
            result = agent.run(question)
            result["classifier"] = classifier
            result["degraded_sources"] = degraded_sources()
            result.pop("error", None)  # budget exhaustion is metadata, not an error
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
    def sources_add(type: str, config: dict) -> dict:
        """Register a source. Types: local_folder, sqlite."""
        if type == "local_folder":
            source_id = state.add_source(type, config)
            stats = pipeline.sync_local_folder(source_id, config["path"])
        elif type == "sqlite":
            source_id = state.add_source(type, config)
            stats = pipeline.sync_sqlite(
                source_id, SqliteSource(config["db_path"], config["table"],
                                        config.get("template", "{row}")))
        else:
            raise NotFoundError(f"unsupported source type for manual add: {type}")
        return {"source_id": source_id, "status": "ok", "sync": stats}

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
        """Server health: decision layer, per-source health, index counters."""
        try:
            laya.classify("ping")
            decision = "laya"
        except DecisionLayerUnavailable:
            decision = "fallback"
        stats = vectors.stats()
        return {
            "version": "0.1.0",
            "decision_layer": decision,
            "sources": sources_list(),
            "index": {"documents": state.doc_count(), "chunks": stats["chunks"],
                      "collections": stats["collections"]},
        }

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(prog="agentic-rag-mcp")
    parser.add_argument("--init", action="store_true", help="write default config and exit")
    args, _unknown = parser.parse_known_args()
    if args.init:
        path = init_config()
        print(f"config written: {path}")
        return
    logging.basicConfig(level=logging.INFO)
    build_server().run()
