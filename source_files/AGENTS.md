# GenV1 — Agents Architecture

> **Location:** `docs/architecture/AGENTS.md`
> **Next:** `docs/architecture/TOOLS.md` · **Prev:** `docs/architecture/FRONTEND.md`

## Purpose

Describe the agent engine: the reusable think/act/observe runtime, the prompt
builder, the loaders/registry/factory, the tool-loop guard, and the 3-step
pipeline.

## Responsibilities

- Run one agent per request: `Agent.think()` → `ask_llm()` → optional tool
  rounds (`act()` / `observe()`) → final text reply.
- Load agent definitions from `engine/agent_library/*/` (`agent.md` +
  `agent.json`), resolve the correct folder even when `id != folder name`.
- Build system prompts from agent.md sections + tool docstrings.
- Bound the tool loop and stop repeated identical tool calls (guard).
- Run the configured pipeline chain (`config/pipeline.json`).

## Does Not Own

- The tools themselves (see `docs/architecture/TOOLS.md`).
- HTTP/chat-session management (see `docs/architecture/BACKEND.md`).
- Tool undo/deletion decisions (guarded in `engine/agents/factory.py`).

## Components

- `engine/core/agent.py` — `AgentProfile` + `Agent` (think/act/observe).
- `engine/core/llm.py` — `ask_llm()`, model resolution, context window.
- `engine/core/prompt.py` — `PromptManager` (sections → system prompt).
- `engine/agents/loader.py` — `agent_dir`, `load_definition`, save helpers.
- `engine/agents/registry.py` — `list_agents()` scan.
- `engine/agents/factory.py` — `build_agent()`, session-aware tool wrappers,
  grounding block.
- `engine/pipeline.py` — `run_pipeline()` for `config/pipeline.json`.
- `engine/agent_library/*/` — the agent definitions themselves.

## Inputs

- A user message (and, in pipeline mode, the chain config).
- `agent.md` + `agent.json` from the agent folder.
- The requested model and the installed Ollama model scan.

## Processing

1. `build_agent(agent_id, model)` → `load_definition` → resolve tools → build
   prompt → return `Agent`.
2. `Agent.think(message)`:
   - inject system prompt + `CURRENT FILE SESSION STATE`.
   - `ask_llm(...)`; append reply; extract native `tool_calls` or
     plain-text JSON tool calls.
   - loop up to `MAX_TOOL_ROUNDS = 6`; on identical repeat ≥
     `REPEAT_LIMIT = 3`, emit a guard warning/feedback and stop.
   - each round: `act(tool_call, origin)` + `observe(name, result)`.
   - empty final reply → fallback "(I ran my tools but did not produce a final
     answer. Please ask again.)".
3. `Agent.act()` runs the tool with normalized args, records a `tool_events`
   entry, forwards to `server.tool_log`, classifies success/error/missing.
4. `Agent.observe()` appends `{"role": "tool", ...}` to history.
5. Pipeline (`run_pipeline`): feed the original message + every earlier step's
   reply (labeled) into each step agent; final reply = last step; record the
   run to `<dataDir>/chatlog/pipeline_runs.jsonl` (fail-safe).

## Outputs

- The final reply string; collected `tool_events`; pipeline step outputs.

## Dependencies

- `tools/registry.py`, `tools/state.py` (FileSession), `server/tool_log.py`.
- Ollama via `engine/core/llm.py`.
- `config/models.json` (auto-scanned) and `config/pipeline.json`.

## Consumers

- `server/server.py` (`POST /api/chat`), `server/chat_store/consolidate.py`,
  anything calling `build_agent()`.

## Extension Points

- New agents = new folders under `engine/agent_library/` (id in `agent.json`).
- New tool support added in `tools/` then referenced by `agent.json#tools`.
- Pipeline steps = edit `config/pipeline.json` `steps`.

## Rules

- `chat` mode attaches no tools: no tool loop can occur.
- Tool-armed agents get a "WORKSPACE ROOT / agent folder / skills" grounding
  block; they must stop guessing paths after a "not found" tool result.
- `delete_files(approved=True)` only deletes paths previously proposed via
  `approved=False` (in `FileSession.pending_deletion`).

## Failure Behavior

- Unknown agent id → error string (registry/factory), never a crash.
- Model not installed → fallback to a detected model (warn + use first).
- Model does not support tools → tool schemas dropped; the agent answers
  text-only.
- Repeated tool-call loop → guard message instead of infinite loop.

## Runtime Flow

```text
User -> POST /api/chat
  -> build_agent(agent_id, model)      factory
  -> Agent.think(message)
        -> ask_llm(messages, model, tools)   llm.py -> Ollama
        -> [tool_calls?]
             -> act(call)                    runs tool, logs event
             -> observe(name, result)
             -> ask_llm(...) again
             (max MAX_TOOL_ROUNDS, repeat-guarded)
        -> reply
```

## Configuration

- Per-agent: `agent.json` (`id`, `name`, `description`, `mode`, `model`,
  `tools`).
- Pipeline: `config/pipeline.json` (`name`, `description`, `steps`).
- Model/context bounds: `MAX_NUM_CTX = 32768` in `engine/core/llm.py`.

## APIs

No HTTP API; consumed via Python. The chat endpoint is `docs/reference/API.md`.

## Source Files

```text
engine/core/agent.py
engine/core/llm.py
engine/core/prompt.py
engine/agents/loader.py
engine/agents/registry.py
engine/agents/factory.py
engine/pipeline.py
engine/agent_library/*/agent.md
engine/agent_library/*/agent.json
```

## Related Documentation

- `docs/architecture/TOOLS.md`
- `docs/architecture/MEMORY.md`
- `docs/reference/AGENT_REFERENCE.md`
- `docs/development/ADDING_AGENTS.md`
- `docs/reference/WORKFLOWS.md`