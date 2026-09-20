import json
import logging
import time
from collections.abc import Sequence
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
ResponseT = TypeVar("ResponseT", bound=BaseModel)


class LLMServiceError(RuntimeError):
    """Base class for safe, application-facing LLM failures."""


class LLMConfigurationError(LLMServiceError):
    pass


class LLMServiceUnavailable(LLMServiceError):
    pass


class _RecoverableModelError(Exception):
    pass


def _extract_json(content: str) -> Any:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char not in "[{":
                continue
            try:
                value, end = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if not text[index + end :].strip().strip("`"):
                return value
        raise


class OpenRouterLLMService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._provided_client = client

    def _headers(self) -> dict[str, str]:
        if not self.settings.openrouter_api_key:
            raise LLMConfigurationError("OPENROUTER_API_KEY is not configured.")
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        if self.settings.openrouter_site_url:
            headers["HTTP-Referer"] = self.settings.openrouter_site_url
        if self.settings.openrouter_app_name:
            headers["X-OpenRouter-Title"] = self.settings.openrouter_app_name
        return headers

    async def generate_structured(
        self,
        messages: Sequence[dict[str, str]],
        response_model: type[ResponseT],
        purpose: str,
    ) -> ResponseT:
        headers = self._headers()
        models = self.settings.openrouter_models
        if not models or not models[0]:
            raise LLMConfigurationError("No OpenRouter model is configured.")

        client = self._provided_client or httpx.AsyncClient(
            base_url=self.settings.openrouter_base_url.rstrip("/"),
            timeout=self.settings.openrouter_timeout_seconds,
        )
        owns_client = self._provided_client is None
        try:
            for model_index, model in enumerate(models):
                for attempt in range(self.settings.openrouter_retries_per_model + 1):
                    started = time.perf_counter()
                    try:
                        result, actual_model, usage = await self._request(
                            client, headers, model, messages, response_model
                        )
                        latency_ms = round((time.perf_counter() - started) * 1000)
                        logger.info(
                            "llm_call_succeeded",
                            extra={
                                "purpose": purpose,
                                "requested_model": model,
                                "actual_model": actual_model,
                                "success": True,
                                "fallback_used": model_index > 0,
                                "attempt": attempt + 1,
                                "latency_ms": latency_ms,
                                **usage,
                            },
                        )
                        return result
                    except LLMConfigurationError:
                        raise
                    except _RecoverableModelError as exc:
                        latency_ms = round((time.perf_counter() - started) * 1000)
                        logger.warning(
                            "llm_call_failed",
                            extra={
                                "purpose": purpose,
                                "requested_model": model,
                                "actual_model": None,
                                "success": False,
                                "fallback_used": model_index > 0,
                                "attempt": attempt + 1,
                                "latency_ms": latency_ms,
                                "error_type": type(exc).__name__,
                            },
                        )
            raise LLMServiceUnavailable(
                "The AI service is temporarily unavailable after trying all configured models."
            )
        finally:
            if owns_client:
                await client.aclose()

    async def _request(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        model: str,
        messages: Sequence[dict[str, str]],
        response_model: type[ResponseT],
    ) -> tuple[ResponseT, str, dict[str, int | None]]:
        schema_name = response_model.__name__.lower()
        payload = {
            "model": model,
            "messages": list(messages),
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": response_model.model_json_schema(),
                },
            },
        }
        try:
            response = await client.post(
                "/chat/completions", headers=headers, json=payload
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise _RecoverableModelError("OpenRouter request failed") from exc

        if response.status_code in {401, 403}:
            raise LLMConfigurationError(
                "OpenRouter rejected the configured credentials or access policy."
            )
        if response.status_code == 429 or response.status_code >= 500:
            raise _RecoverableModelError(
                f"OpenRouter returned recoverable HTTP {response.status_code}"
            )
        if response.status_code >= 400:
            # A model may reject structured output or be unavailable even when the
            # gateway reports a 4xx. Let the next configured model handle the task.
            raise _RecoverableModelError(
                f"Model request returned HTTP {response.status_code}"
            )

        try:
            body = response.json()
            choice = body["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty or non-text model content")
            validated = response_model.model_validate(_extract_json(content))
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
            raise _RecoverableModelError("Model returned unusable structured data") from exc

        raw_usage = body.get("usage") or {}
        usage = {
            "prompt_tokens": raw_usage.get("prompt_tokens"),
            "completion_tokens": raw_usage.get("completion_tokens"),
            "total_tokens": raw_usage.get("total_tokens"),
        }
        return validated, body.get("model") or model, usage

