# agentCreator — Project Manager Master Copy

The `project_manager/` half of agentCreator: the FastAPI workspace server, its editor interface, and the managed workspace. File structure plus a description of every module, class and function.

| Field | Value |
| ----- | ----- |
| Scope | `project_manager/` |
| Contains | structure + module reference, no code |
| Files | 48 |
| Generated | 2026-09-29 |
| Generator | `scripts/gen_master_copy.py` |
| Regenerate | `.venv/Scripts/python -m scripts.gen_master_copy` |
| Companions | [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) — the whole repository, verbatim, [`headless_app_MASTER_COPY.md`](headless_app_MASTER_COPY.md) — `headless_app/` |

## Overview

`project_manager/` is the **server and interface half** of agentCreator. It is
a single FastAPI process that browses and edits a managed workspace, serves the
editor and chat pages, and hosts the `headless_app` engine in-process. The
agent engine is reached over HTTP routes owned by this app, but it runs inside
the same process — there is no second server and no HTTP hop to the model.

| Component        | Role                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| `server.py`      | Slim FastAPI host: assembles the pillars, mounts the routers, registers the workspace agent root |
| `parameters/`    | Project parameters — `filesystem.py` is the single filesystem authority     |
| `interface/`     | Editor interface — `core` (controller), `routers` (HTTP), `clients` (Python), `static` (the web UI) |
| `workspace/`     | The managed project: `project.json`, `agents/`, `documentation/`, `project_scope/`, `to_do/`, `updates/`, `config/`, `data/` |
| `scripts/`       | `run.bat` / `run.sh` / `setup.sh`, using the shared `..\.venv`             |

```text
parameters/     Project parameters — filesystem.py is the filesystem owner
interface/      Editor interface — core (controller), routers (HTTP), clients, static
workspace/      The managed project content (project.json, agents/, documentation/, …)
scripts/        run.bat / run.sh / setup.sh, using the shared ..\.venv
server.py       Slim FastAPI host: assembles the pillars, mounts the routers
```

`interface/core/defaults.py` builds the single shared controller, event bus and
session pool that every router, the browser and the Python client all use.
`interface/core/operations.py` is the only place operations are defined, and
every filesystem call it makes is delegated to `parameters/filesystem.py` — the
server itself contains no filesystem logic.

`parameters/filesystem.py` also owns the two **browser roots** the file tree
shows, keyed by the path prefixes the API understands: `workspace` (the
managed project, writable) and `source_files` (this documentation folder,
browse-only). So `workspace/project.json` and
`source_files/APP_CODE_SNAPSHOT.md` each resolve inside their own root.

