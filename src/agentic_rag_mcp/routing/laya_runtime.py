"""Laya decision-model runtime: lazy load, snapshot download, timeout-guarded call.

The model is the vendored RLAgent (see rl_agent_api.py). Loaded once per process
on first use; load failure or timeout surfaces as an exception the decision
module converts into a fallback route (FR-003/FR-004).
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from ..config import Config

_agent = None
_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=1)


def _model_dir(cfg: Config) -> str:
    if cfg.decider_model_dir:
        return cfg.decider_model_dir
    from huggingface_hub import snapshot_download

    return snapshot_download(
        cfg.decider_model_repo,
        allow_patterns=[
            "model.safetensors", "rl_agent_config.json", "encoder/config.json",
            "tokenizer/tokenizer.json", "tokenizer/tokenizer_config.json",
        ],
    )


def get_agent(cfg: Config):
    """Process-wide lazy RLAgent; raises on any load failure."""
    global _agent
    with _lock:
        if _agent is None:
            from .rl_agent_api import RLAgent

            _agent = RLAgent(_model_dir(cfg))
    return _agent


def system_one(cfg: Config, state, questions) -> dict:
    """One forward pass, bounded by cfg.decider_timeout.

    The lazy LOAD happens outside the timeout (first-call cost ~tens of seconds);
    the budget bounds warm inference only.
    ponytail: the worker thread can't be cancelled — a hung pass leaks one
    thread until it finishes; switch to a subprocess if that ever bites.
    """
    agent = get_agent(cfg)
    future = _pool.submit(agent.system_one, state, questions)
    return future.result(timeout=cfg.decider_timeout)


def warm_up(cfg: Config) -> None:
    """Background model pre-load so the first request doesn't pay the load cost."""
    threading.Thread(target=lambda: _try_load(cfg), daemon=True).start()


def _try_load(cfg: Config) -> None:
    try:
        get_agent(cfg)
    except Exception:  # noqa: BLE001 — warm-up is best-effort; decide() reports failures
        pass
