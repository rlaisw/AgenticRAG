from agentic_rag_mcp.errors import (
    ErrorCode, IngestionError, ProviderError, SourceAuthError, SufficiencyExhausted,
)


def test_codes():
    assert IngestionError("x").to_result()["code"] == ErrorCode.PARSE_FAILED.value
    assert SourceAuthError("x").to_result()["code"] == ErrorCode.AUTH_REQUIRED.value
    assert ProviderError("x").to_result()["code"] == ErrorCode.PROVIDER_UNAVAILABLE.value
    assert SufficiencyExhausted("x").to_result()["code"] == ErrorCode.BUDGET_EXHAUSTED.value


def test_message_no_trace():
    r = IngestionError("corrupt pdf", context={"file": "a.pdf"}).to_result()
    assert r == {"error": True, "code": "ParseFailed", "message": "corrupt pdf"}
