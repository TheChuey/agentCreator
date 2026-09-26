# Headless App — MASTER COPY

Single-file snapshot of the complete `headless_app/` source tree: the GenV1 agent engine, its tools, and the bridge that binds them to Project Manager.

| Field | Value |
| ----- | ----- |
| Scope | `headless_app/` |
| Files embedded | 34 |
| Generated | 2026-09-25 |
| Generator | `scripts/gen_master_copy.py` |
| Regenerate | `.venv/Scripts/python -m scripts.gen_master_copy` |
| Sister document | [`project_manager_MASTER_COPY.md`](project_manager_MASTER_COPY.md) — project_manager/ |

## What This Is

`headless_app/` is the **agent half** of the system; `project_manager/` is the
editor/server half. They run as a single process: Project Manager imports this
package directly, so there is no agent server, no port of its own, and no HTTP
hop between the UI and the model.

| Component             | Role                                                                     |
| --------------------- | ------------------------------------------------------------------------ |
| `engine/`             | The think → act → observe runtime, prompt builder, agent loader/registry/factory, pipeline chain |
| `tools/`              | Tool registry, `FileSession` state, chat log, and the file tools that talk to Project Manager |
| `bridge/`             | Project Manager connection layer: sync + async HTTP clients, `DirectProjectIO`, drop-in routers |
| `config/`             | `models.json` (the model picker) and `pipeline.json` (the default cascade) |
| `interface_runner.py` | Programmatic entry point — `AgentInterface`                             |
| `run.py`              | Command-line entry point                                                |

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

`AgentInterface` is the thin, stable API over the engine:

| Method                                    | Purpose                                                                                     |
| ----------------------------------------- | ------------------------------------------------------------------------------------------- |
| `run_chat(message, agent_id)`             | One registered agent from `engine/agent_library/`; returns a chat reply                       |
| `run_single_agent(json_path, md_path, ui)` | One ad-hoc agent built from explicit `agent.json` + `agent.md` paths                           |
| `run_pipeline(agent_configs, user_input)` | Ordered feed-forward chain; each step receives the original message plus every earlier reply |

