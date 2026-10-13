"""Shared state management for the workflow.

WorkflowState is the central data structure that flows through every agent
in the workflow.  It provides:

* A typed key-value store for arbitrary data (code, requirements, etc.)
* A message history log for observability
* Iteration / status tracking for loop control
* JSON serialisation for persistence and debugging
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .message import Message


@dataclass
class WorkflowState:
    """Mutable shared state passed from agent to agent.

    Agents read from and write to this object.  The workflow orchestrator
    inspects it between steps to decide routing (conditional branching).
    """

    # ---- core data store ----
    data: dict[str, Any] = field(default_factory=dict)

    # ---- communication log ----
    messages: list[Message] = field(default_factory=list)

    # ---- execution metadata ----
    current_step: str = ""
    iteration: int = 0
    status: str = "initialized"  # initialized | running | completed | failed
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    error: str | None = None

    # ------------------------------------------------------------------ #
    #  Typed accessors                                                    #
    # ------------------------------------------------------------------ #
    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, **kwargs: Any) -> None:
        self.data.update(kwargs)

    # ------------------------------------------------------------------ #
    #  Message helpers                                                    #
    # ------------------------------------------------------------------ #
    def add_message(self, message: Message) -> None:
        """Append a message to the communication log."""
        self.messages.append(message)

    def get_messages_from(self, agent_name: str) -> list[Message]:
        """Return all messages sent by *agent_name*."""
        return [m for m in self.messages if m.sender == agent_name]

    def get_messages_to(self, agent_name: str) -> list[Message]:
        """Return all messages addressed to *agent_name*."""
        return [m for m in self.messages if m.receiver == agent_name]

    # ------------------------------------------------------------------ #
    #  Serialisation                                                      #
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict[str, Any]:
        """Full serialisation including messages and metadata."""
        return {
            "data": self.data,
            "messages": [m.to_dict() for m in self.messages],
            "current_step": self.current_step,
            "iteration": self.iteration,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)

    # ------------------------------------------------------------------ #
    #  Convenience                                                        #
    # ------------------------------------------------------------------ #
    def mark_completed(self) -> None:
        self.status = "completed"
        self.finished_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.error = error
        self.finished_at = datetime.now()

    def __repr__(self) -> str:
        return (
            f"WorkflowState(status={self.status!r}, "
            f"step={self.current_step!r}, "
            f"iteration={self.iteration}, "
            f"messages={len(self.messages)})"
        )
