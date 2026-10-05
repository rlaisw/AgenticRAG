"""Typed error taxonomy -> MCP error results.

Machine-readable codes per contracts/mcp-tools.md. Stack traces are never
returned over the wire; they are logged server-side only.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass

log = logging.getLogger("agentic_rag_mcp.errors")


class ErrorCode(str, enum.Enum):
    NOT_FOUND = "NotFound"
    AUTH_REQUIRED = "AuthRequired"
    PROVIDER_UNAVAILABLE = "ProviderUnavailable"
    PARSE_FAILED = "ParseFailed"
    BUDGET_EXHAUSTED = "BudgetExhausted"
    FEATURE_DISABLED = "FeatureDisabled"
    DECISION_LAYER_UNAVAILABLE = "DecisionLayerUnavailable"
    INTERNAL = "Internal"


class RagError(Exception):
    code = ErrorCode.INTERNAL

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}
        log.debug("RagError raised", extra={"code": self.code, **self.context})

    # subclasses must not leak internals in __str__ beyond the message
    def to_result(self) -> dict:
        return {"error": True, "code": self.code.value, "message": self.message}


class IngestionError(RagError):
    code = ErrorCode.PARSE_FAILED


class SourceAuthError(RagError):
    code = ErrorCode.AUTH_REQUIRED


class ProviderError(RagError):
    code = ErrorCode.PROVIDER_UNAVAILABLE


class SufficiencyExhausted(RagError):
    """Surfaced as low-confidence metadata in answers, not an RPC error."""

    code = ErrorCode.BUDGET_EXHAUSTED


class DecisionLayerUnavailable(RagError):
    code = ErrorCode.DECISION_LAYER_UNAVAILABLE


class NotFoundError(RagError):
    code = ErrorCode.NOT_FOUND


class FeatureDisabledError(RagError):
    code = ErrorCode.FEATURE_DISABLED


@dataclass
class Ok:
    value: object


@dataclass
class Err:
    error: RagError


def wrap(fn, *args, **kwargs):
    """Run fn; convert RagError to MCP error result; log-and-wrap anything else."""
    try:
        return Ok(fn(*args, **kwargs))
    except RagError as exc:
        return Err(exc)
    except Exception as exc:  # noqa: BLE001 - last-resort boundary
        log.exception("Unhandled error in %s", getattr(fn, "__name__", fn))
        return Err(RagError(str(exc)))
