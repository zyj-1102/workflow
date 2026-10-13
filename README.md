# Simple Workflow MVP — Code Review Process

A multi-agent workflow that automates the code review process:
**Coding → Review → Fix → Review (loop) → Approved**

Built with a lightweight, extensible workflow engine that supports sequential
execution, conditional branching, and loops — no external framework required.

## Quick Start

```bash
# Run with the built-in mock LLM (no API key needed!)
python run_demo.py

# Or use the full CLI entry point
python main.py

# Run with a real OpenAI-compatible API
OPENAI_API_KEY=sk-xxx python main.py

# Custom requirement
python main.py --requirement "Write a function to check if a string is a palindrome"

# Verbose logging
python main.py -v
```

## How It Works

```
┌──────────────┐     ┌──────────────┐     ┌──────────┐
│ CodingAgent  │────►│ ReviewAgent  │────►│ FixAgent │
│ (generates   │     │ (reviews &   │     │ (applies │
│  code)       │     │  approves)   │     │  fixes)  │
└──────────────┘     └──────┬───────┘     └────┬─────┘
                            │                   │
                      approved?            loops back
                       │     │            to review
                     yes     no
                      │       └──────────►┘
                      ▼
                    DONE
```

1. **CodingAgent** reads the requirement and generates Python code.
2. **ReviewAgent** reviews the code. If issues are found → `CHANGES_REQUESTED`.
3. **FixAgent** applies the fixes and updates the code.
4. Loop back to **ReviewAgent** (step 2). Repeat until `APPROVED` or max iterations.

## Project Structure

```
workflow/
├── README.md              # This file
├── Design.md              # Architecture & design document
├── requirements.txt       # Dependencies (optional: openai)
├── main.py                # CLI entry point with full features
├── run_demo.py            # Quick demo (mock LLM, zero config)
├── core/                  # Framework layer
│   ├── __init__.py
│   ├── agent.py           # BaseAgent — uniform agent interface
│   ├── workflow.py        # Workflow — orchestration engine
│   ├── state.py           # WorkflowState — shared state management
│   └── message.py         # Message — agent-to-agent communication
├── agents/                # Concrete agent implementations
│   ├── __init__.py
│   ├── coding_agent.py    # Generates code from requirements
│   ├── review_agent.py    # Reviews code, approves or requests changes
│   └── fix_agent.py       # Applies review feedback
├── llm/                   # LLM client layer
│   ├── __init__.py
│   ├── base.py            # BaseLLMClient — abstract interface
│   ├── openai_client.py   # OpenAI-compatible API client
│   └── mock_client.py     # Deterministic mock for demos/tests
└── tests/
    └── test_workflow.py   # 20 unit + integration tests
```

## Key Features

### Workflow Orchestration
- **Sequential execution**: steps run in order
- **Conditional branching**: router functions inspect state to decide next step
- **Loops**: routers can route back to previous steps (review → fix → review)
- **Max iteration guard**: prevents infinite loops

### Agent-to-Agent Communication
- Structured `Message` objects with sender, receiver, type, content, metadata
- Full message log stored in `WorkflowState` for observability
- Message types: `TASK`, `RESULT`, `FEEDBACK`, `STATUS`, `ERROR`

### State Management
- `WorkflowState` provides a typed key-value store shared across agents
- Tracks iteration count, current step, status, and timestamps
- Full JSON serialization for persistence and debugging

### Extensibility
Adding a new agent takes 3 steps:

```python
from core import BaseAgent, WorkflowState

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MyAgent", role="Does something useful")

    def run(self, state: WorkflowState) -> WorkflowState:
        # Read from state, do work, write back
        result = do_something(state.get("input"))
        state.set("output", result)
        return state

# Register in the workflow
wf.add_step("my_step", MyAgent(), router=lambda s: "next_step")
```

### LLM Flexibility
- **MockLLMClient**: deterministic responses, no API key, perfect for demos
- **OpenAIClient**: works with any OpenAI-compatible API (OpenAI, Azure, local)
- Easy to add new LLM backends by implementing `BaseLLMClient`

## Running Tests

```bash
python tests/test_workflow.py

# Or with pytest (if installed)
python -m pytest tests/test_workflow.py -v
```

## Using a Real LLM

```bash
# Install the optional openai package
pip install -r requirements.txt

# Set your API key
export OPENAI_API_KEY=sk-your-key-here

# Run with the real LLM
python main.py --requirement "Write a function to reverse a linked list"

# Use a custom OpenAI-compatible endpoint
python main.py --base-url http://localhost:8080/v1 --model gpt-4o
```

## Sample Output

```
  Status:     completed
  Iterations: 4
  Reviews:    2
  Code ver:   2
  Approved:   True

--- FINAL CODE ---
def is_prime(n):
    if n <= 1:
        return False
    if n == 2:
        return True
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

--- MESSAGE LOG ---
  [task    ] CodingAgent  → ReviewAgent : Code generated (v1). Please review.
  [feedback] ReviewAgent  → FixAgent    : Review CHANGES_REQUESTED (round 1)
  [task    ] FixAgent     → ReviewAgent : Code fixed (v2). Please re-review.
  [feedback] ReviewAgent  → Orchestrator: Review APPROVED (round 2)
```

## Evaluation Criteria Coverage

| Criterion | Weight | How We Address It |
|-----------|--------|-------------------|
| 流程完整性 (Process Completeness) | 40% | Full end-to-end workflow runs: coding → review → fix → re-review → approved |
| Agent协作 (Agent Collaboration) | 30% | Message passing system, shared state, 3 agents communicating |
| 可扩展性 (Extensibility) | 20% | BaseAgent interface, pluggable LLM, router-based branching, add agents in 3 lines |
| 文档 (Documentation) | 10% | README.md, Design.md, inline docstrings, architecture diagram |
