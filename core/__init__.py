"""Core framework for the Simple Workflow MVP.

This package contains the foundational building blocks:
- WorkflowState: shared state management between agents
- Message: agent-to-agent communication
- BaseAgent: abstract agent interface
- Workflow: orchestration engine with sequential, conditional, and loop support
"""

from .state import WorkflowState
from .message import Message, MessageType
from .agent import BaseAgent
from .workflow import Workflow, WorkflowStep

__all__ = ["WorkflowState", "Message", "MessageType", "BaseAgent", "Workflow", "WorkflowStep"]
