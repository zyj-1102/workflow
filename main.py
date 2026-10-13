"""Simple Workflow MVP — Code Review Process

Entry point for the Code Review Workflow:
    Coding → Review → (Fix → Review)* → Approved

Usage:
    # Run with the built-in mock LLM (no API key needed)
    python main.py

    # Run with a real OpenAI-compatible API
    OPENAI_API_KEY=sk-xxx python main.py

    # Specify a custom requirement
    python main.py --requirement "Write a function to reverse a string"

    # Use a custom OpenAI-compatible base URL (e.g. local server)
    python main.py --base-url http://localhost:8080/v1

Architecture overview:
                    ┌──────────────────────────────────────┐
                    │            Workflow Engine           │
                    │  (sequential + conditional + loop)   │
                    └──────────┬──────────────┬────────────┘
                               │              │
                    ┌──────────▼──┐  ┌───────▼──────┐  ┌───────────┐
                    │ CodingAgent │─►│ ReviewAgent  │─►│  FixAgent  │
                    │ (generates  │  │ (reviews &   │  │ (applies  │
                    │  code)      │  │  approves)  │  │  fixes)   │
                    └─────────────┘  └──────┬───────┘  └─────┬─────┘
                                           │                 │
                                     approved?          loops back
                                      │     │          to review
                                   yes     no
                                    │       └──────────►┘
                                    ▼
                                  DONE
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from agents import CodingAgent, FixAgent, ReviewAgent
from core import Workflow
from llm import BaseLLMClient, MockLLMClient
from llm import get_openai_client


# --------------------------------------------------------------------------- #
#  Logging setup                                                              #
# --------------------------------------------------------------------------- #
def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# --------------------------------------------------------------------------- #
#  LLM factory                                                                #
# --------------------------------------------------------------------------- #
def create_llm(args) -> BaseLLMClient:
    """Create the best available LLM client.

    Priority:
    1. OpenAI API (if OPENAI_API_KEY is set or --api-key provided)
    2. Mock (deterministic, no network needed)
    """
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    base_url = args.base_url or os.environ.get("OPENAI_BASE_URL")
    model = args.model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    if api_key:
        client = get_openai_client(api_key=api_key, model=model, base_url=base_url)
        if client is not None:
            print(f"[INFO] Using OpenAI LLM (model={model})")
            return client
        print("[WARN] openai package not installed, falling back to mock.")
    else:
        print("[INFO] No OPENAI_API_KEY found — using MockLLMClient for demo.")

    return MockLLMClient()


# --------------------------------------------------------------------------- #
#  Workflow builder                                                           #
# --------------------------------------------------------------------------- #
def build_workflow(llm: BaseLLMClient, max_iterations: int = 10) -> Workflow:
    """Build the Code Review Workflow.

    Flow:
        coding  →  review  →  (fix  →  review)*  →  done

    The router after "review" checks ``state.needs_fix``:
        True  → route to "fix" (which loops back to "review")
        False → workflow ends (code approved)
    """

    wf = Workflow("Code Review Workflow", max_iterations=max_iterations)

    # Step 1: Coding — generate initial code
    wf.add_step(
        name="coding",
        agent=CodingAgent(llm=llm),
        router=lambda state: "review",  # always go to review after coding
        is_start=True,
    )

    # Step 2: Review — review the code
    wf.add_step(
        name="review",
        agent=ReviewAgent(llm=llm),
        # Conditional branching: if needs_fix → go to fix; else → done
        router=lambda state: "fix" if state.get("needs_fix") else None,
    )

    # Step 3: Fix — apply review feedback, then loop back to review
    wf.add_step(
        name="fix",
        agent=FixAgent(llm=llm),
        router=lambda state: "review",  # always re-review after fix
    )

    return wf


# --------------------------------------------------------------------------- #
#  Result printer                                                             #
# --------------------------------------------------------------------------- #
def print_result(state):
    """Pretty-print the workflow result."""
    print("\n" + "=" * 70)
    print("  WORKFLOW EXECUTION COMPLETE")
    print("=" * 70)

    print(f"\n  Status:     {state.status}")
    print(f"  Iterations: {state.iteration}")
    print(f"  Messages:   {len(state.messages)}")
    print(f"  Reviews:    {state.get('review_count', 0)}")
    print(f"  Code ver:   {state.get('code_version', 0)}")

    print(f"\n  Requirement: {state.get('requirement', 'N/A')}")

    print("\n" + "-" * 70)
    print("  FINAL CODE:")
    print("-" * 70)
    print(state.get("code", "(none)"))
    print("-" * 70)

    print("\n" + "-" * 70)
    print("  FINAL REVIEW:")
    print("-" * 70)
    print(state.get("review_result", "(none)"))
    print("-" * 70)

    print("\n" + "-" * 70)
    print("  MESSAGE LOG (Agent-to-Agent Communication):")
    print("-" * 70)
    for msg in state.messages:
        print(f"  [{msg.msg_type.value:8s}] {msg.sender:12s} → {msg.receiver:12s}: {msg.content}")
    print("-" * 70)

    print(f"\n  Full state JSON saved to: workflow_result.json")
    with open("workflow_result.json", "w", encoding="utf-8") as f:
        f.write(state.to_json(indent=2))

    print("=" * 70 + "\n")


# --------------------------------------------------------------------------- #
#  Main                                                                        #
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(
        description="Simple Workflow MVP — Code Review Process",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--requirement", "-r",
        default="Write a Python function is_prime(n) that returns True if n is a prime number, False otherwise.",
        help="The coding requirement (default: is_prime function).",
    )
    parser.add_argument("--api-key", default=None, help="OpenAI API key (or set OPENAI_API_KEY env).")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible API base URL.")
    parser.add_argument("--model", default=None, help="Model name (default: gpt-4o-mini).")
    parser.add_argument("--max-iterations", type=int, default=10, help="Max workflow iterations (default: 10).")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    llm = create_llm(args)
    wf = build_workflow(llm, max_iterations=args.max_iterations)

    print(f"\n[INFO] Starting workflow with requirement: {args.requirement}\n")

    state = wf.run({"requirement": args.requirement})

    print_result(state)

    # Exit code: 0 on success, 1 on failure
    sys.exit(0 if state.status == "completed" else 1)


if __name__ == "__main__":
    main()
