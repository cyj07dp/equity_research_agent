from __future__ import annotations

import json
import logging
import os
from typing import Protocol, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)
logger = logging.getLogger("uvicorn.error")


class LLMClient(Protocol):
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        raise NotImplementedError


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str | None,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
        log_max_chars: int = 1000,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.log_max_chars = log_max_chars

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is not configured.")
        if not self.model:
            raise RuntimeError("LLM_MODEL is not configured.")

        from openai import OpenAI

        logger.info(
            "Calling LLM model=%s base_url=%s response_model=%s timeout_seconds=%s",
            self.model,
            self.base_url or "default",
            response_model.__name__,
            self.timeout_seconds,
        )
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url or None,
            timeout=self.timeout_seconds,
        )
        schema = response_model.model_json_schema(by_alias=True)
        completion = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{system_prompt}\n\n"
                        "You must return only a valid JSON object matching this JSON Schema:\n"
                        f"{json.dumps(schema, ensure_ascii=False)}"
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("LLM returned an empty response.")
        logger.info("LLM returned response_model=%s content_length=%s", response_model.__name__, len(content))
        logger.info(_format_llm_response_log(response_model.__name__, content, self.log_max_chars))
        return response_model.model_validate_json(content)


class UnavailableLLMClient:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        raise RuntimeError(self.reason)


def create_llm_client_from_env() -> LLMClient:
    load_dotenv()
    provider = os.getenv("LLM_PROVIDER", "openai-compatible").strip().lower()
    if provider not in {"openai", "openai-compatible"}:
        return UnavailableLLMClient(f"Unsupported LLM_PROVIDER: {provider}")

    return OpenAICompatibleLLMClient(
        api_key=os.getenv("LLM_API_KEY"),
        model=os.getenv("LLM_MODEL"),
        base_url=os.getenv("LLM_BASE_URL") or None,
        timeout_seconds=_timeout_seconds_from_env(),
        log_max_chars=_positive_int_from_env("LLM_LOG_MAX_CHARS", 1000),
    )


def _timeout_seconds_from_env() -> float:
    raw_value = os.getenv("LLM_TIMEOUT_SECONDS", "10").strip()
    try:
        timeout_seconds = float(raw_value)
    except ValueError:
        logger.warning("Invalid LLM_TIMEOUT_SECONDS=%s; using 10 seconds", raw_value)
        return 10.0
    if timeout_seconds <= 0:
        logger.warning("Invalid non-positive LLM_TIMEOUT_SECONDS=%s; using 10 seconds", raw_value)
        return 10.0
    return timeout_seconds


def _positive_int_from_env(name: str, default_value: int) -> int:
    raw_value = os.getenv(name, str(default_value)).strip()
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning("Invalid %s=%s; using %s", name, raw_value, default_value)
        return default_value
    if value <= 0:
        logger.warning("Invalid non-positive %s=%s; using %s", name, raw_value, default_value)
        return default_value
    return value


def _format_llm_response_log(response_model_name: str, content: str, max_chars: int) -> str:
    normalized_content = " ".join(content.split())
    truncated = len(normalized_content) > max_chars
    visible_content = normalized_content[:max_chars]
    if truncated:
        visible_content = f"{visible_content} ... [truncated, original_chars={len(normalized_content)}]"

    return (
        "\n"
        "╭──────────────── 🤖 LLM RESPONSE ────────────────\n"
        f"│ response_model: {response_model_name}\n"
        f"│ visible_chars: {len(visible_content)}\n"
        f"│ max_chars: {max_chars}\n"
        f"│ truncated: {str(truncated).lower()} {'✂️' if truncated else '✅'}\n"
        "├──────────────── 📦 content ────────────────\n"
        f"{visible_content}\n"
        "╰──────────────── ✅ END ────────────────"
    )
