# Coding Style Rule — Temi's AI/ML Engineering Assistant

This rule defines how the assistant should write Python code for an AI/ML Engineer
working primarily with LangChain, LangGraph, Pydantic, and Gemini-backed LLM pipelines.
All directives below are non-negotiable defaults unless explicitly overridden in a prompt.

---

## 1. General Python Style

### Naming
- Variables and functions: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`
- Classes: `PascalCase`
- Names must reflect purpose — what a thing does or represents, not how it is implemented.
  Avoid generic names like `data`, `result`, `obj`, `process`.
- Private helpers: prefix with a single underscore (`_parse_response`, `_build_context`).

### Formatting
- Max line length: **88 characters** (Black-compatible).
- Use Black-style formatting throughout. Trailing commas in multi-line structures.
- No double blank lines inside a function. Two blank lines between top-level definitions.

### Imports
Organise imports in three groups, separated by a blank line, in this order:
1. Standard library (`os`, `json`, `typing`, `datetime`, etc.)
2. LLM/AI framework imports (`langchain_*`, `langgraph`, `google.genai`,
   `pydantic`, `deepeval`, etc.)
3. Local project imports (`from .state import ...`, `from tools.x import ...`)

Within each group, sort by domain proximity — imports that work together go together.
Never use wildcard imports (`from x import *`).

### Type Hints
- **Every function signature** must have type hints — parameters and return type.
- Use `typing` constructs (`Optional`, `Union`, `Annotated`, `Any`) where needed.
- Prefer `X | None` over `Optional[X]` only if the codebase is already on Python 3.10+;
  otherwise use `Optional[X]` for consistency.
- `TypedDict` for state objects. `BaseModel` for validated data contracts.
- Never leave a return type as implicit — always annotate, including `-> None`.

### Docstrings
- **NumPy-style docstrings** on all non-trivial functions.
- Minimum: a one-line summary for short helpers. Full Parameters/Returns sections for
  anything public or complex.
- Do not pad docstrings with obvious restating of the function name.

```python
def compute_importance_weight(days_since_match: int, base_weight: float) -> float:
    """
    Compute a recency-adjusted importance weight for a historical match.

    Parameters
    ----------
    days_since_match : int
        Number of days elapsed since the match was played.
    base_weight : float
        The raw importance weight before recency decay is applied.

    Returns
    -------
    float
        The final decayed weight, clamped to [0.0, 1.0].
    """
```

### Comments
- Comment **most functions** — at minimum a short inline comment explaining the intent
  of any non-obvious block.
- Comment *why*, not *what*. The code says what. The comment explains the reasoning.
- Section headers inside long pipeline functions are encouraged:
  `# --- Stage 2: rolling feature computation ---`
- Never leave commented-out code in committed/shared files.

---

## 2. Function Design

### Size and Responsibility
- Target **15–30 lines** per function. Hard ceiling is ~50 lines before extraction is
  required.
- Group related steps inside a function — strict one-action-only SRP is not required,
  but each function should have a single coherent *purpose*, even if it performs a few
  related operations to achieve it.
- If a function starts to read like a script, split it.

### Arguments
- Prefer **`**kwargs`** for functions that take many optional or configurable arguments.
  Unpack and validate at the top of the function body with clear variable names.
- For functions that are always called with the same argument shape, use a Pydantic
  model or TypedDict as the single input instead of many positional params.
- Avoid positional arguments beyond 2–3. Use keyword-only where the call site would
  otherwise be ambiguous.

### Control Flow
- Use **early returns** when guarding against invalid inputs or empty data at the top of
  a function. Don't nest the entire function body in an `if valid:` block.
- Use a **single exit point** for functions with complex transformation logic where
  following multiple return paths would hurt readability.
- Apply the pattern that makes the code easiest to read for that specific function — not
  a blanket rule.

### Helpers
- Extract logic into `_private_helpers` when a block appears more than once, or when
  naming it would make the parent function significantly cleaner.
- Keep helpers close to their caller — in the same module unless they are genuinely
  reusable across modules.
- Don't over-extract. A 4-line block that only runs once can stay inline.

### Purity
- Prefer pure functions (same input → same output, no side effects) where practical.
- Explicitly separate functions that read/write state or I/O from those that transform
  data. Don't mix transformation logic with side effects in the same function body.

---

## 3. Async, Errors, and Logging

### Async
- Default to **synchronous** code. Use `async/await` only when the operation is
  genuinely I/O-bound and blocking would create a bottleneck (e.g. concurrent tool
  calls, streaming responses, parallel HTTP requests).
- Do not use `asyncio.run()` inside library/module code. Leave event loop management
  to the entry point.
- Never mix sync and async across a call chain without an explicit bridge.

### Error Handling
Scale the response to the severity of the failure:

| Severity | Strategy |
|---|---|
| Unrecoverable / invalid contract | `raise` a descriptive exception immediately |
| Expected partial failure (tool errors, bad LLM output) | Catch, log with context, return a safe default or error-flagged state |
| Non-critical degradation (optional enrichment failed) | Log at `WARNING` level, continue execution |

- Use built-in exception types where semantically correct (`ValueError`, `TypeError`,
  `KeyError`). Define custom exception classes only when callers need to distinguish
  the error programmatically.
- Never silence exceptions with a bare `except: pass`. Always log at minimum.
- When catching exceptions, catch the most specific type possible.

```python
# preferred pattern for expected tool/LLM failures
try:
    result = _call_external_service(payload)
except (httpx.HTTPError, ValueError) as e:
    logger.warning("Service call failed: %s — returning empty result", str(e))
    return []
```

### Logging
- Use Python's **`logging`** module. Configure a module-level logger at the top of
  each file:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  ```
- Log levels:
  - `DEBUG`: LLM input payloads, intermediate state, token counts during development.
  - `INFO`: Node entry/exit, pipeline stage completion, key decisions.
  - `WARNING`: Recoverable failures, fallbacks triggered, unexpected-but-handled states.
  - `ERROR`: Failures that degrade output quality or skip required steps.
- Always include context in log messages — don't log bare `"error occurred"`. Include
  the relevant ID, stage, or input that caused it.
- Do not log raw LLM outputs in production if they may contain sensitive user data.
- Do not log secrets, API keys, or credentials at any level.

---

## 4. State Design (LangGraph)

### TypedDict for Graph State
- Define `AgentState` as a **`TypedDict`**. Keep it lightweight — only fields that need
  to flow between nodes belong here.
- Always include an `errors` field typed as `Annotated[list[str], operator.add]` to
  accumulate non-fatal errors across nodes without overwriting.
- Fields that are accumulated across parallel branches must use
  `Annotated[list[T], operator.add]` reducers. Fields set by a single node use plain
  types.
- Never put heavy objects or un-serialisable data directly into state. Store references
  or summaries; compute the heavy object inside the node that needs it.

```python
from __future__ import annotations
from typing import Annotated
import operator
from typing_extensions import TypedDict


class AgentState(TypedDict):
    topic_profiles: list[dict]
    raw_items: Annotated[list[RawItem], operator.add]
    deduped_items: list[RawItem]
    summaries: Annotated[list[str], operator.add]
    final_digest: str
    errors: Annotated[list[str], operator.add]
```

### Pydantic for LLM Output Contracts
- **Always parse the LLM's raw output into a Pydantic `BaseModel`** before any business
  logic touches it. Never operate on raw dicts or unvalidated strings from an LLM
  response.
- Validation is the gate: if the model fails to parse, raise or return an error state —
  do not proceed with malformed data.
- Define all output schemas in `schemas.py` or `types.py`. Never define ad-hoc Pydantic
  models inline inside a node or tool function.

---

## 5. Tool Design

### Structure
Every tool function must have:
1. A **NumPy docstring** — LangChain reads the docstring to describe the tool to the
   LLM. Make it precise and descriptive of what the tool does and what it returns.
2. **Input validation** at the top — check types, required fields, and value ranges
   before doing any work.
3. An **explicit return type annotation** — always `-> ToolOutputModel` or `-> str`,
   never implicit.
4. **Error handling** — tools should not propagate raw exceptions to the graph. Catch
   expected failures, log them, and return a structured error response.

### Scope
- **One job per tool, strictly.** A tool that fetches and parses is two tools, not one,
  unless the two operations are always performed together and have no independent value.
- Name tools as verbs: `fetch_match_results`, `compute_rolling_stats`,
  `search_arxiv_papers`.

### Return Type
- Tools return **Pydantic models**, not raw dicts or plain strings (except for tools
  where the only meaningful output is a short string, e.g. a status message).
- Define the return model in `schemas.py`/`types.py` alongside the input model.

### Error Handling in Tools
- Catch specific exceptions. Log the failure with context.
- Return a Pydantic model with an `error: str | None` field set, rather than raising.
  This allows the calling node to inspect the result and decide how to proceed without
  crashing the graph.

```python
def fetch_team_fixture(team_id: str, competition: str) -> FixtureResult:
    """
    Fetch the next scheduled fixture for a given team in a competition.

    Parameters
    ----------
    team_id : str
        The internal team identifier.
    competition : str
        Competition slug (e.g. 'world_cup_2026').

    Returns
    -------
    FixtureResult
        Parsed fixture data, or an error-flagged result on failure.
    """
    if not team_id or not isinstance(team_id, str):
        return FixtureResult(error="team_id must be a non-empty string")
    try:
        raw = _call_fixtures_api(team_id=team_id, competition=competition)
        return FixtureResult(**raw)
    except Exception as e:
        logger.error("Failed to fetch fixture for %s: %s", team_id, str(e))
        return FixtureResult(error=str(e))
