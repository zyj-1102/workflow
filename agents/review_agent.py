"""ReviewAgent — reviews code and produces structured feedback.

This is the second node in the Code Review Workflow.  It reads ``code`` from
the shared state, asks the LLM to review it, and parses the response to
determine whether the code is ``APPROVED`` or ``CHANGES_REQUESTED``.

The routing function (defined in ``main.py``) inspects
``state.data["needs_fix"]`` to decide whether to route to the FixAgent
(loop) or end the workflow.
"""

from __future__ import annotations

import logging
import re

from core.agent import BaseAgent
from core.message import MessageType
from core.state import WorkflowState
from llm.base import BaseLLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a strict Python Code Reviewer.  Review the provided code for \
correctness, edge cases, performance, and style.  \

Start your response with either:
  - APPROVED          (if no changes are needed)
  - CHANGES_REQUESTED (if issues were found)

Then list each issue with a clear description and suggested fix.
"""


class ReviewAgent(BaseAgent):
    """Reviews generated code and produces structured feedback."""

    def __init__(self, llm: BaseLLMClient | None = None):
        super().__init__(
            name="ReviewAgent",
            role="Reviews code quality and correctness",
            llm=llm,
        )

    def run(self, state: WorkflowState) -> WorkflowState:
        code = state.get("code", "")
        if not code:
            raise ValueError("No 'code' found in state to review")

        review_count = state.get("review_count", 0) + 1
        state.set("review_count", review_count)

        logger.info("ReviewAgent reviewing code (review #%d)", review_count)

        user_msg = (
            f"Please review the following Python code (review round {review_count}):\n\n"
            f"{code}"
        )

        review_result = self.llm.chat(SYSTEM_PROMPT, user_msg)

        # Parse the verdict
        approved = review_result.strip().upper().startswith("APPROVED")
        needs_fix = not approved

        # Store results in shared state
        state.set("review_result", review_result)
        state.set("needs_fix", needs_fix)
        state.set("approved", approved)

        # Record a message
        self.send_message(
            state,
            receiver="FixAgent" if needs_fix else "Orchestrator",
            content=(
                f"Review {'APPROVED' if approved else 'CHANGES_REQUESTED'} "
                f"(round {review_count})"
            ),
            msg_type=MessageType.FEEDBACK,
            review_result=review_result,
        )

        logger.info(
            "ReviewAgent verdict: %s",
            "APPROVED" if approved else "CHANGES_REQUESTED",
        )

        return state
