# agentCreator — Headless App Master Copy

The `headless_app/` half of agentCreator: the agent engine, its tools, and the bridge that binds them to the Project Manager. File structure plus a description of every module, class and function.

| Field | Value |
| ----- | ----- |
| Scope | `headless_app/` |
| Contains | structure + module reference, no code |
| Files | 35 |
| Generated | 2026-09-28 |
| Generator | `scripts/gen_master_copy.py` |
| Regenerate | `.venv/Scripts/python -m scripts.gen_master_copy` |
| Companions | [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) — the whole repository, verbatim, [`project_manager_MASTER_COPY.md`](project_manager_MASTER_COPY.md) — `project_manager/` |

## Overview

`headless_app/` is the **agent half** of agentCreator. `project_manager/` is
the editor/server half, and it imports this package directly — so there is no
agent server, no second port, and no HTTP hop between the UI and the model.
Both halves run in one process.

| Component             | Role                                                                      |
| --------------------- | ------------------------------------------------------------------------- |
| `engine/`             | The think → act → observe runtime, prompt builder, agent loader/registry/factory, pipeline chain |
| `tools/`              | Tool registry, `FileSession` state, chat log, and the file tools that reach the Project Manager |
| `bridge/`             | Project Manager connection layer: sync + async HTTP clients, `DirectProjectIO`, drop-in routers |
| `config/`             | `models.json` (the model picker) and `pipeline.json` (the default cascade) |
| `interface_runner.py` | Programmatic entry point — `AgentInterface`                                |
| `run.py`              | Command-line entry point                                                   |

The `engine/agent_library/` subfolders are agent definitions, not code
modules: each holds an `agent.json` (metadata) and an `agent.md` (the prompt
whose `## role` / `## purpose` sections are folded into the system prompt).
They are described in the Module Reference like every other file.

---

## Entry Points

### `run.py` — command line

```text
python run.py list-agents
python run.py refresh-models
python run.py run-agent rag_assistant --message "what date is it today?"
python run.py run-pipeline --message "idea: add a settings screen" \
    --steps rag_assistant execute_engineer_agent module_builder_agent
```

