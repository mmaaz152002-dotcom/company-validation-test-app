import json

import httpx
import pytest

from app.config import Settings
from app.models.compliance import ComplianceResult
from app.services.llm import LLMConfigurationError, OpenRouterLLMService


def settings(**overrides: object) -> Settings:
    values = {
        "openrouter_api_key": "test-key",
        "openrouter_primary_model": "primary",
        "openrouter_fallback_models": ["fallback"],
        "openrouter_retries_per_model": 0,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.asyncio
async def test_falls_back_and_validates_fenced_json() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requested.append(payload["model"])
        if payload["model"] == "primary":
            return httpx.Response(429, json={"error": {"message": "rate limited"}})
        content = """```json
{"status":"pass","matched_rule":null,"possible_match":null,"confidence":0.9,"reason":"No match"}
```"""
        return httpx.Response(
            200,
            json={
                "model": "fallback-resolved",
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://openrouter.test/api/v1"
    ) as client:
        result = await OpenRouterLLMService(settings(), client).generate_structured(
            [{"role": "user", "content": "screen"}],
            ComplianceResult,
            "compliance_screening",
        )

    assert result.status == "pass"
    assert requested == ["primary", "fallback"]


@pytest.mark.asyncio
async def test_authentication_failure_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://openrouter.test/api/v1"
    ) as client:
        with pytest.raises(LLMConfigurationError):
            await OpenRouterLLMService(settings(), client).generate_structured(
                [{"role": "user", "content": "screen"}],
                ComplianceResult,
                "compliance_screening",
            )
    assert calls == 1

