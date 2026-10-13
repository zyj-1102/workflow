"""Message passing system for agent-to-agent communication.

Each Message represents a unit of communication between agents (or between
the workflow orchestrator and an agent). Messages carry structured content
and metadata that enable observability and debugging.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    """Types of messages that can be passed between agents."""

    TASK = "task"          # A task or instruction for an agent
    RESULT = "result"     # The result produced by an agent
    FEEDBACK = "feedback"  # Feedback from one agent to another
    STATUS = "status"      # Status update / state transition
    ERROR = "error"        # Error notification


@dataclass
class Message:
    """A single message in the agent communication protocol.

    Attributes:
        sender:    Name of the sending agent (or "orchestrator").
        receiver:  Name of the receiving agent (or "broadcast").
        content:   The message payload as a string.
        msg_type:  Category of message (see MessageType).
        timestamp: When the message was created.
        msg_id:    Unique identifier for tracing.
        metadata:  Extra structured data (e.g. code snippets, review items).
    """

    sender: str
    receiver: str
    content: str
    msg_type: MessageType = MessageType.TASK
    timestamp: datetime = field(default_factory=datetime.now)
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the message to a plain dictionary (for logging / JSON)."""
        return {
            "msg_id": self.msg_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "msg_type": self.msg_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return (
            f"Message[{self.msg_type.value}] "
            f"{self.sender} -> {self.receiver}: "
            f"{self.content[:80]}{'...' if len(self.content) > 80 else ''}"
        )