The dashboard and editor operate in two scopes: **Workspace** (the managed
project, the default) and **Dev** (the application's own files), toggled in the
sidebar.

---

## AI Agent Engine — Entry Point

`/api/chat` is the **AI agent engine entry point**, and it runs a real agent
rather than appending to a log. Every surface — the home page, the editor, the
chat page — reaches the engine through the same stable HTTP contract, so the
engine can be swapped without touching the UI.

| Route       | Method | Purpose                                                                                   |
| ----------- | ------ | ----------------------------------------------------------------------------------------- |
| `/api/chat` | POST   | Send a message. Body: `{"message": str, "agent_id": str?, "model": str?}`. Returns `{status, reply, agent_id, model, tool_events}`. |
| `/api/chat` | GET    | Fetch recent agent conversation history (`?limit=`, default 50, max 500).                  |
| `/api/chat` | DELETE | Clear the thread and truncate the log.                                                    |

The engine lives in `interface/routers/chat.py` and persists history to
`headless_app/data/chatlog/chat.log`, mirrored into
`workspace/data/chat.log` so the managed workspace keeps its own copy.

Everything runs **in one process**. Each router calls
`_ensure_headless_on_path()`, which puts `headless_app/` on `sys.path` and then
imports the engine's `build_agent` and the chat log directly.

```text
┌──────────────────────┐  POST /api/chat  ┌──────────────────────────────┐
│   browser interface  │ ───────────────▶ │  interface/routers/chat.py   │
│  home / editor /chat │                  │            │                 │
│                      │ ◀─────────────── │            ▼                 │
└──────────────────────┘       reply      │  headless_app/ (in-process)  │
                                          │  engine.agents.factory       │
                                          │  tools.chatlog               │
                                          └──────────────────────────────┘
```

### Agent registry, run and pipeline

`interface/routers/agents.py` exposes the rest of the engine surface:

| Route                    | Method | Purpose                                                                          |
| ------------------------ | ------ | -------------------------------------------------------------------------------- |
| `/api/agents`            | GET    | Every selectable agent: library (`headless_app/engine/agent_library/`) plus workspace (`workspace/agents/<name>/agent.json`). |
| `/api/agents/{agent_id}` | GET    | One agent's `{source, meta, sections}` — workspace first, library fallback.      |
| `/api/agents/run`        | POST   | Run one agent. Body: `{json_path, md_path \| agent_id, message, model?}`.        |
| `/api/pipeline`          | GET    | Default step chain from `config/pipeline.json` plus every selectable step candidate. |
| `/api/pipeline`          | POST   | Run a cascade. Body: `{steps: [...], message, model?}`.                           |
| `/api/models`            | GET    | Models listed in `config/models.json`, for the frontend picker.                   |

All file tool calls run through `DirectProjectIO`
(`headless_app/bridge/providers.py`), so `parameters/filesystem.py` remains the
single filesystem authority even when an agent is writing files. Each pipeline
step reports `Agent N (<id>) completed. Tools used: ...`, and the run is
appended to `headless_app/data/pipeline_runs.jsonl`.

---

## Editor Interface — Accessing the Agent Tools

The editor's browser interface reaches the agent engine and the code tools
through `interface/static/js/api.js` and `interface/static/js/session.js`.
Every agent tool the interface can touch is exposed as a small API method:

| Front-end accessor                 | Backend route                        | Purpose                                    |
| ---------------------------------- | ------------------------------------ | ------------------------------------------ |
| `API.chatSend(msg, agent, model)`  | `POST /api/chat`                     | Send a message to the selected agent       |
| `API.chatHistory(limit)`           | `GET /api/chat?limit=`               | Read agent conversation history            |
| `API.chatClear()`                  | `DELETE /api/chat`                   | Wipe the thread                            |
| `API.agents()`                     | `GET /api/agents`                    | Fill the agent selector                    |
| `API.agentDefinition(id)`          | `GET /api/agents/{agent_id}`         | Open an agent's `agent.json` / `agent.md`  |
| `API.agentRun(body)`               | `POST /api/agents/run`               | Run one agent against the open file        |
| `API.pipelineOptions()`            | `GET /api/pipeline`                  | Default steps + step candidates            |
| `API.pipelineRun(body)`            | `POST /api/pipeline`                 | Run the ordered cascade                    |
| `API.models()`                     | `GET /api/models`                    | Fill the model selector                    |
| `API.fileRead(path, scope)`        | `GET /api/file/read?path=&scope=`    | Open a file in the editor                  |
| `API.fileWrite(path, content, sc)` | `PUT /api/file/write`                | Save the current buffer                    |
| `API.project(scope)`               | `GET /api/project?scope=`            | Reload the file tree                       |
| `API.pathRename(old, new, scope)`  | `PUT /api/path/rename`               | Rename a file / folder                     |
| `API.fileDelete(path, scope)`      | `DELETE /api/file/delete?path=`      | Delete a file                              |
| `API.directoryDelete(path, scope)` | `DELETE /api/directory/delete?path=` | Delete a folder                            |

The surfaces that expose them:

- **Save** (`Ctrl+S`) → `API.fileWrite` on the current file
- **+ File / + Folder / Rename / Delete** → the matching create/rename/delete
  accessors
- **Scope toggle** (workspace / app) → `API.project` plus every file accessor
- **Chat page** (`/chat`) → agent and model `<select>`s, `API.chatSend`, and a
  collapsible *Tools used:* disclosure per reply
- **Agent panel** (`interface/static/js/agents.js`, right sidebar of the editor)
  → `+ Agent` scaffold, **Run Agent** against the open file, and a reorderable
  **cascade pipeline** queue

For a new agent tool the pattern to follow is:
`schema → route → API.* accessor → toolbar/panel control`. Nothing else in the
app changes, because every surface already talks to the API client.


## File Structure

```text
project_manager/
├── interface/
│   ├── clients/
│   │   ├── __init__.py
│   │   └── editor_client.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── defaults.py
│   │   ├── events.py
│   │   ├── operations.py
│   │   └── session.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── agents.py
│   │   ├── chat.py
│   │   ├── directories.py
│   │   ├── errors.py
│   │   ├── files.py
│   │   ├── paths.py
│   │   ├── project.py
│   │   ├── testing.py
│   │   └── ws.py
│   └── static/
│       ├── js/
│       │   ├── agentCards.js
│       │   ├── agentColors.js
│       │   ├── agents.js
│       │   ├── api.js
│       │   ├── chat.js
│       │   ├── editor.js
│       │   ├── main.js
│       │   ├── session.js
│       │   ├── topbar.js
│       │   └── tree.js
│       ├── Agentpromptbuilder.html
│       ├── chat.html
│       ├── editor.html
│       ├── home.html
│       ├── index.html
│       └── test.html
├── parameters/
│   ├── __init__.py
│   └── filesystem.py
├── scripts/
│   ├── run.bat
│   ├── run.sh
│   └── setup.sh
├── workspace/
│   ├── agents/
│   │   └── ProjectManager/
│   │       ├── agent.json
│   │       └── agent.md
│   ├── config/
│   ├── data/   # not embedded: runtime output: chat log and saved chat sessions
│   ├── documentation/
│   ├── project_scope/
│   ├── Tests/
│   ├── To Do/
│   │   ├── list.txt
│   │   └── todolistPrompt
│   ├── Tools/
│   ├── updates/
│   └── project.json
├── .gitattributes
├── .gitignore
├── README.md
├── requirements.txt
└── server.py
```

## Scope

This document covers every source file under `project_manager/`, **48 files** in total, in case-insensitive path order, and describes each one in the Module Reference below. No file bodies are embedded: a master copy is a map, and the code is in [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md).

The following are listed in the structure above but deliberately **not** covered:

| Path | Reason |
| ---- | ------ |
| `workspace/data` | runtime output: chat log and saved chat sessions |

Also excluded everywhere: `.git`, `__pycache__/`, virtualenvs, editor and tool caches (`.venv`, `venv`, `.idea`, `.vscode`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`), compiled and runtime artifacts (`*.pyc`, `*.pyo`, `*.log`, `*.dll`).

The three generated documents in `source_files/` are never embedded in each other, so no document can nest inside itself.

Regenerate all three documents with:

```bat
.venv/Scripts/python -m scripts.gen_master_copy
```

Or just this one:

```bat
.venv/Scripts/python -m scripts.gen_master_copy --only project_manager
```

## Module Reference

One entry per file, in the same order as the file structure above. Each entry lists what the file *defines* — its purpose, imports, constants, classes, methods and functions, with signatures and the first line of every docstring. File bodies are not repeated here: every path below is a heading in [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md), which holds the verbatim source.

### `.gitattributes`

*(no structured reference for this file type)*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `.gitattributes`*

### `.gitignore`

*(no structured reference for this file type)*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `.gitignore`*

### `interface/clients/__init__.py`

**Purpose.** Project Manager Python interface client package.
**Imports**
- `from .editor_client import EditorClient, AsyncEditorClient`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/clients/__init__.py`*

### `interface/clients/editor_client.py`

**Purpose.** Project Manager — Python interface client. ============================================
**Imports**
- `from __future__ import annotations`
- `import asyncio`
- `from typing import Any, AsyncIterator, Callable`
- `import httpx`
- `from websockets.asyncio.client import ClientConnection`
- `from websockets.asyncio.client import connect as ws_connect`
**Classes**
- **`EditorClient`** *(class)* — Synchronous HTTP client for the Project Manager interface.
  - **`__init__(self, base_url: str | None=None, timeout: float=30.0)`** *method*
  - **`_get(self, endpoint: str, **params: Any)`** *method*
  - **`_put(self, endpoint: str, params: dict[str, Any] | None=None, payload: dict[str, Any] | None=None)`** *method*
  - **`_post(self, endpoint: str, params: dict[str, Any] | None=None, payload: dict[str, Any] | None=None)`** *method*
  - **`_delete(self, endpoint: str, **params: Any)`** *method*
  - **`health(self)`** *method*
  - **`project(self)`** *method*
  - **`tree(self)`** *method*
  - **`sessions(self)`** *method*
  - **`read(self, path: str, scope: str='workspace')`** *method*
  - **`open(self, path: str, scope: str='workspace')`** *method* — Open a project file and return its contents.
  - **`write(self, path: str, content: str, scope: str='workspace')`** *method*
  - **`save(self, path: str, content: str, scope: str='workspace')`** *method* — Save file content. Alias for write().
  - **`create_file(self, path: str, content: str='', scope: str='workspace')`** *method*
  - **`delete_file(self, path: str, scope: str='workspace')`** *method*
  - **`create_directory(self, path: str, scope: str='workspace')`** *method*
  - **`delete_directory(self, path: str, scope: str='workspace')`** *method*
  - **`rename(self, old_path: str, new_path: str, scope: str='workspace')`** *method*
  - **`subscribe(self, *, timeout: float | None=None)`** *method* — Open a WebSocket and yield events as they arrive.
  - **`close(self)`** *method*
  - **`__enter__(self)`** *method*
  - **`__exit__(self, *exc)`** *method*
- **`AsyncEditorClient`** *(class)* — Asynchronous HTTP + WebSocket client for AI agents.
  - **`__init__(self, base_url: str | None=None, timeout: float=30.0)`** *method*
  - **`_get(self, endpoint: str, **params: Any)`** *async method*
  - **`_put(self, endpoint: str, params: dict[str, Any] | None=None, payload: dict[str, Any] | None=None)`** *async method*
  - **`_post(self, endpoint: str, params: dict[str, Any] | None=None, payload: dict[str, Any] | None=None)`** *async method*
  - **`_delete(self, endpoint: str, **params: Any)`** *async method*
  - **`health(self)`** *async method*
  - **`project(self)`** *async method*
  - **`tree(self)`** *async method*
  - **`sessions(self)`** *async method*
  - **`read(self, path: str, scope: str='workspace')`** *async method*
  - **`open(self, path: str, scope: str='workspace')`** *async method*
  - **`write(self, path: str, content: str, scope: str='workspace')`** *async method*
  - **`save(self, path: str, content: str, scope: str='workspace')`** *async method*
  - **`create_file(self, path: str, content: str='', scope: str='workspace')`** *async method*
  - **`delete_file(self, path: str, scope: str='workspace')`** *async method*
  - **`create_directory(self, path: str, scope: str='workspace')`** *async method*
  - **`delete_directory(self, path: str, scope: str='workspace')`** *async method*
  - **`rename(self, old_path: str, new_path: str, scope: str='workspace')`** *async method*
  - **`subscribe(self)`** *async method* — Open a WebSocket and yield Project Manager events.
**Functions**
- **`_default_base_url()`** *function* — Best-effort default: localhost on the standard Project Manager port.
- **`_apply_project_root(path: str, project_root: str='')`** *function* — Normalize a project-relative path into the API path form.
- **`_raise_for_error(response: httpx.Response)`** *function* — Turn a non-2xx response into a useful Python error.
- **`_decode_message(message: Any)`** *function* — Turn a raw WebSocket message into an event dict.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/clients/editor_client.py`*

### `interface/core/__init__.py`

**Purpose.** Project Manager operation/interface layer.
**Imports**
- `from .session import EditorManager, EditorSession`
- `from .events import EventBus`
- `from .operations import EditorInterface`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/core/__init__.py`*

### `interface/core/defaults.py`

**Purpose.** Project Manager shared defaults. =================================
**Imports**
- `from __future__ import annotations`
- `from typing import Any`
- `from parameters import filesystem`
- `from .events import EventBus`
- `from .session import EditorManager`
- `from .operations import EditorInterface`
**Functions**
- **`get_events()`** *function* — The shared project event bus.
- **`get_sessions()`** *function* — The shared editor session pool.
- **`get_interface()`** *function* — The shared Project Manager controller.
- **`reset_for_tests()`** *function* — Clear all shared state (used by the verification suite).

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/core/defaults.py`*

### `interface/core/events.py`

**Purpose.** Project Manager event system. =============================
**Imports**
- `from __future__ import annotations`
- `import uuid`
- `from typing import Any, Callable`
**Constants**
- `EVENT_TYPES` = `{'saved', 'tree_changed', 'renamed', 'deleted', 'created'}`
**Classes**
- **`EventBus`** *(class)* — Simple in-memory publish/subscribe event bus.
  - **`__init__(self)`** *method*
  - **`subscribe(self, callback: Callable[[dict[str, Any]], None])`** *method* — Subscribe a callback to every project event.
  - **`unsubscribe(self, subscription_id: str)`** *method* — Remove a subscription.
  - **`publish(self, event_type: str, path: str | None=None, **kwargs: Any)`** *method* — Publish an event to all subscribers.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/core/events.py`*

### `interface/core/operations.py`

**Purpose.** Project Manager operation layer. =================================
**Imports**
- `from __future__ import annotations`
- `from pathlib import Path`
- `from typing import Any`
- `from parameters import filesystem as _filesystem`
- `from .events import EventBus`
- `from .session import EditorManager`
**Constants**
- `VALID_SCOPES` = `('workspace', 'app')`
**Classes**
- **`EditorInterface`** *(class)* — The Project Manager operation/interface layer.
  - **`__init__(self, filesystem: Any=None, events: EventBus | None=None, sessions: EditorManager | None=None)`** *method*
  - **`health(self)`** *method* — Project Manager health and project information.
  - **`tree(self, scope: str | None=None)`** *method* — Project state: project info, active root and filesystem tree.
  - **`sessions(self)`** *method* — Snapshot of all connected interface sessions.
  - **`open(self, path: str, scope: str | None=None)`** *method* — Open a project file and return its contents.
  - **`save(self, path: str, content: str, scope: str | None=None)`** *method* — Write file contents back to the project filesystem.
  - **`create_file(self, path: str, content: str='', scope: str | None=None)`** *method* — Create a new project file.
  - **`create_directory(self, path: str, scope: str | None=None)`** *method* — Create a new project directory.
  - **`rename(self, old_path: str, new_path: str, scope: str | None=None)`** *method* — Rename or move a project file/directory.
  - **`delete(self, path: str, scope: str | None=None)`** *method* — Delete a project file or directory.
**Functions**
- **`_root_for(scope: str | None)`** *function* — Resolve a scope string into a filesystem root.
- **`_target(path: str, scope: str | None)`** *function* — Resolve a request path into the arguments the filesystem operations expect.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/core/operations.py`*

### `interface/core/session.py`

**Purpose.** Project Manager interface sessions. ====================================
**Imports**
- `from __future__ import annotations`
- `import time`
- `import uuid`
- `from typing import Any`
**Classes**
- **`EditorSession`** *(class)* — State for a single connected interface client.
  - **`__init__(self, client_id: str | None=None)`** *method*
  - **`snapshot(self)`** *method* — JSON-friendly copy of this session.
  - **`touch(self)`** *method* — Update the last-modified timestamp.
- **`EditorManager`** *(class)* — Maintains the active in-memory interface sessions.
  - **`__init__(self)`** *method*
  - **`register(self, client_id: str | None=None)`** *method* — Register a new connected client.
  - **`unregister(self, client_id: str)`** *method* — Remove a client session.
  - **`get(self, client_id: str)`** *method* — Fetch a session by client id.
  - **`update(self, client_id: str, *, open_file: str | None=None, dirty: bool | None=None)`** *method* — Update one field of a client session.
  - **`snapshot(self)`** *method* — JSON-friendly list of all active sessions.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/core/session.py`*

### `interface/routers/__init__.py`

**Purpose.** Project Manager HTTP API helpers. ==================================
**Imports**
- `from __future__ import annotations`
- `from pathlib import Path`
- `from typing import Any`
- `from fastapi import HTTPException`
- `from parameters import filesystem`
- `from interface.core.defaults import get_interface`
- `from interface.core.operations import VALID_SCOPES`
**Functions**
- **`controller()`** *function* — The single shared Project Manager interface instance.
- **`normalize_scope(scope: str | None)`** *function* — Validate and normalize a scope query parameter.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/routers/__init__.py`*

### `interface/routers/agents.py`

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
- `from engine.agents.loader import AgentNotFoundError`
- `from engine.agents.registry import list_agents`
- `from engine.pipeline import load_pipeline`
**Classes**
- **`AgentRunRequest`** *(class, BaseModel)*
- **`PipelineRunRequest`** *(class, BaseModel)*
**Functions**
- **`_ensure_headless_on_path()`** *function*
- **`_pm_filesystem()`** *function* — parameters.filesystem when running inside the Project Manager.
- **`_workspace()`** *function*
- **`_resolve(relative_path: str)`** *function* — Safe absolute path for an agent file path.
- **`_provider()`** *function*
- **`_api_path(path: str | None)`** *function* — Translate an engine path into a workspace-relative API path.
- **`_agent_payload(summary: dict)`** *function* — Shape one registry summary for /api/agents.
- **`_runner()`** *function* — The shared AgentInterface, the single engine entry point.
- **`_validated_message(message: str)`** *function*
- **`list_all_agents(request: Request)`** *function* — Return every runnable agent, from every registered agent root.
  - *decorator:* `@router.get('/api/agents')`
- **`get_agent_definition(request: Request, agent_id: str)`** *function* — Return one agent's metadata + markdown sections.
  - *decorator:* `@router.get('/api/agents/{agent_id}')`
- **`run_single_agent(request: Request, payload: AgentRunRequest)`** *function* — Build and run one agent, then log the exchange.
  - *decorator:* `@router.post('/api/agents/run')`
- **`pipeline_options(request: Request)`** *function* — Return the default step chain (config/pipeline.json) plus every selectable step candidate (library + workspace agents).
  - *decorator:* `@router.get('/api/pipeline')`
- **`run_agent_pipeline(request: Request, payload: PipelineRunRequest)`** *function* — Cascade many agents one after another.
  - *decorator:* `@router.post('/api/pipeline')`
- **`list_models(request: Request)`** *function* — Return the models in config/models.json for the frontend picker. Run refresh_models to re-scan installed Ollama models.
  - *decorator:* `@router.get('/api/models')`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/routers/agents.py`*

### `interface/routers/chat.py`

**Purpose.** Agent-backed Project Manager chat router (drop-in replacement).
**Imports**
- `from __future__ import annotations`
- `import json`
- `import re`
- `import sys`
- `from datetime import datetime, timezone`
- `from pathlib import Path`
- `from typing import Any`
- `from fastapi import APIRouter, Request`
- `from fastapi.responses import Response`
- `from pydantic import BaseModel`
- `from .errors import project_manager_error`
- `from engine.agents.loader import AgentNotFoundError`
- `from engine.agents.registry import list_agents`
- `from tools.chatlog import append_chat, clear_chat, read_history`
**Constants**
- `MAX_MESSAGE_LENGTH` = `2000`
- `DEFAULT_LIMIT` = `50`
- `MAX_LIMIT` = `500`
- `SESSIONS_DIRNAME` = `'data/chat_sessions'`
- `SAFE_ID`
- `MAX_TITLE_LENGTH` = `80`
- `EXPORT_FORMATS` = `('md', 'json')`
**Classes**
- **`ChatMessage`** *(class, BaseModel)*
- **`SessionSave`** *(class, BaseModel)*
**Functions**
- **`_ensure_headless_on_path()`** *function*
- **`_provider()`** *function* — The active filesystem authority (in-process Project Manager).
- **`_runner()`** *function* — The shared AgentInterface, the single engine entry point.
- **`_default_agent_id()`** *function*
- **`_mirror_pm_log(entry: dict)`** *function* — Mirror one chat entry into the Project Manager's own chat.log.
- **`send_chat_message(request: Request, payload: ChatMessage)`** *function* — Send a message to the agent engine and return its reply.
  - *decorator:* `@router.post('/api/chat')`
- **`get_chat_history(request: Request, limit: int=DEFAULT_LIMIT, agent: str | None=None)`** *function* — Return the most recent chat entries.
  - *decorator:* `@router.get('/api/chat')`
- **`_clear_mirror(agent: str | None)`** *function* — Apply the same wipe to the Project Manager's own chat.log.
- **`clear_chat_history(request: Request, agent: str | None=None)`** *function* — Wipe the chat history.
  - *decorator:* `@router.delete('/api/chat')`
- **`_sessions_root()`** *function* — Absolute path of the sessions directory inside the workspace.
- **`_safe_id(value: str, kind: str)`** *function* — Validate an id used as a single path segment.
- **`_new_session_id()`** *function*
- **`_derive_title(entries: list[dict])`** *function* — Title from the first user turn, else a timestamp.
- **`_session_file(session_id: str, agent_id: str)`** *function*
- **`_summary(record: dict)`** *function* — List-view projection of a stored session.
- **`_read_session(session_id: str, agent_id: str)`** *function*
- **`_sole_owner(session_id: str)`** *function* — The agent that owns a session id, when the id is unique.
- **`_list_sessions(agent_id: str | None)`** *function* — Every stored session, newest first.
- **`_to_markdown(record: dict)`** *function*
- **`list_saved_sessions(request: Request, agent: str | None=None)`** *function* — List saved chat sessions, newest first.
  - *decorator:* `@router.get('/api/chat/sessions')`
- **`save_chat_session(request: Request, payload: SessionSave)`** *function* — Copy the agent's current thread into a saved session.
  - *decorator:* `@router.post('/api/chat/sessions')`
- **`get_saved_session(request: Request, session_id: str, agent: str | None=None)`** *function* — Return one saved session, entries included.
  - *decorator:* `@router.get('/api/chat/sessions/{session_id}')`
- **`delete_saved_session(request: Request, session_id: str, agent: str | None=None)`** *function* — Delete one saved session. The live chat log is unaffected.
  - *decorator:* `@router.delete('/api/chat/sessions/{session_id}')`
- **`export_saved_session(request: Request, session_id: str, agent: str | None=None, format: str='md')`** *function* — Download a saved session as a file.
  - *decorator:* `@router.get('/api/chat/sessions/{session_id}/export')`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/routers/chat.py`*

### `interface/routers/directories.py`

**Purpose.** Project directory resource router (create / delete).
**Imports**
- `from __future__ import annotations`
- `from fastapi import APIRouter, Request`
- `from . import normalize_scope`
- `from .errors import project_manager_error`
**Functions**
- **`create_directory(request: Request, path: str, scope: str | None=None)`** *function* — Create a project directory.
  - *decorator:* `@router.post('/api/directory/create')`
- **`delete_directory(request: Request, path: str, scope: str | None=None)`** *function* — Delete a project directory.
  - *decorator:* `@router.delete('/api/directory/delete')`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/routers/directories.py`*

### `interface/routers/errors.py`

**Purpose.** Shared FastAPI error mapping for the Project Manager API.
**Imports**
- `from __future__ import annotations`
- `from fastapi import HTTPException`
**Functions**
- **`project_manager_error(error: Exception)`** *function* — Convert a Project Manager operation error into an HTTP error.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/routers/errors.py`*

### `interface/routers/files.py`

**Purpose.** Project file resource router (read / write / create / delete).
**Imports**
- `from __future__ import annotations`
- `from typing import Any`
- `from fastapi import APIRouter, Request`
- `from pydantic import BaseModel`
- `from . import normalize_scope`
- `from .errors import project_manager_error`
**Classes**
- **`FileWriteRequest`** *(class, BaseModel)*
- **`FileCreateRequest`** *(class, BaseModel)*
**Functions**
- **`read_file(request: Request, path: str, scope: str | None=None)`** *function* — Read a project text file.
  - *decorator:* `@router.get('/api/file/read')`
- **`write_file(request: Request, payload: FileWriteRequest)`** *function* — Create or overwrite a project text file.
  - *decorator:* `@router.put('/api/file/write')`
- **`create_file(request: Request, payload: FileCreateRequest)`** *function* — Create a new project file.
  - *decorator:* `@router.post('/api/file/create')`
- **`delete_file(request: Request, path: str, scope: str | None=None)`** *function* — Delete a project file.
  - *decorator:* `@router.delete('/api/file/delete')`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/routers/files.py`*

### `interface/routers/paths.py`

**Purpose.** Project path resource router (rename / move).
**Imports**
- `from __future__ import annotations`
- `from fastapi import APIRouter, Request`
- `from pydantic import BaseModel`
- `from . import normalize_scope`
- `from .errors import project_manager_error`
**Classes**
- **`RenameRequest`** *(class, BaseModel)*
**Functions**
- **`rename_path(request: Request, payload: RenameRequest)`** *function* — Rename or move a project file/directory.
  - *decorator:* `@router.put('/api/path/rename')`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/routers/paths.py`*

### `interface/routers/project.py`

**Purpose.** Project resource router.
**Imports**
- `from __future__ import annotations`
- `from typing import Any`
- `from fastapi import APIRouter, Request`
- `from . import normalize_scope`
- `from .errors import project_manager_error`
**Functions**
- **`health(request: Request)`** *function* — Project Manager health and project information.
  - *decorator:* `@router.get('/api/health')`
- **`get_project(request: Request, scope: str | None=None)`** *function* — Project information and filesystem tree.
  - *decorator:* `@router.get('/api/project')`
- **`get_sessions(request: Request)`** *function* — Active interface sessions.
  - *decorator:* `@router.get('/api/sessions')`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/routers/project.py`*

### `interface/routers/testing.py`

**Purpose.** Agent header test endpoints for the Project Manager.
**Imports**
- `from __future__ import annotations`
- `import importlib.util`
- `import sys`
- `from pathlib import Path`
- `from types import ModuleType`
- `from typing import Any`
- `from fastapi import APIRouter, Request`
- `from pydantic import BaseModel`
- `from .errors import project_manager_error`
**Constants**
- `_REPO_ROOT`
- `_HEADLESS_APP`
- `_TEST_ENVIRONMENT`
**Classes**
- **`HeaderTestRequest`** *(class, BaseModel)*
**Functions**
- **`_agent_test()`** *function* — Import test_environment/agent_test.py once per process.
- **`list_test_agents(request: Request)`** *function* — Return every published test agent.
  - *decorator:* `@router.get('/api/test/agents')`
- **`run_header_tests(request: Request, payload: HeaderTestRequest)`** *function* — Test one published agent against its four headers.
  - *decorator:* `@router.post('/api/test/run_header_tests')`
- **`read_results(request: Request)`** *function* — Return the last header test report, or 404 when there is none.
  - *decorator:* `@router.get('/api/test/results')`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/routers/testing.py`*

### `interface/routers/ws.py`

**Purpose.** Project Manager WebSocket router. =================================
**Imports**
- `from __future__ import annotations`
- `import asyncio`
- `import json`
- `from typing import Any`
- `from fastapi import APIRouter, WebSocket, WebSocketDisconnect`
**Functions**
- **`project_manager_socket(websocket: WebSocket)`** *async function* — Real-time Project Manager socket.
  - *decorator:* `@router.websocket('/api/ws')`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/routers/ws.py`*

### `interface/static/Agentpromptbuilder.html`

**Title.** Agent Prompt Builder
**Element ids (26).** `parts_folder_label`, `refresh_parts_btn`, `storage_status`, `form_title`, `part_category`, `new_category_btn`, `delete_category_btn`, `new_category_row`, `new_category_name`, `create_category_btn`, `categories_file_label`, `part_name`, `part_text`, `save_part_btn`, `clear_form_btn`, `part_status`, `new_part_btn`, `parts_list`, `create_master_btn`, `agent_id`, `master_prompt`, `save_agent_btn`, `publish_btn`, `test_btn`, `open_test_btn`, `master_status`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/Agentpromptbuilder.html`*

### `interface/static/chat.html`

**Title.** AI Agent Creator
**Includes**
- `https://unpkg.com/lucide@latest`
- `/static/js/chat.js`
**Element ids (19).** `toggleSources`, `toggleTest`, `panelSources`, `newNoteInput`, `notesList`, `activeAgentChip`, `activeAgentName`, `agentSelect`, `modelSelect`, `statusDot`, `chatStatus`, `chatLog`, `chatForm`, `chatInput`, `chatSend`, `panelTest`, `closeTest`, `savedChatsList`, `toast`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/chat.html`*

### `interface/static/editor.html`

**Title.** Project Manager Editor
**Includes**
- `https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js`
- `/static/js/main.js`
**Element ids (31).** `pageActions`, `saveBtn`, `newFileBtn`, `newFolderBtn`, `renameBtn`, `deleteBtn`, `refreshBtn`, `agentCreateBtn`, `runAgentBtn`, `pipelineBtn`, `sidebar`, `tree`, `resizeHandle`, `currentFile`, `unsavedIndicator`, `readOnlyIndicator`, `language`, `editor`, `agentPanel`, `runAgentHint`, `agentPrompt`, `runAgentBtnRun`, `agentResult`, `pipelineAgents`, `pipelineQueue`, `pipelineClearBtn`, `modelBox`, `pipelinePrompt`, `pipelineRunBtn`, `pipelineResult`, `statusMessage`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/editor.html`*

### `interface/static/home.html`

**Title.** Project Manager
**Includes**
- `/static/js/main.js`
**Element ids (7).** `projectName`, `pageActions`, `sidebar`, `tree`, `resizeHandle`, `agentCards`, `statusMessage`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/home.html`*

### `interface/static/index.html`

**Title.** Project Manager Dashboard
**Element ids (2).** `projectTree`, `statusMessage`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/index.html`*

### `interface/static/js/agentCards.js`

**Purpose.** Agent cards module
**Declarations**
- **`openChatWithAgent(agentId)`** *function*
- **`buildCard(agent, color)`** *function*
- **`initAgentCards(options = {})`** *function*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/js/agentCards.js`*

### `interface/static/js/agentColors.js`

**Purpose.** Stable per-agent color module
**Declarations**
- **`AGENT_PALETTE`** *array* = `[`
- **`hashId(id)`** *function*
- **`agentColor(id)`** *function*
- **`assignAgentColors(agents)`** *function*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/js/agentColors.js`*

### `interface/static/js/agents.js`

**Purpose.** Agent engine panel for the editor.
**Declarations**
- **`$(id)`** *arrow function*
- **`initAgentsPanel(ctx)`** *function*
- **`togglePanel()`** *function*
- **`agentLabel(a)`** *function*
- **`loadPanelData()`** *function*
- **`activeModel()`** *function*
- **`renderChecklist()`** *function*
- **`toggleAgent(a, checked)`** *function*
- **`moveStep(index, delta)`** *function*
- **`renderQueue()`** *function*
- **`updateRunTarget()`** *function*
- **`runCurrentAgent()`** *function*
- **`runPipeline()`** *function*
- **`scaffoldAgent()`** *function*
- **`setPanel(id, text)`** *function*
- **`renderResult(hostId, items)`** *function*
- **`refreshEnabled()`** *function*
- **`state`** *object literal, 0 methods*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/js/agents.js`*

### `interface/static/js/api.js`

**Purpose.** Project Manager API client module
**Declarations**
- **`API`** *object literal, 27 methods*
**Methods**
- **`API.request(method, url, body = null)`** *method*
- **`API.health()`** *method*
- **`API.withPath(path, scope)`** *method*
- **`API.withScope(body, scope)`** *method*
- **`API.project(scope = null)`** *method*
- **`API.fileRead(path, scope = null)`** *method*
- **`API.fileWrite(path, content, scope = null)`** *method*
- **`API.fileCreate(path, content = '', scope = null)`** *method*
- **`API.fileDelete(path, scope = null)`** *method*
- **`API.directoryCreate(path, scope = null)`** *method*
- **`API.directoryDelete(path, scope = null)`** *method*
- **`API.pathRename(oldPath, newPath, scope = null)`** *method*
- **`API.chatSend(message, agent_id = null, model = null)`** *method*
- **`API.chatHistory(limit = 100, agent = null)`** *method*
- **`API.chatClear(agent = null)`** *method*
- **`API.chatSessions(agent = null)`** *method*
- **`API.chatSessionSave(agent, title = null)`** *method*
- **`API.chatSession(id, agent = null)`** *method*
- **`API.chatSessionDelete(id, agent = null)`** *method*
- **`API.chatSessionExportUrl(id, agent = null, format = 'md')`** *method*
- **`API.sessions()`** *method*
- **`API.agents()`** *method*
- **`API.agentDefinition(id)`** *method*
- **`API.agentRun(body)`** *method*
- **`API.pipelineOptions()`** *method*
- **`API.pipelineRun(body)`** *method*
- **`API.models()`** *method*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/js/api.js`*

### `interface/static/js/chat.js`

**Purpose.** Chat popup module
**Declarations**
- **`log`** *constant* = `document.getElementById('chatLog')`
- **`form`** *constant* = `document.getElementById('chatForm')`
- **`input`** *constant* = `document.getElementById('chatInput')`
- **`sendBtn`** *constant* = `document.getElementById('chatSend')`
- **`status`** *constant* = `document.getElementById('chatStatus')`
- **`agentSelect`** *constant* = `document.getElementById('agentSelect')`
- **`modelSelect`** *constant* = `document.getElementById('modelSelect')`
- **`agentChip`** *constant* = `document.getElementById('activeAgentChip')`
- **`agentName`** *constant* = `document.getElementById('activeAgentName')`
- **`savedChatsList`** *constant* = `document.getElementById('savedChatsList')`
- **`requestedAgent`** *constant* = `new URLSearchParams(window.location.search).get('agent')`
- **`agentColorById`** *constant* = `new Map()`
- **`appendLine(role, text, meta = '', labelText = null)`** *function*
- **`copyText(text, message)`** *function*
- **`appendTools(tools)`** *function*
- **`setStatus(text)`** *function*
- **`activeAgentId()`** *function*
- **`agentLabel(id)`** *function*
- **`paintAgentChip()`** *function*
- **`populateAgents()`** *function*
- **`populateModels()`** *function*
- **`populateSelectors()`** *function*
- **`refreshAgents()`** *function*
- **`loadHistory()`** *function*
- **`sendMessage()`** *function*
- **`scaffoldNewAgent()`** *function*
- **`wipeChat()`** *function*
- **`sessionText(record)`** *function*
- **`sessionStamp(created)`** *function*
- **`rowAction(icon, title, handler)`** *function*
- **`sessionRow(session)`** *function*
- **`emptySessionRow(text)`** *function*
- **`renderSavedChats()`** *function*
- **`saveCurrentChat()`** *function*
- **`showSession(record)`** *function*
- **`openSavedSession(sessionId, agentId)`** *function*
- **`copySavedSession(sessionId, agentId)`** *function*
- **`deleteSavedSession(session, agentId)`** *function*
**Wiring**
- `window.scaffoldNewAgent = scaffoldNewAgent`
- `window.wipeChat = wipeChat`
- `window.saveCurrentChat = saveCurrentChat`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/js/chat.js`*

### `interface/static/js/editor.js`

**Purpose.** Monaco editor module
**Declarations**
- **`editor`** *constant* = `null`
- **`Editor`** *object literal, 9 methods*
**Methods**
- **`Editor.hasHost()`** *method*
- **`Editor.init()`** *method*
- **`Editor.getEditor()`** *method*
- **`Editor.setValue(content)`** *method*
- **`Editor.getValue()`** *method*
- **`Editor.setLanguage(lang)`** *method*
- **`Editor.setReadOnly(flag)`** *method*
- **`Editor.onChange(callback)`** *method*
- **`Editor.layout()`** *method*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/js/editor.js`*

### `interface/static/js/main.js`

**Purpose.** Main application wiring
**Declarations**
- **`currentFile`** *constant* = `null`
- **`currentLanguage`** *constant* = `'plaintext'`
- **`isDirty`** *constant* = `false`
- **`currentIsFolder`** *constant* = `false`
- **`currentIsReadOnly`** *constant* = `false`
- **`hasEditor()`** *arrow function*
- **`isPathReadOnly(path)`** *function*
- **`applyReadOnly()`** *function*
- **`getLanguage(filePath)`** *function*
- **`setStatus(msg)`** *function*
- **`updateFileDisplay()`** *function*
- **`openFile(filePath)`** *function*
- **`selectFolder(path)`** *function*
- **`saveFile()`** *function*
- **`requireWritableRoot(path)`** *function*
- **`isRootFolder(path)`** *function*
- **`newFile()`** *function*
- **`newFolder()`** *function*
- **`renameSelected()`** *function*
- **`deleteSelected()`** *function*
- **`refreshTree()`** *function*
- **`selectRoot(rootName)`** *function*
- **`openChatPopup(agentId)`** *function*
- **`init()`** *function*
**Wiring**
- `document.addEventListener('DOMContentLoaded', init)`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/js/main.js`*

### `interface/static/js/session.js`

**Purpose.** Project Manager WebSocket session module
**Declarations**
- **`ws`** *constant* = `null`
- **`wsConnected`** *constant* = `false`
- **`reconnectTimeout`** *constant* = `null`
- **`Session`** *object literal, 5 methods*
**Methods**
- **`Session.connect()`** *method*
- **`Session.send(msg)`** *method*
- **`Session.sendOpen(path)`** *method*
- **`Session.sendDirty(dirty)`** *method*
- **`Session.sendSessions()`** *method*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/js/session.js`*

### `interface/static/js/topbar.js`

**Purpose.** Shared topbar navigation
**Declarations**
- **`NAV_ITEMS`** *array* = `[`
- **`STYLE_ID`** *constant* = `'pmnav-style'`
- **`NAV_CSS`** *constant* = ```
- **`openPopup(url, spec)`** *function*
- **`ensureStyle()`** *function*
- **`initTopbar(options = {})`** *function*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/js/topbar.js`*

### `interface/static/js/tree.js`

**Purpose.** Project tree rendering module
**Declarations**
- **`Tree`** *object literal, 12 methods*
**Methods**
- **`Tree.rootOf(path)`** *method*
- **`Tree.isWritable()`** *method*
- **`Tree.nodeFor(path, items = this.root)`** *method*
- **`Tree.load()`** *method*
- **`Tree.key(path)`** *method*
- **`Tree.render(containerId = 'tree')`** *method*
- **`Tree.renderItems(items, container, depth = 0)`** *method*
- **`Tree.toggle(path)`** *method*
- **`Tree.reveal(path)`** *method*
- **`Tree.setSelected(path)`** *method*
- **`Tree.refresh()`** *method*
- **`Tree.getFileIcon(name)`** *method*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/js/tree.js`*

### `interface/static/test.html`

**Title.** Agent Header Test Dashboard
**Element ids (7).** `agent_select`, `model_select`, `run_btn`, `refresh_btn`, `run_status`, `summary`, `results`

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `interface/static/test.html`*

### `parameters/__init__.py`

**Purpose.** Project parameters package.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `parameters/__init__.py`*

### `parameters/filesystem.py`

**Purpose.** Project Manager Filesystem ==========================
**Imports**
- `from __future__ import annotations`
- `import errno`
- `import json`
- `import os`
- `import shutil`
- `import time`
- `from pathlib import Path`
- `from typing import Any`
**Constants**
- `PARAMETERS_DIR`
- `REPO_ROOT`
- `PROJECT_ROOT`
- `PROJECT_JSON`
- `SOURCE_FILES_ROOT`
- `TEST_ENVIRONMENT_ROOT`
- `PROJECT_FOLDERS` = `['documentation', 'project_scope', 'To Do', 'updates', 'config', 'data', 'Tests']`
- `BROWSE_ROOTS`
- `MAX_EDITABLE_BYTES`
- `TEXT_EXTENSIONS` = `{'.tsx', '.ts', '.html', '.sql', '.css', '.htm', '.yaml', '.toml', '.xml', '.cfg', '.json…`
- `IGNORED_DIRECTORIES` = `{'.idea', '.pytest_cache', '.vscode', '__pycache__', '.mypy_cache', 'venv', '.venv', '.gi…`
- `DEFAULT_PROJECT`
- `TRANSIENT_DELETE_WIN_ERRORS`
- `TRANSIENT_DELETE_ERRNOS`
- `DELETE_ATTEMPTS` = `3`
- `DELETE_BACKOFF` = `0.05`
**Functions**
- **`resolve_project_path(relative_path: str, root: Path | None=None)`** *function* — Convert a project-relative path into a safe absolute path.
- **`split_root(relative_path: str)`** *function* — Split a path into its browser-root name and the remainder.
- **`is_writable_root(root_name: str | None)`** *function* — Whether a browser root accepts writes.
- **`resolve_browse_target(relative_path: str, legacy_root: Path | None=None)`** *function* — Split a possibly root-qualified path into the arguments the filesystem operations expect.
- **`resolve_browse_path(relative_path: str, legacy_root: Path | None=None)`** *function* — Resolve a possibly root-qualified path to a safe absolute path.
- **`require_writable(relative_path: str, legacy_root: Path | None=None)`** *function* — Ensure a path may be written to.
- **`read_browse_filesystem()`** *function* — Build the browser tree.
- **`build_project_filesystem()`** *function* — Create the standard Project Manager filesystem.
- **`read_project_info()`** *function* — Read project.json.
- **`should_ignore(path: Path)`** *function* — Determine whether a path should be hidden from the project browser.
- **`is_text_file(path: Path)`** *function* — Determine whether a file should be editable.
- **`is_oversized(path: Path)`** *function* — Determine whether a file is too large to edit in the browser.
- **`read_filesystem(directory: Path | None=None, _root: Path | None=None, _prefix: str='')`** *function* — Recursively read the project filesystem.
- **`get_project_state()`** *function* — Return complete project information.
- **`read_file(relative_path: str, root: Path | None=None)`** *function* — Read a text file.
- **`write_file(relative_path: str, content: str, root: Path | None=None)`** *function* — Create or overwrite a text file.
- **`create_file(relative_path: str, content: str='', root: Path | None=None)`** *function* — Create a new file.
- **`create_directory(relative_path: str, root: Path | None=None)`** *function* — Create a directory.
- **`rename_path(old_path: str, new_path: str, root: Path | None=None)`** *function* — Rename or move a file/directory within the active root.
- **`delete_path(relative_path: str, root: Path | None=None)`** *function* — Delete a file or directory.
- **`is_transient_delete_error(error: OSError)`** *function* — Whether a delete failure is worth retrying.
- **`remove_tree_manual(target: Path)`** *function* — Remove a directory tree bottom-up.
- **`remove_tree(target: Path)`** *function* — Delete a directory tree, surviving a tree that is still settling.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `parameters/filesystem.py`*

### `README.md`

**Purpose.** The server half of [agentCreator](../README.md): a FastAPI workspace server with a Monaco-powered editor, an agent-backed chat page, and the routes that run single agents and cascade pipelines. It imports `headless_app/` in-process, so…
# Project Manager

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `README.md`*

### `requirements.txt`

*(no symbols extracted)*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `requirements.txt`*

### `scripts/run.bat`

*(no symbols extracted)*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `scripts/run.bat`*

### `scripts/run.sh`

**Purpose.** usr/bin/env bash Project Manager - start the server from the virtual environment.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `scripts/run.sh`*

### `scripts/setup.sh`

**Purpose.** usr/bin/env bash Project Manager - one-time setup for (Chromebook) Linux. Creates a virtual environment and installs dependencies.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `scripts/setup.sh`*

### `server.py`

**Purpose.** Project Manager Server - application entry point.
**Imports**
- `from __future__ import annotations`
- `import os`
- `import sys`
- `from contextlib import asynccontextmanager`
- `from pathlib import Path`
- `from fastapi import FastAPI`
- `from fastapi.responses import FileResponse`
- `from fastapi.staticfiles import StaticFiles`
- `from parameters import filesystem`
- `from interface.routers.project import router as project_router`
- `from interface.routers.files import router as files_router`
- `from interface.routers.directories import router as directories_router`
- `from interface.routers.paths import router as paths_router`
- `from interface.routers.ws import router as ws_router`
- `from interface.routers.chat import router as chat_router`
- `from interface.routers.agents import router as agents_router`
- `from interface.routers.testing import router as testing_router`
- `from interface.core.defaults import get_interface, get_events, get_sessions`
**Constants**
- `HOST`
- `PORT`
- `PROJECT_ROOT`
- `STATIC_DIR`
- `HOME_HTML`
- `EDITOR_HTML`
- `CHAT_HTML`
- `PROMPT_BUILDER_HTML`
- `TEST_HTML`
- `WORKSPACE_AGENT_ROOT` = `'workspace'`
**Functions**
- **`_ensure_headless_on_path()`** *function* — Put headless_app/ on sys.path so the engine can be imported.
- **`register_workspace_agent_root()`** *function* — Teach the agent engine about ``workspace/agents/``.
- **`unregister_workspace_agent_root()`** *function* — Drop the workspace root again (used on shutdown).
- **`lifespan(app: FastAPI)`** *async function* — Build the basic project filesystem on startup and register the workspace agent root with the agent engine.
  - *decorator:* `@asynccontextmanager`
- **`create_app()`** *function* — Assemble the Project Manager application.

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `server.py`*

### `workspace/agents/ProjectManager/agent.json`

**Top-level keys (6).**
- `id` = "project_manager"
- `name` = "Project Manager"
- `description` = "A custom agent for planning projects."
- `mode` = "agent"
- `model` = ""
- `tools` = ["map_files", "read_file", "write_text_file"]

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `workspace/agents/ProjectManager/agent.json`*

### `workspace/agents/ProjectManager/agent.md`

**Purpose.** You are Project Manager, a helpful agent for planning projects.
# Project Manager
## role
## purpose
## boundaries
## output format

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `workspace/agents/ProjectManager/agent.md`*

### `workspace/project.json`

**Top-level keys (3).**
- `name` = "Project Manager"
- `version` = "1.0.0"
- `workspace_version` = "1.0"

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `workspace/project.json`*

### `workspace/To Do/list.txt`

*(no symbols extracted)*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `workspace/To Do/list.txt`*

### `workspace/To Do/todolistPrompt`

*(no structured reference for this file type)*

*Source: [`APP_CODE_SNAPSHOT.md`](APP_CODE_SNAPSHOT.md) § `workspace/To Do/todolistPrompt`*


---

> Generated by `scripts/gen_master_copy.py` on 2026-09-29. Do not edit by hand; regenerate with:
>
> ```bat
> .venv/Scripts/python -m scripts.gen_master_copy
> ```
