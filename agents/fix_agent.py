"""FixAgent — applies review feedback to produce corrected code.

This is the third node in the Code Review Workflow.  It reads the current
``code`` and the ``review_result`` from the shared state, asks the LLM to
produce a fixed version, and stores it back into ``state.data["code"]``.

After the FixAgent runs, the workflow router loops back to the ReviewAgent
for another review round, demonstrating the loop / conditional-branching
capabilities of the engine.
"""

from __future__ import annotations

import logging

from core.agent import BaseAgent
from core.message import MessageType
from core.state import WorkflowState
from llm.base import BaseLLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a Python Fix Agent.  You are given code and review comments.  \
Apply ALL the suggested fixes and return ONLY the corrected code — \
no markdown fences, no explanations.
"""


class FixAgent(BaseAgent):
    """Applies review feedback to produce corrected code."""

    def __init__(self, llm: BaseLLMClient | None = None):
        super().__init__(
            name="FixAgent",
            role="Applies review fixes to code",
            llm=llm,
        )

    def run(self, state: WorkflowState) -> WorkflowState:
        code = state.get("code", "")
        review_result = state.get("review_result", "")
        if not code or not review_result:
            raise ValueError("Missing 'code' or 'review_result' in state")

        logger.info("FixAgent applying fixes (code v%d)", state.get("code_version", 0))

        user_msg = (
            f"The following code was reviewed and changes were requested.\n\n"
            f"--- Code ---\n{code}\n\n"
            f"--- Review Comments ---\n{review_result}\n\n"
            f"Apply all fixes and return only the corrected code."
        )

        fixed_code = self.llm.chat(SYSTEM_PROMPT, user_msg)

        # Update the code in shared state
        state.set("code", fixed_code)
        state.set("code_version", state.get("code_version", 0) + 1)
        # Reset needs_fix so the next review round can set it again
        state.set("needs_fix", False)

        # Record a message for the ReviewAgent
        self.send_message(
            state,
            receiver="ReviewAgent",
            content=f"Code fixed (v{state.get('code_version')}). Please re-review.",
            msg_type=MessageType.TASK,
            code=fixed_code,
        )

        return state
