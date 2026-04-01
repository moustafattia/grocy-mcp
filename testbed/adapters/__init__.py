"""Model-adapter factory functions."""

from __future__ import annotations

from testbed.adapters.anthropic import AnthropicAdapter
from testbed.adapters.base import ModelAdapter
from testbed.adapters.openai import OpenAIAdapter
from testbed.adapters.openai_compatible import OpenAICompatibleAdapter
from testbed.config import TestbedConfig


def create_adapter(
    source: str, config: TestbedConfig, provider_model: str | None = None
) -> ModelAdapter:
    """Create a provider-backed model adapter for extraction.

    The ``"golden"`` source is handled directly by ``load_normalized_items``
    and never reaches this factory.
    """
    if source == "openai":
        if not config.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        if not (provider_model or config.openai_model):
            raise RuntimeError("TESTBED_OPENAI_MODEL or --provider-model is required.")
        return OpenAIAdapter(config.openai_api_key, provider_model or config.openai_model)
    if source == "anthropic":
        if not config.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")
        if not (provider_model or config.anthropic_model):
            raise RuntimeError("TESTBED_ANTHROPIC_MODEL or --provider-model is required.")
        return AnthropicAdapter(
            config.anthropic_api_key,
            provider_model or config.anthropic_model,
        )
    if source == "openai_compatible":
        if not config.openai_compatible_base_url:
            raise RuntimeError("TESTBED_OPENAI_COMPAT_BASE_URL is not configured.")
        if not (provider_model or config.openai_compatible_model):
            raise RuntimeError("TESTBED_OPENAI_COMPAT_MODEL or --provider-model is required.")
        return OpenAICompatibleAdapter(
            base_url=config.openai_compatible_base_url,
            api_key=config.openai_compatible_api_key,
            model=provider_model or config.openai_compatible_model,
        )
    raise RuntimeError(f"Unsupported adapter source '{source}'.")