Useful flags: `--base-url` (Project Manager URL, default
`$PROJECT_MANAGER_BASE_URL` or `http://127.0.0.1:8000`), `--no-bridge` (skip
the bridge and fall back to local-disk tools), and `-m/--model` (override the
agent's own `agent.json` model).

### `interface_runner.py` — programmatic

`AgentInterface` is the thin, stable API over the engine, and the single seam
every caller goes through — the CLI, the Project Manager routers, and any
Python script — so build/think/log behaviour cannot drift between frontends.

| Method                                    | Purpose                                                                                     |
| ----------------------------------------- | ------------------------------------------------------------------------------------------- |
| `run_chat(message, agent_id)`             | One registered agent from any registered root; returns a chat reply                        |
| `run_single_agent(json_path, md_path, ui)` | One ad-hoc agent built from explicit `agent.json` + `agent.md` paths                          |
| `run_pipeline(agent_configs, user_input)` | Ordered feed-forward chain; each step receives the original message plus every earlier reply |

Every run persists the user turn and the reply to `data/chatlog/chat.log` (so
history survives reloads and an agent's `search_chat_logs` tool can recall it)
and records tool events to `data/toollog/tool_usage.jsonl`.

---

## How Project Manager Embeds This Package

`project_manager/interface/routers/chat.py` and
`project_manager/interface/routers/agents.py` each call a small guard,
`_ensure_headless_on_path()`, which resolves `headless_app/` relative to the
router's own location and puts it on `sys.path`. Because the router sits three
levels below the repository root, that is `<repo>/headless_app`. The same
helper in `bridge/routers/` resolves `parents[2]` instead, which is why
`bridge/routers/chat.py` and `bridge/routers/agents.py` are **drop-in
routers** — distributable copies of the Project Manager routers, importable as
`bridge.routers.*`. No server in this repository mounts them; the live
endpoints are the ones under `project_manager/interface/routers/`.

---

## Think → Act → Observe

`engine/core/agent.py` runs one agent per request:

1. `think(user_input)` inserts the system prompt (if absent) and injects a
   `CURRENT FILE SESSION STATE` block, then calls `ask_llm()`.
2. Native `tool_calls` are used when the model supports them; otherwise
   plain-text JSON tool calls are parsed out of the content.
3. Each round calls `act(tool_call, origin)` — normalize the arguments, run
   the tool, record a `tool_events` entry, classify it as success / error /
   missing — followed by `observe(name, result)`, which appends a
   `{"role": "tool", ...}` history entry.
4. The loop is bounded. `MAX_TOOL_ROUNDS = 6` caps the rounds, and
   `REPEAT_LIMIT = 3` trips a guard when an order-independent fingerprint of
   the tool calls repeats three times: the agent is told to stop calling tools
   and answer in plain text, and if it still will not, the loop ends with
   `(The agent kept repeating the same tool call and stopped answering in
   text. Please rephrase your request or ask again.)`
5. A blank final reply falls back to
   `(I ran my tools but did not produce a final answer. Please ask again.)`

`chat` mode attaches no tools at all, so no tool loop can occur. Tool-armed
agents get a grounding block from `engine/agents/factory.py` pinning a real
`WORKSPACE ROOT`, the agent's own folder, and the skills directory, so file
paths are never guessed.

`engine/pipeline.py::run_pipeline` chains agents: every step receives the
original message plus all earlier replies, the last reply is the result, and
the run is appended to `data/pipeline_runs.jsonl` (fail-safe — a logging error
never fails the run).

```text
User -> build_agent(agent_id, model)          agents/factory.py
  -> Agent.think(message)                     core/agent.py
       -> ask_llm(messages, model, tools)     core/llm.py -> Ollama
       -> [tool_calls?]
            -> act(call)     tool runs, event recorded
            -> observe(name, result)
            -> ask_llm(...) again
            (max 6 rounds, repeat-guarded)
       -> reply
```

### The tools

`tools/project_tools.py` holds every executable tool, one function each. The
function's **docstring is what the model sees**: `PromptManager` turns its
first line into the system prompt's AVAILABLE TOOLS section, and Ollama derives
the JSON schema from the name, signature and types.

| Tool id                      | Purpose                                           |
| ---------------------------- | ------------------------------------------------- |
| `map_files`                  | Map a directory tree                              |
| `read_file`                  | Read a workspace file                             |
| `write_text_file`            | Create or overwrite a workspace file              |
| `delete_files`               | Delete files, behind a two-step approval protocol  |
| `get_current_date`           | Today's date                                      |
| `tell_me_the_date_and_time`  | Current date and time                             |
| `search_chat_logs`           | Recall the agent's own chat history               |

File tools run against one of three backends, chosen once via `configure()`:
a Project Manager bridge over HTTP, a **direct** in-process Project Manager
provider (`DirectProjectIO`, used when mounted inside Project Manager), or the
local disk when no provider is configured. Whatever the backend, it exposes the
same small surface — `workspace_root`, `relpath()`, `list_tree()`, `read()`,
`write()`, `create()`, `delete()`, `exists()`.

---

## Agents and configuration

`engine/agent_library/<folder>/` holds an `agent.json` and an `agent.md`. The
folder name is for humans; `agent.json#id` is the id you select in the UI and
pass to `/api/agents/run`. Roots are registered with
`engine/agents/roots.py` — `engine/agent_library/` at import time, and
`workspace/agents/` when the Project Manager starts — and searched
most-recently-registered first, so a workspace agent shadows a library agent
with the same id.

| Folder          | `agent.json#id`           | Mode    | Model                    | Tools                        |
| --------------- | ------------------------ | ------- | ------------------------ | ---------------------------- |
| `rag_assistant` | `rag_assistant`          | `agent` | `gemma4:e2b`             | map, read, write, delete, date, search_chat_logs |
| `Planner`       | `feature_planner_agent`  | `chat`  | `qwen2.5-coder:latest`   | none — `chat` mode takes no tools |
| `Enginner`      | `execute_engineer_agent` | `agent` | `qwen2.5-coder:latest`   | `read_file`                  |
| `Builder`       | `module_builder_agent`   | `agent` | `qwen2.5-coder:latest`   | map, read, write             |

- `config/models.json` — the models offered by the UI picker, each with `id`,
  `name`, `source` and `size`. `refresh_models` re-scans the local Ollama
  install.
- `config/pipeline.json` — the default `module-generation` cascade:
  `feature_planner_agent` → `execute_engineer_agent` →
  `module_builder_agent`, served by `GET /api/pipeline`.

Model and context bounds live in `engine/core/llm.py` (`MAX_NUM_CTX = 32768`).
Failure behaviour is deliberate rather than fatal: an unknown agent id returns
an error string, a model that is not installed falls back to a detected one
with a warning, and a model that does not support tools has its schemas dropped
so the agent answers text-only.


## File Structure

```text
headless_app/
├── bridge/
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── agents.py
│   │   └── chat.py
│   ├── __init__.py
│   ├── client.py
│   ├── providers.py
│   └── tools_adapter.py
├── config/
│   ├── models.json
│   └── pipeline.json
├── data/   # not embedded: runtime output: chat log, tool log, pipeline run records
├── engine/
│   ├── agent_library/
│   │   ├── Builder/
│   │   │   ├── agent.json
│   │   │   └── agent.md
│   │   ├── Enginner/
│   │   │   ├── agent.json
│   │   │   └── agent.md
│   │   ├── Planner/
│   │   │   ├── agent.json
│   │   │   └── agent.md
│   │   └── rag_assistant/
│   │       ├── agent.json
│   │       └── agent.md
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── factory.py
│   │   ├── loader.py
│   │   ├── registry.py
│   │   └── roots.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── llm.py
│   │   └── prompt.py
│   ├── __init__.py
│   └── pipeline.py
├── tools/
│   ├── __init__.py
│   ├── chatlog.py
│   ├── project_tools.py
│   ├── registry.py
│   └── state.py
├── interface_runner.py
└── run.py
```

## Scope

This document covers every source file under `headless_app/`, **35 files** in total, in case-insensitive path order, and describes each one in the Module Reference below. No file bodies are embedded: a master copy is a map, and the code is in [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md).

The following are listed in the structure above but deliberately **not** covered:

| Path | Reason |
| ---- | ------ |
| `data` | runtime output: chat log, tool log, pipeline run records |

Also excluded everywhere: `.git`, `__pycache__/`, virtualenvs, editor and tool caches (`.venv`, `venv`, `.idea`, `.vscode`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`), compiled and runtime artifacts (`*.pyc`, `*.pyo`, `*.log`, `*.dll`).

The three generated documents in `source_files/` are never embedded in each other, so no document can nest inside itself.

Regenerate all three documents with:

```bat
.venv/Scripts/python -m scripts.gen_master_copy
```

Or just this one:

```bat
.venv/Scripts/python -m scripts.gen_master_copy --only headless_app
```

## Module Reference

One entry per file, in the same order as the file structure above. Each entry lists what the file *defines* — its purpose, imports, constants, classes, methods and functions, with signatures and the first line of every docstring. File bodies are not repeated here: every path below is a heading in [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md), which holds the verbatim source.

### `bridge/__init__.py`

**Purpose.** bridge - Project Manager connection layer for the headless engine.
**Imports**
- `from bridge.client import ProjectManagerBridge, AsyncProjectManagerBridge`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `bridge/__init__.py`*

### `bridge/client.py`

**Purpose.** Project Manager bridge clients for the headless engine.
**Imports**
- `from __future__ import annotations`
- `import time`
- `from pathlib import Path`
- `from typing import Any, AsyncIterator, Callable`
- `import httpx`
- `from websockets.asyncio.client import ClientConnection`
- `from websockets.asyncio.client import connect as ws_connect`
**Classes**
- **`ProjectManagerBridge`** *(class)* — Synchronous HTTP bridge to the Project Manager server.
  - **`__init__(self, base_url: str | None=None, timeout: float=30.0)`** *method*
  - **`workspace_root(self)`** *method* — The Project Manager workspace root (from /api/health).
  - **`relpath(self, path: str)`** *method*
  - **`_fresh_tree(self)`** *method*
  - **`list_tree(self)`** *method* — Nested project tree ([{name, path, type, children?, size?}...]).
  - **`read(self, rel: str)`** *method* — Read a workspace text file; returns the content.
  - **`write(self, rel: str, content: str)`** *method*
  - **`create(self, rel: str, content: str)`** *method*
  - **`delete(self, rel: str)`** *method*
  - **`exists(self, rel: str)`** *method*
  - **`_flatten_paths(self)`** *method*
  - **`_get(self, endpoint: str, **params: Any)`** *method*
  - **`_put(self, endpoint: str, params: dict[str, Any] | None=None, payload: dict[str, Any] | None=None)`** *method*
  - **`_post(self, endpoint: str, params: dict[str, Any] | None=None, payload: dict[str, Any] | None=None)`** *method*
  - **`_delete(self, endpoint: str, **params: Any)`** *method*
  - **`health(self)`** *method*
  - **`project(self)`** *method*
  - **`tree(self)`** *method*
  - **`sessions(self)`** *method*
  - **`read_file(self, path: str, scope: str | None=None)`** *method*
  - **`open(self, path: str, scope: str | None=None)`** *method* — Open a project file and return its contents.
  - **`write_file(self, path: str, content: str, scope: str | None=None)`** *method*
  - **`save(self, path: str, content: str, scope: str | None=None)`** *method* — Save file content. Alias for write_file().
  - **`create_file(self, path: str, content: str='', scope: str | None=None)`** *method*
  - **`delete_file(self, path: str, scope: str | None=None)`** *method*
  - **`create_directory(self, path: str, scope: str | None=None)`** *method*
  - **`delete_directory(self, path: str, scope: str | None=None)`** *method*
  - **`rename(self, old_path: str, new_path: str, scope: str | None=None)`** *method*
  - **`subscribe(self, *, timeout: float | None=None)`** *method* — Open a WebSocket and yield Project Manager frames as they arrive.
  - **`expose(self)`** *method* — Self-description: which Project Manager endpoints the bridge uses.
  - **`close(self)`** *method*
  - **`__enter__(self)`** *method*
  - **`__exit__(self, *exc)`** *method*
- **`AsyncProjectManagerBridge`** *(class)* — Asynchronous HTTP + WebSocket bridge to the Project Manager.
  - **`__init__(self, base_url: str | None=None, timeout: float=30.0)`** *method*
  - **`workspace_root(self)`** *async method*
  - **`relpath(self, path: str)`** *method*
  - **`_fresh_tree(self)`** *async method*
  - **`list_tree(self)`** *async method*
  - **`read(self, rel: str)`** *async method*
  - **`write(self, rel: str, content: str)`** *async method*
  - **`create(self, rel: str, content: str)`** *async method*
  - **`delete(self, rel: str)`** *async method*
  - **`exists(self, rel: str)`** *async method*
  - **`_flatten_paths(self)`** *async method*
  - **`_get(self, endpoint: str, **params: Any)`** *async method*
  - **`_put(self, endpoint: str, params: dict[str, Any] | None=None, payload: dict[str, Any] | None=None)`** *async method*
  - **`_post(self, endpoint: str, params: dict[str, Any] | None=None, payload: dict[str, Any] | None=None)`** *async method*
  - **`_delete(self, endpoint: str, **params: Any)`** *async method*
  - **`health(self)`** *async method*
  - **`project(self)`** *async method*
  - **`tree(self)`** *async method*
  - **`sessions(self)`** *async method*
  - **`read_file(self, path: str, scope: str | None=None)`** *async method*
  - **`open(self, path: str, scope: str | None=None)`** *async method*
  - **`write_file(self, path: str, content: str, scope: str | None=None)`** *async method*
  - **`save(self, path: str, content: str, scope: str | None=None)`** *async method*
  - **`create_file(self, path: str, content: str='', scope: str | None=None)`** *async method*
  - **`delete_file(self, path: str, scope: str | None=None)`** *async method*
  - **`create_directory(self, path: str, scope: str | None=None)`** *async method*
  - **`delete_directory(self, path: str, scope: str | None=None)`** *async method*
  - **`rename(self, old_path: str, new_path: str, scope: str | None=None)`** *async method*
  - **`subscribe(self)`** *async method* — Open a WebSocket and yield Project Manager event frames.
  - **`expose(self)`** *async method*
  - **`close(self)`** *async method*
**Functions**
- **`_default_base_url()`** *function* — Best-effort default: localhost on the standard Project Manager port.
- **`_apply_project_root(path: str, project_root: str='')`** *function* — Normalize a project-relative path into the API path form.
- **`_raise_for_error(response: httpx.Response)`** *function* — Turn a non-2xx response into a useful Python error.
- **`_decode_message(message: Any)`** *function* — Turn a raw WebSocket message into a dict (bytes or str payload).
- **`_normalize(raw: str)`** *function*
- **`_relpath(root: Path, path: str)`** *function* — Translate an absolute-or-relative path into a posix relative path that stays inside the Project Manager workspace root. The root itself maps to "". R…

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `bridge/client.py`*

### `bridge/providers.py`

**Purpose.** In-process Project Manager filesystem authority.
**Imports**
- `from __future__ import annotations`
- `from pathlib import Path`
- `from typing import Any`
- `from bridge.client import _relpath`
**Classes**
- **`DirectProjectIO`** *(class)* — Filesystem provider backed directly by the Project Manager's parameters.filesystem authority.
  - **`__init__(self)`** *method*
  - **`workspace_root(self)`** *method*
  - **`relpath(self, path: str)`** *method*
  - **`list_tree(self)`** *method*
  - **`read(self, rel: str)`** *method*
  - **`write(self, rel: str, content: str)`** *method*
  - **`create(self, rel: str, content: str)`** *method*
  - **`delete(self, rel: str)`** *method*
  - **`exists(self, rel: str)`** *method*
  - **`health(self)`** *method*
  - **`tree(self)`** *method*
  - **`project(self)`** *method*
  - **`sessions(self)`** *method*
  - **`expose(self)`** *method*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `bridge/providers.py`*

### `bridge/routers/__init__.py`

**Purpose.** bridge.routers - drop-in FastAPI routers for the Project Manager.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `bridge/routers/__init__.py`*

### `bridge/routers/agents.py`

**Purpose.** Agent registry, run, and pipeline endpoints for the Project Manager.
**Imports**
- `from __future__ import annotations`
- `import json`
- `import sys`
- `from pathlib import Path`
- `from typing import Any`
- `from fastapi import APIRouter, Request`
- `from pydantic import BaseModel`
- `from .errors import project_manager_error`
- `from .chat import MAX_MESSAGE_LENGTH, _mirror_pm_log`
- `from engine.agents.factory import build_agent, build_agent_from_definition`
- `from engine.agents.loader import AgentNotFoundError`
- `from engine.agents.registry import list_agents`
- `from engine.pipeline import load_pipeline, run_pipeline`
- `from tools.chatlog import append_chat`
**Classes**
- **`AgentRunRequest`** *(class, BaseModel)*
- **`PipelineRunRequest`** *(class, BaseModel)*
**Functions**
- **`_ensure_headless_on_path()`** *function*
- **`_pm_filesystem()`** *function* — parameters.filesystem when running inside the Project Manager.
- **`_workspace()`** *function*
- **`_resolve(relative_path: str)`** *function* — Safe absolute path for a workspace-relative agent file path.
- **`_provider()`** *function*
- **`_workspace_agents()`** *function* — Scan <workspace>/agents/*/agent.json for runnable agent definitions.
- **`_all_agents()`** *function*
- **`_record_entries(user_message: str, reply: str)`** *function*
- **`_validated_message(message: str)`** *function*
- **`list_all_agents(request: Request)`** *function* — Return every runnable agent: library (engine/agent_library/) and workspace (workspace/agents/<name>/) definitions.
  - *decorator:* `@router.get('/api/agents')`
- **`get_agent_definition(request: Request, agent_id: str)`** *function* — Return one agent's metadata + markdown sections. Workspace agents (agents/<id>/) win over library agents with the same id.
  - *decorator:* `@router.get('/api/agents/{agent_id}')`
- **`run_single_agent(request: Request, payload: AgentRunRequest)`** *function* — Build and run one agent, then log the exchange.
  - *decorator:* `@router.post('/api/agents/run')`
- **`pipeline_options(request: Request)`** *function* — Return the default step chain (config/pipeline.json) plus every selectable step candidate (library + workspace agents).
  - *decorator:* `@router.get('/api/pipeline')`
- **`run_agent_pipeline(request: Request, payload: PipelineRunRequest)`** *function* — Cascade many agents one after another.
  - *decorator:* `@router.post('/api/pipeline')`
- **`list_models(request: Request)`** *function* — Return the models in config/models.json for the frontend picker. Run refresh_models to re-scan installed Ollama models.
  - *decorator:* `@router.get('/api/models')`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `bridge/routers/agents.py`*

### `bridge/routers/chat.py`

**Purpose.** Agent-backed Project Manager chat router (drop-in replacement).
**Imports**
- `from __future__ import annotations`
- `import json`
- `import sys`
- `from pathlib import Path`
- `from typing import Any`
- `from fastapi import APIRouter, Request`
- `from pydantic import BaseModel`
- `from .errors import project_manager_error`
- `from engine.agents.factory import build_agent`
- `from engine.agents.loader import AgentNotFoundError`
- `from engine.agents.registry import list_agents`
- `from tools.chatlog import append_chat, read_history`
**Constants**
- `MAX_MESSAGE_LENGTH` = `2000`
- `DEFAULT_LIMIT` = `50`
- `MAX_LIMIT` = `500`
**Classes**
- **`ChatMessage`** *(class, BaseModel)*
**Functions**
- **`_ensure_headless_on_path()`** *function*
- **`_provider()`** *function* — The active filesystem authority (in-process Project Manager).
- **`_default_agent_id()`** *function*
- **`_mirror_pm_log(entry: dict)`** *function* — Mirror one chat entry into the Project Manager's own chat.log.
- **`_record_entries(user_message: str, reply: str)`** *function* — Persist user + reply to the headless chat log; mirror to PM's log.
- **`send_chat_message(request: Request, payload: ChatMessage)`** *function* — Send a message to the agent engine and return its reply.
  - *decorator:* `@router.post('/api/chat')`
- **`get_chat_history(request: Request, limit: int=DEFAULT_LIMIT)`** *function* — Return the most recent chat entries.
  - *decorator:* `@router.get('/api/chat')`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `bridge/routers/chat.py`*

### `bridge/tools_adapter.py`

**Purpose.** Maps the headless agent tools to their Project Manager HTTP surface and binds a bridge to the tool registry.
**Imports**
- `from __future__ import annotations`
- `from typing import Any`
- `import tools.registry as _registry`
**Constants**
- `TOOL_ENDPOINT_MAP` = `{'map_files': 'GET /api/project (filesystem tree)', 'read_file': 'GET /api/file/read', 'w…`
**Functions**
- **`bind_tools(bridge: Any)`** *function* — Point the tool registry's file tools at a Project Manager provider.
- **`unbind_tools()`** *function* — Return the file tools to the local-disk backend.
- **`describe_tools()`** *function* — Return the tool-id -> endpoint map for documentation/debugging.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `bridge/tools_adapter.py`*

### `config/models.json`

**Top-level keys (1).**
- `models` = list of 4 objects

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `config/models.json`*

### `config/pipeline.json`

**Top-level keys (3).**
- `name` = "module-generation"
- `description` = "One idea -> a working drop-in custom module. Step 1 drafts the feature plan, Step 2 turn…
- `steps` = ["feature_planner_agent", "execute_engineer_agent", "module_builder_agent"]

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `config/pipeline.json`*

### `engine/__init__.py`

*(no symbols extracted)*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/__init__.py`*

### `engine/agent_library/Builder/agent.json`

**Top-level keys (6).**
- `id` = "module_builder_agent"
- `name` = "Module Builder Agent"
- `description` = "Step 3: Confirms the target save location, then compiles Step 2 blueprints into complete…
- `mode` = "agent"
- `model` = "qwen2.5-coder:latest"
- `tools` = ["map_files", "read_file", "write_text_file"]

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agent_library/Builder/agent.json`*

### `engine/agent_library/Builder/agent.md`

**Purpose.** You are the **Module Builder Agent** (Step 3 of the agentCreator Module Development Pipeline). Your role is to take a Stage 2 Technical Implementation Blueprint provided directly in the user's message and compile it into a single…
# Module Builder Agent
## role
## purpose
## tools
## do_not_hallucinate
## input_contract
## workflow
### Phase 1: UI Phase (`UI_MANIFEST` Declaration)
### Phase 2: Logic & Server Endpoints Phase (`register_routes` + Real-Time Logging)
### Phase 3: Variable Map & Extension Architecture
## boundaries
## output_format
# ==============================================================================
# PHASE 1: UI PHASE (UI_MANIFEST Declaration)
# ==============================================================================
# ==============================================================================
# PHASE 2: LOGIC & SERVER ENDPOINTS PHASE (register_routes + Real-Time Logging)
# ==============================================================================
# ==============================================================================
# PHASE 3: VARIABLE ARCHITECTURE MAP & EXTENSION HOOKS
# ==============================================================================

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agent_library/Builder/agent.md`*

### `engine/agent_library/Enginner/agent.json`

**Top-level keys (6).**
- `id` = "execute_engineer_agent"
- `name` = "Execute Engineer Agent"
- `description` = "Step 2: Uses read_file to inspect ux_module_designer_skills.md and translates Step 1 fun…
- `mode` = "agent"
- `model` = "qwen2.5-coder:latest"
- `tools` = ["read_file"]

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agent_library/Enginner/agent.json`*

### `engine/agent_library/Enginner/agent.md`

**Purpose.** You are the **Execute Engineer Agent** (Step 2). Your role is to take the functional feature list from Step 1 and translate it into structured pseudo-code and Python implementation blueprints grounded strictly in the agentCreator skills…
# Execute Engineer Agent
## role
## purpose
## input_contract
## skills
## workflow
## boundaries
## output_format
### 1. Executive Summary
### 2. UI Manifest Specification
### 3. Backend Route Handlers (`register_routes`)
### 4. Path & Core Wiring Integration

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agent_library/Enginner/agent.md`*

### `engine/agent_library/Planner/agent.json`

**Top-level keys (6).**
- `id` = "feature_planner_agent"
- `name` = "Feature Planner Agent"
- `description` = "Step 1: Translates raw feature ideas into a functional specification list (UI actions, e…
- `mode` = "chat"
- `model` = "qwen2.5-coder:latest"
- `tools` = []

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agent_library/Planner/agent.json`*

### `engine/agent_library/Planner/agent.md`

*(no headings)*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agent_library/Planner/agent.md`*

### `engine/agent_library/rag_assistant/agent.json`

**Top-level keys (7).**
- `id` = "rag_assistant"
- `name` = "RAG Assistant"
- `description` = "Stateful agent with workspace file-management access and memory retrieval."
- `mode` = "agent"
- `model` = "gemma4:e2b"
- `tools` = ["map_files", "read_file", "write_text_file", "delete_files", "get_current_date", "search…
- `tests` = list of 1 objects

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agent_library/rag_assistant/agent.json`*

### `engine/agent_library/rag_assistant/agent.md`

**Purpose.** You are the **RAG Assistant**, a secure workspace file-manager and memory-retrieval specialist.
# RAG Assistant
## role
## greeting
## purpose
## boundaries
## how to call tools (critical)
## safe deletion protocol (two-step confirmation)

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agent_library/rag_assistant/agent.md`*

### `engine/agents/__init__.py`

*(no symbols extracted)*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agents/__init__.py`*

### `engine/agents/factory.py`

**Purpose.** Constructs runtime Agents from agent definitions.
**Imports**
- `from typing import Callable`
- `from pathlib import Path`
- `from engine.agents.loader import load_definition, load_definition_from_paths, agent_dir, AgentNotFoundError`
- `from engine.core.agent import Agent`
- `from engine.core.prompt import PromptManager`
- `from tools.registry import new_session, resolve_tools`
**Classes**
- **`AgentDefinitionError`** *(class, ValueError)* — A definition parsed, but cannot produce a working agent.
**Functions**
- **`_session_aware(func: Callable, session)`** *function* — Wrap a tool so its results are recorded into this agent's FileSession.
- **`_bind_delete_args(func, args, kwargs)`** *function* — Bind delete_files(*args, **kwargs) into (BoundArguments, approved, file_list).
- **`_record_result(result, session)`** *function* — Translate a tool result dict into this agent's FileSession state.
- **`_append_grounding(agent_id: str, profile, bridge=None)`** *function* — Append a compact grounding block to a tool-armed agent's system prompt.
- **`_assemble(meta: dict, sections: dict, agent_id: str, model: str | None, bridge=None)`** *function* — Shared Agent construction from a parsed definition.
- **`build_agent(agent_id: str, model: str | None=None, bridge=None)`** *function* — Build a ready-to-use Agent for the given agent_id.
- **`build_agent_from_definition(json_path: str, md_path: str, model: str | None=None, bridge=None)`** *function* — Build a ready-to-use Agent from explicit agent.json + agent.md paths.
- **`replay_history(agent: Agent, history: list[dict] | None)`** *function* — Replay prior frontend turns ({role, content}) into the agent's history.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agents/factory.py`*

### `engine/agents/loader.py`

**Purpose.** Locates, reads, and parses one agent definition.
**Imports**
- `import json`
- `import re`
- `from pathlib import Path`
- `from engine.agents import roots`
- `from engine.agents.roots import AGENT_MD_FILE, AGENT_META_FILE, AgentRoot, LIBRARY_ROOT_NAME, register_agent_root, unregister_agent_root`
**Constants**
- `AGENT_LIBRARY_DIR`
**Classes**
- **`AgentNotFoundError`** *(class, FileNotFoundError)* — Raised when an agent folder or its required files are missing.
**Functions**
- **`agent_dir(agent_id: str)`** *function* — The folder for an agent id inside the highest-precedence root.
- **`agent_root(agent_id: str)`** *function* — The registered root that owns ``agent_id``, or None.
- **`agent_json_path(agent_id: str)`** *function* — Workspace-relative ``agent.json`` path for a registered agent.
- **`agent_md_path(agent_id: str)`** *function* — Workspace-relative ``agent.md`` path for a registered agent.
- **`_resolve_agent_dir(agent_id: str)`** *function* — Find the on-disk folder for an agent by id across all roots.
- **`save_meta(agent_id: str, meta: dict)`** *function* — Merge `meta` into the agent's agent.json (top-level keys only) and write it back pretty-printed. Unknown keys survive untouched.
- **`save_markdown(agent_id: str, markdown: str)`** *function* — Write the agent's behavior prose to agent.md.
- **`save_tests(agent_id: str, tests: list)`** *function* — Store the agent's own chat tests under agent.json#tests.
- **`_parse_sections(text: str)`** *function* — Split agent.md into '## <name>' sections (section name lowercased).
- **`_clean_body(text: str)`** *function* — Trim blank lines and '---' separators from the edges of a section body.
- **`load_definition(agent_id: str)`** *function* — Load one agent definition from agent_library/{agent_id}/.
- **`load_definition_from_paths(json_path: str | Path, md_path: str | Path)`** *function* — Load one agent definition from explicit agent.json + agent.md paths.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agents/loader.py`*

### `engine/agents/registry.py`

**Purpose.** Agent discovery over the registered roots (engine/agents/roots.py).
**Imports**
- `import json`
- `from engine.agents import roots`
- `from engine.agents.loader import AGENT_LIBRARY_DIR`
**Functions**
- **`_read_meta(agent_dir)`** *function* — Parsed agent.json, or None when missing/unreadable/malformed.
- **`list_agents()`** *function* — One summary per discovered agent, highest-precedence root first.
- **`get_agent_meta(agent_id: str)`** *function* — Return the summary for one agent id, or None if not registered.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agents/registry.py`*

### `engine/agents/roots.py`

**Purpose.** Pluggable agent roots.
**Imports**
- `from __future__ import annotations`
- `import json`
- `from dataclasses import dataclass`
- `from pathlib import Path`
- `from typing import Iterator`
**Constants**
- `AGENT_META_FILE` = `'agent.json'`
- `AGENT_MD_FILE` = `'agent.md'`
- `LIBRARY_ROOT_NAME` = `'library'`
- `DEFAULT_LIBRARY_DIR`
**Classes**
- **`AgentRoot`** *(dataclass)* — One directory of agent folders.
  - *decorator:* `@dataclass(frozen=True)`
  - **`agent_dirs(self)`** *method* — Yield every candidate agent folder, sorted for determinism.
  - **`json_path(self, agent_dir: Path)`** *method* — Workspace-relative ``agent.json`` path for the agent API.
  - **`md_path(self, agent_dir: Path)`** *method* — Workspace-relative ``agent.md`` path for the agent API.
**Functions**
- **`register_agent_root(name: str, path: str | Path, source: str | None=None)`** *function* — Register (or re-register) an agent root and give it top precedence.
- **`unregister_agent_root(name: str)`** *function* — Remove a root by name. Returns True when something was removed.
- **`agent_roots()`** *function* — Registered roots, highest precedence first.
- **`get_root(name: str)`** *function*
- **`reset_agent_roots()`** *function* — Drop every root except the built-in library root (used by tests).
- **`_read_meta(agent_dir: Path)`** *function*
- **`find_agent(agent_id: str)`** *function* — Locate an agent folder by id across every registered root.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/agents/roots.py`*

### `engine/core/__init__.py`

*(no symbols extracted)*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/core/__init__.py`*

### `engine/core/agent.py`

**Purpose.** The reusable runtime agent.
**Imports**
- `import inspect`
- `import json`
- `import re`
- `from datetime import datetime`
- `from dataclasses import dataclass, field`
- `from typing import Callable, List`
- `from engine.core.llm import ask_llm`
- `from tools.state import FileSession`
**Classes**
- **`AgentProfile`** *(dataclass)* — Identity + behavior of one agent.
  - *decorator:* `@dataclass`
- **`Agent`** *(class)* — A generic AI agent that can think (ask the LLM), act (call a tool) and observe (record the tool's result back into the conversation).
  - **`__init__(self, model: str | None, tools: List[Callable], profile: AgentProfile, session: FileSession | None=None)`** *method* — Store the model, tools, profile, and optional FileSession.
  - **`_extract_text_tool_calls(self, content: str)`** *method* — Find tool calls that a model wrote as plain-text JSON instead of using Ollama's native tool_calls field (a common quirk of small local models).
  - **`_has_required_args(self, name: str, args: dict)`** *method* — True when every required (no-default) parameter of the tool is present in args. Prevents executing narration that merely mentions a tool.
  - **`_normalize_args(self, name: str, args)`** *method* — Coerce the many different argument shapes small local models send for tool calls into a clean dict of keyword args the tool actually accepts.
  - **`_coerce_bools(args: dict, bool_params: set)`** *method* — Turn string 'true'/'false'/'1'/'0' into real bools, but ONLY for parameters that are actually typed as bool (so a string param like name="yes" is nev…
  - **`_round_signature(tool_calls)`** *method* — Order-independent, hashable fingerprint of one tool round so two rounds with the same calls and same arguments compare as identical.
  - **`think(self, user_input: str)`** *method* — Add user input to history, send the conversation to the LLM, and return its reply.
  - **`_inject_session_context(self)`** *method* — Add current FileSession state as context for the model, replacing any previously injected block so history doesn't grow duplicate state.
  - **`_op_succeeded(result)`** *method* — Classify a tool's result as (ok, error_msg).
  - **`act(self, tool_call: dict, origin: str='')`** *method* — Run one tool that the LLM asked for, using the name and args it chose.
  - **`_log_tool_event(self, event: dict)`** *method* — Report one structured tool event to the process-wide tool log (headless data/toollog/tool_usage.jsonl). Deliberately fail-safe so a logging problem c…
  - **`observe(self, name: str, result: str)`** *method* — Record a tool's result back into the conversation history.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/core/agent.py`*

### `engine/core/llm.py`

**Purpose.** The LLM backend. Everything that talks to Ollama lives here:
**Imports**
- `import json`
- `import time`
- `from pathlib import Path`
- `from typing import Callable, List`
- `import ollama`
**Constants**
- `MAX_NUM_CTX` = `32768`
- `CONFIG_DIR`
- `_MODEL_SCAN_TTL` = `60.0`
**Functions**
- **`_config_model_ids()`** *function* — The model ids in config/models.json (re-scanned by refresh_models() at every server startup, so it reflects THIS machine's Ollama).
- **`_installed_model_ids()`** *function* — Ordered ids of installed Ollama models, cached briefly.
- **`_capabilities(model: str)`** *function* — The reported capabilities for `model` (['completion', 'tools', ...]).
- **`_supports_tools(model: str)`** *function* — True/False when Ollama reports capabilities, None when unknown.
- **`_resolve_model(model: str | None, require_tools: bool=False)`** *function* — Pick which model to use: explicit arg (when suitable) > config > Ollama list.
- **`_get_context_window(model: str)`** *function* — Return the model's max context length from Ollama, capped; None if unknown.
- **`ask_llm(messages: List[dict], model: str | None=None, tools: List[Callable] | None=None)`** *function* — Send structured messages to the resolved model via Ollama and return the full message dict.
- **`scan_models()`** *function* — Return the deduped list of locally installed Ollama models.
- **`refresh_models()`** *function* — Scan Ollama and write config/models.json (returns the model list).

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/core/llm.py`*

### `engine/core/prompt.py`

**Purpose.** PromptManager: converts an agent definition (agent.json + parsed agent.md sections) plus the agent's resolved tools into an AgentProfile with a composed system prompt.
**Imports**
- `from dataclasses import field`
- `from typing import Callable, List`
- `from engine.core.agent import AgentProfile`
**Constants**
- `KNOWN_SECTIONS` = `('role', 'purpose', 'personality', 'boundaries', 'communication', 'principles', 'decision…`
- `PROMPT_SECTIONS`
**Classes**
- **`PromptManager`** *(class)* — Builds an AgentProfile from an agent definition and composes the system prompt.
  - **`build(definition: dict, tools: List[Callable] | None=None)`** *method* — Build an AgentProfile.
  - **`compose_system_prompt(profile: AgentProfile, tools: List[Callable] | None=None)`** *method* — Build the final system prompt from profile sections.
  - **`_tool_lines(tools: List[Callable] | None)`** *method* — Format tool callables as '- id: first docstring line' lines.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/core/prompt.py`*

### `engine/pipeline.py`

**Purpose.** Runs the ordered agent chain from config/pipeline.json so a single user idea can travel Step 1 -> Step 2 -> Step 3 automatically.
**Imports**
- `import json`
- `from datetime import datetime`
- `from pathlib import Path`
- `from engine.agents.factory import build_agent, build_agent_from_definition`
**Constants**
- `CONFIG_FILE`
- `_STEP_FEED_TEMPLATE` = `'Below is what the previous pipeline step ({name}) produced.\nUse it as your required inp…`
**Functions**
- **`_iso_now()`** *function*
- **`_records_file()`** *function* — pipeline_runs.jsonl inside the headless data directory.
- **`_record_run(snapshot: dict)`** *function* — Append one JSONL line per pipeline run. Fail-safe: a recording failure never breaks the run itself (same philosophy as the tool log).
- **`load_pipeline(config_path=None)`** *function* — Ordered step configs from config/pipeline.json ([] when missing/broken).
- **`_build_step(step, model: str | None, bridge=None)`** *function* — Build the Agent for one pipeline step.
- **`_step_label(step)`** *function*
- **`run_pipeline(user_message: str, model: str | None=None, config_path=None, steps: list | None=None, bridge=None)`** *function* — Run every step in order; return {reply, outputs, tool_events}.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `engine/pipeline.py`*

### `interface_runner.py`

**Purpose.** The single execution seam of the agentCreator engine.
**Imports**
- `from __future__ import annotations`
- `import json`
- `from typing import Any, Callable`
- `from engine.agents.factory import build_agent, build_agent_from_definition, replay_history`
- `from engine.agents.registry import get_agent_meta, list_agents`
- `from engine.pipeline import run_pipeline as _run_pipeline`
- `from tools.chatlog import append_chat, read_history`
**Constants**
- `DEFAULT_HISTORY_LIMIT` = `20`
**Classes**
- **`AgentInterface`** *(class)* — Thin, stable API over the build/think loop and pipeline chain.
  - **`__init__(self, bridge: Any=None, model: str | None=None, log_sink: Callable[[dict], None] | None=None)`** *method* — Create a runner.
  - **`_log(self, sender: str, message: str, agent_id: str)`** *method* — Write one chat log entry and hand it to the sink.
  - **`_think(self, agent: Any, message: str, agent_id: str, history: list[dict] | None)`** *method* — Replay history, run one turn, and log both sides.
  - **`run_chat(self, message: str, agent_id: str | None=None, model: str | None=None, history: list[dict] | None=None, use_logged_history: bool=True)`** *method* — Run one agent and return its reply.
  - **`run_single_agent(self, user_input: str, json_path: str | None=None, md_path: str | None=None, agent_id: str | None=None, model: str | None=None, history: list[dict] | None=None, use_logged_history: bool=False)`** *method* — Run one agent built from explicit agent.json + agent.md paths.
  - **`run_pipeline(self, user_input: str, agent_configs: list | None=None, model: str | None=None)`** *method* — Run the ordered agent chain (feed-forward).
  - **`_default_agent_id(self)`** *method*
  - **`list_agents(self)`** *method* — Every agent across every registered root (see registry).
  - **`get_agent(self, agent_id: str)`** *method* — Metadata for one agent id, or None when it is not registered.
  - **`__repr__(self)`** *method*
**Functions**
- **`_as_history(agent_id: str | None, limit: int | None=DEFAULT_HISTORY_LIMIT)`** *function* — Read one agent's recent turns from the chat log as model messages.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface_runner.py`*

### `run.py`

**Purpose.** Command-line entry point for the headless agentCreator engine.
**Imports**
- `from __future__ import annotations`
- `import argparse`
- `import json`
- `import sys`
- `from pathlib import Path`
- `from interface_runner import AgentInterface`
- `from engine.core.llm import refresh_models`
- `from engine.agents.registry import list_agents`
**Functions**
- **`_build_bridge(args)`** *function*
- **`_read_message(args)`** *function*
- **`cmd_list_agents(args)`** *function*
- **`cmd_refresh_models(args)`** *function*
- **`_print_run(result: dict, args)`** *function*
- **`cmd_run_agent(args)`** *function*
- **`cmd_run_pipeline(args)`** *function*
- **`_parser()`** *function*
- **`main(argv: list[str] | None=None)`** *function*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `run.py`*

### `tools/__init__.py`

*(no symbols extracted)*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `tools/__init__.py`*

### `tools/chatlog.py`

**Purpose.** Headless data store.
**Imports**
- `import json`
- `from datetime import datetime, timezone`
- `from pathlib import Path`
**Constants**
- `DATA_DIR`
- `CHATLOG_DIR`
- `CHATLOG_FILE`
- `TOOLLOG_DIR`
- `TOOLLOG_FILE`
- `MAX_MESSAGE_LENGTH` = `2000`
- `DEFAULT_HISTORY_LIMIT` = `50`
- `MAX_HISTORY_LIMIT` = `500`
**Functions**
- **`_iso_ts()`** *function*
- **`append_chat(sender: str, message: str, agent: str | None=None)`** *function* — Append one timestamped chat entry. Returns the stored entry dict.
- **`read_history(limit: int=DEFAULT_HISTORY_LIMIT, agent: str | None=None)`** *function* — Most recent chat entries in chronological order.
- **`clear_chat(agent: str | None=None)`** *function* — Wipe the chat log entirely. Returns how many entries were removed.
- **`search_text(query: str, limit: int=15)`** *function* — Case-folded substring search over the chat log, newest first.
- **`append_tool_event(event: dict)`** *function* — Append one JSONL tool-event line. Fail-safe (never raise).

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `tools/chatlog.py`*

### `tools/project_tools.py`

**Purpose.** Every executable tool in the headless runtime, consolidated into one module.
**Imports**
- `import os`
- `import sys`
- `from contextlib import contextmanager`
- `from contextvars import ContextVar`
- `from pathlib import Path`
- `from typing import Any`
- `from tools.chatlog import search_text as _search_chatlog`
**Constants**
- `_PLAIN_TEXT_EXTENSIONS` = `{'.js', '.markdown', '.cfg', '.css', '.yaml', '.py', '.md', '.ini', '.sass', '.ts', '.tom…`
- `_DOCLING_CONVERTERS` = `{}`
- `DEFAULT_IGNORE_DIRS` = `{'.git', '.vscode', 'venv', 'node_modules', '.venv', '__pycache__', '.idea'}`
- `ROOT_DIR`
**Functions**
- **`configure(provider: Any)`** *function* — Set the process-wide default provider (None for local disk).
- **`current_provider()`** *function* — The provider in force right now: the per-call binding, else the default.
- **`using(provider: Any)`** *function* — Activate ``provider`` for the duration of the block.
  - *decorator:* `@contextmanager`
- **`_is_plain_text(path)`** *function* — True for files whose raw text is already the well-formatted content.
- **`_unquote_path(value)`** *function* — Strip one level of surrounding quotes a model may have left on a path.
- **`_docling_converter(ocr: bool)`** *function* — Return a cached, lazily-created Docling DocumentConverter.
- **`_convert_with_docling(path: Path, ocr: bool)`** *function* — Return Docling markdown for a binary document, or None when unavailable.
- **`_read_local_file(p: Path, ocr: bool)`** *function* — Read a file from the local disk (text direct, binary via Docling).
- **`read_file(path: str, ocr: bool=True)`** *function* — Reads a file and returns its content as well-formatted text (markdown).
- **`_flatten_tree(entries: list, prefix: str='')`** *function* — Flatten a nested provider tree into one flat list of {path, type, name, size}.
- **`_map_entries_local(root: Path)`** *function* — os.walk the local disk; returns flat {name, path, type, level} entries.
- **`map_files(path: str, max_depth: int=8, max_entries: int=5000)`** *function* — Inspects a directory and returns a structured list of its files and folders.
- **`write_text_file(name: str, content: str, output_path: str, overwrite: bool=False)`** *function* — Creates a text file containing the given content.
- **`delete_files(file_list: list, approved: bool=False)`** *function* — Deletes files ONLY after explicit approval has been given.
- **`get_current_date()`** *function* — Returns the real current calendar date (e.g. 'Monday, January 05, 2026').
- **`tell_me_the_date_and_time()`** *function* — Returns the current date and time down to the second.
- **`search_chat_logs(query: str)`** *function* — Searches past chat transcripts for a keyword and returns the matching segments.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `tools/project_tools.py`*

### `tools/registry.py`

**Purpose.** Central tool registry. Maps tool IDs (strings used in agent.json) to Python callables. Agents declare which tools they need by ID; the factory resolves those IDs here into actual functions.
**Imports**
- `from typing import Any, Callable`
- `from tools.project_tools import configure as _configure_provider, map_files, read_file, write_text_file, delete_files, get_current_date, tell_me_the_date_and_time, search_chat_logs, using as _using_provider`
- `from tools.state import FileSession`
**Constants**
- `_TOOL_REGISTRY`
**Functions**
- **`_bind(func: Callable, provider: Any)`** *function* — Return ``func`` with ``provider`` active for the duration of each call.
- **`configure(provider=None)`** *function* — Set the process-wide default provider (or None for local disk).
- **`get(tool_name: str)`** *function* — Retrieve an executable tool by its registered name.
- **`list_tools()`** *function* — Returns a list of all registered tool names.
- **`available_tool_ids()`** *function* — Backward-compatible alias for list_tools().
- **`resolve_tools(tool_ids: list[str], provider: Any=None)`** *function* — Map a list of tool ID strings to their callable functions.
- **`new_session()`** *function* — Create a FileSession owned by exactly one agent.
- **`get_session()`** *function* — Return the shared default FileSession instance.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `tools/registry.py`*

### `tools/state.py`

**Purpose.** Shared working state for the file-management tools.
**Classes**
- **`FileSession`** *(class)* — Manages file-management working state for AI agents dynamically.
  - **`__init__(self)`** *method*
  - **`add_discovered(self, paths: list)`** *method* — Record files/directories surfaced by map_files (deduplicated).
  - **`select_files(self, paths: list)`** *method* — Mark paths as the agent's active working set (deduplicated).
  - **`record_read(self, path: str, content: str)`** *method* — Remember that a path was read and cache its extracted content.
  - **`add_output(self, path: str)`** *method* — Remember a path produced by the write tool (deduplicated).
  - **`mark_for_deletion(self, paths: list)`** *method* — Propose paths for deletion (deduplicated; approval happens later).
  - **`get_state(self)`** *method* — Snapshot the current session state for injection into the prompt.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `tools/state.py`*


---

> Generated by `scripts/gen_master_copy.py` on 2026-09-28. Do not edit by hand; regenerate with:
>
> ```bat
> .venv/Scripts/python -m scripts.gen_master_copy
> ```
