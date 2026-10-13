"""Deterministic mock LLM client.

Produces realistic, scenario-specific responses for the Code Review Workflow
**without requiring an API key or network access**.  This makes the MVP
immediately runnable for demos and tests.

The mock routes based on the agent's **system prompt** (not the user message)
to avoid false keyword matches:

* **Coding Agent**  → returns a ``is_prime`` implementation with a
  subtle bug (doesn't handle ``n <= 1``).
* **Review Agent**  → inspects the provided code: if the bug is still
  present it returns structured review comments; if the code has been
  fixed it approves it.
* **Fix Agent**     → returns the corrected code.
"""

from __future__ import annotations

import re

from .base import BaseLLMClient


class MockLLMClient(BaseLLMClient):
    """Deterministic mock that simulates a code-review conversation."""

    # The "buggy" code the coding agent would produce.
    BUGGY_CODE = """\
def is_prime(n):
    if n == 2:
        return True
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
"""

    # The corrected code the fix agent would produce.
    FIXED_CODE = """\
def is_prime(n):
    if n <= 1:
        return False
    if n == 2:
        return True
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
"""

    def chat(self, system_prompt: str, user_message: str) -> str:
        """Return a canned response based on the agent's system prompt.

        Using the system prompt (not the user message) for routing avoids
        false matches — e.g. the FixAgent's user message contains the word
        "review" (from "Review Comments") which would otherwise trigger the
        review path.
        """
        sp = system_prompt.lower()

        # ---- Fix agent: apply fixes (check first — its prompt mentions "review") ----
        if "fix agent" in sp:
            return self._fix_code(user_message)

        # ---- Coding agent: generate initial code ----
        if "coding agent" in sp:
            return self.BUGGY_CODE

        # ---- Review agent: inspect code ----
        if "reviewer" in sp or "review" in sp:
            return self._review_code(user_message)

        # Fallback: echo a generic response.
        return "[Mock LLM] I received your message but am not sure what to do."

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                   #
    # ------------------------------------------------------------------ #
    def _review_code(self, user_message: str) -> str:
        """Simulate a code review.  Detects the n<=1 bug if present."""
        # Extract code from the user message (look for 'def' block).
        code_match = re.search(r"(def .+?)(?:\n\n|\Z)", user_message, re.DOTALL)
        code = code_match.group(1) if code_match else user_message

        # Check whether the code handles n <= 1.
        handles_edge_case = bool(
            re.search(r"n\s*<=\s*1", code) or re.search(r"n\s*<\s*2", code)
        )

        if handles_edge_case:
            return (
                "APPROVED\n\n"
                "Code review passed. The implementation correctly handles "
                "edge cases (n <= 1, n == 2) and uses trial division up to "
                "sqrt(n) for efficiency.\n"
                "No issues found."
            )
        else:
            return (
                "CHANGES_REQUESTED\n\n"
                "ISSUE 1: The function does not handle n <= 1.\n"
                "  - is_prime(1) returns True, but 1 is not a prime number.\n"
                "  - is_prime(0) returns True, but 0 is not a prime number.\n"
                "  - is_prime(-5) returns True, but negative numbers are not prime.\n"
                "  Suggestion: Add `if n <= 1: return False` at the beginning.\n"
                "\n"
                "ISSUE 2: Missing docstring.\n"
                "  Suggestion: Add a docstring explaining the function's purpose."
            )

    def _fix_code(self, user_message: str) -> str:
        """Return the fixed code."""
        return self.FIXED_CODE
