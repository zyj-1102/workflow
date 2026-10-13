# Design Document — Simple Workflow MVP

## 1. Overview

This document describes the architecture and design decisions behind the
Code Review Workflow MVP. The system implements a multi-agent workflow where
three agents collaborate to generate, review, and fix code.

### 1.1 Project Goals

Per the homework specification:
- Build a simple Workflow with **2-3 collaborating Agents**
- Understand **Workflow orchestration**, **Agent-to-Agent communication**,
  and **state management**
- Support **basic flow control** (sequential execution) — must implement
- Support **conditional branching, loops** — recommended

### 1.2 Chosen Direction

**Code Review Process**: 编码 → 审查 → 修复 (Coding → Review → Fix)

This direction was chosen because:
1. **Natural feedback loop**: Review → Fix → Review demonstrates loops and
   conditional branching out of the box.
2. **Clear validation criteria**: Code either passes review or doesn't —
   no ambiguity in the outcome.
3. **Real-world applicability**: Automated code review is a practical use case.
4. **3 agents**: Meets the "2-3 agents" requirement with room to demonstrate
   collaboration.


## 2. Architecture

### 2.1 Layered Architecture

```
┌─────────────────────────────────────────────────┐
│                  Entry Points                   │
│         (main.py / run_demo.py)                 │
├─────────────────────────────────────────────────┤
│               Agents Layer                       │
│  CodingAgent  ReviewAgent  FixAgent             │
├─────────────────────────────────────────────────┤
│               Core Framework                     │
│  Workflow  BaseAgent  WorkflowState  Message   │
├─────────────────────────────────────────────────┤
│               LLM Layer                          │
│  BaseLLMClient  OpenAIClient  MockLLMClient     │
└─────────────────────────────────────────────────┘
```

Each layer depends only on the layer below it, enabling:
- **Agent layer** to be swapped without touching the framework
- **LLM layer** to be swapped without touching agents
- **Core framework** to be reused for entirely different workflows

### 2.2 Core Framework Components

#### 2.2.1 BaseAgent (`core/agent.py`)

Abstract base class defining the uniform agent interface:

```python
class BaseAgent(ABC):
    def __init__(self, name: str, role: str, llm: BaseLLMClient | None = None): ...

    @abstractmethod
    def run(self, state: WorkflowState) -> WorkflowState: ...
```

