#!/usr/bin/env python3
"""Quick demo script — runs the Code Review Workflow with the mock LLM.

This script requires NO API key and NO external dependencies.
Just run:  python run_demo.py
"""

import logging
import sys

from agents import CodingAgent, FixAgent, ReviewAgent
from core import Workflow
from llm.mock_client import MockLLMClient


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    llm = MockLLMClient()

    # Build the workflow
    wf = Workflow("Code Review Demo", max_iterations=10)

    wf.add_step(
        name="coding",
        agent=CodingAgent(llm=llm),
        router=lambda s: "review",
        is_start=True,
    )
    wf.add_step(
        name="review",
        agent=ReviewAgent(llm=llm),
        router=lambda s: "fix" if s.get("needs_fix") else None,
    )
    wf.add_step(
        name="fix",
        agent=FixAgent(llm=llm),
        router=lambda s: "review",
    )

    # Run with a sample requirement
    initial_data = {
        "requirement": "Write a Python function is_prime(n) that returns True if n is a prime number, False otherwise."
    }

    print("\n" + "=" * 60)
    print("  Code Review Workflow — Demo (Mock LLM)")
    print("=" * 60 + "\n")

    state = wf.run(initial_data)

    print("\n" + "=" * 60)
    print("  RESULT")
    print("=" * 60)
    print(f"  Status:     {state.status}")
    print(f"  Iterations: {state.iteration}")
    print(f"  Reviews:    {state.get('review_count', 0)}")
    print(f"  Code ver:   {state.get('code_version', 0)}")
    print(f"  Approved:   {state.get('approved', False)}")

    print("\n--- FINAL CODE ---")
    print(state.get("code", "(none)"))

    print("\n--- FINAL REVIEW ---")
    print(state.get("review_result", "(none)"))

    print("\n--- MESSAGE LOG ---")
    for msg in state.messages:
        print(f"  [{msg.msg_type.value:8s}] {msg.sender:12s} -> {msg.receiver:12s}: {msg.content}")

    print("\n" + "=" * 60 + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