```

---

## 6. LLM Calls and Structured Output

### AI Service
- **Never instantiate LLM clients directly** in nodes, tools, or pipeline code. All
  LLM calls route through the centralised AI service. This handles model selection,
  API key management, retries, and fallbacks.
- Do not write retry logic for LLM calls in application code — that is the service's
  responsibility.

### Structured Output
- Always use **`with_structured_output(PydanticModel)`** to extract structured data
  from LLMs. Never parse JSON strings from LLM responses with regex or manual
  `json.loads` unless there is a documented reason the structured output API cannot
  be used.
- The Pydantic model passed to `with_structured_output` must be defined in
  `schemas.py`/`types.py`, not inline at the call site.

```python
# correct
chain = llm.with_structured_output(MatchSummarySchema)
result: MatchSummarySchema = chain.invoke(prompt)

# never do this
raw = llm.invoke(prompt)
data = json.loads(raw.content)  # fragile, unvalidated
```

### Prompts
- System prompts are **module-level string constants** in a dedicated `prompts.py`
  file or `prompts/` directory. Never define prompts inline inside a function body
  unless they are trivially short one-liners.
- Structure prompts clearly: role definition first, then instructions, then output
  format specification.
- When using variable interpolation, use f-strings with named variables — never
  positional `.format()` or `%s` substitution.
- Use XML-style tags to delineate sections in complex prompts:
  `<context>...</context>`, `<instructions>...</instructions>`,
  `<output_format>...</output_format>`.

---

## 7. Configuration and Shared Types

### Configuration
- All configuration and secrets via **`pydantic-settings`** with a `.env` file.
- Define a single `Settings` class in `config.py` at the project root. Import the
  settings singleton — do not call `os.environ.get` directly in application code.
- Never hardcode API keys, URLs, or environment-specific values anywhere outside
  `.env`.

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str
    newscatcher_api_key: str
    redis_url: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"

settings = Settings()
```

### Shared Types
- All Pydantic models, TypedDicts, enums, and dataclasses that are shared across
  more than one module live in **`types.py`** or **`schemas.py`**.
- Never duplicate type definitions across files. If two modules need the same shape,
  it belongs in the shared types file.
- Enums over magic strings. If a field can only take a known set of values, define
  an `Enum` for it.

---

## 8. Testing and Evaluation

### Unit Tests
- **Mock the LLM client** in all unit tests. Never make live API calls in test suites.
- Use `unittest.mock.patch` or pytest fixtures to inject a mock client. The mock
  should return a pre-defined Pydantic model matching the expected `with_structured_output`
  schema, not a raw string.
- Test node logic independently of the LLM — the node function should be structured
  so the LLM call is injectable/mockable.

```python
from unittest.mock import MagicMock, patch

def test_summarise_node_returns_expected_state():
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = SummarySchema(
        summary="Test summary", key_points=["point A"]
    )
    state = AgentState(raw_items=[...], summaries=[], errors=[])
    result = summarise_node(state, llm=mock_llm)
    assert len(result["summaries"]) == 1
```

### LLM Evaluation
- Evaluation pipelines use **DeepEval** and/or **Opik** depending on the component.
- Always define evaluation datasets in `goldens` format with seed examples before
  synthesising.
- For structured-output agents, always evaluate schema compliance as a baseline metric
  before task-specific metrics.
- Use `LangSmith` traces for debugging pipeline behaviour during development.
- Do not ship an LLM feature without at least a smoke test on a golden set.

---

## 9. General Best Practices for LLM Code

- **Prompt and schema are a contract.** If the prompt changes, the output schema must
  be reviewed. If the schema changes, the prompt must be reviewed. Treat them as coupled.
- **Never trust raw LLM output.** Always parse through a Pydantic model, even for
  "simple" string outputs where you expect a specific format.
- **Fail loudly at the boundaries, gracefully inside the graph.** Validate inputs at
  node entry. Inside the graph, prefer logging errors to state and continuing over
  crashing the entire run.
- **Determinism by default.** Use `temperature=0` for any node that produces structured
  output, classification decisions, or routing signals. Only increase temperature for
  explicitly generative/creative nodes.
- **Keep LLM calls out of loops where possible.** Batch inputs before calling the
  model. A single prompt with 10 items is almost always better than 10 sequential
  single-item calls.
- **Document LLM-specific assumptions.** If a node depends on the LLM behaving in a
  particular way (e.g. always returning a specific field), add a comment noting the
  assumption and what happens downstream if it breaks.
- **Notebooks are for exploration only.** Any code that belongs in a pipeline or is
  reused more than once gets ported to a `.py` module. Notebooks are never the source
  of truth for pipeline logic.
