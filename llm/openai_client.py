"""OpenAI-compatible LLM client.

Works with any provider that implements the OpenAI chat-completions API
(OpenAI, Azure OpenAI, local servers via ``base_url``, etc.).
"""

from __future__ import annotations

import logging

from .base import BaseLLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """Thin wrapper around the ``openai`` Python SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ):
        try:
            import openai
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for OpenAIClient. "
                "Install it with: pip install openai"
            ) from exc

        self.model = model
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        logger.info("OpenAIClient initialised (model=%s, base_url=%s)", model, base_url)

    def chat(self, system_prompt: str, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content
