from app.llm.client import _format_llm_response_log, _positive_int_from_env


def test_format_llm_response_log_truncates_content() -> None:
    message = _format_llm_response_log("QueryUnderstanding", '{"answer":"' + "a" * 50 + '"}', 20)

    assert "LLM RESPONSE" in message
    assert "QueryUnderstanding" in message
    assert "truncated: true" in message
    assert "[truncated, original_chars=" in message
    assert len(message) < 500


def test_positive_int_from_env_uses_default_for_invalid_value(monkeypatch) -> None:
    monkeypatch.setenv("LLM_LOG_MAX_CHARS", "bad")

    assert _positive_int_from_env("LLM_LOG_MAX_CHARS", 1000) == 1000
