"""LLM client layer.

Provides a uniform ``BaseLLMClient`` interface so that agents can be powered
by either a real LLM (OpenAI-compatible API) or a deterministic mock that
requires no API key — perfect for demos and tests.
"""

from .base import BaseLLMClient
from .mock_client import MockLLMClient

__all__ = ["BaseLLMClient", "MockLLMClient"]

# OpenAI client is imported lazily so the project still works without
# the ``openai`` package installed (e.g. when using only the mock).
def get_openai_client(api_key: str | None = None, model: str = "gpt-4o-mini", base_url: str | None = None):
    """Create an OpenAI-compatible LLM client.

    Returns ``None`` if the ``openai`` package is not installed.
    """
    try:
        from .openai_client import OpenAIClient
        return OpenAIClient(api_key=api_key, model=model, base_url=base_url)
    except ImportError:
        return None
