"""CodingAgent — generates code from a natural-language requirement.

This is the first node in the Code Review Workflow.  It reads the
``requirement`` from the shared state, asks the LLM to produce Python code,
and stores the result back into ``state.data["code"]``.
"""

from __future__ import annotations

import logging

from core.agent import BaseAgent
from core.message import MessageType
from core.state import WorkflowState
from llm.base import BaseLLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a Python Coding Agent.  Given a requirement, write clean, correct, \
and well-structured Python code.  Return ONLY the code — no markdown fences, \
no explanations.
"""


class CodingAgent(BaseAgent):
    """Generates Python code based on a natural-language requirement."""

    def __init__(self, llm: BaseLLMClient | None = None):
        super().__init__(
            name="CodingAgent",
            role="Generates Python code from requirements",
            llm=llm,
        )

    def run(self, state: WorkflowState) -> WorkflowState:
        requirement = state.get("requirement", "")
        if not requirement:
            raise ValueError("No 'requirement' found in state")

        logger.info("CodingAgent generating code for: %s", requirement)

        user_msg = (
            f"Write Python code for the following requirement.\n\n"
            f"Requirement: {requirement}\n\n"
            f"Return only the code."
        )

        code = self.llm.chat(SYSTEM_PROMPT, user_msg)

        # Store the generated code in shared state
        state.set("code", code)
        state.set("code_version", state.get("code_version", 0) + 1)

        # Record a message for the ReviewAgent
        self.send_message(
            state,
            receiver="ReviewAgent",
            content=f"Code generated (v{state.get('code_version')}). Please review.",
            msg_type=MessageType.TASK,
            code=code,
        )

        return state