- `run()` is the only method agents must implement
- Agents read from and write to `WorkflowState`
- `send_message()` helper logs inter-agent communication
- The `llm` attribute is optional (agents that don't need an LLM ignore it)

#### 2.2.2 WorkflowState (`core/state.py`)

Central data structure flowing through every agent:

| Component | Purpose |
|-----------|---------|
| `data` (dict) | Key-value store for arbitrary data (code, requirements, etc.) |
| `messages` (list) | Full communication log for observability |
| `current_step` | Name of the step currently executing |
| `iteration` | Counter incremented each step (for loop control) |
| `status` | `initialized` / `running` / `completed` / `failed` |
| `started_at` / `finished_at` | Execution timestamps |

Methods: `get()`, `set()`, `add_message()`, `get_messages_from()`,
`get_messages_to()`, `to_dict()`, `to_json()`, `mark_completed()`,
`mark_failed()`.

#### 2.2.3 Message (`core/message.py`)

Structured communication protocol:

| Field | Type | Description |
|-------|------|-------------|
| `sender` | str | Sending agent name |
| `receiver` | str | Receiving agent name (or "broadcast") |
| `content` | str | Message payload |
| `msg_type` | MessageType | TASK / RESULT / FEEDBACK / STATUS / ERROR |
| `timestamp` | datetime | Creation time |
| `msg_id` | str | Unique ID for tracing |
| `metadata` | dict | Extra structured data |

#### 2.2.4 Workflow (`core/workflow.py`)

Orchestration engine supporting three flow-control patterns:

**1. Sequential Execution**
```python
wf.add_step("a", agent_a, router=lambda s: "b")
wf.add_step("b", agent_b)  # no router → ends
```

**2. Conditional Branching**
```python
wf.add_step("review", review_agent,
    router=lambda s: "fix" if s.get("needs_fix") else None)
```
The router inspects the state and decides the next step name (or `None` to end).

**3. Loops**
```python
wf.add_step("fix", fix_agent,
    router=lambda s: "review")  # always routes back to review
```
Combined with the conditional branching above, this creates a
review → fix → review loop that terminates when review passes.

**Loop Safety**: `max_iterations` (default 20) prevents infinite loops.

**Error Handling**: If an agent raises an exception, the workflow catches
it, marks the state as failed with the error message, and stops.


### 2.3 Agent Implementations

#### CodingAgent (`agents/coding_agent.py`)
- **Input**: `state.requirement` (natural language)
- **Output**: `state.code` (generated Python code), `state.code_version`
- **Message**: Sends a TASK message to ReviewAgent

#### ReviewAgent (`agents/review_agent.py`)
- **Input**: `state.code`
- **Output**: `state.review_result`, `state.needs_fix`, `state.approved`,
  `state.review_count`
- **Logic**: Parses LLM response for "APPROVED" or "CHANGES_REQUESTED"
- **Message**: Sends FEEDBACK to FixAgent (if changes needed) or Orchestrator

#### FixAgent (`agents/fix_agent.py`)
- **Input**: `state.code`, `state.review_result`
- **Output**: `state.code` (updated), `state.code_version` (incremented)
- **Message**: Sends TASK to ReviewAgent for re-review

### 2.4 LLM Layer

#### BaseLLMClient (`llm/base.py`)
```python
class BaseLLMClient(ABC):
    @abstractmethod
    def chat(self, system_prompt: str, user_message: str) -> str: ...
```

#### MockLLMClient (`llm/mock_client.py`)
Deterministic mock that produces a realistic code-review scenario:
- CodingAgent → returns `is_prime()` with a bug (missing `n <= 1` check)
- ReviewAgent → analyzes code: if `n <= 1` check is absent → CHANGES_REQUESTED; if present → APPROVED
- FixAgent → returns the corrected code

The mock routes based on the **system prompt** (not the user message) to
avoid false keyword matches — e.g. the FixAgent's user message contains the
word "review" (from "Review Comments") which would otherwise trigger the
review path.

#### OpenAIClient (`llm/openai_client.py`)
Wraps the `openai` Python SDK. Works with any OpenAI-compatible API by
setting `base_url`.

### 2.5 Routing Logic (main.py)

The workflow is assembled in `build_workflow()`:

```
coding  ──router──►  review  ──router──►  (needs_fix? fix : end)
                                 ▲               │
                                 └──router───────┘
```

- After `coding`: always go to `review`
- After `review`: if `state.needs_fix` → go to `fix`; else → end (None)
- After `fix`: always go to `review` (re-review the fixed code)


## 3. Design Decisions

### 3.1 Why Not Use LangGraph / Temporal / Airflow?

The homework goal is to **understand** workflow orchestration concepts,
not to use an existing framework. Building from scratch:
- Demonstrates understanding of orchestration, routing, and state management
- Keeps dependencies to zero (mock LLM needs nothing)
- Makes the architecture fully transparent for evaluation

### 3.2 Router Functions vs. Fixed Graph

Routes are defined as Python lambda functions (`router=lambda s: ...`) rather
than a declarative graph (YAML/JSON). This is intentional for an MVP:
- **Pros**: type-safe, debuggable, no extra config format to learn
- **Trade-off**: less declarative, but simpler for 3-agent workflows

For larger workflows, the router pattern scales to a declarative format —
just replace lambdas with config-driven lookup tables.

### 3.3 Mock LLM Design

The mock is designed to produce a **realistic scenario** that exercises all
flow control features:
1. First code has a bug → ReviewAgent requests changes (conditional branch to fix)
2. FixAgent produces corrected code → loop back to review
3. Second review finds no issues → APPROVED (conditional branch to end)

This guarantees the workflow always demonstrates loops and conditional
branching in a demo, even without an API key.

### 3.4 State as a Single Object vs. Message Passing

We use a hybrid approach:
- **WorkflowState** is the shared data store (code, review result, etc.)
- **Messages** are the communication log (who said what to whom)

This separates "what data the agents share" from "how they communicate",
making both observable independently.


## 4. Extensibility

### 4.1 Adding a New Agent

1. Create a class inheriting `BaseAgent`
2. Implement `run(state)` — read inputs, do work, write outputs
3. Register with `wf.add_step(name, agent, router=...)`

Example: adding a "TestAgent" after code is approved:

```python
class TestAgent(BaseAgent):
    def __init__(self, llm=None):
        super().__init__("TestAgent", "Generates and runs tests", llm)

    def run(self, state):
        code = state.get("code")
        tests = self.llm.chat("You are a test agent...", f"Write tests for:\n{code}")
        state.set("tests", tests)
        return state

# Modify the router to include the new step
wf.add_step("review", ReviewAgent(llm=llm),
    router=lambda s: "fix" if s.get("needs_fix") else "test")  # → test instead of end
wf.add_step("test", TestAgent(llm=llm))  # no router → ends
```

### 4.2 Adding a New LLM Backend

Implement `BaseLLMClient.chat()`:

```python
class MyLLMClient(BaseLLMClient):
    def chat(self, system_prompt, user_message):
        # Call your LLM API
        return response
```

### 4.3 Building a Different Workflow

The framework is workflow-agnostic. To build a different workflow (e.g.,
Content Creation), just define new agents and a new routing graph:

```python
wf = Workflow("Content Creation")
wf.add_step("plan", PlanningAgent(llm), router=lambda s: "write")
wf.add_step("write", WritingAgent(llm), router=lambda s: "proofread")
wf.add_step("proofread", ProofreadAgent(llm),
    router=lambda s: "write" if s.get("needs_revision") else None)
```


## 5. Testing

20 tests covering:
- **Unit tests**: Message, WorkflowState, MockLLM, individual agents
- **Integration tests**: Full workflow execution, message log, max iterations
- **Extensibility test**: Adding a new agent to the workflow

```
Ran 20 tests in 0.003s — OK
```


## 6. Flow Diagram (Detailed)

```
START
  │
  ▼
[coding] CodingAgent.run()
  │  - Reads requirement from state
  │  - Calls LLM to generate code
  │  - Writes code to state
  │  - Sends message to ReviewAgent
  │
  ▼ router: → "review"
[review] ReviewAgent.run()
  │  - Reads code from state
  │  - Calls LLM to review code
  │  - Parses APPROVED / CHANGES_REQUESTED
  │  - Writes review_result, needs_fix, approved to state
  │  - Sends feedback message
  │
  ├── needs_fix == True ──► router: → "fix"
  │                          │
  │                     [fix] FixAgent.run()
  │                          │  - Reads code + review_result
  │                          │  - Calls LLM to fix code
  │                          │  - Writes updated code to state
  │                          │  - Sends message to ReviewAgent
  │                          │
  │                          ▼ router: → "review" (loop back)
  │                          │
  └── needs_fix == False ──► router: → None (END)
                               │
                               ▼
                            COMPLETED
```