Every run persists the user turn and the reply to `data/chatlog/chat.log` (so
history survives reloads and an agent's `search_chat_logs` tool can recall it)
and records tool events to `data/toollog/tool_usage.jsonl`.

---

## How Project Manager Embeds This Package

`project_manager/interface/routers/chat.py` and
`project_manager/interface/routers/agents.py` each open with the same guard:

```python
def _ensure_headless_on_path() -> None:
    here = Path(__file__).resolve()
    if here.name == "chat.py" and here.parent.name == "routers":
        candidate = here.parents[3] / "headless_app"
    else:
        candidate = here.parents[2]
    candidate = candidate.resolve()
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
```

The `if` branch covers the copy that lives in
`project_manager/interface/routers/`, where `parents[3]` is the repository
root. The `else` branch covers a drop-in copy sitting in `bridge/routers/`,
where `parents[2]` is `headless_app/` itself. Either way `headless_app/` lands
on `sys.path`, and the router can then do
`from engine.agents.factory import build_agent`.

For the same reason `bridge/routers/chat.py` and `bridge/routers/agents.py`
are **drop-in routers**: distributable copies of the Project Manager routers,
importable as `bridge.routers.*`. No server in this repository mounts them —
the live endpoints are the ones under `project_manager/interface/routers/`.

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

| Tool id                     | Purpose                                            |
| -------------------------- | -------------------------------------------------- |
| `map_files`                | Map a directory tree                               |
| `read_file`                | Read a workspace file                              |
| `write_text_file`          | Create or overwrite a workspace file               |
| `delete_files`             | Delete files, behind a two-step approval protocol   |
| `get_current_date`         | Today's date                                       |
| `tell_me_the_date_and_time`| Current date and time                              |
| `search_chat_logs`         | Recall the agent's own chat history                |

File tools run against one of three backends, chosen once via `configure()`:
a Project Manager bridge over HTTP, a **direct** in-process Project Manager
provider (`DirectProjectIO`, used when mounted inside Project Manager), or the
local disk when no provider is configured. Whatever the backend, it exposes the
same small surface — `workspace_root`, `relpath()`, `list_tree()`, `read()`,
`write()`, `create()`, `delete()`, `exists()`.

---

## Agents and configuration

Each `engine/agent_library/<folder>/` holds an `agent.json` (metadata) and an
`agent.md` (the markdown spec whose `## role` / `## purpose` sections are folded
into the system prompt by `engine/core/prompt.py`). The folder name is for
humans; `agent.json#id` is the id you select in the UI and pass to
`/api/agents/run`.

| Folder          | `agent.json#id`        | Mode    | Model                    |
| --------------- | --------------------- | ------- | ------------------------ |
| `rag_assistant` | `rag_assistant`       | `agent` | `gemma4:e2b`             |
| `Planner`       | `feature_planner_agent` | `chat`  | `qwen2.5-coder:latest`   |
| `Enginner`      | `execute_engineer_agent` | `agent` | `qwen2.5-coder:latest` |
| `Builder`       | `module_builder_agent` | `agent` | `qwen2.5-coder:latest`   |

`Planner` is the only `chat`-mode agent, which is why its `agent.md` carries no
tool sections — `chat` mode attaches no tools.

- `config/models.json` — the models offered by the UI picker, each with `id`,
  `name`, `source` and `size`. `refresh_models` re-scans the local Ollama
  install.
- `config/pipeline.json` — the default cascade: `feature_planner_agent` →
  `execute_engineer_agent` → `module_builder_agent`, served by
  `GET /api/pipeline`.

Model and context bounds live in `engine/core/llm.py` (`MAX_NUM_CTX = 32768`).
Failure behaviour is deliberate rather than fatal: an unknown agent id returns
an error string, a model that is not installed falls back to a detected one
with a warning, and a model that does not support tools has its schemas
dropped so the agent answers text-only.


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
│   │   └── registry.py
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

## Snapshot Scope

This document embeds every source file under `headless_app/`, **34 files** in total, in case-insensitive path order.

The following are listed in the tree above but deliberately **not** embedded:

| Path | Reason |
| ---- | ------ |
| `data` | runtime output: chat log, tool log, pipeline run records |

Also excluded everywhere: `__pycache__/`, virtualenvs, editor and tool caches (`__pycache__`, `.venv`, `venv`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.idea`, `.vscode`), compiled artifacts (`*.pyc`, `*.pyo`, `*.log`).

A master copy is **never** embedded in a master copy, so this document cannot nest inside itself.

Regenerate both documents with:

```bat
.venv/Scripts/python -m scripts.gen_master_copy
```

Or just this one:

```bat
.venv/Scripts/python -m scripts.gen_master_copy --only headless_app
```

<!-- ==== 1/34 : bridge/__init__.py ==== -->

### bridge/__init__.py

```python
"""bridge - Project Manager connection layer for the headless engine."""

from bridge.client import (
    ProjectManagerBridge,
    AsyncProjectManagerBridge,
)

__all__ = [
    "ProjectManagerBridge",
    "AsyncProjectManagerBridge",
]
```

---

<!-- ==== 2/34 : bridge/client.py ==== -->

### bridge/client.py

```python
"""
bridge/client.py
================

Project Manager bridge clients for the headless engine.

The bridge is the *interface* the headless agents use to reach the running
Project Manager. Every file operation goes through the Project Manager
server (or its direct in-process filesystem authority) - the bridge never
touches the project filesystem itself unless a direct provider is used.

Two transports:

    ProjectManagerBridge       - synchronous HTTP (+ sync WebSocket subscribe)
    AsyncProjectManagerBridge  - async/await HTTP (+ async WebSocket subscribe)

Both implement the provider surface the file tools expect:

    workspace_root (str)    .relpath(path) -> posix relative (or raises)
    .list_tree() -> nested  .read(rel) -> str    .write(rel, content)
    .create(rel, content)   .delete(rel)         .exists(rel) -> bool

Plus Project Manager conveniences: health(), project(), sessions(),
rename(), create_directory(), delete_directory(), open(), subscribe().

The server responses follow the Project Manager contract:

    GET  /api/health          -> {"status", "project", "root"}
    GET  /api/project         -> {"scope", "project", "root", "filesystem"}
    GET  /api/file/read       -> {"path", "content", "scope"}
    PUT  /api/file/write      -> {"status": "saved", "path", "scope"}
    POST /api/file/create     -> {"status": "created", "path", "scope"}
    DELETE /api/file/delete   -> {"status": "deleted", "path", "scope"}
    DELETE /api/directory/delete -> {"status": "deleted", ...}
    POST /api/directory/create   -> {"status": "created", ...}
    PUT  /api/path/rename     -> {"status": "renamed", ...}
    WS   /api/ws              -> {"type": "event", "event": {...}} frames
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, AsyncIterator, Callable

import httpx
from websockets.asyncio.client import ClientConnection
from websockets.asyncio.client import connect as ws_connect


# ============================================================
# BASE URL DETECTION
# ============================================================

def _default_base_url() -> str:
    """
    Best-effort default: localhost on the standard Project Manager port.
    """

    import os

    return os.environ.get(
        "PROJECT_MANAGER_BASE_URL",
        "http://127.0.0.1:8000",
    )


def _apply_project_root(
    path: str,
    project_root: str = "",
) -> str:
    """
    Normalize a project-relative path into the API path form.
    """

    path = path.replace("\\", "/").strip("/")

    return path


# ============================================================
# SHARED RESPONSE MACHINERY
# ============================================================

def _raise_for_error(
    response: httpx.Response,
) -> None:
    """
    Turn a non-2xx response into a useful Python error.
    """

    if response.is_success:
        return

    detail = ""

    try:

        detail = response.json().get(
            "detail",
            "",
        )

    except Exception:
        pass

    message = detail or f"Project Manager error (HTTP {response.status_code})."

    raise RuntimeError(
        message
    )


def _decode_message(message: Any) -> dict[str, Any]:
    """
    Turn a raw WebSocket message into a dict (bytes or str payload).
    """

    import json

    if isinstance(message, bytes):
        return json.loads(
            message.decode(
                "utf-8"
            )
        )

    try:

        return json.loads(
            message
        )

    except Exception:

        return {
            "type": "message",
            "data": message,
        }


# ============================================================
# PATH HELPERS (shared by both clients)
# ============================================================

def _normalize(raw: str) -> str:
    return str(raw).replace("\\", "/").strip("/")


def _relpath(root: Path, path: str) -> str:
    """Translate an absolute-or-relative path into a posix relative path that
    stays inside the Project Manager workspace root. The root itself maps to
    "". Raises ValueError when the path would escape the root."""
    raw = str(path).strip()
    if not raw:
        return ""
    if raw in (".", "/", "\\"):
        return ""

    root = root.resolve()

    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        try:
            rel = resolved.relative_to(root)
        except ValueError:
            raise ValueError(
                f"Path '{raw}' is outside the Project Manager workspace root "
                f"({root})."
            )
        return rel.as_posix()

    joined = (root / _normalize(raw)).resolve()
    try:
        rel = joined.relative_to(root)
    except ValueError:
        raise ValueError(
            f"Path '{raw}' is outside the Project Manager workspace root "
            f"({root})."
        )
    as_posix = rel.as_posix()
    return "" if as_posix == "." else as_posix


# ============================================================
# SYNC CLIENT
# ============================================================

class ProjectManagerBridge:
    """Synchronous HTTP bridge to the Project Manager server.

    Implements the provider surface used by the headless file tools and the
    Project Manager operations exposed by the original Python client.
    """

    #: how long a project tree snapshot is trusted (list/exists lookups)
    _TREE_TTL = 2.0

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (
            base_url
            if base_url is not None
            else _default_base_url()
        )
        self.timeout = timeout
        self.scope = "workspace"

        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
        )

        self._root: str | None = None
        self._tree_cache: tuple[float, list] = (0.0, [])

    # ========================================================
    # PROVIDER SURFACE
    # ========================================================

    @property
    def workspace_root(self) -> str:
        """The Project Manager workspace root (from /api/health)."""
        if self._root is None:
            health = self.health()
            self._root = str((health or {}).get("root", ""))
        if not self._root:
            raise RuntimeError(
                "Project Manager did not report a workspace root."
            )
        return self._root

    def relpath(self, path: str) -> str:
        return _relpath(Path(self.workspace_root), path)

    def _fresh_tree(self) -> list:
        now = time.monotonic()
        if now - self._tree_cache[0] < self._TREE_TTL:
            return self._tree_cache[1]
        tree: list = (self.tree() or {}).get("filesystem") or []
        self._tree_cache = (now, tree)
        return tree

    def list_tree(self) -> list:
        """Nested project tree ([{name, path, type, children?, size?}...])."""
        return self._fresh_tree()

    def read(self, rel: str) -> str:
        """Read a workspace text file; returns the content."""
        return self.open(rel)["content"]

    def write(self, rel: str, content: str) -> dict[str, Any]:
        return self.save(rel, content)

    def create(self, rel: str, content: str) -> dict[str, Any]:
        return self.create_file(rel, content)

    def delete(self, rel: str) -> dict[str, Any]:
        return self.delete_file(rel)

    def exists(self, rel: str) -> bool:
        rel = rel.replace("\\", "/").strip("/")
        for entry in self._flatten_paths():
            if entry == rel:
                return True
        return False

    def _flatten_paths(self) -> list[str]:
        paths: list[str] = []

        def walk(entries):
            for entry in entries or []:
                rel = entry.get("path", "")
                if rel:
                    paths.append(rel)
                walk(entry.get("children") or [])

        walk(self._fresh_tree())
        return paths

    # ========================================================
    # GET HELPERS
    # ========================================================

    def _get(
        self,
        endpoint: str,
        **params: Any,
    ) -> dict[str, Any]:
        response = self._http.get(
            endpoint,
            params=params,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    def _put(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._http.put(
            endpoint,
            params=params,
            json=payload,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    def _post(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._http.post(
            endpoint,
            params=params,
            json=payload,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    def _delete(
        self,
        endpoint: str,
        **params: Any,
    ) -> dict[str, Any]:
        response = self._http.delete(
            endpoint,
            params=params,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    # ========================================================
    # PROJECT OPERATIONS
    # ========================================================

    def health(self) -> dict[str, Any]:
        return self._get("/api/health")

    def project(self) -> dict[str, Any]:
        return self._get("/api/project", scope=self.scope)

    def tree(self) -> dict[str, Any]:
        return self.project()

    def sessions(self) -> dict[str, Any]:
        return self._get("/api/sessions")

    # ========================================================
    # FILE OPERATIONS
    # ========================================================

    def read_file(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._get(
            "/api/file/read",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    def open(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Open a project file and return its contents.
        """

        return self.read_file(path, scope=scope)

    def write_file(
        self,
        path: str,
        content: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._put(
            "/api/file/write",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope or self.scope,
            },
        )

    def save(
        self,
        path: str,
        content: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Save file content. Alias for write_file().
        """

        return self.write_file(path, content, scope=scope)

    def create_file(
        self,
        path: str,
        content: str = "",
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._post(
            "/api/file/create",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope or self.scope,
            },
        )

    def delete_file(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._delete(
            "/api/file/delete",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    # ========================================================
    # DIRECTORY OPERATIONS
    # ========================================================

    def create_directory(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._post(
            "/api/directory/create",
            params={
                "path": _apply_project_root(path),
                "scope": scope or self.scope,
            },
        )

    def delete_directory(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._delete(
            "/api/directory/delete",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    # ========================================================
    # RENAME / MOVE OPERATIONS
    # ========================================================

    def rename(
        self,
        old_path: str,
        new_path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._put(
            "/api/path/rename",
            payload={
                "old_path": _apply_project_root(old_path),
                "new_path": _apply_project_root(new_path),
                "scope": scope or self.scope,
            },
        )

    # ========================================================
    # LIFECYCLE
    # ========================================================

    def subscribe(
        self,
        *,
        timeout: float | None = None,
    ):
        """
        Open a WebSocket and yield Project Manager frames as they arrive.

        Frames keep the server contract: {"type": "event", "event": {...}}
        for project changes, {"type": "hello", ...} and
        {"type": "sessions", ...} for session state.
        """

        ws_url = self.base_url.replace(
            "http",
            "ws",
            count=1
        )

        ws_url = ws_url.rstrip("/") + "/api/ws"

        import websockets.sync.client as ws_sync

        with ws_sync.connect(
            ws_url,
            timeout=timeout,
        ) as socket:

            while True:

                message = socket.recv()

                if message is None:
                    break

                yield _decode_message(message)

    def expose(
        self,
    ) -> dict[str, Any]:
        """Self-description: which Project Manager endpoints the bridge uses."""
        return {
            "base_url": self.base_url,
            "workspace_root": self.workspace_root,
            "scope": self.scope,
        }

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "ProjectManagerBridge":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


# ============================================================
# ASYNC CLIENT
# ============================================================

class AsyncProjectManagerBridge:
    """Asynchronous HTTP + WebSocket bridge to the Project Manager.

    Provides the same operations as ProjectManagerBridge with async/await,
    plus subscribe() for real-time project events.
    """

    _TREE_TTL = 2.0

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (
            base_url
            if base_url is not None
            else _default_base_url()
        )
        self.timeout = timeout
        self.scope = "workspace"

        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
        )

        self._root: str | None = None
        self._tree_cache: tuple[float, list] = (0.0, [])

    # ========================================================
    # PROVIDER SURFACE (async)
    # ========================================================

    @property
    async def workspace_root(self) -> str:
        if self._root is None:
            health = await self.health()
            self._root = str((health or {}).get("root", ""))
        if not self._root:
            raise RuntimeError(
                "Project Manager did not report a workspace root."
            )
        return self._root

    def relpath(self, path: str) -> str:
        root = self._root or "."
        return _relpath(Path(root), path)

    async def _fresh_tree(self) -> list:
        now = time.monotonic()
        if now - self._tree_cache[0] < self._TREE_TTL:
            return self._tree_cache[1]
        payload = await self.tree()
        tree: list = (payload or {}).get("filesystem") or []
        self._tree_cache = (now, tree)
        return tree

    async def list_tree(self) -> list:
        return await self._fresh_tree()

    async def read(self, rel: str) -> str:
        return (await self.open(rel))["content"]

    async def write(self, rel: str, content: str) -> dict[str, Any]:
        return await self.save(rel, content)

    async def create(self, rel: str, content: str) -> dict[str, Any]:
        return await self.create_file(rel, content)

    async def delete(self, rel: str) -> dict[str, Any]:
        return await self.delete_file(rel)

    async def exists(self, rel: str) -> bool:
        rel = rel.replace("\\", "/").strip("/")
        for path in await self._flatten_paths():
            if path == rel:
                return True
        return False

    async def _flatten_paths(self) -> list[str]:
        paths: list[str] = []

        def walk(entries):
            for entry in entries or []:
                rel = entry.get("path", "")
                if rel:
                    paths.append(rel)
                walk(entry.get("children") or [])

        walk(await self._fresh_tree())
        return paths

    # ========================================================
    # ASYNC HELPERS
    # ========================================================

    async def _get(
        self,
        endpoint: str,
        **params: Any,
    ) -> dict[str, Any]:
        response = await self._http.get(
            endpoint,
            params=params,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    async def _put(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._http.put(
            endpoint,
            params=params,
            json=payload,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    async def _post(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._http.post(
            endpoint,
            params=params,
            json=payload,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    async def _delete(
        self,
        endpoint: str,
        **params: Any,
    ) -> dict[str, Any]:
        response = await self._http.delete(
            endpoint,
            params=params,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    # ========================================================
    # OPERATIONS (ASYNC)
    # ========================================================

    async def health(self) -> dict[str, Any]:
        return await self._get("/api/health")

    async def project(self) -> dict[str, Any]:
        return await self._get("/api/project", scope=self.scope)

    async def tree(self) -> dict[str, Any]:
        return await self.project()

    async def sessions(self) -> dict[str, Any]:
        return await self._get("/api/sessions")

    async def read_file(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._get(
            "/api/file/read",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    async def open(
        self,
        path: str,
        scope: str | None = None,
    ):
        return await self.read_file(path, scope=scope)

    async def write_file(
        self,
        path: str,
        content: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._put(
            "/api/file/write",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope or self.scope,
            },
        )

    async def save(
        self,
        path: str,
        content: str,
        scope: str | None = None,
    ):
        return await self.write_file(path, content, scope=scope)

    async def create_file(
        self,
        path: str,
        content: str = "",
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            "/api/file/create",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope or self.scope,
            },
        )

    async def delete_file(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._delete(
            "/api/file/delete",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    async def create_directory(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            "/api/directory/create",
            params={
                "path": _apply_project_root(path),
                "scope": scope or self.scope,
            },
        )

    async def delete_directory(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._delete(
            "/api/directory/delete",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    async def rename(
        self,
        old_path: str,
        new_path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._put(
            "/api/path/rename",
            payload={
                "old_path": _apply_project_root(old_path),
                "new_path": _apply_project_root(new_path),
                "scope": scope or self.scope,
            },
        )

    # ========================================================
    # REAL-TIME SUBSCRIPTION
    # ========================================================

    async def subscribe(
        self,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Open a WebSocket and yield Project Manager event frames.

        Example:
            >>> async for frame in client.subscribe():
            ...     if frame.get("type") == "event":
            ...         event = frame["event"]
            ...         if event["type"] == "saved":
            ...             print("Saved", event["path"])
        """

        ws_url = self.base_url.replace(
            "http",
            "ws",
            count=1
        )

        ws_url = ws_url.rstrip("/") + "/api/ws"

        async with ws_connect(
            ws_url
        ) as socket:

            async for message in socket:

                yield _decode_message(
                    message
                )

    async def expose(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "workspace_root": await self.workspace_root,
            "scope": self.scope,
        }

    async def close(self) -> None:
        await self._http.aclose()


__all__ = [
    "ProjectManagerBridge",
    "AsyncProjectManagerBridge",
    "_default_base_url",
]
```

---

<!-- ==== 3/34 : bridge/providers.py ==== -->

### bridge/providers.py

```python
"""
bridge/providers.py
===================

In-process Project Manager filesystem authority.

Used when the agent engine is mounted INSIDE a running Project Manager
server (the agent-backed /api/chat router). In that case a separate HTTP
loop-back bridge is unnecessary, so this provider drives the SAME
parameters.filesystem module the Project Manager itself uses - keeping the
Project Manager as the single filesystem owner even in-process.

It implements the provider surface the headless file tools expect, exactly
like the HTTP ProjectManagerBridge does:

    workspace_root (str)    .relpath(path) -> posix relative (or raises)
    .list_tree() -> nested  .read(rel) -> str    .write(rel, content)
    .create(rel, content)   .delete(rel)         .exists(rel) -> bool
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bridge.client import _relpath


class DirectProjectIO:
    """
    Filesystem provider backed directly by the Project Manager's
    parameters.filesystem authority.

    Requires the Project Manager package to be importable
    (``from parameters import filesystem``).
    """

    def __init__(self) -> None:
        from parameters import filesystem

        self._filesystem = filesystem
        self._root = Path(filesystem.PROJECT_ROOT)
        self.scope = "workspace"

    # --------------------------------------------------------
    # PROVIDER SURFACE
    # --------------------------------------------------------

    @property
    def workspace_root(self) -> str:
        return str(self._root)

    def relpath(self, path: str) -> str:
        return _relpath(self._root, path)

    def list_tree(self) -> list:
        return self._filesystem.read_filesystem()

    def read(self, rel: str) -> str:
        return self._filesystem.read_file(rel)

    def write(self, rel: str, content: str) -> dict[str, Any]:
        self._filesystem.write_file(rel, content)
        return {"status": "saved", "path": rel, "scope": self.scope}

    def create(self, rel: str, content: str) -> dict[str, Any]:
        self._filesystem.create_file(rel, content)
        return {"status": "created", "path": rel, "scope": self.scope}

    def delete(self, rel: str) -> dict[str, Any]:
        self._filesystem.delete_path(rel)
        return {"status": "deleted", "path": rel, "scope": self.scope}

    def exists(self, rel: str) -> bool:
        target = (self._root / rel.replace("\\", "/").strip("/")).resolve()
        try:
            target.relative_to(self._root.resolve())
        except ValueError:
            return False
        return target.exists()

    # --------------------------------------------------------
    # PROJECT MANAGER CONVENIENCES
    # --------------------------------------------------------

    def health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "project": self._filesystem.read_project_info(),
            "root": str(self._root),
        }

    def tree(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "project": self._filesystem.read_project_info(),
            "root": str(self._root),
            "filesystem": self._filesystem.read_filesystem(),
        }

    def project(self) -> dict[str, Any]:
        return self.tree()

    def sessions(self) -> list:
        return []

    def expose(self) -> dict[str, Any]:
        return {
            "mode": "direct",
            "workspace_root": self.workspace_root,
            "scope": self.scope,
        }


__all__ = ["DirectProjectIO"]
```

---

<!-- ==== 4/34 : bridge/routers/__init__.py ==== -->

### bridge/routers/__init__.py

```python
"""bridge.routers - drop-in FastAPI routers for the Project Manager."""
```

---

<!-- ==== 5/34 : bridge/routers/agents.py ==== -->

### bridge/routers/agents.py

```python
"""
bridge/routers/agents.py
========================

Agent registry, run, and pipeline endpoints for the Project Manager.

Turns the Project Manager into an agent workspace: browse every agent
(library + workspace), run one agent from its ``agent.json``/``agent.md``
files, or cascade many agents one after another (each later step receives
every earlier step's reply) through ``/api/pipeline``.

    GET  /api/agents
        -> library agents (engine/agent_library/) plus workspace agents
           discovered under <workspace>/agents/<name>/agent.json.

    GET  /api/agents/{agent_id}
        -> {"source", "meta", "sections"} for one agent (workspace first,
           library fallback), so the editor can open/read its definition.

    POST /api/agents/run
        {"json_path", "md_path" | "agent_id", "message", "model"?}
        -> builds the agent (workspace-relative paths resolved through the
           Project Manager filesystem), runs it, records chat entries, and
           returns {"reply", "agent_id", "name", "model", "tool_events"}.

    GET /api/pipeline
        -> default step chain from config/pipeline.json plus every selectable
           step candidate (library + workspace agents).

    POST /api/pipeline
        {"steps": [id | {"json_path", "md_path"}], "message", "model"?}
        -> run_pipeline: cascade the ordered steps, feed-forward every
           earlier step's reply into the next; each step's stdout line is
           "Agent N (<id>) completed. Tools used: <tools>".

    GET /api/models
        -> models listed in config/models.json, for the frontend picker.

All file tool calls run in-process through DirectProjectIO, so
parameters.filesystem remains the single filesystem authority.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .errors import project_manager_error
from .chat import MAX_MESSAGE_LENGTH, _mirror_pm_log


# ------------------------------------------------------------
# Headless engine bootstrap
# ------------------------------------------------------------

def _ensure_headless_on_path() -> None:
    here = Path(__file__).resolve()
    if here.name == "agents.py" and here.parent.name == "routers":
        candidate = here.parents[3] / "headless_app"
    else:
        candidate = here.parents[2]
    candidate = candidate.resolve()
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


_ensure_headless_on_path()

from engine.agents.factory import (  # noqa: E402
    build_agent,
    build_agent_from_definition,
)
from engine.agents.loader import AgentNotFoundError  # noqa: E402
from engine.agents.registry import list_agents  # noqa: E402
from engine.pipeline import load_pipeline, run_pipeline  # noqa: E402
from tools.chatlog import append_chat  # noqa: E402

try:
    from bridge.providers import DirectProjectIO  # noqa: E402
except Exception:
    DirectProjectIO = None  # type: ignore[assignment]


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# REQUEST MODELS
# ============================================================

class AgentRunRequest(BaseModel):

    message: str

    agent_id: str | None = None

    json_path: str | None = None

    md_path: str | None = None

    model: str | None = None


class PipelineRunRequest(BaseModel):

    steps: list = []

    message: str

    model: str | None = None


# ============================================================
# PROJECT MANAGER FILESYSTEM AUTHORITY
# ============================================================

_workspace_root: Any = None


def _pm_filesystem():
    """parameters.filesystem when running inside the Project Manager."""
    try:
        from parameters import filesystem
        return filesystem
    except Exception:
        return None


def _workspace() -> Path | None:
    global _workspace_root
    if _workspace_root is not None:
        return _workspace_root
    filesystem = _pm_filesystem()
    if filesystem is None:
        _workspace_root = None
        return None
    _workspace_root = filesystem.PROJECT_ROOT
    return _workspace_root


def _resolve(relative_path: str) -> Path:
    """Safe absolute path for a workspace-relative agent file path."""
    filesystem = _pm_filesystem()
    if filesystem is None:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            return candidate
        raise ValueError(
            "Running outside the Project Manager - a workspace-relative "
            "path cannot be resolved."
        )
    return filesystem.resolve_project_path(relative_path)


def _provider() -> Any:
    if DirectProjectIO is None:
        raise RuntimeError(
            "DirectProjectIO is unavailable - the agent router must run "
            "inside the Project Manager package."
        )
    return DirectProjectIO()


# ============================================================
# WORKSPACE AGENT DISCOVERY
# ============================================================

def _workspace_agents() -> list[dict]:
    """Scan <workspace>/agents/*/agent.json for runnable agent definitions."""
    workspace = _workspace()
    if workspace is None:
        return []

    discovered: list[dict] = []
    base = workspace / "agents"
    if not base.is_dir():
        return discovered

    for agent_dir in sorted(base.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name.startswith(("_", ".")):
            continue
        json_file = agent_dir / "agent.json"
        md_file = agent_dir / "agent.md"
        if not json_file.exists() or not md_file.exists():
            continue
        try:
            meta = json.loads(json_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        rel_dir = f"agents/{agent_dir.name}"
        discovered.append({
            "id": meta.get("id") or agent_dir.name,
            "name": meta.get("name") or agent_dir.name,
            "description": meta.get("description", ""),
            "mode": meta.get("mode", "chat"),
            "model": meta.get("model", "") or "",
            "tools": meta.get("tools", []),
            "source": "workspace",
            "json_path": f"{rel_dir}/agent.json",
            "md_path": f"{rel_dir}/agent.md",
            "dir": rel_dir,
        })

    return discovered


def _all_agents() -> list[dict]:
    library = [dict(a, source="library") for a in list_agents()]
    return library + _workspace_agents()


# ============================================================
# CHAT LOG RECORDING
# ============================================================

def _record_entries(user_message: str, reply: str) -> list[dict]:
    user_entry = append_chat("user", user_message)
    reply_entry = append_chat("agent", reply)
    _mirror_pm_log(user_entry)
    _mirror_pm_log(reply_entry)
    return [user_entry, reply_entry]


def _validated_message(message: str) -> str:
    text = message.strip()
    if not text:
        raise project_manager_error(ValueError("Chat message cannot be empty."))
    if len(text) > MAX_MESSAGE_LENGTH:
        raise project_manager_error(
            ValueError(
                f"Chat message is too long "
                f"(max {MAX_MESSAGE_LENGTH} characters)."
            )
        )
    return text


# ============================================================
# LIST AGENTS
# ============================================================

@router.get("/api/agents")
def list_all_agents(
    request: Request,
):
    """
    Return every runnable agent: library (engine/agent_library/) and
    workspace (workspace/agents/<name>/) definitions.

    Workspace agents include json_path/md_path so the frontend can run or
    open them directly.
    """

    try:

        return {
            "agents": _all_agents(),
        }

    except Exception as error:

        raise project_manager_error(error)


# ============================================================
# GET ONE AGENT DEFINITION
# ============================================================

@router.get("/api/agents/{agent_id}")
def get_agent_definition(
    request: Request,
    agent_id: str,
):
    """
    Return one agent's metadata + markdown sections. Workspace agents
    (agents/<id>/) win over library agents with the same id.
    """

    from engine.agents.loader import load_definition

    workspace = _workspace()
    ws_dir = (workspace / "agents" / agent_id) if workspace is not None else None

    if ws_dir is not None and (ws_dir / "agent.json").exists():
        try:
            meta = json.loads(
                (ws_dir / "agent.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise project_manager_error(
                ValueError(f"Agent config unreadable: {ws_dir / 'agent.json'} ({exc})")
            )
        md_file = ws_dir / "agent.md"
        md_text = md_file.read_text(encoding="utf-8")
        from engine.agents.loader import _parse_sections, _clean_body
        raw = _parse_sections(md_text)
        sections = {name: _clean_body(body) for name, body in raw.items()}
        return {
            "source": "workspace",
            "meta": meta,
            "sections": sections,
            "json_path": f"agents/{agent_id}/agent.json",
            "md_path": f"agents/{agent_id}/agent.md",
        }

    try:
        definition = load_definition(agent_id)
        return {
            "source": "library",
            "meta": definition["meta"],
            "sections": definition["sections"],
        }
    except Exception as error:
        raise project_manager_error(
            ValueError(f"Agent not found: {agent_id} ({error})")
        )


# ============================================================
# RUN ONE AGENT (from agent.json / agent.md or a library id)
# ============================================================

@router.post("/api/agents/run")
def run_single_agent(
    request: Request,
    payload: AgentRunRequest,
):
    """
    Build and run one agent, then log the exchange.

    Body:
        message:   the user's instruction (required).
        json_path/md_path:
                   workspace-relative paths to agent.json + agent.md
                   (e.g. "agents/demo/agent.json"). When given, the agent
                   is built from those files; otherwise agent_id is used.
        agent_id:  library agent to run when json_path is not given.
        model:     optional model override.
    """

    message = _validated_message(payload.message)

    try:

        if payload.json_path and payload.md_path:
            json_file = _resolve(str(payload.json_path))
            md_file = _resolve(str(payload.md_path))
            agent = build_agent_from_definition(
                str(json_file),
                str(md_file),
                model=payload.model,
                bridge=_provider(),
            )
            agent_id = str(agent.profile.id)
        elif payload.agent_id:
            agent_id = payload.agent_id
            agent = build_agent(
                agent_id,
                model=payload.model,
                bridge=_provider(),
            )
        else:
            raise project_manager_error(
                ValueError(
                    "Provide json_path + md_path, or an agent_id, to run."
                )
            )

        reply = agent.think(message)

        entries = _record_entries(message, reply)

        return {
            "status": "ok",
            "reply": reply,
            "agent_id": agent_id,
            "name": agent.profile.name,
            "description": agent.profile.description,
            "model": agent.model,
            "tool_events": agent.tool_events,
            "entry": entries[0],
        }

    except AgentNotFoundError as error:

        raise project_manager_error(
            ValueError(f"Agent definition not found: {error}")
        )

    except ValueError as error:

        raise project_manager_error(error)

    except Exception as error:

        raise project_manager_error(error)


# ============================================================
# PIPELINE OPTIONS
# ============================================================

@router.get("/api/pipeline")
def pipeline_options(
    request: Request,
):
    """
    Return the default step chain (config/pipeline.json) plus every
    selectable step candidate (library + workspace agents).

    The frontend starts with an empty selection and lets the user build an
    ordered, reorderable cascade from these candidates.
    """

    try:

        return {
            "default_steps": load_pipeline(),
            "candidates": _all_agents(),
        }

    except Exception as error:

        raise project_manager_error(error)


# ============================================================
# RUN PIPELINE (multi-agent cascade)
# ============================================================

@router.post("/api/pipeline")
def run_agent_pipeline(
    request: Request,
    payload: PipelineRunRequest,
):
    """
    Cascade many agents one after another.

    Body:
        steps:   ordered list. Each element is either a library agent id
                 (str) or a dict with workspace-relative json_path + md_path
                 (workspace agent). Every later step receives the original
                 message plus all earlier steps' replies as its input.
        message: the original user request.
        model:   optional model override for every step.

    Returns {"reply", "outputs": [{agent_id, agent_name, output, tools_used}],
    "tool_events"} and logs the exchange.
    """

    message = _validated_message(payload.message)
    steps = list(payload.steps or [])

    if not steps:

        raise project_manager_error(
            ValueError("Pipeline requires at least one step.")
        )

    try:

        normalized: list = []
        for step in steps:
            if isinstance(step, dict):
                if not (step.get("json_path") and step.get("md_path")):
                    raise project_manager_error(
                        ValueError(
                            "Pipeline step dicts need json_path + md_path: "
                            f"{step!r}"
                        )
                    )
                normalized.append({
                    "json_path": str(_resolve(str(step["json_path"]))),
                    "md_path": str(_resolve(str(step["md_path"]))),
                })
            else:
                normalized.append(str(step))

        result = run_pipeline(
            message,
            model=payload.model,
            steps=normalized,
            bridge=_provider(),
        )

        _record_entries(message, result["reply"])

        return {
            "status": "ok",
            "reply": result["reply"],
            "outputs": result["outputs"],
            "tool_events": result["tool_events"],
        }

    except AgentNotFoundError as error:

        raise project_manager_error(
            ValueError(f"Agent definition not found: {error}")
        )

    except ValueError as error:

        raise project_manager_error(error)

    except Exception as error:

        raise project_manager_error(error)


# ============================================================
# MODELS
# ============================================================

@router.get("/api/models")
def list_models(
    request: Request,
):
    """
    Return the models in config/models.json for the frontend picker.
    Run refresh_models to re-scan installed Ollama models.
    """

    from engine.core import llm

    model_file = llm.CONFIG_DIR / "models.json"

    try:

        if model_file.exists():
            data = json.loads(model_file.read_text(encoding="utf-8"))
            models = data.get("models") or []
        else:
            models = []

        return {
            "models": [
                {
                    "id": m.get("id", ""),
                    "name": m.get("name", m.get("id", "")),
                    "source": m.get("source", "ollama"),
                }
                for m in models
            ],
        }

    except Exception as error:

        raise project_manager_error(error)
```

---

<!-- ==== 6/34 : bridge/routers/chat.py ==== -->

### bridge/routers/chat.py

```python
"""
bridge/routers/chat.py
======================

Agent-backed Project Manager chat router (drop-in replacement).

The Project Manager keeps a stub chat surface: ``POST /api/chat`` logs a
message and ``GET /api/chat`` fetches history. This router swaps the stub
handler for the GenV1 agent engine, so the Project Manager becomes a fully
agent-driven server:

    POST /api/chat  {"message": str, "agent_id": str?, "model": str?}
        -> builds the requested agent (headless engine),
        -> runs agent.think(message),
        -> records user turn + reply into the headless chat log
           (data/chatlog/chat.log, which search_chat_logs reads) AND
           mirrors both entries into the Project Manager's own
           workspace/data/chat.log, and
        -> returns {"status", "reply", "agent_id", "model", "tool_events"}.

    GET /api/chat  ?limit=
        -> most recent headless chat log entries.

In-process file tools run through DirectProjectIO, so the Project Manager's
parameters.filesystem stays the single filesystem authority.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .errors import project_manager_error


# ------------------------------------------------------------
# Headless engine bootstrap (works when this file is copied into
# the Project Manager package as well as when imported from bridge/).
# ------------------------------------------------------------

def _ensure_headless_on_path() -> None:
    here = Path(__file__).resolve()
    if here.name == "chat.py" and here.parent.name == "routers":
        candidate = here.parents[3] / "headless_app"
    else:
        candidate = here.parents[2]
    candidate = candidate.resolve()
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


_ensure_headless_on_path()

from engine.agents.factory import build_agent  # noqa: E402
from engine.agents.loader import AgentNotFoundError  # noqa: E402
from engine.agents.registry import list_agents  # noqa: E402
from tools.chatlog import append_chat, read_history  # noqa: E402

try:
    from bridge.providers import DirectProjectIO  # noqa: E402
except Exception:
    DirectProjectIO = None  # type: ignore[assignment]


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# REQUEST MODELS
# ============================================================

class ChatMessage(BaseModel):

    message: str

    agent_id: str | None = None

    model: str | None = None


# ============================================================
# CHAT LOG HELPERS
# ============================================================

MAX_MESSAGE_LENGTH = 2000

DEFAULT_LIMIT = 50

MAX_LIMIT = 500

_provider_cache: Any = None


def _provider() -> Any:
    """The active filesystem authority (in-process Project Manager)."""
    global _provider_cache
    if _provider_cache is None:
        if DirectProjectIO is None:
            raise RuntimeError(
                "DirectProjectIO is unavailable - the agent-backed chat "
                "router must run inside the Project Manager package."
            )
        _provider_cache = DirectProjectIO()
    return _provider_cache


def _default_agent_id() -> str | None:
    agents = list_agents()
    if not agents:
        return None
    return agents[0]["id"]


def _mirror_pm_log(entry: dict) -> None:
    """Mirror one chat entry into the Project Manager's own chat.log."""
    try:
        from parameters import filesystem

        log_path = filesystem.resolve_project_path("data/chat.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # fail-safe: never break the chat response over a log write


def _record_entries(user_message: str, reply: str) -> list[dict]:
    """Persist user + reply to the headless chat log; mirror to PM's log."""
    user_entry = append_chat("user", user_message)
    reply_entry = append_chat("agent", reply)
    _mirror_pm_log(user_entry)
    _mirror_pm_log(reply_entry)
    return [user_entry, reply_entry]


# ============================================================
# SEND MESSAGE
# ============================================================

@router.post("/api/chat")
def send_chat_message(
    request: Request,
    payload: ChatMessage,
):
    """
    Send a message to the agent engine and return its reply.

    Body:
        message (str):   the user's message (required, non-empty, max 2000).
        agent_id (str):  agent to use; defaults to the first registered.
        model (str):     optional model override.
    """

    message = payload.message.strip()

    if not message:

        raise project_manager_error(
            ValueError(
                "Chat message cannot be empty."
            )
        )

    if len(message) > MAX_MESSAGE_LENGTH:

        raise project_manager_error(
            ValueError(
                f"Chat message is too long "
                f"(max {MAX_MESSAGE_LENGTH} characters)."
            )
        )

    agent_id = payload.agent_id or _default_agent_id()

    if not agent_id:

        raise project_manager_error(
            RuntimeError(
                "No agents are registered in engine/agent_library/."
            )
        )

    try:

        agent = build_agent(
            agent_id,
            model=payload.model,
            bridge=_provider(),
        )

        reply = agent.think(message)

        entries = _record_entries(message, reply)

        return {
            "status": "ok",
            "reply": reply,
            "agent_id": agent_id,
            "model": agent.model,
            "tool_events": agent.tool_events,
            "entry": entries[0],
        }

    except AgentNotFoundError as error:

        raise project_manager_error(
            ValueError(
                f"Agent not found: {agent_id} ({error})"
            )
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# FETCH HISTORY
# ============================================================

@router.get("/api/chat")
def get_chat_history(
    request: Request,
    limit: int = DEFAULT_LIMIT,
):
    """
    Return the most recent chat entries.

    Query params:
        limit:
            Maximum number of entries to return.
    """

    try:

        return {
            "entries": read_history(limit),
        }

    except Exception as error:

        raise project_manager_error(
            error
        )


if __name__ == "__main__":
    print(__doc__)
```

---

<!-- ==== 7/34 : bridge/tools_adapter.py ==== -->

### bridge/tools_adapter.py

```python
"""
bridge/tools_adapter.py
=======================

Maps the headless agent tools to their Project Manager HTTP surface and
binds a bridge to the tool registry.

The tools themselves live in tools/project_tools.py and branch on the
configured provider; this module is the wiring point that turns a bridge
(or direct provider) into the active filesystem authority for all agents
built afterwards.

TOOL_ENDPOINT_MAP documents, for each tool id, the Project Manager endpoint
the tool ultimately drives when a bridge is connected.
"""

from __future__ import annotations

from typing import Any

import tools.registry as _registry

#: Tool id -> Project Manager endpoint backing it (informational).
TOOL_ENDPOINT_MAP: dict[str, str] = {
    "map_files": "GET /api/project (filesystem tree)",
    "read_file": "GET /api/file/read",
    "write_text_file": "PUT /api/file/write | POST /api/file/create",
    "delete_files": "DELETE /api/file/delete",
    "get_current_date": "(local)",
    "tell_me_the_date_and_time": "(local)",
    "search_chat_logs": "get data/chatlog/chat.log (local store)",
}


def bind_tools(bridge: Any) -> Any:
    """Point the tool registry's file tools at a Project Manager provider.

    Pass either a ProjectManagerBridge (HTTP) or a DirectProjectIO
    (in-process filesystem authority). Returns the same provider for
    convenience, so callers can chain it.

    All agents built AFTER this call route their file tools through the
    provider until configure(None) is called again.
    """
    _registry.configure(bridge)
    print(
        f"[tools_adapter] file tools bound to Project Manager "
        f"(root={getattr(bridge, 'workspace_root', '?')})"
    )
    return bridge


def unbind_tools() -> None:
    """Return the file tools to the local-disk backend."""
    _registry.configure(None)


def describe_tools() -> dict[str, str]:
    """Return the tool-id -> endpoint map for documentation/debugging."""
    return dict(TOOL_ENDPOINT_MAP)


__all__ = [
    "bind_tools",
    "unbind_tools",
    "describe_tools",
    "TOOL_ENDPOINT_MAP",
]
```

---

<!-- ==== 8/34 : config/models.json ==== -->

### config/models.json

```json
{
  "models": [
    {
      "id": "llama3.1:8b",
      "name": "llama3.1:8b",
      "source": "ollama",
      "size": 4920753328
    },
    {
      "id": "nomic-embed-text:latest",
      "name": "nomic-embed-text:latest",
      "source": "ollama",
      "size": 274302450
    },
    {
      "id": "qwen2.5-coder:latest",
      "name": "qwen2.5-coder:latest",
      "source": "ollama",
      "size": 4683087561
    },
    {
      "id": "gemma4:e2b",
      "name": "gemma4:e2b",
      "source": "ollama",
      "size": 7162405886
    }
  ]
}
```

---

<!-- ==== 9/34 : config/pipeline.json ==== -->

### config/pipeline.json

```json
{
  "name": "module-generation",
  "description": "One idea -> a working drop-in custom module. Step 1 drafts the feature plan, Step 2 turns it into a blueprint grounded on the skills reference, Step 3 writes the .py module file.",
  "steps": [
    "feature_planner_agent",
    "execute_engineer_agent",
    "module_builder_agent"
  ]
}
```

---

<!-- ==== 10/34 : engine/__init__.py ==== -->

### engine/__init__.py

```python
(empty file — 0 bytes)
```

---

<!-- ==== 11/34 : engine/agent_library/Builder/agent.json ==== -->

### engine/agent_library/Builder/agent.json

```json
{
  "id": "module_builder_agent",
  "name": "Module Builder Agent",
  "description": "Step 3: Confirms the target save location, then compiles Step 2 blueprints into complete 3-phase drop-in Python modules.",
  "mode": "agent",
  "model": "qwen2.5-coder:latest",
  "tools": [
    "map_files",
    "read_file",
    "write_text_file"
  ]
}
```

---

<!-- ==== 12/34 : engine/agent_library/Builder/agent.md ==== -->

### engine/agent_library/Builder/agent.md

````markdown
# Module Builder Agent

## role
You are the **Module Builder Agent** (Step 3 of the Genessis Module Development Pipeline). Your role is to take a Stage 2 Technical Implementation Blueprint provided directly in the user's message and compile it into a single, complete, production-ready Python custom module file.

## purpose
To convert technical blueprints into runnable Python custom module code (`<module_name>.py`) that communicates with the rest of the Genessis application through the interface framework (`UI_MANIFEST` + `register_routes(app)` FastAPI endpoints + `server.paths` path authority + `InterfaceDispatcher` wiring).

## tools
You have access to exactly **THREE tools** and MUST ONLY use these tools:
1. `read_file`: Reads text and document file contents from disk.
2. `write_text_file`: Writes text files directly to a specified directory on disk.
3. `map_files`: Inspects directory structures and lists file trees on disk.

**Tool Rule**: You MUST ONLY use `read_file`, `write_text_file`, and `map_files`. Do NOT attempt to execute or call any other tools outside of these three.

## do_not_hallucinate
- **Strict Route Encapsulation**: EVERY route decorator (`@app.get(...)`, `@app.post(...)`) MUST be placed INSIDE the top-level `def register_routes(app: FastAPI):` function definition. NEVER write `@app.get` or `@app.post` at the root level of the file, because `app` is only passed to `register_routes(app)` at runtime.
- **Strict Grounding**: Do NOT fabricate or invent non-existent UI action types, ungrounded schema keys, or fake framework decorators. Only use the 4 supported Genessis UI action patterns (`prompt_input`, `dropdown_menu`, `open_modal`, `qa_survey`) and standard FastAPI decorators (`@app.get`, `@app.post`).
- **No Incomplete / Imaginary Code**: Never invent imaginary function calls, fake imports, or unverified backend helper methods. Always import path storage authority from `server.paths` (`DATA_DIR`, `EXPORTS_DIR`, `RECORDS_DIR`, `RAG_DB_DIR`).
- **No Hallucinated Tool Calls**: Never output fake tool JSON schemas or imaginary function names like `execute_plan()`. When using your tools, emit valid calls for `read_file`, `write_text_file`, or `map_files` only.

## input_contract
- You accept the **Stage 2 Technical Implementation Blueprint** passed directly as text in the conversation message.
- Output the complete Python custom module code in a single markdown code block. Do NOT ask save questions or emit pre-script chatter.

## workflow
Compile the incoming Stage 2 blueprint into a single Python script file organized into three explicit code phases:

### Phase 1: UI Phase (`UI_MANIFEST` Declaration)
- Declare the top-level `UI_MANIFEST` dictionary matching the module ID and header button action specifications (`prompt_input`, `dropdown_menu`, `open_modal`, `qa_survey`).

### Phase 2: Logic & Server Endpoints Phase (`register_routes` + Real-Time Logging)
- Define `register_routes(app: FastAPI)` to mount ALL GET and POST route handlers INSIDE this function.
- **Real-Time Terminal Execution Logging**: Include descriptive `print(f"[{module_id}] ...")` statements at key execution points inside every endpoint to stream execution logic live to the terminal console.
- Import storage paths directly from `server.paths` (`EXPORTS_DIR`, `DATA_DIR`, `RECORDS_DIR`, `RAG_DB_DIR`).
- Return standard JSON response contracts: `{"status": "success", "message": "...", "indicate_success": True}`.

### Phase 3: Variable Map & Extension Architecture
- Include a structured docstring block mapping all global imports, path authorities, data payload keys, and output files.
- Provide explicit extension hook functions (`_extension_pre_process_hook` and `_extension_post_process_hook`) for future feature additions.

## boundaries
- **Code Only**: Output ONLY the Python script inside a single markdown code block. No preambles or file save questions.
- **All Routes Enclosed**: All FastAPI route handlers must be defined inside `def register_routes(app: FastAPI):`.
- **Strict Genessis Contracts**: Use exact schema keys (`components`, `target_endpoint`, `indicate_success`, `status`, `message`).
- **No Incomplete Placeholders**: Produce complete, syntactically valid, runnable Python code without unindented blocks or `TODO` gaps.
- **Path Authority**: Always import storage locations from `server.paths`. Never hardcode relative string paths or drive letters.

## output_format
Output strictly the Python code block:

```python
"""
Drop-in Custom Module: <module_name>.py
Generated by: Module Builder Agent (Step 3)
"""

from datetime import datetime
import json
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from server.paths import DATA_DIR, EXPORTS_DIR, RECORDS_DIR

# ==============================================================================
# PHASE 1: UI PHASE (UI_MANIFEST Declaration)
# ==============================================================================
UI_MANIFEST = {
    "module_id": "<module_name>",
    "buttons": [
        {
            "id": "btn-<module_name>",
            "label": "💬 <Label>",
            "target": "header",
            "action": "open_modal",
            "schema_endpoint": "/api/<module_name>/schema",
            "title": "<Title>"
        }
    ]
}

# ==============================================================================
# PHASE 2: LOGIC & SERVER ENDPOINTS PHASE (register_routes + Real-Time Logging)
# ==============================================================================
def register_routes(app: FastAPI):
    """Registers FastAPI endpoints with real-time terminal execution logging."""

    @app.get("/api/<module_name>/schema")
    def get_schema():
        print("[<module_name>] GET /api/<module_name>/schema -> Serving modal schema.")
        return {
            "title": "<Modal Title>",
            "target_endpoint": "/api/<module_name>/execute",
            "components": [
                {"type": "input", "name": "user_message", "label": "Message", "placeholder": "Type here..."},
                {"type": "button", "label": "Submit", "action": "submit"}
            ]
        }

    @app.post("/api/<module_name>/execute")
    async def execute_action(payload: dict):
        print(f"[<module_name>] POST /api/<module_name>/execute -> Payload: {payload}")

        # Extension Hook execution
        payload = _extension_pre_process_hook(payload)

        user_message = payload.get("user_message", "").strip()

        response = {
            "status": "success",
            "message": f"Successfully processed message: '{user_message}'",
            "indicate_success": True
        }

        _extension_post_process_hook(None, response)
        return response

# ==============================================================================
# PHASE 3: VARIABLE ARCHITECTURE MAP & EXTENSION HOOKS
# ==============================================================================
"""
--- MODULE ARCHITECTURE & VARIABLE MAP ---
• Global Imports / Path Authority:
  - EXPORTS_DIR: Resolved path for saved JSON export records.
• Data Objects & Keys:
  - payload.user_message (str): Primary input key.

--- EXTENSION HOOKS & FUTURE CAPABILITIES ---
To add extra features to this module:
1. Insert custom data transformation inside `_extension_pre_process_hook()`.
2. Add external webhook triggers inside `_extension_post_process_hook()`.
"""

def _extension_pre_process_hook(data: dict) -> dict:
    """Extension Point: Pre-process incoming payload before endpoint execution."""
    return data

def _extension_post_process_hook(record_path: Path, result: dict) -> None:
    """Extension Point: Post-process after file persistence."""
    pass
````

---

<!-- ==== 13/34 : engine/agent_library/Enginner/agent.json ==== -->

### engine/agent_library/Enginner/agent.json

```json
{
  "id": "execute_engineer_agent",
  "name": "Execute Engineer Agent",
  "description": "Step 2: Uses read_file to inspect ux_module_designer_skills.md and translates Step 1 functional plans into section-by-section pseudo-code and Genessis Python blueprints.",
  "mode": "agent",
  "model": "qwen2.5-coder:latest",
  "tools": [
    "read_file"
  ]
}
```

---

<!-- ==== 14/34 : engine/agent_library/Enginner/agent.md ==== -->

### engine/agent_library/Enginner/agent.md

````markdown
# Execute Engineer Agent

## role
You are the **Execute Engineer Agent** (Step 2). Your role is to take the functional feature list from Step 1 and translate it into structured pseudo-code and Python implementation blueprints grounded strictly in the Genessis skills reference.

## purpose
To bridge functional requirements and code by applying the implementation patterns defined in `E:\genV2_Interface_projectManager\skills\ux_module_designer_skills.md`.

## input_contract
Accepts the **Feature Plan** document from Step 1. The Feature Plan for the CURRENT task is always included in your incoming message - never ask for it or wait for it.

## skills
Reference `E:\genV2_Interface_projectManager\skills\ux_module_designer_skills.md` for:
1. `UI_MANIFEST` button declarations.
2. Action button logic (`prompt_input`, `dropdown_menu`, `open_modal`, `qa_survey`).
3. Endpoint registration via `register_routes(app)`.
4. Standard status response contracts (`status`, `message`, `indicate_success`).
5. Storage path authority using `server.paths`.

## workflow
0. **Load the Skills Reference ONCE**: call the `read_file` tool on `E:\genV2_Interface_projectManager\skills\ux_module_designer_skills.md` by default, and read exactly ONE TIME. If the result of that read is already in the conversation (any earlier `read_file` result message with tool "read_file" and path `ux_module_designer_skills.md`), do NOT call it again - that file never changes during your turn. Ground every decision on what that file actually contains. Never guess or invent patterns not present in it.
1. Map the functional requirements from Step 1 to skills in `ux_module_designer_skills.md`.
2. Write step-by-step pseudo-code explaining the UI and server endpoint logic.
3. Provide concrete Python code examples for `UI_MANIFEST` and `register_routes(app)`.

## boundaries
- **Strict Grounding**: Do NOT invent unsupported UI action types or non-existent framework decorators.
- **Dynamic Scoping**: Adapt logic dynamically to whatever module ID and fields are passed in the plan.
- **No Stalling**: The Step 1 Feature Plan IS included in your message. Never ask for it, never repeat that you are waiting for it, and never ask the user to provide it - act on it immediately. If a detail is missing, state the one missing field in a single line and move on.

## output_format
### 1. Executive Summary
- **Module ID**: `<module_name>`
- **UI Action Type**: [`prompt_input` | `dropdown_menu` | `open_modal` | `qa_survey`]

### 2. UI Manifest Specification
**Pseudo-Code:**
```text
[Step-by-step logic for UI_MANIFEST declaration]
```
**Python Implementation:**
```python
UI_MANIFEST = { ... }
```

### 3. Backend Route Handlers (`register_routes`)
**Pseudo-Code:**
```text
[Step-by-step logic for FastAPI GET/POST endpoints]
```
**Python Implementation:**
```python
def register_routes(app: FastAPI):
    ...
```

### 4. Path & Core Wiring Integration
**Pseudo-Code & Python Examples for `server.paths` storage.**
````

---

<!-- ==== 15/34 : engine/agent_library/Planner/agent.json ==== -->

### engine/agent_library/Planner/agent.json

```json
{
  "id": "feature_planner_agent",
  "name": "Feature Planner Agent",
  "description": "Step 1: Translates raw feature ideas into a functional specification list (UI actions, endpoint contracts, storage needs) without writing code.",
  "mode": "chat",
  "model": "qwen2.5-coder:latest",
  "tools": []
}
```

---

<!-- ==== 16/34 : engine/agent_library/Planner/agent.md ==== -->

### engine/agent_library/Planner/agent.md

```markdown
(empty file — 0 bytes)
```

---

<!-- ==== 17/34 : engine/agent_library/rag_assistant/agent.json ==== -->

### engine/agent_library/rag_assistant/agent.json

```json
{
  "id": "rag_assistant",
  "name": "RAG Assistant",
  "description": "Stateful agent with workspace file-management access and memory retrieval.",
  "mode": "agent",
  "model": "gemma4:e2b",
  "tools": [
    "map_files",
    "read_file",
    "write_text_file",
    "delete_files",
    "get_current_date",
    "search_chat_logs"
  ],
  "tests": [
    {
      "id": "custom-mtqa6k4j-s1wo",
      "name": "Please help me consolidate my chat records in: E:\\data\\rag_s...",
      "steps": [
        "Please help me consolidate my chat records in: E:\\data\\rag_store\\chatlog\\agent-text-records",
        "Follow these steps sequentially using your tools:",
        "Run `map_files` on that directory to find all \".txt\" files.",
        "Use `read_file` to open and extract the text from each discovered file.",
        "Combine all the chat lines, remove any duplicate logs or repeat entries, and organize them into one chronological file.",
        "Run `write_text_file` to save this clean consolidated log in that same directory as \"consolidated_chat_records.txt\".",
        "Call `delete_files` with approved=False for all the original duplicate files you read, and ask me for my confirmation to permanently delete them."
      ],
      "expectedResult": {
        "mode": "type",
        "value": "nonEmpty"
      },
      "enabled": true
    }
  ]
}
```

---

<!-- ==== 18/34 : engine/agent_library/rag_assistant/agent.md ==== -->

### engine/agent_library/rag_assistant/agent.md

```markdown
# RAG Assistant

## role
You are the **RAG Assistant**, a secure workspace file-manager and memory-retrieval specialist.

## greeting
Standard greeting: I am a RAG Assistant.

## purpose
Retrieve insights from past sessions and help Jesus discover, read, write, and manage workspace files safely.

## boundaries
- **Past Memory:** When asked about past work, call `search_chat_logs`. Translate temporal keywords (like "last session") into topical terms.
- **Workspace Discovery:** Use `map_files` to inspect workspace structure. Do not assume file paths.
- **File Access:** Open text or document contents strictly via `read_file`. Keep the context window clean by only reading what is needed.
- **Writing Results:** Write results using `write_text_file`. Ensure safety rules are followed.
- **Grounding:** Ground every factual claim strictly in the retrieved logs or file contexts. Do not fabricate.

## how to call tools (critical)
You can only take actions by ACTUALLY executing the tools given to you. To call a tool, emit ONLY a
JSON object as your entire reply, with a `name` key and a `parameters` key:

    {"name": "read_file", "parameters": {"path": "E:\\data\\example.txt"}}

- Use exactly `parameters` for the arguments object (the runtime also accepts `arguments` or `args`).
- For multiple steps in one turn, emit a JSON ARRAY of such objects; each will be executed in order.
- Never describe a call in words, never put calls inside Python/markdown code blocks, and never write
  pseudo-code like `read_file("x")` — those are NOT executed.
- Never invent or guess file paths or file contents. Only reference paths you actually saw in the
  session state: `discovered_files`, `read_files`, `output_files`, or `pending_deletion`.
- When reading many files, still read them one `read_file` call per file.

## safe deletion protocol (two-step confirmation)
To ensure no files are deleted accidentally, you must strictly follow this two-step verification protocol:

1. **Step 1: Request Deletion (Propose & Ask)**
   - When files are identified as no longer needed, you must **NEVER** call `delete_files(..., approved=True)` first.
   - You must first call `delete_files(file_list, approved=False)` to register the pending deletion.
   - You must then explicitly present the list of files to Jesus and ask: *"Are you sure you want to delete these files? Please confirm to finalize."*

2. **Step 2: Execute Deletion (After Approval)**
   - Only after Jesus explicitly responds with confirmation (e.g., "yes", "go ahead", "approved", "confirm") are you authorized to execute the deletion.
   - At this point, call `delete_files(file_list, approved=True)` to permanently remove the files and report the success or failure status back to Jesus.
```

---

<!-- ==== 19/34 : engine/agents/__init__.py ==== -->

### engine/agents/__init__.py

```python
(empty file — 0 bytes)
```

---

<!-- ==== 20/34 : engine/agents/factory.py ==== -->

### engine/agents/factory.py

```python
"""
app/agents/factory.py
=====================

Constructs runtime Agents from agent definitions.

    build_agent(agent_id, model)
        ↓
    loader.load_definition()      (agent.md + agent.json)
        ↓
    registry: resolve tools       (IDs -> Python functions)
        ↓
    PromptManager.build()         (sections + tool docstrings -> system prompt)
        ↓
    Agent

The caller never needs to know where definitions live or how prompts are
composed. Chat-mode agents get an empty tool list, which disables the
tool loop entirely - same Agent class, behavior driven by configuration.
"""

from typing import Callable
from pathlib import Path

from engine.agents.loader import (
    load_definition,
    load_definition_from_paths,
    agent_dir,
    AgentNotFoundError,
)
from engine.core.agent import Agent
from engine.core.prompt import PromptManager
from tools.registry import resolve_tools, get_session, configure as configure_tools


def _session_aware(func: Callable, session) -> Callable:
    """Wrap a tool so its results are recorded into the shared FileSession.

    Uses functools.wraps so inspect.signature() (and therefore the schema
    Ollama builds for tool calling) sees the REAL tool signature, not the
    wrapper's (*args, **kwargs).

    Standard tool response shape: {"success", "tool", "data": {...}, "error"}.
    Known data keys are translated into session state:
        files                   -> add_discovered(paths)
        path / path+content     -> record_read(...)
        filename/path (written) -> add_output(path)
        pending_files (delete)  -> mark_for_deletion(paths)

    Safety gate: delete_files(approved=True) can only delete paths that were
    previously PROPOSED (approved=False) and recorded in session.pending_deletion.
    Any path the model fabricates or invents is rejected instead of deleted.
    """
    import functools
    import inspect as _inspect

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if func.__name__ == "delete_files" and session is not None:
            bound, approved, file_list = _bind_delete_args(func, args, kwargs)
            if approved and file_list:
                pending = list(session.pending_deletion or [])
                proposed = [f for f in file_list if f in pending]
                rejected = [f for f in file_list if f not in pending]
                if not proposed:
                    return {
                        "success": False,
                        "tool": "delete_files",
                        "data": {},
                        "error": (
                            "Deletion blocked: none of these paths were previously "
                            "proposed for deletion. Run delete_files with "
                            "approved=False first."
                        ),
                    }
                bound.arguments["file_list"] = proposed
                try:
                    result = func(*bound.args, **bound.kwargs)
                except TypeError:
                    result = None
                if isinstance(result, dict):
                    data = result.get("data") or {}
                    data["rejected"] = rejected
                    if rejected and not result.get("error"):
                        result["error"] = "Some paths were not previously proposed and were skipped."
                    deleted = [k for k, v in data.get("results", {}).items() if v == "deleted"]
                    if deleted:
                        session.pending_deletion = [p for p in session.pending_deletion if p not in deleted]
                return result

        result = func(*args, **kwargs)
        _record_result(result, session)
        return result

    # Belt-and-braces: even if a future consumer uses follow_wrapped=False,
    # the wrapper advertises the real signature and annotations.
    wrapper.__signature__ = _inspect.signature(func)
    wrapper.__annotations__ = func.__annotations__
    return wrapper


def _bind_delete_args(func, args, kwargs):
    """Bind delete_files(*args, **kwargs) into (BoundArguments, approved, file_list)."""
    import inspect as _inspect
    try:
        bound = _inspect.signature(func).bind(*args, **kwargs)
        bound.apply_defaults()
    except TypeError:
        return None, False, []
    return bound, bool(bound.arguments.get("approved")), list(bound.arguments.get("file_list") or [])


def _record_result(result, session) -> None:
    """Translate a tool result dict into shared FileSession state."""
    if not (isinstance(result, dict) and session is not None):
        return
    from tools.state import FileSession
    data = result.get("data") or {}
    if result.get("tool") == "map_files":
        files = data.get("files") or []
        session.add_discovered([f["path"] for f in files])
    elif result.get("tool") == "read_file":
        session.record_read(data.get("path", ""), data.get("extracted_content", ""))
    elif result.get("tool") == "write_text_file" and data.get("path"):
        session.add_output(data["path"])
    elif result.get("tool") == "delete_files" and data.get("pending_files"):
        session.mark_for_deletion(data["pending_files"])


def _append_grounding(agent_id: str, profile, bridge=None) -> None:
    """Append a compact grounding block to a tool-armed agent's system prompt.

    Small local models routinely call path tools with invented paths, bare
    filenames, or literally '/path/to/...' placeholders copied from a prompt.
    Pinning a real WORKSPACE ROOT plus the agent's own folder and skills dir
    gives the model deterministic places to start with map_files, and an
    explicit instruction to stop guessing once a lookup fails.

    When a Project Manager bridge is present it is the filesystem authority,
    so its workspace root becomes the grounding root instead of the local app.
    """
    from pathlib import Path

    if bridge is not None:
        workspace_root = str(getattr(bridge, "workspace_root", ""))
        if not workspace_root:
            bridge_health = getattr(bridge, "health", lambda: {})()
            workspace_root = str((bridge_health or {}).get("root", ""))
    else:
        workspace_root = str(Path(__file__).resolve().parents[2].resolve())

    root = Path(workspace_root)
    skill_dir = Path(__file__).resolve().parents[2] / "skills"
    skills = ", ".join(sorted(p.name for p in skill_dir.glob("*.md"))) if skill_dir.is_dir() else ""

    block = [
        "GROUNDING (read this before you call any file tool)",
        f"- WORKSPACE ROOT: {workspace_root}",
        f"- THIS AGENT FOLDER: {str(agent_dir(agent_id).resolve())}",
    ]
    if skills:
        block.append(f"- SKILLS DIRECTORY: {str(skill_dir.resolve())} (files: {skills})")
    block += [
        "- Use file paths relative to WORKSPACE ROOT. Start by calling map_files on the",
        "  root, then read_file only on a path map_files returned.",
        "- Never call readonly tools on a bare filename, a '/path/to/...' placeholder, or any",
        "  path you invented. If a tool reports 'not found', DO NOT guess another filename:",
        "  run map_files on WORKSPACE ROOT / THIS AGENT FOLDER first and read what exists.",
    ]
    profile.system_prompt = profile.system_prompt + "\n\n" + "\n".join(block)


def _assemble(
    meta: dict,
    sections: dict,
    agent_id: str,
    model: str | None,
    bridge=None,
) -> Agent:
    """Shared Agent construction from a parsed definition."""
    definition = {"meta": meta, "sections": sections}

    mode = (meta.get("mode") or "chat").lower()
    tool_ids = [] if mode == "chat" else (meta.get("tools") or [])
    tools: list[Callable] = resolve_tools(tool_ids)

    profile = PromptManager.build(definition, tools)
    if tools:
        _append_grounding(agent_id, profile, bridge=bridge)

    resolved_model = model or meta.get("model") or None
    session = get_session()
    tools = [_session_aware(fn, session) for fn in tools]
    return Agent(model=resolved_model, tools=tools, profile=profile, session=session)


def build_agent(agent_id: str, model: str | None = None, bridge=None) -> Agent:
    """Build a ready-to-use Agent for the given agent_id.

    Args:
        agent_id: folder name / id inside agent_library/
        model:    explicit model override; when empty, falls back to the
                  agent's own "model" field, then to ask_llm's resolution
                  (config/models.json > first Ollama model).
        bridge:   optional Project Manager bridge (HTTP client or direct
                  filesystem authority). When present, the agent's file tools
                  route through the Project Manager instead of the local disk.

    Raises AgentNotFoundError if the definition is missing.
    """
    if bridge is not None:
        configure_tools(bridge)
    definition = load_definition(agent_id)
    return _assemble(
        definition["meta"],
        definition["sections"],
        agent_id,
        model,
        bridge=bridge,
    )


def build_agent_from_definition(
    json_path: str,
    md_path: str,
    model: str | None = None,
    bridge=None,
) -> Agent:
    """Build a ready-to-use Agent from explicit agent.json + agent.md paths.

    This is the headless construction path (run_single_agent, pipelines that
    take raw configs): the definition is loaded from any location, not only
    engine/agent_library/.

    Raises AgentNotFoundError if either file is missing/unreadable.
    """
    if bridge is not None:
        configure_tools(bridge)
    definition = load_definition_from_paths(json_path, md_path)
    meta = definition["meta"]
    agent_id = str(meta.get("id") or Path(json_path).parent.name or "custom")
    return _assemble(
        meta,
        definition["sections"],
        agent_id,
        model,
        bridge=bridge,
    )


def replay_history(agent: Agent, history: list[dict] | None) -> None:
    """Replay prior frontend turns ({role, content}) into the agent's history."""
    for m in (history or []):
        role = "assistant" if m.get("role") == "ai" else m.get("role", "user")
        content = m.get("content", "")
        if not content:
            continue
        agent.messages.append({"role": role, "content": content})


__all__ = ["build_agent", "build_agent_from_definition", "replay_history", "AgentNotFoundError"]
```

---

<!-- ==== 21/34 : engine/agents/loader.py ==== -->

### engine/agents/loader.py

```python
"""
app/agents/loader.py
====================

Locates, reads, and parses one agent definition from agent_library/.

An agent folder contains:
    agent.json  - metadata/configuration (id, name, mode, tools, model)
    agent.md    - behavior sections (## role, ## purpose, ## boundaries, ...)

load_definition() returns:
    {"meta": {...agent.json...}, "sections": {...parsed markdown sections...}}

This module does NOT run agents. Its job is only: find, read, parse, return.
"""

import json
import re
from pathlib import Path

AGENT_LIBRARY_DIR = Path(__file__).resolve().parent.parent / "agent_library"
AGENT_META_FILE = "agent.json"
AGENT_MD_FILE = "agent.md"


def agent_dir(agent_id: str) -> Path:
    """The folder for an agent id inside agent_library/.

    First tries the literal ``agent_library/<agent_id>`` path (fast path).
    When that is missing or not a directory, scans ``agent_library/*/agent.json``
    and returns the first folder (sorted) whose ``meta["id"]`` matches, so
    folder names with spaces, kebab-case, etc. all work as long as the
    ``agent.json`` ``id`` field is set. Falls back to the literal path so
    callers that create folders (``save_markdown``) still work for brand-new
    agents.
    """
    resolved = _resolve_agent_dir(agent_id)
    return resolved if resolved is not None else AGENT_LIBRARY_DIR / agent_id


def _resolve_agent_dir(agent_id: str) -> Path | None:
    """Find the on-disk folder for an agent by id.

    Two strategies, tried in order:
        1. Literal: ``AGENT_LIBRARY_DIR / agent_id`` exists and is a directory.
        2. Scan: walk every subfolder of ``AGENT_LIBRARY_DIR``, read its
           ``agent.json``, and return the first (sorted by folder name) whose
           ``meta["id"]`` equals ``agent_id``.

    Returns ``None`` when nothing matches so callers can fall back to the
    literal path (which preserves the existing create-folder semantics for
    ``save_markdown`` on genuinely new agents).
    """
    literal = AGENT_LIBRARY_DIR / agent_id
    if literal.is_dir():
        return literal

    # Scan: read agent.json in each sibling folder, match by "id" field.
    # Folders are sorted for deterministic tie-breaking when (unlikely)
    # multiple folders declare the same id.
    candidates: list[tuple[str, Path]] = []
    if AGENT_LIBRARY_DIR.exists():
        for child in AGENT_LIBRARY_DIR.iterdir():
            if not child.is_dir() or child.name.startswith(("_", ".")):
                continue
            meta_file = child / AGENT_META_FILE
            if not meta_file.exists():
                continue
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if meta.get("id") == agent_id:
                candidates.append((child.name, child))

    candidates.sort(key=lambda t: t[0])
    return candidates[0][1] if candidates else None


def save_meta(agent_id: str, meta: dict) -> dict:
    """Merge `meta` into the agent's agent.json (top-level keys only) and
    write it back pretty-printed. Unknown keys survive untouched."""
    agent_path = agent_dir(agent_id)
    meta_file = agent_path / AGENT_META_FILE
    if not meta_file.exists():
        raise AgentNotFoundError(f"Agent config not found: {meta_file}")

    stored = json.loads(meta_file.read_text(encoding="utf-8"))
    stored.update(meta)
    meta_file.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return stored


def save_markdown(agent_id: str, markdown: str) -> str:
    """Write the agent's behavior prose to agent.md."""
    agent_path = agent_dir(agent_id)
    agent_path.mkdir(parents=True, exist_ok=True)
    md_file = agent_path / AGENT_MD_FILE
    md_file.write_text(str(markdown), encoding="utf-8")
    return str(markdown)


def save_tests(agent_id: str, tests: list) -> list:
    """Store the agent's own chat tests under agent.json#tests.

    Tests are scoped by their location, so any stored `agentId` is dropped;
    ensures every test keeps a unique id.
    """
    normalized = []
    for test in tests or []:
        if not isinstance(test, dict):
            continue
        entry = dict(test)
        entry.pop("agentId", None)
        if not entry.get("id"):
            entry["id"] = "t-" + json.dumps(entry, sort_keys=True)[:8]
        normalized.append(entry)
    save_meta(agent_id, {"tests": normalized})
    return normalized


class AgentNotFoundError(FileNotFoundError):
    """Raised when an agent folder or its required files are missing."""


def _parse_sections(text: str) -> dict:
    """Split agent.md into '## <name>' sections (section name lowercased)."""
    sections = {}
    current = None
    buffer = []
    for line in text.splitlines(keepends=True):
        match = re.match(r"^\s*##\s+(.+?)\s*$", line)
        if match:
            if current is not None:
                sections[current] = "".join(buffer)
            current, buffer = match.group(1).strip().lower(), []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "".join(buffer)
    return sections


def _clean_body(text: str) -> str:
    """Trim blank lines and '---' separators from the edges of a section body."""
    lines = text.splitlines()
    while lines and (not lines[0].strip() or lines[0].strip() in ("---", "***")):
        lines.pop(0)
    while lines and (not lines[-1].strip() or lines[-1].strip() in ("---", "***")):
        lines.pop()
    return "\n".join(lines).strip("\n")


def load_definition(agent_id: str) -> dict:
    """Load one agent definition from agent_library/{agent_id}/.

    Returns {"meta": dict, "sections": dict}. Raises AgentNotFoundError
    when the folder or either required file is missing/unreadable.
    """
    agent_dir = _resolve_agent_dir(agent_id)
    if agent_dir is None:
        agent_dir = AGENT_LIBRARY_DIR / agent_id
    json_file = agent_dir / AGENT_META_FILE
    md_file = agent_dir / AGENT_MD_FILE

    if not json_file.exists():
        raise AgentNotFoundError(f"Agent not found: {json_file}")
    if not md_file.exists():
        raise AgentNotFoundError(f"Agent not found: {md_file}")

    try:
        meta = json.loads(json_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentNotFoundError(f"Agent config unreadable: {json_file} ({exc})")

    try:
        md_text = md_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise AgentNotFoundError(f"Agent markdown unreadable: {md_file} ({exc})")

    raw_sections = _parse_sections(md_text)
    # The '# Title' line before the first section is ignored; every
    # '## section' body gets whitespace/separator cleanup.
    sections = {name: _clean_body(body) for name, body in raw_sections.items()}

    return {"meta": meta, "sections": sections}


def load_definition_from_paths(
    json_path: str | Path,
    md_path: str | Path,
) -> dict:
    """Load one agent definition from explicit agent.json + agent.md paths.

    This is the headless entry point used when an agent's definition comes
    from arbitrary locations (e.g. ad-hoc agents built by run_single_agent)
    instead of the bundled engine/agent_library/.

    Returns {"meta": dict, "sections": dict}. Raises AgentNotFoundError
    when either file is missing/unreadable.
    """
    json_file = Path(json_path)
    md_file = Path(md_path)

    if not json_file.exists():
        raise AgentNotFoundError(f"Agent config not found: {json_file}")
    if not md_file.exists():
        raise AgentNotFoundError(f"Agent markdown not found: {md_file}")

    try:
        meta = json.loads(json_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentNotFoundError(f"Agent config unreadable: {json_file} ({exc})")

    try:
        md_text = md_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise AgentNotFoundError(f"Agent markdown unreadable: {md_file} ({exc})")

    raw_sections = _parse_sections(md_text)
    sections = {name: _clean_body(body) for name, body in raw_sections.items()}

    return {"meta": meta, "sections": sections}
```

---

<!-- ==== 22/34 : engine/agents/registry.py ==== -->

### engine/agents/registry.py

```python
"""
app/agents/registry.py
======================

Automatic agent discovery.

The filesystem is the source of truth: every folder in agent_library/
that contains an agent.json is an available agent. Dropping a new folder
in agent_library/ makes it appear in GET /api/agents and the frontend
selector on the next server restart - no code changes, no manual lists.
"""

import json
from pathlib import Path

from engine.agents.loader import AGENT_LIBRARY_DIR


def list_agents() -> list[dict]:
    """Scan agent_library/ and return one summary per discovered agent:

        [{"id", "name", "description", "mode", "model"}, ...]

    Folders without a readable agent.json are skipped with a warning so
    a half-created agent cannot break the whole application.
    """
    agents = []
    if not AGENT_LIBRARY_DIR.exists():
        print(f"[REGISTRY] agent_library not found at {AGENT_LIBRARY_DIR}")
        return agents

    for agent_dir in sorted(AGENT_LIBRARY_DIR.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name.startswith(("_", ".")):
            continue

        meta_file = agent_dir / "agent.json"
        if not meta_file.exists():
            print(f"[REGISTRY] skipping {agent_dir.name}: no agent.json")
            continue

        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[REGISTRY] skipping {agent_dir.name}: unreadable agent.json ({exc})")
            continue

        # Fall back to the folder name when metadata is incomplete, so the
        # agent still shows up in the frontend.
        agents.append({
            "id": meta.get("id") or agent_dir.name,
            "name": meta.get("name") or agent_dir.name,
            "description": meta.get("description", ""),
            "mode": meta.get("mode", "chat"),
            "model": meta.get("model", "") or "",
        })

    return agents


def get_agent_meta(agent_id: str) -> dict | None:
    """Return the summary for one agent id, or None if not registered."""
    for summary in list_agents():
        if summary["id"] == agent_id:
            return summary
    return None
```

---

<!-- ==== 23/34 : engine/core/__init__.py ==== -->

### engine/core/__init__.py

```python
(empty file — 0 bytes)
```

---

<!-- ==== 24/34 : engine/core/agent.py ==== -->

### engine/core/agent.py

````python
"""
app/core/agent.py
=================

The reusable runtime agent.

    AgentProfile - the agent's identity and prompt sections (from config)
    Agent        - the generic think / act / observe loop

The Agent does not know what KIND of agent it is (research, coding, chat...).
Its behavior comes entirely from its AgentProfile and the tools it was given.
"""

import inspect
import json
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import Callable, List

from engine.core.llm import ask_llm
from tools.state import FileSession


# ==========================================================================
# AGENT PROFILE
# --------------------------------------------------------------------------
# The identity and behavior of an agent. Metadata fields come from
# agent.json; the section fields come from agent.md.
# ==========================================================================

@dataclass
class AgentProfile:
    """Identity + behavior of one agent.

    From agent.json:    id, name, description, mode
    From agent.md:      role, purpose, personality, boundaries,
                        communication, principles, decision_style,
                        plus any extra '## sections' (extras)
    Composed at build:  system_prompt
    """

    id: str = ""
    name: str = ""
    description: str = ""
    mode: str = "chat"

    system_prompt: str = ""

    # Prompt sections from agent.md
    role: str = ""
    purpose: str = ""
    personality: str = ""
    boundaries: str = ""
    communication: str = ""
    principles: str = ""
    decision_style: str = ""

    # Documentation only (NOT included in the system prompt)
    priorities: str = ""

    extras: dict = field(default_factory=dict)


# ==========================================================================
# THE GENERIC AGENT OBJECT
# --------------------------------------------------------------------------
# The Agent maintains conversation history and interacts with the LLM
# backend through structured messages. When tools are attached, the LLM
# can request tool calls, which flow through act() -> observe() and a
# follow-up LLM round.
# ==========================================================================

class Agent:
    """A generic AI agent that can think (ask the LLM), act (call a tool) and
    observe (record the tool's result back into the conversation)."""

    def __init__(self, model: str | None, tools: List[Callable], profile: AgentProfile, session: FileSession | None = None):
        """Store the model, tools, profile, and optional FileSession."""
        self.model = model
        self.profile = profile
        self.tools = {f.__name__: f for f in tools}
        self.messages: List[dict] = []
        self.session = session or FileSession()
        self.tool_events: List[dict] = []  # structured tool-execution log for this turn

    def _extract_text_tool_calls(self, content: str) -> List[dict]:
        """Find tool calls that a model wrote as plain-text JSON instead of using
        Ollama's native tool_calls field (a common quirk of small local models).

        Accepts bare JSON, ```json fenced blocks, a JSON object or ARRAY of
        objects embedded in prose, and objects wrapped under keys like
        "tool_calls" / "calls" / "functions". ONLY names present in self.tools
        are returned, and only when the call's required arguments are present
        (so prose that merely mention a tool is never executed).

        Tool-call objects may use "arguments", "args" OR "parameters" as the
        arguments key (small models differ).
        """
        text = (content or "").strip()
        if text.startswith("```"):  # unwrap markdown code fences
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()

        candidates: List[dict] = []
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            parsed = None

        if parsed is not None:
            # Top-level array of calls, object wrapped around a list of calls,
            # or a single call object.
            if isinstance(parsed, list):
                candidates.extend(parsed)
            elif isinstance(parsed, dict):
                found = False
                for wrap_key in ("tool_calls", "calls", "functions", "call"):
                    wrapped = parsed.get(wrap_key)
                    if isinstance(wrapped, list):
                        candidates.extend(wrapped)
                        found = True
                        break
                    if isinstance(wrapped, dict):
                        candidates.append(wrapped)
                        found = True
                        break
                if not found:
                    candidates.append(parsed)
        else:
            # one nesting level allowed so nested "arguments" objects are captured
            for match in re.finditer(r"\{(?:[^{}]|\{[^{}]*\})*\}", content or ""):
                try:
                    candidates.append(json.loads(match.group(0)))
                except json.JSONDecodeError:
                    continue

        calls: List[dict] = []
        for item in candidates:
            if not isinstance(item, dict) or item.get("name") not in self.tools:
                continue
            # Accept "arguments", "args", or "parameters" as the args key.
            args = item.get("arguments", item.get("args", item.get("parameters", {}))) or {}
            args = self._normalize_args(item["name"], args)
            if not self._has_required_args(item["name"], args):
                continue
            calls.append({"function": {"name": item["name"], "arguments": args}})
        return calls

    def _has_required_args(self, name: str, args: dict) -> bool:
        """True when every required (no-default) parameter of the tool is present
        in args. Prevents executing narration that merely mentions a tool."""
        fn = self.tools.get(name)
        if fn is None:
            return False
        try:
            sig = inspect.signature(fn)
        except (TypeError, ValueError):
            return True
        required = {
            p.name for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        }
        return required.issubset(args.keys())

    def _normalize_args(self, name: str, args) -> dict:
        """Coerce the many different argument shapes small local models send for
        tool calls into a clean dict of keyword args the tool actually accepts.

        Handles:
            - args as a JSON string: '{"path": "..."}'
            - single-key wrappers:   {"args": {...}}, {"arguments": {...}}
            - positional list:       ["E:\\..."], [name, content, path]
            - string booleans:       {"overwrite": "false"} -> False
            - anything non-dict:     gracefully -> {}
        """
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, TypeError):
                return {}

        if isinstance(args, dict) and len(args) == 1:
            if "args" in args:
                args = args["args"]
            elif "arguments" in args:
                args = args["arguments"]
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, TypeError):
                    return {}

        if isinstance(args, list):
            fn = self.tools.get(name)
            if fn is not None:
                try:
                    params = [
                        p for p in inspect.signature(fn).parameters.values()
                        if p.kind in (
                            inspect.Parameter.POSITIONAL_ONLY,
                            inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        )
                    ]
                    bound = {}
                    for param, value in zip(params, args):
                        if param.name not in bound:
                            bound[param.name] = value
                    return self._coerce_bools(bound, {p.name for p in params if p.annotation is bool})
                except (TypeError, ValueError):
                    pass
            return {}

        if not isinstance(args, dict):
            return {}

        # Drop any keys that aren't actual parameters of the tool, so stray
        # keys the model invents (e.g. "path" on a no-arg tool) never crash
        # the call. Tools exposing **kwargs keep everything.
        bool_params = set()
        fn = self.tools.get(name)
        if fn is not None:
            try:
                sig = inspect.signature(fn)
                if not any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in sig.parameters.values()
                ):
                    valid = {p.name for p in sig.parameters.values() if p.kind in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        inspect.Parameter.KEYWORD_ONLY,
                    )}
                    args = {k: v for k, v in args.items() if k in valid}
                bool_params = {
                    p.name for p in sig.parameters.values() if p.annotation is bool
                }
            except (TypeError, ValueError):
                pass

        return self._coerce_bools(args, bool_params)

    @staticmethod
    def _coerce_bools(args: dict, bool_params: set) -> dict:
        """Turn string 'true'/'false'/'1'/'0' into real bools, but ONLY for
        parameters that are actually typed as bool (so a string param like
        name="yes" is never mangled)."""
        coerced = dict(args)
        for key, value in list(coerced.items()):
            if (
                key in bool_params
                and isinstance(value, str)
                and value.strip().lower() in ("true", "false", "yes", "no", "1", "0")
            ):
                coerced[key] = value.strip().lower() in ("true", "yes", "1")
        return coerced

    MAX_TOOL_ROUNDS = 6
    REPEAT_LIMIT = 3
    _REPEAT_WARNING = (
        "System guard: you have already sent this exact tool call with the "
        "same arguments earlier in this conversation, and it already ran. "
        "Calling it again will not change its result. STOP issuing tool calls "
        "now and answer in plain text, using the tool results you already have."
    )
    _REPEAT_FEEDBACK = (
        "(The agent kept repeating the same tool call and stopped answering "
        "in text. Please rephrase your request or ask again.)"
    )

    @staticmethod
    def _round_signature(tool_calls) -> tuple:
        """Order-independent, hashable fingerprint of one tool round so two
        rounds with the same calls and same arguments compare as identical."""
        normalized = []
        for tool_call in tool_calls:
            fn = tool_call.get("function", {})
            name = str(fn.get("name", ""))
            args = fn.get("arguments", {})
            if isinstance(args, dict):
                items = tuple(sorted((str(k), repr(v)) for k, v in args.items()))
            else:
                items = (repr(args),)
            normalized.append((name, items))
        return tuple(sorted(normalized))

    def think(self, user_input: str) -> str:
        """Add user input to history, send the conversation to the LLM, and return its reply."""
        if not self.messages or self.messages[0].get("role") != "system":
            self.messages.insert(0, {"role": "system", "content": self.profile.system_prompt})

        self._inject_session_context()

        self.messages.append({"role": "user", "content": user_input})

        tool_callables = list(self.tools.values()) if self.tools else None

        message = ask_llm(messages=self.messages, model=self.model, tools=tool_callables)
        self.messages.append(message)

        # Native tool_calls, or calls the model wrote as plain-text JSON.
        # Both paths flow through act()/observe() and a follow-up LLM round.
        # Keep looping while the model keeps issuing tool calls, so a chain of
        # tool calls always ends in a real text reply (never a silent "").
        tool_calls = message.get("tool_calls") or self._extract_text_tool_calls(message.get("content", ""))
        last_signature = None
        repeat_count = 0
        for _ in range(self.MAX_TOOL_ROUNDS):
            if not tool_calls:
                break

            signature = self._round_signature(tool_calls)
            if signature == last_signature:
                repeat_count += 1
            else:
                repeat_count = 1
                last_signature = signature

            if repeat_count >= self.REPEAT_LIMIT:
                print(f"[Agent.think] identical tool round {signature} repeated x{repeat_count}; suppressing.")
                self.messages.append({"role": "user", "content": self._REPEAT_WARNING})
                message = ask_llm(messages=self.messages, model=self.model, tools=tool_callables)
                self.messages.append(message)
                content = (message.get("content", "") or "").strip()
                tool_calls = message.get("tool_calls") or self._extract_text_tool_calls(content)
                if content and not tool_calls:
                    print("[Agent.think] loop suppressed; model answered in text.")
                    return content
                print("[Agent.think] model ignored the loop warning; returning feedback reply.")
                return self._REPEAT_FEEDBACK

            origin = "native tool_calls" if message.get("tool_calls") else "TEXT reply"
            print(f"[Agent.think] Executing {len(tool_calls)} tool call(s) from {origin}.")
            for tool_call in tool_calls:
                result = self.act(tool_call, origin)
                self.observe(tool_call["function"]["name"], result)

            self._inject_session_context()

            message = ask_llm(messages=self.messages, model=self.model, tools=tool_callables)
            self.messages.append(message)
            tool_calls = message.get("tool_calls") or self._extract_text_tool_calls(message.get("content", ""))

        content = message.get("content", "") or ""
        if not content.strip():
            print(f"[Agent.think] No text reply after {self.MAX_TOOL_ROUNDS} tool round(s); returning fallback.")
            return "(I ran my tools but did not produce a final answer. Please ask again.)"
        return content

    _SESSION_CONTEXT_ROLE = "system"
    _SESSION_CONTEXT_PREFIX = "CURRENT FILE SESSION STATE"

    def _inject_session_context(self) -> None:
        """Add current FileSession state as context for the model, replacing any
        previously injected block so history doesn't grow duplicate state."""
        if not self.session:
            return
        state = self.session.get_state()
        if not any(state.values()):
            return
        context_entries = []
        for key, value in state.items():
            if value:
                context_entries.append(f"  {key}: {value}")
        context = f"{self._SESSION_CONTEXT_PREFIX} (from previous tool calls):\n" + "\n".join(context_entries)

        # Replace any earlier context block instead of appending another one.
        for i, message in enumerate(self.messages):
            if (
                message.get("role") == self._SESSION_CONTEXT_ROLE
                and str(message.get("content", "")).startswith(self._SESSION_CONTEXT_PREFIX)
            ):
                self.messages[i]["content"] = context
                return
        self.messages.append({"role": self._SESSION_CONTEXT_ROLE, "content": context})

    @staticmethod
    def _op_succeeded(result) -> tuple[bool, str]:
        """Classify a tool's result as (ok, error_msg).

        Tools report failed OPERATIONS as dicts with success=False or an
        "error" key even when the call itself executed (e.g. read_file on a
        path that does not exist). Execution-level 'success' and operation
        success are different things; the op_ok field records the difference
        so the live feed can flag hallucinated paths instead of showing
        [OK] everywhere.

        The result may arrive as a real dict or as a string representation
        (str(dict) uses single quotes, which is NOT valid JSON - so this
        inspects the object directly and only JSON-parses real JSON strings).
        """
        payload = result
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                return True, ""
        if isinstance(payload, dict):
            if payload.get("success") is False:
                return False, str(payload.get("error") or "operation failed")
            if payload.get("error"):
                return False, str(payload["error"])
        return True, ""

    def act(self, tool_call: dict, origin: str = "") -> str:
        """Run one tool that the LLM asked for, using the name and args it chose."""
        name = tool_call.get("function", {}).get("name")
        args = self._normalize_args(name, tool_call.get("function", {}).get("arguments", {}))
        timestamp = datetime.now().strftime("%H:%M:%S")
        if name in self.tools:
            try:
                raw_result = self.tools[name](**args)
                result = str(raw_result)
                print(f"[Agent.act] Executed {name} -> {result[:100]}...")
                op_ok, op_error = self._op_succeeded(raw_result)
                run_event = {
                    "time": timestamp,
                    "tool": name,
                    "args": args,
                    "result_preview": result[:200],
                    "status": "success",
                    "op_ok": op_ok,
                }
                if op_error:
                    run_event["op_error"] = op_error
                self.tool_events.append(run_event)
                self._log_tool_event({
                    **run_event,
                    "origin": origin,
                })
                return result
            except Exception as e:
                print(f"[Agent.act] Error executing {name}: {e}")
                self.tool_events.append({
                    "time": timestamp,
                    "tool": name,
                    "args": args,
                    "error": str(e),
                    "status": "error",
                })
                self._log_tool_event({
                    "time": timestamp,
                    "tool": name,
                    "args": args,
                    "error": str(e),
                    "status": "error",
                    "origin": origin,
                })
                return f"Error executing tool: {e}"
        print(f"[Agent.act] Missing tool requested: {name}")
        self.tool_events.append({
            "time": timestamp,
            "tool": name,
            "args": args,
            "status": "missing",
        })
        self._log_tool_event({
            "time": timestamp,
            "tool": name,
            "args": args,
            "status": "missing",
            "origin": origin,
        })
        return f"Error: {name} missing"

    def _log_tool_event(self, event: dict) -> None:
        """Report one structured tool event to the process-wide tool log
        (headless data/toollog/tool_usage.jsonl). Deliberately fail-safe so a
        logging problem can never break the tool call that just succeeded."""
        event.setdefault("agentId", self.profile.id or "")
        event.setdefault("agentName", self.profile.name or "")
        event.setdefault("model", self.model or "")
        event["time"] = datetime.now().isoformat(timespec="seconds")
        try:
            from tools.chatlog import append_tool_event

            append_tool_event(event)
        except Exception:
            pass

    def observe(self, name: str, result: str) -> None:
        """Record a tool's result back into the conversation history."""
        self.messages.append({"role": "tool", "content": result, "name": name})
````

---

<!-- ==== 25/34 : engine/core/llm.py ==== -->

### engine/core/llm.py

```python
"""
app/core/llm.py
===============

The LLM backend. Everything that talks to Ollama lives here:

    ask_llm               - send structured messages, get the reply message dict
    _resolve_model        - explicit arg > config/models.json > first Ollama model
    _get_context_window   - model context length lookup (capped)
    refresh_models        - scan installed Ollama models -> config/models.json

The Agent does not know about Ollama details; it only calls ask_llm().
"""

import json
import time
from pathlib import Path
from typing import Callable, List

import ollama

MAX_NUM_CTX = 32768
CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

# How long a successful Ollama model scan is trusted before we re-list.
_MODEL_SCAN_TTL = 60.0
_model_scan_cache = {"at": -1.0, "ids": []}  # ordered list of installed model ids


# ==========================================================================
# MODEL RESOLUTION AND CONTEXT SIZING
# ==========================================================================

def _config_model_ids() -> list:
    """The model ids in config/models.json (re-scanned by refresh_models() at
    every server startup, so it reflects THIS machine's Ollama)."""
    try:
        data = json.loads((CONFIG_DIR / "models.json").read_text(encoding="utf-8"))
        return [m.get("id") for m in data.get("models", []) if m.get("id")]
    except (OSError, json.JSONDecodeError):
        return []


def _installed_model_ids() -> list:
    """Ordered ids of installed Ollama models, cached briefly.

    A failed scan keeps the previous snapshot (or [] when there was none),
    so "no models visible" and "Ollama unreachable" stay distinguishable.
    """
    global _model_scan_cache
    now = time.monotonic()
    if _model_scan_cache["ids"] and now - _model_scan_cache["at"] < _MODEL_SCAN_TTL:
        return _model_scan_cache["ids"]
    try:
        ids = []
        for m in ollama.list().get("models", []):
            mid = m.get("model") if isinstance(m, dict) else getattr(m, "model", None)
            if mid and mid not in ids:
                ids.append(mid)
        _model_scan_cache = {"at": now, "ids": ids}
    except Exception:
        pass  # keep whatever we had before
    return _model_scan_cache["ids"]


# Per-model capabilities (ollama.show), cached per process. None = unknown
# (older Ollama that does not report capabilities yet).
_cap_cache: dict = {}


def _capabilities(model: str) -> list | None:
    """The reported capabilities for `model` (['completion', 'tools', ...])."""
    if model in _cap_cache:
        return _cap_cache[model]
    try:
        info = ollama.show(model=model).model_dump()
        caps = info.get("capabilities") or []
        _cap_cache[model] = caps
        return caps
    except Exception:
        _cap_cache[model] = None
        return None


def _supports_tools(model: str) -> bool | None:
    """True/False when Ollama reports capabilities, None when unknown."""
    caps = _capabilities(model)
    if caps is None:
        return None
    return "tools" in caps


def _resolve_model(model: str | None, require_tools: bool = False) -> str:
    """Pick which model to use: explicit arg (when suitable) > config > Ollama list.

    An explicitly requested model that is NOT installed on this machine is
    dropped so the app falls back to a detected one instead of erroring with
    a 404 - this keeps settings written on one OS (e.g. Windows) from
    breaking the app on another (e.g. Linux). When no models are visible at
    all, the explicit request is honoured as-is (previous behaviour).

    `require_tools`: when the caller needs tool calling, models that Ollama
    reports as NOT supporting tools are skipped so an agent with tools never
    gets a model that Ollama will reject with 400.
    """
    explicit = None
    if model:
        detected = set(_config_model_ids()) | set(_installed_model_ids())
        if model in detected:
            explicit = model
        elif detected:
            print(
                f"[ask_llm] requested model '{model}' is not installed locally - "
                "falling back to a detected model"
            )
        else:
            print(f"[ask_llm] no installed models visible - using requested '{model}' as-is")
            return model

    # Ordered candidates: explicit > config/models.json > live Ollama scan.
    candidates = []
    if explicit:
        candidates.append(explicit)
    for m in _config_model_ids():
        if m not in candidates:
            candidates.append(m)
    for m in _installed_model_ids():
        if m not in candidates:
            candidates.append(m)

    if require_tools:
        # Prefer models that definitely support tools; keep "unknown" ones as a
        # last resort (older Ollama), push confirmed-no-tools models to the end.
        tooled = [c for c in candidates if _supports_tools(c) is True]
        unknown = [c for c in candidates if _supports_tools(c) is None]
        others = [c for c in candidates if c not in tooled and c not in unknown]
        ordered = tooled + unknown + others
        if explicit and others and explicit in others:
            print(
                f"[ask_llm] requested model '{explicit}' does not support tools - "
                "falling back to one that does"
            )
    else:
        ordered = candidates

    if not ordered:
        raise RuntimeError(
            "No model available. Specify one in the frontend, "
            "add models to config/models.json, or install one in Ollama."
        )

    chosen = ordered[0]
    if chosen is explicit:
        print(f"[ask_llm] explicit model used: {model}")
    elif chosen in _config_model_ids():
        print(f"[ask_llm] model from config/models.json: {chosen}")
    else:
        print(f"[ask_llm] first installed Ollama model: {chosen}")
    return chosen


def _get_context_window(model: str) -> int | None:
    """Return the model's max context length from Ollama, capped; None if unknown."""
    try:
        info = ollama.show(model=model).model_dump()
        model_info = info.get("modelinfo") or info.get("model_info") or {}
        length = model_info.get("llama.context_length")
        if not length:
            return None
        return min(int(length), MAX_NUM_CTX)
    except Exception as exc:
        print(f"[ask_llm] context lookup failed for {model}: {exc}")
        return None


# ==========================================================================
# THE LLM CALL
# ==========================================================================

def ask_llm(messages: List[dict], model: str | None = None, tools: List[Callable] | None = None) -> dict:
    """Send structured messages to the resolved model via Ollama and return the full message dict."""
    resolved = _resolve_model(model, require_tools=bool(tools))

    # A model Ollama reports as NOT supporting tools must not be asked to
    # (Ollama rejects the request with 400) - drop the tool schemas and let
    # the agent answer without tool use rather than crash the chat.
    if tools and _supports_tools(resolved) is False:
        print(f"[ask_llm] model '{resolved}' does not support tools - continuing without tool use")
        tools = None

    num_ctx = _get_context_window(resolved)

    options = {"num_ctx": num_ctx} if num_ctx else {}
    print(f"[ask_llm] calling ollama.chat with model={resolved} num_ctx={num_ctx} tools={len(tools) if tools else 0}")

    for attempt in (1, 2):
        kwargs = {
            "model": resolved,
            "messages": messages,
            "options": options,
        }
        if tools:
            kwargs["tools"] = tools

        response = ollama.chat(**kwargs)
        message = response["message"]

        content = message.get("content", "") or ""
        tool_calls = message.get("tool_calls") or []

        print(f"[ask_llm] reply received ({len(content)} chars, {len(tool_calls)} tool calls)")

        if content.strip() or tool_calls:
            return message

        print(f"[ask_llm] empty reply on attempt {attempt} - retrying")

    return {"role": "assistant", "content": "(The model returned an empty reply. Please try again.)"}


# ==========================================================================
# MODEL SCAN (startup)
# --------------------------------------------------------------------------
# Lists locally installed Ollama models and writes config/models.json so
# the frontend dropdown has something to show. An empty scan (Ollama down)
# leaves the last known good file untouched.
# ==========================================================================

def scan_models() -> list:
    """Return the deduped list of locally installed Ollama models."""
    models = []
    try:
        for m in ollama.list().get("models", []):
            model_id = m.get("model") if isinstance(m, dict) else getattr(m, "model", None)
            size = m.get("size", 0) if isinstance(m, dict) else getattr(m, "size", 0)
            if model_id:
                models.append({"id": model_id, "name": model_id, "source": "ollama", "size": size})
    except Exception as exc:
        print(f"[llm] ollama scan failed: {exc}")

    seen, unique = set(), []
    for m in models:
        if m["id"] not in seen:
            seen.add(m["id"])
            unique.append(m)
    return unique


def refresh_models() -> list:
    """Scan Ollama and write config/models.json (returns the model list)."""
    models = scan_models()
    models_file = CONFIG_DIR / "models.json"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if models:
        models_file.write_text(
            json.dumps({"models": models}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"[llm] wrote {len(models)} models to {models_file}")
    else:
        print(f"[llm] scan found no models - keeping {models_file}")
    return models
```

---

<!-- ==== 26/34 : engine/core/prompt.py ==== -->

### engine/core/prompt.py

```python
"""
app/core/prompt.py
==================

PromptManager: converts an agent definition (agent.json + parsed agent.md
sections) plus the agent's resolved tools into an AgentProfile with a
composed system prompt.

    agent.md + agent.json + tools
        ↓
    PromptManager.build()
        ↓
    AgentProfile (system_prompt ready)
"""

from dataclasses import field
from typing import Callable, List

from engine.core.agent import AgentProfile

# Markdown '## sections' that map to named profile fields.
# Any other section passes through verbatim into the prompt as an
# UPPERCASE-titled block, so new sections need no code changes.
KNOWN_SECTIONS = (
    "role",
    "purpose",
    "personality",
    "boundaries",
    "communication",
    "principles",
    "decision_style",
    "priorities",
)

# Sections actually composed INTO the system prompt.
# 'priorities' is documentation-only and is deliberately excluded,
# matching the original PromptManager behavior.
PROMPT_SECTIONS = tuple(name for name in KNOWN_SECTIONS if name != "priorities")


class PromptManager:
    """Builds an AgentProfile from an agent definition and composes the system prompt."""

    @staticmethod
    def build(definition: dict, tools: List[Callable] | None = None) -> AgentProfile:
        """Build an AgentProfile.

        Args:
            definition: {"meta": {...agent.json...}, "sections": {...parsed agent.md...}}
            tools:      resolved tool functions; their docstrings become the
                        AVAILABLE TOOLS section of the prompt.

        Steps:
            1. Map metadata and markdown sections onto the profile fields
            2. Collect unknown sections as extras
            3. Compose the system prompt
        """
        meta = definition.get("meta", {})
        sections = {k.lower().strip(): v for k, v in definition.get("sections", {}).items()}

        known = {name: sections.get(name, "") for name in KNOWN_SECTIONS}
        extras = {
            name: content for name, content in sections.items()
            if name not in KNOWN_SECTIONS and name not in ("skills", "identity")
        }

        profile = AgentProfile(
            id=meta.get("id", ""),
            name=meta.get("name", ""),
            description=meta.get("description", ""),
            mode=meta.get("mode", "chat"),
            **known,
            extras=extras,
        )
        profile.system_prompt = PromptManager.compose_system_prompt(profile, tools)
        return profile

    @staticmethod
    def compose_system_prompt(profile: AgentProfile, tools: List[Callable] | None = None) -> str:
        """Build the final system prompt from profile sections."""
        parts = []

        if profile.role:
            parts.append(f"ROLE\n{profile.role}")

        if profile.purpose:
            parts.append(f"PURPOSE\n{profile.purpose}")

        if profile.personality:
            parts.append(f"PERSONALITY\n{profile.personality}")

        if profile.boundaries:
            parts.append(f"BOUNDARIES\n{profile.boundaries}")

        if profile.communication:
            parts.append(f"COMMUNICATION STYLE\n{profile.communication}")

        if profile.principles:
            parts.append(f"PRINCIPLES\n{profile.principles}")

        if profile.decision_style:
            parts.append(f"DECISION STYLE\n{profile.decision_style}")

        tool_lines = PromptManager._tool_lines(tools)
        if tool_lines:
            parts.append("AVAILABLE TOOLS\n" + "\n".join(tool_lines))

        # Generic extra sections (user, greeting, project_notes, ...) become
        # UPPERCASE-titled blocks, sorted for deterministic prompts.
        for title, content in sorted(profile.extras.items()):
            if content:
                parts.append(f"{title.upper()}\n{content}")

        return "\n\n".join(parts)

    @staticmethod
    def _tool_lines(tools: List[Callable] | None) -> List[str]:
        """Format tool callables as '- id: first docstring line' lines."""
        lines = []
        for fn in tools or []:
            doc = (fn.__doc__ or "").strip()
            summary = doc.splitlines()[0] if doc else ""
            lines.append(f"- {fn.__name__}: {summary}")
        return lines
```

---

<!-- ==== 27/34 : engine/pipeline.py ==== -->

### engine/pipeline.py

```python
"""
engine/pipeline.py
==================

Runs the ordered agent chain from config/pipeline.json so a single user idea
can travel Step 1 -> Step 2 -> Step 3 automatically.

Why this exists: chat.html sends one message to ONE agent. A Step-2 agent whose
prompt says "accepts the Feature Plan from Step 1" has nothing to work from when
the user sends it a fresh idea, so it stalls asking for that plan again and
again. The pipeline feeds each later step the OUTPUT of every earlier step as
part of its own message, so the planner's spec reaches the engineer and the
engineer's blueprint reaches the builder without any copy/paste.

Feed-forward messages carry:
    - the ORIGINAL user message (so the module name / scope never gets lost), and
    - each earlier step's final reply, labelled with the producing agent's name.

Every step's tool_events are collected and returned together, so the UI can
render the complete tool usage of a pipeline run in one shot.
"""

import json
from datetime import datetime
from pathlib import Path

from engine.agents.factory import build_agent, build_agent_from_definition

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "pipeline.json"

_STEP_FEED_TEMPLATE = (
    "Below is what the previous pipeline step ({name}) produced.\n"
    "Use it as your required input. Do NOT ask for it again - just act on it.\n"
    "--- {name} OUTPUT ---\n"
    "{output}\n"
    "--- END {name} OUTPUT ---\n"
)


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _records_file() -> Path:
    """pipeline_runs.jsonl inside the headless data directory."""
    return Path(__file__).resolve().parent.parent / "data" / "pipeline_runs.jsonl"


def _record_run(snapshot: dict) -> None:
    """Append one JSONL line per pipeline run. Fail-safe: a recording failure
    never breaks the run itself (same philosophy as the tool log)."""
    record = {
        "time": _iso_now(),
        "request": snapshot.get("request", ""),
        "model": snapshot.get("model"),
        "steps": snapshot.get("steps", []),
        "reply": snapshot.get("reply", ""),
    }
    try:
        target = _records_file()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass  # a recording failure never blocks the pipeline


def load_pipeline(config_path=None) -> list:
    """Ordered step configs from config/pipeline.json ([] when missing/broken).

    Missing files return [] so the app degrades gracefully to plain per-agent
    chat instead of crashing on a config problem.
    """
    path = config_path or CONFIG_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data.get("steps") or []


def _build_step(step, model: str | None, bridge=None):
    """Build the Agent for one pipeline step.

    A step is either an agent id (engine/agent_library/) or a dict with
    explicit `json_path` + `md_path` (headless ad-hoc agents).
    """
    if isinstance(step, dict) and step.get("json_path") and step.get("md_path"):
        return build_agent_from_definition(
            step["json_path"],
            step["md_path"],
            model=model,
            bridge=bridge,
        )
    return build_agent(str(step), model=model, bridge=bridge)


def _step_label(step) -> str:
    # A workspace agent's json_path is .../agents/<name>/agent.json, so the
    # agent FOLDER name (not the file stem "agent") is the readable label.
    if isinstance(step, dict):
        json_file = Path(step.get("json_path", ""))
        folder = json_file.parent.name
        return str(step.get("id") or folder or json_file.stem or "custom")
    return str(step)


def run_pipeline(user_message: str, model: str | None = None,
                 config_path=None, steps: list | None = None,
                 bridge=None) -> dict:
    """Run every step in order; return {reply, outputs, tool_events}.

    outputs is a list of {agent_id, agent_name, output, tools_used} - one entry
    per step, so callers can display each stage's contribution separately and
    the cascade's per-agent tool usage.

    Args:
        user_message: the original user idea to run through the chain.
        model:        optional model override for every step.
        config_path:  optional path to a pipeline.json (defaults to the
                      bundled config/pipeline.json).
        steps:        optional explicit step list (agent ids or
                      {json_path, md_path} dicts). Overrides the config file.
        bridge:       optional Project Manager bridge passed to every agent.
    """
    chain = steps if steps is not None else load_pipeline(config_path)
    if not chain:
        return {
            "reply": "(pipeline not configured - add config/pipeline.json or pass steps)",
            "outputs": [],
            "tool_events": [],
        }

    results: list[dict] = []
    tool_events: list[dict] = []

    for index, step in enumerate(chain):
        agent = _build_step(step, model=model, bridge=bridge)

        feed = user_message
        if results:
            chain_text = "\n\n".join(
                _STEP_FEED_TEMPLATE.format(name=r["agent_name"], output=r["output"])
                for r in results
            )
            feed = f"ORIGINAL USER REQUEST:\n{user_message}\n\n{chain_text}"

        reply = agent.think(feed)
        tools_used = sorted({
            e.get("tool")
            for e in agent.tool_events
            if isinstance(e, dict) and e.get("tool")
        })
        results.append({
            "agent_id": _step_label(step),
            "agent_name": agent.profile.name or _step_label(step),
            "output": reply,
            "tools_used": tools_used,
        })
        tool_events.extend(agent.tool_events)
        print(
            f"Agent {index + 1} ({_step_label(step)}) completed. "
            f"Tools used: {', '.join(tools_used) or 'none'}"
        )

    result = {
        "reply": results[-1]["output"],
        "outputs": results,
        "tool_events": tool_events,
    }
    print(
        f"PIPELINE COMPLETE ({len(chain)}/{len(chain)}) -> "
        f"{result['reply'][:80]!r}"
    )
    _record_run({
        "request": user_message,
        "model": model,
        "steps": [
            {
                "agent_id": r["agent_id"],
                "agent_name": r["agent_name"],
                "output": r["output"],
                "tools_used": r["tools_used"],
            }
            for r in results
        ],
        "reply": result["reply"],
    })
    return result
```

---

<!-- ==== 28/34 : interface_runner.py ==== -->

### interface_runner.py

```python
"""
interface_runner.py
===================

Headless agent runners for the GenV1 engine.

This is the programmatic entry point of the headless runtime:

    AgentInterface.run_chat(message, agent_id)
        - one registered agent from engine/agent_library/, chat reply.

    AgentInterface.run_single_agent(json_path, md_path, user_input)
        - one ad-hoc agent built from explicit agent.json + agent.md paths.

    AgentInterface.run_pipeline(agent_configs, user_input)
        - an ordered agent chain (feed-forward). Each step receives the
          original message plus every earlier step's reply, labelled; the
          final step's reply is the pipeline result.

Every run persists the user turn + agent reply to the plain-text chat log
(data/chatlog/chat.log), so history survives and the agent's own
search_chat_logs tool can recall it. Tool events are recorded to
data/toollog/tool_usage.jsonl.

An optional Project Manager bridge makes the Project Manager server (or its
direct filesystem authority) the filesystem owner for the file tools.
"""

from __future__ import annotations

import json
from typing import Any

from engine.agents.factory import build_agent, build_agent_from_definition
from engine.agents.registry import list_agents
from engine.pipeline import run_pipeline as _run_pipeline
from tools.chatlog import append_chat


class AgentInterface:
    """Thin, stable API over the build/think loop and pipeline chain."""

    def __init__(self, bridge: Any = None, model: str | None = None) -> None:
        """Create a runner.

        Args:
            bridge: optional Project Manager provider (ProjectManagerBridge
                or DirectProjectIO). When present, the file tools route through
                the Project Manager filesystem.
            model:  optional default model override for every run.
        """
        self.bridge = bridge
        self.model = model

    # ============================================================
    # CHAT (one registered agent)
    # ============================================================

    def run_chat(
        self,
        message: str,
        agent_id: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run one registered agent and return its reply.

        agent_id defaults to the first agent found in engine/agent_library/.
        Returns {"reply", "agent_id", "model", "tool_events"}.
        """
        resolved_id = agent_id or self._default_agent_id()
        agent = build_agent(resolved_id, model=model or self.model, bridge=self.bridge)
        reply = agent.think(message)
        append_chat("user", message)
        append_chat("agent", reply)
        return {
            "reply": reply,
            "agent_id": resolved_id,
            "model": agent.model,
            "tool_events": agent.tool_events,
        }

    # ============================================================
    # SINGLE AD-HOC AGENT
    # ============================================================

    def run_single_agent(
        self,
        json_path: str,
        md_path: str,
        user_input: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run one agent built from explicit agent.json + agent.md paths.

        This is the headless construction path: the definition can live
        anywhere, not only inside engine/agent_library/.

        Returns {"reply", "agent_id", "model", "tool_events", "name",
        "description"}.
        """
        agent = build_agent_from_definition(
            json_path,
            md_path,
            model=model or self.model,
            bridge=self.bridge,
        )
        reply = agent.think(user_input)
        append_chat("user", user_input)
        append_chat("agent", reply)
        return {
            "reply": reply,
            "agent_id": agent.profile.id,
            "name": agent.profile.name,
            "description": agent.profile.description,
            "model": agent.model,
            "tool_events": agent.tool_events,
        }

    # ============================================================
    # PIPELINE
    # ============================================================

    def run_pipeline(
        self,
        agent_configs: list | None,
        user_input: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run the ordered agent chain (feed-forward).

        agent_configs:
            None  -> load steps from config/pipeline.json.
            list  -> each element is either an agent id (str) or a dict with
                     "json_path" + "md_path" (ad-hoc step agents).

        Returns:
            {"reply", "outputs": [...step outputs...], "tool_events",
             "model"}.
        """
        result = _run_pipeline(
            user_input,
            model=model or self.model,
            steps=agent_configs,
            bridge=self.bridge,
        )
        reply = result["reply"]
        append_chat("user", user_input)
        append_chat("agent", reply)
        result["model"] = model or self.model
        return result

    # ============================================================
    # UTILITIES
    # ============================================================

    def _default_agent_id(self) -> str:
        agents = list_agents()
        if not agents:
            raise RuntimeError(
                "No agents are registered in engine/agent_library/. "
                "Check that <id>/agent.json and <id>/agent.md exist."
            )
        return agents[0]["id"]

    def available_agents(self) -> list[dict]:
        return list_agents()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        bridge = getattr(self.bridge, "expose", lambda: None)()
        return (
            f"<AgentInterface model={self.model!r} "
            f"bridge={json.dumps(bridge or {}, default=str) or 'local disk'}>"
        )


__all__ = ["AgentInterface"]
```

---

<!-- ==== 29/34 : run.py ==== -->

### run.py

```python
"""
run.py
======

Command-line entry point for the headless GenV1 engine.

Examples:
    python run.py list-agents
    python run.py refresh-models

    python run.py run-agent rag_assistant --message "what date is it today?"

    python run.py run-agent enginner --base-url http://127.0.0.1:8011 \
        --message "read config/agents.json"

    python run.py run-pipeline --message "idea: add a settings screen" \
        --steps rag_assistant execute_engineer_agent module_builder_agent

Options:
    --base-url    Project Manager URL (default: $PROJECT_MANAGER_BASE_URL or
                  http://127.0.0.1:8000).
    --no-bridge   do not connect to the Project Manager; file tools fall back
                  to the local disk.
    -m/--model    model override (default: per-agent agent.json model).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from interface_runner import AgentInterface
from engine.core.llm import refresh_models
from engine.agents.registry import list_agents


def _build_bridge(args) -> object | None:
    if args.no_bridge:
        print("[run] --no-bridge: file tools use the local disk.")
        return None
    try:
        from bridge.client import ProjectManagerBridge

        bridge = ProjectManagerBridge(base_url=args.base_url)
        health = bridge.health()
        root = (health or {}).get("root", "?")
        print(f"[run] connected to Project Manager at {args.base_url} (root={root})")
        return bridge
    except Exception as exc:
        print(
            f"[run] WARNING: could not connect to Project Manager at "
            f"{args.base_url} ({exc}). Continuing WITHOUT a bridge "
            "(local disk tools)."
        )
        return None


def _read_message(args) -> str:
    if args.message:
        return args.message
    try:
        return input("> ")
    except EOFError:
        return ""


def cmd_list_agents(args) -> int:
    agents = list_agents()
    if not agents:
        print("No agents found in engine/agent_library/.")
        return 1
    for agent in agents:
        tools = "chat" if agent["mode"] == "chat" else agent["model"] or "default model"
        print(
            f"- {agent['id']}  [{agent['name']}]  "
            f"({tools}) - {agent['description']}"
        )
    return 0


def cmd_refresh_models(args) -> int:
    models = refresh_models()
    print(
        f"Installed Ollama models ({len(models)}): "
        + ", ".join(m["id"] for m in models)
    )
    print("Wrote config/models.json")
    return 0


def _print_run(result: dict, args) -> None:
    print("\n" + "=" * 60)
    print("REPLY")
    print("=" * 60)
    print(result.get("reply", ""))
    tool_events = result.get("tool_events") or []
    if tool_events:
        print("\nTOOL EVENTS")
        for event in tool_events:
            print(
                f"- {event.get('time', '')} {event.get('tool')} "
                f"{json.dumps(event.get('args', {}) or {}, default=str)[:160]} "
                f"-> {event.get('status')}"
            )
    if args.json:
        print("\nJSON")
        print(json.dumps(result, indent=2, default=str))


def cmd_run_agent(args) -> int:
    bridge = _build_bridge(args)
    runner = AgentInterface(bridge=bridge, model=args.model)
    message = _read_message(args)
    if not message:
        print("No message provided. Use --message or pipe stdin.")
        return 2
    result = runner.run_chat(message, agent_id=args.agent_id, model=args.model)
    _print_run(result, args)
    return 0


def cmd_run_pipeline(args) -> int:
    bridge = _build_bridge(args)
    runner = AgentInterface(bridge=bridge, model=args.model)
    message = _read_message(args)
    if not message:
        print("No message provided. Use --message or pipe stdin.")
        return 2
    steps = args.steps or None
    result = runner.run_pipeline(steps, message, model=args.model)
    _print_run(result, args)
    if result.get("outputs"):
        print("\nPIPELINE STEPS")
        for step in result["outputs"]:
            print(f"- {step['agent_id']}: {step['output'][:100]!r}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Headless GenV1 agent engine runner.",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Project Manager base URL (default: PROJECT_MANAGER_BASE_URL env "
             "or http://127.0.0.1:8000).",
    )
    parser.add_argument(
        "--no-bridge",
        action="store_true",
        help="Do not connect to a Project Manager; file tools use local disk.",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Model override for all agents.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full JSON result as well.",
    )
    parser.add_argument(
        "--message",
        default=None,
        help="Message to send (read interactively when omitted).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-agents", help="List registered agents.")
    p_list.set_defaults(func=cmd_list_agents)

    p_refresh = sub.add_parser("refresh-models", help="Scan Ollama models.")
    p_refresh.set_defaults(func=cmd_refresh_models)

    p_run = sub.add_parser("run-agent", help="Run one registered agent.")
    p_run.add_argument("agent_id", nargs="?", default=None,
                       help="Agent id (default: first registered).")
    p_run.set_defaults(func=cmd_run_agent)

    p_pipe = sub.add_parser("run-pipeline", help="Run the agent chain.")
    p_pipe.add_argument("steps", nargs="*",
                        help="Step agent ids (default: config/pipeline.json).")
    p_pipe.set_defaults(func=cmd_run_pipeline)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

---

<!-- ==== 30/34 : tools/__init__.py ==== -->

### tools/__init__.py

```python
(empty file — 0 bytes)
```

---

<!-- ==== 31/34 : tools/chatlog.py ==== -->

### tools/chatlog.py

```python
"""
tools/chatlog.py
================

Headless data store.

The headless runtime keeps its own plain-text records so conversation and
tool history survive reloads and so the agent's ``search_chat_logs`` tool
has a single file to read. Two stores live here:

    data/chatlog/chat.log            - every user turn + agent reply (JSON lines)
    data/toollog/tool_usage.jsonl    - every tool execution event (JSON lines)

Nothing in this module requires a server. Writes are fail-safe: a broken
data path or disk error never breaks the agent call that produced the event.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CHATLOG_DIR = DATA_DIR / "chatlog"
CHATLOG_FILE = CHATLOG_DIR / "chat.log"

TOOLLOG_DIR = DATA_DIR / "toollog"
TOOLLOG_FILE = TOOLLOG_DIR / "tool_usage.jsonl"

MAX_MESSAGE_LENGTH = 2000
DEFAULT_HISTORY_LIMIT = 50
MAX_HISTORY_LIMIT = 500


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ==========================================================================
# CHAT LOG
# ==========================================================================

def append_chat(sender: str, message: str, agent: str | None = None) -> dict:
    """Append one timestamped chat entry. Returns the stored entry dict.

    ``agent`` tags the entry with the agent that produced it so a
    caller can keep separate per-agent threads in one log. Callers
    that do not pass it keep the original unscoped behaviour.
    """
    CHATLOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": _iso_ts(), "sender": sender, "message": message}
    if agent:
        entry["agent"] = agent
    with CHATLOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_history(limit: int = DEFAULT_HISTORY_LIMIT, agent: str | None = None) -> list[dict]:
    """Most recent chat entries in chronological order.

    With ``agent`` set, only that agent's entries are returned.
    Entries written before per-agent tagging have no agent key and
    therefore belong to no thread.
    """
    limit = max(1, min(limit, MAX_HISTORY_LIMIT))
    entries: list[dict] = []
    if not CHATLOG_FILE.exists():
        return entries
    with CHATLOG_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if agent and entry.get("agent") != agent:
                continue
            entries.append(entry)
    return entries[-limit:]


def clear_chat(agent: str | None = None) -> int:
    """Wipe the chat log entirely. Returns how many entries were removed.

    With ``agent`` set, only that agent's entries are removed and
    every other thread is preserved.
    """
    if not CHATLOG_FILE.exists():
        return 0
    if not agent:
        removed = 0
        with CHATLOG_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    removed += 1
        CHATLOG_FILE.write_text("", encoding="utf-8")
        return removed

    kept: list[str] = []
    removed = 0
    with CHATLOG_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("agent") == agent:
                removed += 1
                continue
            kept.append(line if line.endswith("\n") else line + "\n")
    CHATLOG_FILE.write_text("".join(kept), encoding="utf-8")
    return removed


def search_text(query: str, limit: int = 15) -> str:
    """Case-folded substring search over the chat log, newest first.

    Returns an empty string when nothing matches, otherwise a numbered
    transcript of the matching turns. This is the agent's long-term memory:
    it only ever reads the plain-text chat.log, so no vector DB is needed.
    """
    needle = (query or "").strip().lower()
    if not needle:
        return ""
    if not CHATLOG_FILE.exists():
        return ""
    matches: list[str] = []
    with CHATLOG_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if needle not in line.lower():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            sender = entry.get("sender", "?")
            message = entry.get("message", "")
            matches.append(f"[{sender}] {message}")
    if not matches:
        return ""
    matches = matches[-limit:]
    header = f"--- CHAT LOG SEARCH RESULTS FOR: '{query}' ---"
    return "\n".join([header, *reversed(matches)])


# ==========================================================================
# TOOL LOG
# ==========================================================================

def append_tool_event(event: dict) -> None:
    """Append one JSONL tool-event line. Fail-safe (never raise)."""
    try:
        TOOLLOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with TOOLLOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(event, ensure_ascii=False, default=str) + "\n"
            )
    except Exception:
        pass
```

---

<!-- ==== 32/34 : tools/project_tools.py ==== -->

### tools/project_tools.py

```python
"""
tools/project_tools.py
======================

Every executable tool in the headless runtime, consolidated into one module.

One function per tool; each function's docstring is what the LLM "sees":
PromptManager turns the first line into the system prompt's AVAILABLE TOOLS
section, and Ollama derives the JSON tool schema from the function name,
signature, types, and docstring. Keep them precise and self-describing.

Registered tools (IDs in agent.json):
    map_files, read_file, write_text_file, delete_files,
    get_current_date, tell_me_the_date_and_time, search_chat_logs

File tools run against one of three backends, selected once via configure():

    * a Project Manager bridge (HTTP)          - the Project Manager server
                                                  is the filesystem authority
    * a "direct" Project Manager provider      - in-process filesystem authority
                                                  (used when mounted inside PM)
    * the local disk (default, no provider)    - bare local filesystem

The provider is a small object with a stable surface:

    workspace_root (str)          .relpath(path) -> posix relative (or raises)
    .list_tree() -> nested tree   .read(rel) -> str     .write(rel, content)
    .create(rel, content)         .delete(rel)          .exists(rel) -> bool

The shared FileSession lives in tools/state.py.
"""

import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# DATA STORE (chat memory + tool log)
# ---------------------------------------------------------------------------

from tools.chatlog import search_text as _search_chatlog  # noqa: E402

# ---------------------------------------------------------------------------
# PROVIDER SELECTION
# ---------------------------------------------------------------------------

#: The active Project Manager provider (None = operate on the local disk).
_io: Any = None


def configure(provider: Any) -> None:
    """Point the file tools at a Project Manager provider (or None for local).

    The provider decides where files live AND how paths are translated. Both
    the HTTP bridge (bridge.client) and the in-process filesystem authority
    (bridge.providers.DirectProjectIO) implement the same surface.
    """
    global _io
    _io = provider


# ---------------------------------------------------------------------------
# READ - Docling-powered document reader (IBM Docling)
# ---------------------------------------------------------------------------

# Plain-text formats are read straight off disk (fast path). Everything else
# (PDF/DOCX/PPTX/XLSX/HTML/images/...) goes through IBM Docling's pipeline,
# which returns clean, structurally-formatted markdown.
_PLAIN_TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".log", ".text",
    ".csv", ".tsv",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx",
    ".css", ".scss", ".sass", ".xml", ".tex", ".rst",
}


def _is_plain_text(path) -> bool:
    """True for files whose raw text is already the well-formatted content."""
    return Path(str(path)).suffix.lower() in _PLAIN_TEXT_EXTENSIONS


def _unquote_path(value) -> str:
    """Strip one level of surrounding quotes a model may have left on a path.

    Small local models frequently emit tool args that still include the
    double/single quotes from the prompt (e.g. output_path='"E:\\data\\x"').
    Quote characters are invalid inside Windows path components, so passing
    them through makes read/map/write/delete fail with WinError 123 - even
    though the underlying path was perfectly real. Only matching quote pairs
    at the very edges are stripped, and only for string arguments that are
    really paths, so ordinary quoted prose is never mangled.
    """
    v = str(value).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1]
    return v


_DOCLING_CONVERTERS = {}


def _docling_converter(ocr: bool):
    """Return a cached, lazily-created Docling DocumentConverter.

    The converter is created once per ocr setting and reused across calls so
    the (expensive) pipeline + model artifacts are initialized only once.
    First-ever conversion downloads the layout/OCR models from HuggingFace.
    """
    if ocr not in _DOCLING_CONVERTERS:
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except ImportError:
            _DOCLING_CONVERTERS[ocr] = None
            return None

        if ocr:
            options = PdfPipelineOptions(do_ocr=True)
            converter = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
            )
        else:
            converter = DocumentConverter()

        _DOCLING_CONVERTERS[ocr] = converter
    return _DOCLING_CONVERTERS[ocr]


def _convert_with_docling(path: Path, ocr: bool) -> str | None:
    """Return Docling markdown for a binary document, or None when unavailable."""
    converter = _docling_converter(ocr)
    if converter is None:
        return None

    from docling.datamodel.base_models import ConversionStatus

    result = converter.convert(str(path), max_num_pages=400)
    if result.status is ConversionStatus.FAILURE:
        errors = "; ".join(e.error_message for e in getattr(result, "errors", []))
        raise ValueError(errors or "Docling could not convert the document.")
    return result.document.export_to_markdown()


def _read_local_file(p: Path, ocr: bool) -> dict:
    """Read a file from the local disk (text direct, binary via Docling)."""
    if _is_plain_text(p):
        return {
            "success": True,
            "tool": "read_file",
            "data": {
                "path": str(p),
                "filename": p.name,
                "file_type": p.suffix.lower(),
                "extracted_content": p.read_text(encoding="utf-8", errors="replace"),
                "status": "success",
            },
            "error": None,
        }
    markdown = _convert_with_docling(p, ocr)
    if markdown is None:
        return {
            "success": False,
            "tool": "read_file",
            "data": {},
            "error": "Docling is not installed. Install it with `pip install docling` "
                     "to read PDF/DOCX/PPTX/XLSX/HTML/image files.",
        }
    return {
        "success": True,
        "tool": "read_file",
        "data": {
            "path": str(p),
            "filename": p.name,
            "file_type": p.suffix.lower(),
            "extracted_content": markdown,
            "status": "success",
        },
        "error": None,
    }


def read_file(path: str, ocr: bool = True) -> dict:
    """Reads a file and returns its content as well-formatted text (markdown).

    Use this tool whenever you need the contents of a document, source file,
    or any file on disk. It returns the extracted content ready to use.

    Plain text and code files (.txt, .md, .log, .json, source code, ...) are
    read directly. All other formats - PDF, DOCX, PPTX, XLSX, HTML, images -
    are converted by IBM Docling into clean, structured markdown (OCR on by
    default for scanned PDFs). When a Project Manager is connected, project
    files are read through it (the Project Manager is the filesystem owner).

    Args:
        path (str): Absolute path to the file to read (relative to the
            Project Manager workspace when one is connected).
        ocr (bool): When True (default), optical character recognition is
            enabled for PDFs so scanned/rotated pages can be read.

    Returns:
        dict: {"success": bool, "tool": "read_file", "data": {...}, "error": str|None}
            data keys: path, filename, file_type, extracted_content, status
    """
    raw = _unquote_path(path)

    if _io is not None:
        # Project Manager is the filesystem authority. Plain text is read
        # through the provider; binary documents are converted locally when
        # the file is reachable on this machine, otherwise the provider's
        # own answer (or error) is returned.
        try:
            rel = _io.relpath(raw)
        except Exception as exc:
            return {"success": False, "tool": "read_file", "data": {}, "error": str(exc)}

        if _is_plain_text(rel):
            try:
                content = _io.read(rel)
                return {
                    "success": True,
                    "tool": "read_file",
                    "data": {
                        "path": str(Path(_io.workspace_root) / rel),
                        "path_relative": rel,
                        "filename": Path(rel).name,
                        "file_type": Path(rel).suffix.lower(),
                        "extracted_content": content,
                        "status": "success",
                    },
                    "error": None,
                }
            except Exception as exc:
                return {"success": False, "tool": "read_file", "data": {}, "error": str(exc)}

        # Binary document: best-effort local Docling conversion, then the
        # provider's read (which may serve extracted text or refuse).
        local = Path(_io.workspace_root) / rel
        if local.is_file():
            try:
                return _read_local_file(local, ocr)
            except Exception as exc:
                pass
        try:
            content = _io.read(rel)
            return {
                "success": True,
                "tool": "read_file",
                "data": {
                    "path": str(Path(_io.workspace_root) / rel),
                    "path_relative": rel,
                    "filename": Path(rel).name,
                    "file_type": Path(rel).suffix.lower(),
                    "extracted_content": content,
                    "status": "success",
                },
                "error": None,
            }
        except Exception as exc:
            return {"success": False, "tool": "read_file", "data": {}, "error": str(exc)}

    p = Path(raw)
    if not p.exists() or not p.is_file():
        return {
            "success": False,
            "tool": "read_file",
            "data": {},
            "error": f"File '{path}' not found."
        }

    try:
        return _read_local_file(p, ocr)
    except Exception as e:
        return {"success": False, "tool": "read_file", "data": {}, "error": str(e)}


# ---------------------------------------------------------------------------
# MAP - directory inspection
# ---------------------------------------------------------------------------

DEFAULT_IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".idea", ".vscode"}


def _flatten_tree(entries: list, prefix: str = "") -> list[dict]:
    """Flatten a nested provider tree into one flat list of {path, type, name, size}."""
    flat = []
    for entry in entries or []:
        name = entry.get("name", "")
        rel = entry.get("path", "")
        if not rel and name:
            rel = f"{prefix}/{name}" if prefix else name
        flat.append({
            "name": name or Path(rel).name,
            "path": rel,
            "type": entry.get("type", "file"),
        })
        for child in entry.get("children") or []:
            flat.extend(_flatten_tree([child], prefix=rel))
    return flat


def _map_entries_local(root: Path) -> list[dict]:
    """os.walk the local disk; returns flat {name, path, type, level} entries."""
    files_data = []
    for current_dir, dirs, files in os.walk(root, topdown=True):
        depth = len(Path(current_dir).relative_to(root).parts)
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS]
        for d in dirs:
            full = Path(current_dir) / d
            files_data.append({"name": d, "path": str(full), "type": "directory", "level": depth + 1})
        for f in files:
            full = Path(current_dir) / f
            files_data.append({"name": f, "path": str(full), "type": "file", "level": depth + 1})
    return files_data


def map_files(path: str, max_depth: int = 8, max_entries: int = 5000) -> dict:
    """Inspects a directory and returns a structured list of its files and folders.

    Use this tool to see what exists on disk before reading, writing, or
    deleting anything. Returns every file and subfolder under the given
    directory (to max_depth), excluding ordinary noise like .git, .venv, and
    __pycache__. Folders are listed with their subpaths so you know exactly
    where a file lives before you touch it.

    Args:
        path (str): Absolute path to the directory to inspect, or a path
            relative to the Project Manager workspace when one is connected.
        max_depth (int): Maximum subdirectory depth to descend into (default 8).
        max_entries (int): Maximum number of entries to return (default 5000).

    Returns:
        dict: {"success": bool, "tool": "map_files", "data": {...}, "error": str|None}
            data keys: files (list of {name, path, extension, type, parent, level}),
                        truncated (bool), max_entries (int)
    """
    # Small local models sometimes render ints as strings ("5000"); coerce so
    # the `>=` comparisons below never crash on a type mismatch.
    if isinstance(max_depth, str) and max_depth.strip().isdigit():
        max_depth = int(max_depth)
    if isinstance(max_entries, str) and max_entries.strip().isdigit():
        max_entries = int(max_entries)
    raw = _unquote_path(path)

    if _io is not None:
        try:
            base = _io.relpath(raw)
        except Exception as exc:
            return {"success": False, "tool": "map_files", "data": {}, "error": str(exc)}
        try:
            flat = _flatten_tree(_io.list_tree())
        except Exception as exc:
            return {"success": False, "tool": "map_files", "data": {}, "error": str(exc)}

        base = base.strip("/")
        base_parts = tuple(base.split("/")) if base else ()
        files_data = []
        for entry in flat:
            rel = entry.get("path", "").replace("\\", "/").strip("/")
            if not rel:
                continue
            rel_parts = tuple(rel.split("/"))
            if base_parts and rel_parts[:len(base_parts)] != base_parts:
                continue
            if base_parts and len(rel_parts) == len(base_parts):
                continue  # the requested directory itself, not an entry inside it
            level = len(rel_parts) - len(base_parts)
            if level > max_depth:
                continue
            if base_parts and any(p in DEFAULT_IGNORE_DIRS for p in rel_parts):
                continue
            files_data.append({
                "name": entry.get("name") or rel_parts[-1],
                "path": str(Path(_io.workspace_root) / rel),
                "path_relative": rel,
                "extension": Path(rel).suffix,
                "type": entry.get("type", "file"),
                "parent": rel_parts[-2] if len(rel_parts) >= 2 else "",
                "level": level,
            })
            if len(files_data) >= max_entries:
                break
        truncated = len(files_data) >= max_entries
        return {
            "success": True,
            "tool": "map_files",
            "data": {"files": files_data, "truncated": truncated, "max_entries": max_entries},
            "error": None,
        }

    root = Path(raw)
    if not root.exists() or not root.is_dir():
        return {
            "success": False,
            "tool": "map_files",
            "data": {},
            "error": f"Path '{path}' is not a valid directory."
        }

    files_data = []
    for current_dir, dirs, files in os.walk(root, topdown=True):
        depth = len(Path(current_dir).relative_to(root).parts)
        if depth >= max_depth:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS]

        for d in dirs:
            if len(files_data) >= max_entries:
                break
            full = Path(current_dir) / d
            files_data.append({
                "name": d,
                "path": str(full),
                "extension": "",
                "type": "directory",
                "parent": Path(current_dir).name if Path(current_dir) != root else "",
                "level": depth + 1,
            })

        for f in files:
            if len(files_data) >= max_entries:
                break
            full = Path(current_dir) / f
            files_data.append({
                "name": f,
                "path": str(full),
                "extension": Path(f).suffix,
                "type": "file",
                "parent": Path(current_dir).name if Path(current_dir) != root else "",
                "level": depth + 1,
            })

        if len(files_data) >= max_entries:
            break

    truncated = len(files_data) >= max_entries
    return {
        "success": True,
        "tool": "map_files",
        "data": {
            "files": files_data,
            "truncated": truncated,
            "max_entries": max_entries,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# WRITE - file creation
# ---------------------------------------------------------------------------

def write_text_file(name: str, content: str, output_path: str, overwrite: bool = False) -> dict:
    """Creates a text file containing the given content.

    Use this tool to save any text or code you have produced to disk. The
    parent directory is created automatically, so you do not need a separate
    "create folder" step. By default an existing file with the same name is
    NOT overwritten - pass overwrite=True when you intentionally want to.

    Args:
        name (str): File name to write, e.g. "summary.txt".
        content (str): Full text content to write into the file.
        output_path (str): Directory in which to create the file (inside the
            Project Manager workspace when one is connected).
        overwrite (bool): Whether to overwrite the file if it already exists
            (default False).

    Returns:
        dict: {"success": bool, "tool": "write_text_file", "data": {...}, "error": str|None}
            data keys: filename, path, type, size, status (built on success)
    """
    if not name or content is None or not output_path:
        return {
            "success": False,
            "tool": "write_text_file",
            "data": {},
            "error": "Missing required arguments. Need name (file name), content (text), and output_path (folder)."
        }

    if _io is not None:
        try:
            rel_dir = _io.relpath(_unquote_path(output_path)).strip("/")
        except Exception as exc:
            return {"success": False, "tool": "write_text_file", "data": {}, "error": str(exc)}
        rel_file = f"{rel_dir}/{_unquote_path(name)}" if rel_dir else f"{_unquote_path(name)}"
        try:
            if overwrite:
                _io.write(rel_file, content)
            else:
                _io.create(rel_file, content)
        except Exception as exc:
            return {"success": False, "tool": "write_text_file", "data": {}, "error": str(exc)}
        absolute = str(Path(_io.workspace_root) / rel_file)
        return {
            "success": True,
            "tool": "write_text_file",
            "data": {
                "filename": _unquote_path(name),
                "path": absolute,
                "path_relative": rel_file,
                "type": "text/plain",
                "size": 0,
                "status": "written",
            },
            "error": None,
        }

    try:
        out_dir = Path(_unquote_path(output_path))
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / _unquote_path(name)

        if file_path.exists() and not overwrite:
            return {
                "success": False,
                "tool": "write_text_file",
                "data": {},
                "error": f"File '{file_path}' already exists and overwrite is set to False."
            }

        file_path.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "tool": "write_text_file",
            "data": {
                "filename": name,
                "path": str(file_path),
                "type": "text/plain",
                "size": file_path.stat().st_size,
                "status": "written",
            },
            "error": None,
        }
    except Exception as e:
        return {"success": False, "tool": "write_text_file", "data": {}, "error": str(e)}


# ---------------------------------------------------------------------------
# DELETE - two-step approval-safe deletion
# ---------------------------------------------------------------------------

def delete_files(file_list: list, approved: bool = False) -> dict:
    """Deletes files ONLY after explicit approval has been given.

    Deleting is permanent. Calling this tool with approved=False (the safe
    default) only PREPARES the deletion. Call it a second time with
    approved=True to actually remove the files; the runtime additionally
    blocks any path that was never proposed in the first (approved=False) call.

    Args:
        file_list (list): List of file paths to delete.
        approved (bool): Must be True to actually delete. False only records
            the pending request (two-step confirmation).

    Returns:
        dict: {"success": bool, "tool": "delete_files", "data": {...}, "error": str|None}
            data keys: results (path -> "deleted"/"file_not_found"/"error: ..."),
                        or pending_files (list) when approval is still required
    """
    if not file_list:
        return {
            "success": False,
            "tool": "delete_files",
            "data": {},
            "error": "No files provided for deletion."
        }

    if not approved:
        return {
            "success": False,
            "tool": "delete_files",
            "data": {"pending_files": file_list},
            "error": "Deletion requires explicit approval. Set approved=True to finalize."
        }

    results = {}
    for f_path in file_list:
        try:
            if _io is not None:
                rel = _io.relpath(f_path)
                if _io.exists(rel):
                    _io.delete(rel)
                    results[f_path] = "deleted" if not _io.exists(rel) else "failed_to_verify"
                else:
                    results[f_path] = "file_not_found"
            else:
                p = Path(_unquote_path(f_path))
                if p.exists() and p.is_file():
                    p.unlink()
                    results[f_path] = "deleted" if not p.exists() else "failed_to_verify"
                else:
                    results[f_path] = "file_not_found"
        except Exception as e:
            results[f_path] = f"error: {str(e)}"

    all_success = all(v == "deleted" for v in results.values())
    return {
        "success": all_success,
        "tool": "delete_files",
        "data": {"results": results},
        "error": None if all_success else "One or more files failed to delete.",
    }


# ---------------------------------------------------------------------------
# DATE / TIME
# ---------------------------------------------------------------------------

def get_current_date() -> str:
    """Returns the real current calendar date (e.g. 'Monday, January 05, 2026').

    Use this tool when you need to know today's date - for example when a
    user asks "what day is it", when dating a response, or when reasoning
    about relative dates. No arguments.
    """
    from datetime import datetime
    return datetime.now().strftime("%A, %B %d, %Y")


def tell_me_the_date_and_time() -> str:
    """Returns the current date and time down to the second.

    Use this tool for anything needing the moment now (date + time), like
    timestamps, "what time is it", or checking elapsed time. No arguments.
    """
    from datetime import datetime
    now = datetime.now()
    return f"The current date and time is {now.strftime('%Y-%m-%d %H:%M:%S')}"


# ---------------------------------------------------------------------------
# SEARCH - chat transcript / memory recall
# ---------------------------------------------------------------------------

def search_chat_logs(query: str) -> str:
    """Searches past chat transcripts for a keyword and returns the matching segments.

    Use this tool to recall what was discussed in earlier conversations: this
    is the agent's long-term memory. It searches the saved plain-text chat log
    (data/chatlog/chat.log) and returns the matching turns with their speaker.

    Args:
        query (str): The search keyword, term, or phrase to look up.

    Returns:
        str: Formatted search results ('' when nothing matches).
    """
    try:
        result = _search_chatlog(query)
        if not result:
            return f"No matches found in the chat log for the query: '{query}'."
        return result
    except Exception as e:
        return f"Error executing chat log search: {e}"


# Keep the module importable in environments without fancy deps (mirrors the
# original module header which inserted the app root into sys.path).
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
```

---

<!-- ==== 33/34 : tools/registry.py ==== -->

### tools/registry.py

```python
"""
tools/registry.py
=================

Central tool registry. Maps tool IDs (strings used in agent.json) to Python
callables. Agents declare which tools they need by ID; the factory resolves
those IDs here into actual functions.

All tool implementations live in tools/project_tools.py; their docstrings are
the schema the LLM sees. This module only wires them to their public IDs.

configure(provider) points the file tools at a Project Manager provider so a
bridge-bound headless runtime routes every tool call through the Project
Manager filesystem instead of the local disk.

Adding a new tool:
    1. Write the function in tools/project_tools.py (with a clear docstring)
    2. Import it below and add it to _TOOL_REGISTRY with its string ID
"""

from typing import Callable

from tools.project_tools import (
    configure as _configure_provider,
    map_files,
    read_file,
    write_text_file,
    delete_files,
    get_current_date,
    tell_me_the_date_and_time,
    search_chat_logs,
)
from tools.state import FileSession

# ---------------------------------------------------------------------------
# Canonical registry  –  tool_id -> callable
# ---------------------------------------------------------------------------
_TOOL_REGISTRY: dict[str, Callable] = {
    # File management
    "map_files": map_files,
    "read_file": read_file,
    "write_text_file": write_text_file,
    "delete_files": delete_files,

    # Date/time
    "get_current_date": get_current_date,
    "tell_me_the_date_and_time": tell_me_the_date_and_time,

    # RAG / search
    "search_chat_logs": search_chat_logs,
}

# Shared session instance (created once, shared across agents in a process)
_session = FileSession()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure(provider=None) -> None:
    """Point the file tools at a Project Manager provider (or None for local).

    Called by the factory when an agent is built with a bridge so the tools'
    file operations go through the correct filesystem authority.
    """
    _configure_provider(provider)


def get(tool_name: str) -> Callable | None:
    """Retrieve an executable tool by its registered name."""
    return _TOOL_REGISTRY.get(tool_name)


def list_tools() -> list[str]:
    """Returns a list of all registered tool names."""
    return list(_TOOL_REGISTRY.keys())


def available_tool_ids() -> list[str]:
    """Backward-compatible alias for list_tools()."""
    return list_tools()


def resolve_tools(tool_ids: list[str]) -> list[Callable]:
    """Map a list of tool ID strings to their callable functions.

    Unknown IDs are silently skipped (with a warning) so that agent
    definitions can reference tools that may not be installed.
    """
    resolved = []
    for tid in tool_ids:
        fn = _TOOL_REGISTRY.get(tid)
        if fn is not None:
            resolved.append(fn)
        else:
            print(f"[registry] WARNING: tool '{tid}' not found – skipped.")
    return resolved


def get_session() -> FileSession:
    """Return the shared FileSession instance."""
    return _session
```

---

<!-- ==== 34/34 : tools/state.py ==== -->

### tools/state.py

```python
"""
app/tools/state.py
==================

Shared working state for the file-management tools.

The FileSession is the single in-memory record of everything a file-aware
agent has discovered, read, written, or proposed for deletion during the
current process. It lets later tool calls (and the model itself) build on
previous results instead of re-scanning the filesystem each turn.

The session is process-wide: one instance is created lazily and shared by
every agent that is built in this process.

It is injected into the conversation by Agent._inject_session_context and
hydrated from tool results by the _record_result wrapper in app/agents/factory.py.
"""


class FileSession:
    """Manages file-management working state for AI agents dynamically.

    Tracks, across tool calls in one process:

        discovered_files   - paths surfaced by map_files / other listing tools
        selected_files     - paths the agent has explicitly chosen to work on
        read_files         - paths whose contents have already been read
        working_content    - path -> last extracted text content (read_file)
        output_files       - paths the agent has written (write_text_file)
        pending_deletion   - paths proposed for deletion but not yet approved
    """

    def __init__(self):
        self.discovered_files = []
        self.selected_files = []
        self.read_files = []
        self.working_content = {}
        self.output_files = []
        self.pending_deletion = []

    def add_discovered(self, paths: list):
        """Record files/directories surfaced by map_files (deduplicated)."""
        self.discovered_files = list(set(self.discovered_files + paths))

    def select_files(self, paths: list):
        """Mark paths as the agent's active working set (deduplicated)."""
        self.selected_files = list(set(self.selected_files + paths))

    def record_read(self, path: str, content: str):
        """Remember that a path was read and cache its extracted content."""
        if path not in self.read_files:
            self.read_files.append(path)
        self.working_content[path] = content

    def add_output(self, path: str):
        """Remember a path produced by the write tool (deduplicated)."""
        if path not in self.output_files:
            self.output_files.append(path)

    def mark_for_deletion(self, paths: list):
        """Propose paths for deletion (deduplicated; approval happens later)."""
        self.pending_deletion = list(set(self.pending_deletion + paths))

    def get_state(self) -> dict:
        """Snapshot the current session state for injection into the prompt."""
        return {
            "discovered_files": self.discovered_files,
            "selected_files": self.selected_files,
            "read_files": self.read_files,
            "output_files": self.output_files,
            "pending_deletion": self.pending_deletion
        }
```

---

> Generated by `scripts/gen_master_copy.py` on 2026-09-25. Do not edit by hand; regenerate with:
>
> ```bat
> .venv/Scripts/python -m scripts.gen_master_copy
> ```
