"""Base agent class defining the uniform interface every agent must implement.

To add a new agent to the workflow:
1. Subclass ``BaseAgent``.
2. Implement ``run(state)`` — read inputs from *state*, do work, write
   outputs back to *state*, and return the updated state.
3. Register the agent instance in the workflow (see ``Workflow.add_step``).

That's it — the workflow engine handles orchestration, routing, logging,
and loop control.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .message import Message, MessageType
from .state import WorkflowState

if TYPE_CHECKING:
    from llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all workflow agents.

    Attributes:
        name: Human-readable identifier used in logs and messages.
        role: Short description of the agent's responsibility.
        llm:  Optional LLM client (agents that don't need an LLM can ignore it).
    """

    def __init__(self, name: str, role: str, llm: BaseLLMClient | None = None):
        self.name = name
        self.role = role
        self.llm = llm

    @abstractmethod
    def run(self, state: WorkflowState) -> WorkflowState:
        """Execute the agent's task.

        Args:
            state: The current shared workflow state.  Read inputs from it,
                   write outputs back to it.

        Returns:
            The updated state (same object, mutated in place is fine).
        """
        ...

    # ------------------------------------------------------------------ #
    #  Helpers available to subclasses                                    #
    # ------------------------------------------------------------------ #
    def send_message(
        self,
        state: WorkflowState,
        receiver: str,
        content: str,
        msg_type: MessageType = MessageType.RESULT,
        **metadata,
    ) -> Message:
        """Record a message from this agent to *receiver* in the state log."""
        msg = Message(
            sender=self.name,
            receiver=receiver,
            content=content,
            msg_type=msg_type,
            metadata=metadata,
        )
        state.add_message(msg)
        logger.info("%s -> %s: %s", self.name, receiver, content[:100])
        return msg

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} role={self.role!r}>"
