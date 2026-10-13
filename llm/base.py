"""Abstract base class for LLM clients.

All agents interact with the LLM through this interface, making it trivial
to swap between a real API and the mock for testing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Uniform LLM interface used by all agents."""

    @abstractmethod
    def chat(self, system_prompt: str, user_message: str) -> str:
        """Send a single-turn chat request and return the assistant's reply.

        Args:
            system_prompt: System-level instructions (agent role, rules).
            user_message:  The user's message / task description.

        Returns:
            The assistant's response as a plain string.
        """
        ...
