# Project Manager — MASTER COPY

Single-file snapshot of the complete `project_manager/` source tree: the FastAPI workspace server, its editor interface, and the in-process agent engine it hosts.

| Field | Value |
| ----- | ----- |
| Scope | `project_manager/` |
| Files embedded | 44 |
| Generated | 2026-09-25 |
| Generator | `scripts/gen_master_copy.py` |
| Regenerate | `.venv/Scripts/python -m scripts.gen_master_copy` |
| Sister document | [`headless_app_MASTER_COPY.md`](headless_app_MASTER_COPY.md) — headless_app/ |

## AI Agent Engine — Entry Point

`/api/chat` is the **AI agent engine entry point**, and it now runs a real
agent rather than appending to a log. Every surface — the home page, the
editor, the chat page — reaches the engine through the same stable HTTP
contract, so the engine can be swapped without touching the UI.

| Route       | Method | Purpose                                                          |
| ----------- | ------ | ---------------------------------------------------------------- |
| `/api/chat` | POST   | Send a message. Body: `{"message": str, "agent_id": str?, "model": str?}`. Returns `{status, reply, agent_id, model, tool_events}`. |
| `/api/chat` | GET    | Fetch recent agent conversation history (`?limit=`, default 50, max 500). |
| `/api/chat` | DELETE | Clear the thread and truncate the log.                           |

The engine lives in `interface/routers/chat.py` and persists history to
`headless_app/data/chatlog/chat.log`, mirrored into
`workspace/data/chat.log` so the managed workspace keeps its own copy.

Everything runs **in one process**. Each router calls
`_ensure_headless_on_path()`, which puts `headless_app/` on `sys.path` and
then imports `engine.agents.factory.build_agent` and `tools.chatlog`
directly — no agent server, no second port, no HTTP hop between the UI and
the model.

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

| Route                   | Method | Purpose                                                                |
| ----------------------- | ------ | ---------------------------------------------------------------------- |
| `/api/agents`           | GET    | Every selectable agent: library (`headless_app/engine/agent_library/`) plus workspace (`workspace/agents/<name>/agent.json`). |
| `/api/agents/{agent_id}`| GET    | One agent's `{source, meta, sections}` — workspace first, library fallback. |
| `/api/agents/run`       | POST   | Run one agent. Body: `{json_path, md_path \| agent_id, message, model?}`. |
| `/api/pipeline`         | GET    | Default step chain from `config/pipeline.json` plus every selectable step candidate. |
| `/api/pipeline`         | POST   | Run a cascade. Body: `{steps: [...], message, model?}`.                 |
| `/api/models`           | GET    | Models listed in `config/models.json`, for the frontend picker.          |

All file tool calls run through `DirectProjectIO` (`headless_app/bridge/providers.py`),
so `parameters/filesystem.py` remains the single filesystem authority even when
an agent is writing files. Each pipeline step prints
`Agent N (<id>) completed. Tools used: ...`, and the run is appended to
`headless_app/data/pipeline_runs.jsonl`.

---

## Editor Interface — Accessing the Agent Tools

The editor's browser interface reaches the agent engine and the code tools
through `interface/static/js/api.js` and `interface/static/js/session.js`.
Every agent tool the interface can touch is exposed as a small API method:

| Front-end accessor                 | Backend route                        | Purpose                                 |
| ---------------------------------- | ------------------------------------ | --------------------------------------- |
| `API.chatSend(msg, agent, model)`  | `POST /api/chat`                     | Send a message to the selected agent    |
| `API.chatHistory(limit)`           | `GET /api/chat?limit=`               | Read agent conversation history         |
| `API.chatClear()`                  | `DELETE /api/chat`                   | Wipe the thread                         |
| `API.agents()`                     | `GET /api/agents`                    | Fill the agent selector                 |
| `API.agentDefinition(id)`          | `GET /api/agents/{agent_id}`         | Open an agent's `agent.json` / `agent.md` |
| `API.agentRun(body)`               | `POST /api/agents/run`               | Run one agent against the open file     |
| `API.pipelineOptions()`            | `GET /api/pipeline`                  | Default steps + step candidates         |
| `API.pipelineRun(body)`            | `POST /api/pipeline`                 | Run the ordered cascade                 |
| `API.models()`                     | `GET /api/models`                    | Fill the model selector                 |
| `API.fileRead(path, scope)`        | `GET /api/file/read?path=&scope=`    | Open a file in the editor               |
| `API.fileWrite(path, content, sc)` | `PUT /api/file/write`                | Save the current buffer                 |
| `API.project(scope)`               | `GET /api/project?scope=`            | Reload the file tree                    |
| `API.pathRename(old, new, scope)`  | `PUT /api/path/rename`               | Rename a file / folder                  |
| `API.fileDelete(path, scope)`      | `DELETE /api/file/delete?path=`      | Delete a file                           |
| `API.directoryDelete(path, scope)` | `DELETE /api/directory/delete?path=` | Delete a folder                         |

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

---

## Three pillars

```text
parameters/     Project parameters — filesystem.py is the filesystem owner
interface/      Editor interface — core (controller), routers (HTTP), clients, static
workspace/      The managed project content (project.json, agents/, documentation/, …)
scripts/        run.bat / run.sh / setup.sh, using the shared ..\.venv
server.py       Slim FastAPI host: assembles the pillars, mounts the routers
```

`interface/core/defaults.py` builds the single shared controller, event bus
and session pool that every router, the browser and the Python client all use.
`interface/core/operations.py` is the only place operations are defined, and
every filesystem call it makes is delegated to `parameters/filesystem.py` — the
server itself contains no filesystem logic.


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
│       ├── ai_agent_creator.html
│       ├── chat.html
│       ├── editor.html
│       ├── home.html
│       └── index.html
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
│   ├── data/   # not embedded: runtime logs written by the server
│   ├── documentation/
│   ├── project_scope/
│   ├── source_files/
│   ├── to_do/
│   ├── updates/
│   ├── project.json
│   └── ws_evt_probe.txt   # not embedded: stray WebSocket debug probe
├── .gitattributes
├── .gitignore
├── README.md
├── requirements.txt
└── server.py
```

## Snapshot Scope

This document embeds every source file under `project_manager/`, **44 files** in total, in case-insensitive path order.

The following are listed in the tree above but deliberately **not** embedded:

| Path | Reason |
| ---- | ------ |
| `interface/static/chatbackuporiginal.html` | pre-rewrite backup copy of the chat page |
| `workspace/data` | runtime logs written by the server |
| `workspace/ws_evt_probe.txt` | stray WebSocket debug probe |

Also excluded everywhere: `__pycache__/`, virtualenvs, editor and tool caches (`__pycache__`, `.venv`, `venv`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.idea`, `.vscode`), compiled artifacts (`*.pyc`, `*.pyo`, `*.log`).

A master copy is **never** embedded in a master copy, so this document cannot nest inside itself.

Regenerate both documents with:

```bat
.venv/Scripts/python -m scripts.gen_master_copy
```

Or just this one:

```bat
.venv/Scripts/python -m scripts.gen_master_copy --only project_manager
```

<!-- ==== 1/44 : .gitattributes ==== -->

### .gitattributes

```text
# Text files use LF line endings everywhere.
* text=auto eol=lf

# Explicit text / code files
*.py text eol=lf
*.sh text eol=lf
*.bat text eol=lf
*.html text eol=lf
*.css text eol=lf
*.js text eol=lf
*.json text eol=lf
*.md text eol=lf
*.txt text eol=lf
```

---

<!-- ==== 2/44 : .gitignore ==== -->

### .gitignore

```text
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.eggs/
build/
dist/

# Virtual environments
.venv/
venv/
env/

# Test / tooling caches
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Editor / IDE
.idea/
.vscode/

# Logs
*.log
```

---

<!-- ==== 3/44 : interface/clients/__init__.py ==== -->

### interface/clients/__init__.py

```python
"""Project Manager Python interface client package.

Talk to the Project Manager over HTTP from any Python program or
AI agent::

    from interface.clients import EditorClient

    client = EditorClient()
    client.health()

The async agent client::

    from interface.clients import AsyncEditorClient
"""

from .editor_client import EditorClient, AsyncEditorClient

__all__ = [
    "EditorClient",
    "AsyncEditorClient",
]
```

---

<!-- ==== 4/44 : interface/clients/editor_client.py ==== -->

### interface/clients/editor_client.py

```python
"""
Project Manager — Python interface client.
============================================

Talk to the Project Manager over HTTP from any Python program or
AI agent.

The client is the *interface*. It never touches the filesystem; it
always goes through the running Project Manager server.

Sync client:
    >>> from interface.clients import EditorClient
    >>> client = EditorClient()
    >>> client.health()

Async client (for agents / async code):
    >>> from interface.clients import AsyncEditorClient
    >>> client = AsyncEditorClient()
    >>> await client.health()

WebSocket subscriptions (real-time events):
    >>> async for event in client.subscribe():
    ...     print(event)

File operations accept a ``scope`` argument:
    * ``"workspace"`` (default) — the managed workspace
    * ``"app"``               — the application repository (dev files)
"""

from __future__ import annotations

import asyncio
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


# ============================================================
# SYNC CLIENT
# ============================================================

class EditorClient:
    """
    Synchronous HTTP client for the Project Manager interface.

    All calls hit the running Project Manager server. Nothing is
    done directly against the filesystem.
    """

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

        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
        )

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
        return self._get("/api/project")

    def tree(self) -> dict[str, Any]:
        return self.project()

    def sessions(self) -> dict[str, Any]:
        return self._get("/api/sessions")

    # ========================================================
    # FILE OPERATIONS
    # ========================================================

    def read(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._get(
            "/api/file/read",
            path=_apply_project_root(path),
            scope=scope,
        )

    def open(
        self,
        path: str,
        scope: str = "workspace",
    ):
        """
        Open a project file and return its contents.

        Alias for read().
        """

        return self.read(path, scope=scope)

    def write(
        self,
        path: str,
        content: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._put(
            "/api/file/write",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope,
            },
        )

    def save(
        self,
        path: str,
        content: str,
        scope: str = "workspace",
    ):
        """
        Save file content. Alias for write().
        """

        return self.write(path, content, scope=scope)

    def create_file(
        self,
        path: str,
        content: str = "",
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._post(
            "/api/file/create",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope,
            },
        )

    def delete_file(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._delete(
            "/api/file/delete",
            path=_apply_project_root(path),
            scope=scope,
        )

    # ========================================================
    # DIRECTORY OPERATIONS
    # ========================================================

    def create_directory(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._post(
            "/api/directory/create",
            params={
                "path": _apply_project_root(path),
                "scope": scope,
            },
        )

    def delete_directory(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._delete(
            "/api/directory/delete",
            path=_apply_project_root(path),
            scope=scope,
        )

    # ========================================================
    # RENAME / MOVE OPERATIONS
    # ========================================================

    def rename(
        self,
        old_path: str,
        new_path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._put(
            "/api/path/rename",
            payload={
                "old_path": _apply_project_root(old_path),
                "new_path": _apply_project_root(new_path),
                "scope": scope,
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
        Open a WebSocket and yield events as they arrive.

        Returns:
            Synchronous iterator over Project Manager event dicts.
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

    def close(self) -> None:
        self._http.close()

    # context-manager support
    def __enter__(self) -> "EditorClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _decode_message(message: Any) -> dict[str, Any]:
    """
    Turn a raw WebSocket message into an event dict.

    Handles bytes and str payloads.
    """

    if isinstance(message, bytes):

        import json

        return json.loads(
            message.decode(
                "utf-8"
            )
        )

    import json

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
# ASYNC CLIENT
# ============================================================

class AsyncEditorClient:
    """
    Asynchronous HTTP + WebSocket client for AI agents.

    Provides the same operations as EditorClient but with
    async/await, plus ``subscribe()`` for real-time events.
    """

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

        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
        )

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
        return await self._get("/api/project")

    async def tree(self) -> dict[str, Any]:
        return await self.project()

    async def sessions(self) -> dict[str, Any]:
        return await self._get("/api/sessions")

    async def read(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._get(
            "/api/file/read",
            path=_apply_project_root(path),
            scope=scope,
        )

    async def open(
        self,
        path: str,
        scope: str = "workspace",
    ):
        return await self.read(path, scope=scope)

    async def write(
        self,
        path: str,
        content: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._put(
            "/api/file/write",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope,
            },
        )

    async def save(
        self,
        path: str,
        content: str,
        scope: str = "workspace",
    ):
        return await self.write(path, content, scope=scope)

    async def create_file(
        self,
        path: str,
        content: str = "",
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._post(
            "/api/file/create",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope,
            },
        )

    async def delete_file(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._delete(
            "/api/file/delete",
            path=_apply_project_root(path),
            scope=scope,
        )

    async def create_directory(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._post(
            "/api/directory/create",
            params={
                "path": _apply_project_root(path),
                "scope": scope,
            },
        )

    async def delete_directory(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._delete(
            "/api/directory/delete",
            path=_apply_project_root(path),
            scope=scope,
        )

    async def rename(
        self,
        old_path: str,
        new_path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._put(
            "/api/path/rename",
            payload={
                "old_path": _apply_project_root(old_path),
                "new_path": _apply_project_root(new_path),
                "scope": scope,
            },
        )

    # ========================================================
    # REAL-TIME SUBSCRIPTION
    # ========================================================

    async def subscribe(
        self,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Open a WebSocket and yield Project Manager events.

        Example:
            >>> async for event in client.subscribe():
            ...     if event["type"] == "saved":
            ...         print("Saved", event["path"])
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
```

---

<!-- ==== 5/44 : interface/core/__init__.py ==== -->

### interface/core/__init__.py

```python
"""Project Manager operation/interface layer.

This package sits between the HTTP API and the filesystem.
It is not a replacement for the Project Manager; it provides a
clean set of operations that multiple interfaces (browser, AI
agents, scripts) can use.

Every filesystem mutation eventually goes through
parameters.filesystem.
"""

from .session import EditorManager, EditorSession
from .events import EventBus
from .operations import EditorInterface

__all__ = [
    "EditorManager",
    "EditorSession",
    "EventBus",
    "EditorInterface",
]
```

---

<!-- ==== 6/44 : interface/core/defaults.py ==== -->

### interface/core/defaults.py

```python
"""
Project Manager shared defaults.
=================================

Builds the single, shared Project Manager interface state so every
router, the browser, the WebSocket endpoint and the Python client
all talk to the same in-memory event bus, session pool and
controller.

    routers/project.py  ──┐
    routers/files.py    ──┤        editor.defaults
    routers/dirs.py     ──┼────►   get_interface()
    routers/ws.py       ──┤              │
                          │              ▼
    browser (JS)      ────┘        EditorInterface
                                          │
                                    Project_files
                                          │
                                        Filesystem

All other interfaces build on this shared state; nothing here
bypasses Project_files.
"""

from __future__ import annotations

from typing import Any

from parameters import filesystem

from .events import EventBus
from .session import EditorManager
from .operations import EditorInterface


# ============================================================
# SHARED STATE
# ============================================================

_events: EventBus | None = None

_sessions: EditorManager | None = None

_interface: EditorInterface | None = None


def get_events() -> EventBus:
    """
    The shared project event bus.
    """

    global _events

    if _events is None:

        _events = EventBus()

    return _events


def get_sessions() -> EditorManager:
    """
    The shared editor session pool.
    """

    global _sessions

    if _sessions is None:

        _sessions = EditorManager()

    return _sessions


def get_interface() -> EditorInterface:
    """
    The shared Project Manager controller.

    Called by routers and by the web dashboard.
    """

    global _interface

    if _interface is None:

        _interface = EditorInterface(
            filesystem=filesystem,
            events=get_events(),
            sessions=get_sessions(),
        )

    return _interface


def reset_for_tests() -> None:
    """
    Clear all shared state (used by the verification suite).
    """

    global _events
    global _sessions
    global _interface

    _events = None

    _sessions = None

    _interface = None
```

---

<!-- ==== 7/44 : interface/core/events.py ==== -->

### interface/core/events.py

```python
"""
Project Manager event system.
=============================

A small publish/subscribe event bus. Changes inside the Project
Manager publish events so that the browser and future agents can
receive information without monitoring the filesystem directly.

Example event:
    {
        "type": "saved",
        "path": "app.py"
    }
"""

from __future__ import annotations

import uuid
from typing import Any, Callable


# ============================================================
# EVENT TYPES
# ============================================================

EVENT_TYPES = {
    "saved",
    "created",
    "renamed",
    "deleted",
    "tree_changed",
}


# ============================================================
# EVENT BUS
# ============================================================

class EventBus:
    """
    Simple in-memory publish/subscribe event bus.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, Callable[[dict[str, Any]], None]] = {}

    def subscribe(
        self,
        callback: Callable[[dict[str, Any]], None],
    ) -> str:
        """
        Subscribe a callback to every project event.

        Args:
            callback:
                Function called with each published event dict.

        Returns:
            Subscription id (use with unsubscribe()).
        """

        subscription_id = uuid.uuid4().hex

        self._subscribers[subscription_id] = callback

        return subscription_id

    def unsubscribe(self, subscription_id: str) -> None:
        """
        Remove a subscription.
        """

        self._subscribers.pop(subscription_id, None)

    def publish(
        self,
        event_type: str,
        path: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event_type:
                One of EVENT_TYPES.
            path:
                Optional project-relative path the event refers to.
            kwargs:
                Extra fields merged into the event payload.
        """

        event: dict[str, Any] = {
            "type": event_type,
        }

        if path is not None:
            event["path"] = path

        event.update(kwargs)

        for callback in list(self._subscribers.values()):
            callback(event)
```

---

<!-- ==== 8/44 : interface/core/operations.py ==== -->

### interface/core/operations.py

```python
"""
Project Manager operation layer.
=================================

This is the single controller that HTTP routers, the browser, and
the Python client all funnel through.

The controller does NOT implement filesystem logic. Every filesystem
operation is delegated to parameters.filesystem, which
remains the sovereign owner of the Project Manager filesystem.

    Router / Client
        ↓
    EditorInterface
        ↓
    parameters.filesystem
        ↓
    Filesystem

Scopes
------
Operations address files relative to an active root chosen by scope:

    * workspace  ->  the managed workspace (default)
    * app        ->  the application repository root (dev files)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from parameters import filesystem as _filesystem
from .events import EventBus
from .session import EditorManager


# ============================================================
# SCOPES
# ============================================================

VALID_SCOPES = ("workspace", "app")


def _root_for(scope: str | None) -> Path:
    """
    Resolve a scope string into a filesystem root.

    ``app`` reaches the application repository root (dev files);
    everything else defaults to the managed workspace.
    """

    if scope == "app":

        return _filesystem.REPO_ROOT

    return _filesystem.PROJECT_ROOT


def _target(
    path: str,
    scope: str | None,
) -> tuple[str, Path, str | None]:
    """
    Resolve a request path into the arguments the filesystem
    operations expect.

    A path prefixed with a browser root (``source_files/AGENTS.md``)
    resolves inside that root. Anything else keeps the legacy
    behaviour and resolves against the scope's root.

    Returns:
        ``(stripped_relative, root, root_name)``.
    """

    return _filesystem.resolve_browse_target(
        path,
        _root_for(scope),
    )


# ============================================================
# EDITOR INTERFACE
# ============================================================

class EditorInterface:
    """
    The Project Manager operation/interface layer.

    Provides a narrow set of high-level operations agents and the
    web editor can use. All filesystem work goes through
    parameters.filesystem.
    """

    def __init__(
        self,
        filesystem: Any = None,
        events: EventBus | None = None,
        sessions: EditorManager | None = None,
    ) -> None:

        # The Project Manager remains the filesystem authority.
        self.filesystem = (
            filesystem
            if filesystem is not None
            else _filesystem
        )

        self.events = (
            events
            if events is not None
            else EventBus()
        )

        self.session_manager = (
            sessions
            if sessions is not None
            else EditorManager()
        )

    # ========================================================
    # HEALTH / STATE
    # ========================================================

    def health(self) -> dict[str, Any]:
        """
        Project Manager health and project information.
        """

        return {
            "status": "healthy",
            "project": self.filesystem.read_project_info(),
            "root": str(self.filesystem.PROJECT_ROOT),
        }

    def tree(
        self,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Project state: project info, active root and filesystem tree.

        Args:
            scope:
                None (default) returns the browser tree, whose top
                level is the configured ``BROWSE_ROOTS`` folders.
                ``"workspace"`` or ``"app"`` return the legacy
                single-root tree for that scope.
        """

        try:

            if not scope:

                return {
                    "scope": None,
                    "project": self.filesystem.read_project_info(),
                    "roots": [
                        {
                            "name": name,
                            "writable": bool(
                                config.get(
                                    "writable",
                                    False,
                                )
                            ),
                        }
                        for name, config
                        in self.filesystem.BROWSE_ROOTS.items()
                    ],
                    "root": str(
                        self.filesystem.PROJECT_ROOT
                    ),
                    "filesystem": self.filesystem.read_browse_filesystem(),
                }

            root = _root_for(scope)

            return {
                "scope": scope,
                "project": self.filesystem.read_project_info(),
                "root": str(root),
                "filesystem": self.filesystem.read_filesystem(
                    directory=root
                ),
            }

        except Exception as error:

            raise self._to_error(
                error
            )

    def sessions(self) -> list[dict[str, Any]]:
        """
        Snapshot of all connected interface sessions.
        """

        return self.session_manager.snapshot()

    # ========================================================
    # READ / WRITE
    # ========================================================

    def open(
        self,
        path: str,
        scope: str | None = None,
    ) -> str:
        """
        Open a project file and return its contents.

        Args:
            path:
                Root-qualified or root-relative file path.
            scope:
                ``None`` (default) or ``"workspace"`` or ``"app"``.

        Returns:
            The file contents.
        """

        stripped, root, _ = _target(path, scope)

        return self.filesystem.read_file(
            stripped,
            root=root,
        )

    def save(
        self,
        path: str,
        content: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Write file contents back to the project filesystem.

        Publishes a ``saved`` event on success. Raises ValueError
        if the path targets a read-only browser root.
        """

        self.filesystem.require_writable(
            path,
            _root_for(scope),
        )

        stripped, root, _ = _target(path, scope)

        self.filesystem.write_file(
            stripped,
            content,
            root=root,
        )

        self.events.publish(
            "saved",
            path=path,
            scope=scope,
        )

        return {
            "status": "saved",
            "path": path,
            "scope": scope,
        }

    # ========================================================
    # CREATE
    # ========================================================

    def create_file(
        self,
        path: str,
        content: str = "",
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new project file.

        Publishes a ``created`` event on success. Raises ValueError
        if the path targets a read-only browser root.
        """

        self.filesystem.require_writable(
            path,
            _root_for(scope),
        )

        stripped, root, _ = _target(path, scope)

        self.filesystem.create_file(
            stripped,
            content,
            root=root,
        )

        self.events.publish(
            "created",
            path=path,
            scope=scope,
        )

        return {
            "status": "created",
            "path": path,
            "scope": scope,
        }

    def create_directory(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new project directory.

        Publishes a ``created`` event on success. Raises ValueError
        if the path targets a read-only browser root.
        """

        self.filesystem.require_writable(
            path,
            _root_for(scope),
        )

        stripped, root, _ = _target(path, scope)

        self.filesystem.create_directory(
            stripped,
            root=root,
        )

        self.events.publish(
            "created",
            path=path,
            scope=scope,
        )

        return {
            "status": "created",
            "path": path,
            "scope": scope,
        }

    # ========================================================
    # RENAME
    # ========================================================

    def rename(
        self,
        old_path: str,
        new_path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Rename or move a project file/directory.

        Publishes a ``renamed`` event on success. Raises ValueError
        if either path targets a read-only browser root, or if the
        two paths belong to different browser roots.
        """

        self.filesystem.require_writable(
            old_path,
            _root_for(scope),
        )

        self.filesystem.require_writable(
            new_path,
            _root_for(scope),
        )

        old_stripped, old_root, old_name = _target(
            old_path,
            scope,
        )

        new_stripped, new_root, new_name = _target(
            new_path,
            scope,
        )

        if old_root != new_root:

            raise ValueError(
                "Cannot rename across browser roots "
                f"({old_name or 'scope'} -> "
                f"{new_name or 'scope'})."
            )

        self.filesystem.rename_path(
            old_stripped,
            new_stripped,
            root=old_root,
        )

        self.events.publish(
            "renamed",
            path=new_path,
            old_path=old_path,
            scope=scope,
        )

        return {
            "status": "renamed",
            "old_path": old_path,
            "new_path": new_path,
            "scope": scope,
        }

    # ========================================================
    # DELETE
    # ========================================================

    def delete(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Delete a project file or directory.

        Publishes a ``deleted`` event on success. Raises ValueError
        if the path targets a read-only browser root.
        """

        self.filesystem.require_writable(
            path,
            _root_for(scope),
        )

        stripped, root, _ = _target(path, scope)

        self.filesystem.delete_path(
            stripped,
            root=root,
        )

        self.events.publish(
            "deleted",
            path=path,
            scope=scope,
        )

        return {
            "status": "deleted",
            "path": path,
            "scope": scope,
        }

    # ========================================================
    # ERROR MAPPING
    # ========================================================

    # Kept on the controller so every interface shares the same
    # error behaviour. See routers/error.py for the HTTP mapping.
    _to_error = staticmethod(
        lambda error: error
    )
```

---

<!-- ==== 9/44 : interface/core/session.py ==== -->

### interface/core/session.py

```python
"""
Project Manager interface sessions.
====================================

Tracks connected interface clients (browser tabs, agents).

This is intentionally an in-memory system. No database.
"""

from __future__ import annotations

import time
import uuid
from typing import Any


# ============================================================
# EDITOR SESSION
# ============================================================

class EditorSession:
    """
    State for a single connected interface client.
    """

    def __init__(
        self,
        client_id: str | None = None,
    ) -> None:
        self.client_id = client_id or uuid.uuid4().hex
        self.open_file: str | None = None
        self.dirty: bool = False
        self.last_modified: float | None = None

    def snapshot(self) -> dict[str, Any]:
        """
        JSON-friendly copy of this session.
        """

        return {
            "client_id": self.client_id,
            "open_file": self.open_file,
            "dirty": self.dirty,
            "last_modified": self.last_modified,
        }

    def touch(self) -> None:
        """
        Update the last-modified timestamp.
        """

        self.last_modified = time.time()


# ============================================================
# EDITOR MANAGER
# ============================================================

class EditorManager:
    """
    Maintains the active in-memory interface sessions.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, EditorSession] = {}

    def register(self, client_id: str | None = None) -> EditorSession:
        """
        Register a new connected client.
        """

        session = EditorSession(client_id=client_id)
        session.touch()

        self._sessions[session.client_id] = session

        return session

    def unregister(self, client_id: str) -> None:
        """
        Remove a client session.
        """

        self._sessions.pop(client_id, None)

    def get(self, client_id: str) -> EditorSession | None:
        """
        Fetch a session by client id.
        """

        return self._sessions.get(client_id)

    def update(
        self,
        client_id: str,
        *,
        open_file: str | None = None,
        dirty: bool | None = None,
    ) -> EditorSession | None:
        """
        Update one field of a client session.

        Returns the session, or None if the client is unknown.
        """

        session = self._sessions.get(client_id)

        if session is None:
            return None

        session.touch()

        if open_file is not None:
            session.open_file = open_file

        if dirty is not None:
            session.dirty = dirty

        return session

    def snapshot(self) -> list[dict[str, Any]]:
        """
        JSON-friendly list of all active sessions.
        """

        return [
            session.snapshot()
            for session in self._sessions.values()
        ]
```

---

<!-- ==== 10/44 : interface/routers/__init__.py ==== -->

### interface/routers/__init__.py

```python
"""
Project Manager HTTP API helpers.
==================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import HTTPException

from parameters import filesystem
from interface.core.defaults import get_interface
from interface.core.operations import VALID_SCOPES


# ============================================================
# SHARED CONTROLLER
# ============================================================

def controller() -> Any:
    """
    The single shared Project Manager interface instance.
    """

    return get_interface()


# ============================================================
# SCOPE HANDLING
# ============================================================

def normalize_scope(scope: str | None) -> str | None:
    """
    Validate and normalize a scope query parameter.

    Returns None when the parameter is absent, which selects the
    browser view (paths may carry a browser-root prefix). An
    explicit scope keeps the legacy single-root behaviour.

    Raises:
        HTTPException (422):
            If the scope is not a known scope.
    """

    if scope is None:

        return None

    if scope not in VALID_SCOPES:

        raise HTTPException(
            status_code=422,
            detail=f"Unknown scope: {scope}",
        )

    return scope
```

---

<!-- ==== 11/44 : interface/routers/agents.py ==== -->

### interface/routers/agents.py

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

<!-- ==== 12/44 : interface/routers/chat.py ==== -->

### interface/routers/chat.py

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
from tools.chatlog import append_chat, clear_chat, read_history  # noqa: E402

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


def _record_entries(user_message: str, reply: str, agent_id: str) -> list[dict]:
    """Persist user + reply to the headless chat log; mirror to PM's log.

    The agent id is stored on both entries so each agent keeps its own
    conversation in the shared log.
    """
    user_entry = append_chat("user", user_message, agent=agent_id)
    reply_entry = append_chat("agent", reply, agent=agent_id)
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

        entries = _record_entries(message, reply, agent_id)

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
    agent: str | None = None,
):
    """
    Return the most recent chat entries.

    Query params:
        limit:
            Maximum number of entries to return.
        agent:
            Restrict the history to one agent's thread. Omit to
            return the whole log.
    """

    try:

        return {
            "entries": read_history(limit, agent=agent),
        }

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# CLEAR CHAT HISTORY
# ============================================================

def _clear_mirror(agent: str | None) -> int:
    """Apply the same wipe to the Project Manager's own chat.log."""
    from parameters import filesystem

    log_path = filesystem.resolve_project_path("data/chat.log")
    if not log_path.exists():
        return 0
    if not agent:
        with log_path.open("r", encoding="utf-8") as handle:
            removed = sum(1 for line in handle if line.strip())
        log_path.write_text("", encoding="utf-8")
        return removed

    kept: list[str] = []
    removed = 0
    with log_path.open("r", encoding="utf-8") as handle:
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
    log_path.write_text("".join(kept), encoding="utf-8")
    return removed


@router.delete("/api/chat")
def clear_chat_history(
    request: Request,
    agent: str | None = None,
):
    """
    Wipe the chat history.

    Truncates the headless chat log (data/chatlog/chat.log) and mirrors the
    wipe onto the Project Manager's own log (workspace/data/chat.log).
    With ``agent`` set, only that agent's thread is wiped in both logs.
    Returns how many entries were removed.
    """

    try:

        removed = clear_chat(agent=agent)

        try:
            mirrored = _clear_mirror(agent)
        except Exception:
            mirrored = removed  # fail-safe: headless log is the authority

        return {
            "status": "ok",
            "cleared": removed,
            "mirrored_cleared": mirrored,
        }

    except Exception as error:

        raise project_manager_error(
            error
        )


if __name__ == "__main__":
    print(__doc__)
```

---

<!-- ==== 13/44 : interface/routers/directories.py ==== -->

### interface/routers/directories.py

```python
"""Project directory resource router (create / delete)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from . import normalize_scope
from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# CREATE DIRECTORY
# ============================================================

@router.post("/api/directory/create")
def create_directory(
    request: Request,
    path: str,
    scope: str | None = None,
):
    """
    Create a project directory.

    Query params:
        path:
            Browser-root-qualified or root-relative directory path.
        scope:
            Omit for the browser view; ``"workspace"`` or
            ``"app"`` for a legacy single-root view.
    """

    try:

        return request.app.state.editor.create_directory(
            path,
            scope=normalize_scope(scope),
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# DELETE DIRECTORY
# ============================================================

@router.delete("/api/directory/delete")
def delete_directory(
    request: Request,
    path: str,
    scope: str | None = None,
):
    """
    Delete a project directory.

    Query params:
        path:
            Browser-root-qualified or root-relative directory path.
        scope:
            Omit for the browser view; ``"workspace"`` or
            ``"app"`` for a legacy single-root view.
    """

    try:

        return request.app.state.editor.delete(
            path,
            scope=normalize_scope(scope),
        )

    except Exception as error:

        raise project_manager_error(
            error
        )
```

---

<!-- ==== 14/44 : interface/routers/errors.py ==== -->

### interface/routers/errors.py

```python
"""Shared FastAPI error mapping for the Project Manager API."""

from __future__ import annotations

from fastapi import HTTPException


def project_manager_error(
    error: Exception,
) -> HTTPException:
    """
    Convert a Project Manager operation error into an HTTP error.

    This is the single translator for the HTTP API. Routers do
    not implement their own status-code logic.
    """

    if isinstance(
        error,
        HTTPException,
    ):

        return error

    if isinstance(
        error,
        FileNotFoundError,
    ):

        return HTTPException(
            status_code=404,
            detail=str(error),
        )

    if isinstance(
        error,
        FileExistsError,
    ):

        return HTTPException(
            status_code=409,
            detail=str(error),
        )

    if isinstance(
        error,
        ValueError,
    ):

        return HTTPException(
            status_code=400,
            detail=str(error),
        )

    # --------------------------------------------------------
    # WebSocket-disconnect / client errors
    # --------------------------------------------------------

    if isinstance(
        error,
        KeyError,
    ):

        return HTTPException(
            status_code=404,
            detail=str(error),
        )

    return HTTPException(
        status_code=500,
        detail=str(error),
    )
```

---

<!-- ==== 15/44 : interface/routers/files.py ==== -->

### interface/routers/files.py

```python
"""Project file resource router (read / write / create / delete)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from . import normalize_scope
from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# REQUEST MODELS
# ============================================================

class FileWriteRequest(BaseModel):

    path: str

    content: str

    scope: str | None = None


class FileCreateRequest(BaseModel):

    path: str

    content: str = ""

    scope: str | None = None


# ============================================================
# READ FILE
# ============================================================

@router.get("/api/file/read")
def read_file(
    request: Request,
    path: str,
    scope: str | None = None,
):
    """
    Read a project text file.

    Query params:
        path:
            Browser-root-qualified or root-relative file path.
        scope:
            Omit for the browser view; ``"workspace"`` or
            ``"app"`` for a legacy single-root view.
    """

    try:

        content = request.app.state.editor.open(
            path,
            scope=normalize_scope(scope),
        )
        return {
            "path": path,
            "content": content,
            "scope": scope,
        }

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# WRITE FILE
# ============================================================

@router.put("/api/file/write")
def write_file(
    request: Request,
    payload: FileWriteRequest,
):
    """
    Create or overwrite a project text file.
    """

    try:

        return request.app.state.editor.save(
            payload.path,
            payload.content,
            scope=normalize_scope(payload.scope),
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# CREATE FILE
# ============================================================

@router.post("/api/file/create")
def create_file(
    request: Request,
    payload: FileCreateRequest,
):
    """
    Create a new project file.
    """

    try:

        return request.app.state.editor.create_file(
            payload.path,
            payload.content,
            scope=normalize_scope(payload.scope),
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# DELETE FILE
# ============================================================

@router.delete("/api/file/delete")
def delete_file(
    request: Request,
    path: str,
    scope: str | None = None,
):
    """
    Delete a project file.

    Query params:
        path:
            Browser-root-qualified or root-relative file path.
        scope:
            Omit for the browser view; ``"workspace"`` or
            ``"app"`` for a legacy single-root view.
    """

    try:

        return request.app.state.editor.delete(
            path,
            scope=normalize_scope(scope),
        )

    except Exception as error:

        raise project_manager_error(
            error
        )
```

---

<!-- ==== 16/44 : interface/routers/paths.py ==== -->

### interface/routers/paths.py

```python
"""Project path resource router (rename / move)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from . import normalize_scope
from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# REQUEST MODELS
# ============================================================

class RenameRequest(BaseModel):

    old_path: str

    new_path: str

    scope: str | None = None


# ============================================================
# RENAME
# ============================================================

@router.put("/api/path/rename")
def rename_path(
    request: Request,
    payload: RenameRequest,
):
    """
    Rename or move a project file/directory.
    """

    try:

        return request.app.state.editor.rename(
            payload.old_path,
            payload.new_path,
            scope=normalize_scope(payload.scope),
        )

    except Exception as error:

        raise project_manager_error(
            error
        )
```

---

<!-- ==== 17/44 : interface/routers/project.py ==== -->

### interface/routers/project.py

```python
"""Project resource router.

Dashboard, health and interface-state endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from . import normalize_scope
from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# HEALTH
# ============================================================

@router.get("/api/health")
def health(
    request: Request,
):
    """
    Project Manager health and project information.
    """

    try:

        return request.app.state.editor.health()

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# PROJECT STATE
# ============================================================

@router.get("/api/project")
def get_project(
    request: Request,
    scope: str | None = None,
):
    """
    Project information and filesystem tree.

    Query params:
        scope:
            Omit for the browser tree, whose top level is the
            configured browser roots. ``"workspace"`` or ``"app"``
            return the legacy single-root tree.
    """

    try:

        return request.app.state.editor.tree(
            scope=normalize_scope(scope)
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# SESSIONS
# ============================================================

@router.get("/api/sessions")
def get_sessions(
    request: Request,
):
    """
    Active interface sessions.
    """

    try:

        return request.app.state.editor.sessions()

    except Exception as error:

        raise project_manager_error(
            error
        )
```

---

<!-- ==== 18/44 : interface/routers/ws.py ==== -->

### interface/routers/ws.py

```python
"""
Project Manager WebSocket router.
=================================

Real-time interface sync for the Project Manager. Every client
connection gets:

  * a dedicated EditorSession inside the shared EditorManager;
  * a subscription to the shared EventBus, so every publish is
    forwarded to the browser over the same socket.

Not every publish reaches the browser -- only the projected
types the dashboard cares about (saved / created / renamed /
deleted / session events). Everything goes through the shared
EventBus; there is no direct filesystem access here.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter()


@router.websocket("/api/ws")
async def project_manager_socket(
    websocket: WebSocket,
) -> None:
    """
    Real-time Project Manager socket.

    Client -> Server (JSON messages):

        {"type": "open",        "path": "src/app.py"}
        {"type": "dirty",       "dirty": true}
        {"type": "subscribe",   "events": ["saved", "created"]}

    Server -> Client (JSON messages):

        {"type": "hello",        "client_id": "..."}
        {"type": "event",        "event": {publish payload}}
        {"type": "sessions",     "sessions": [...]}
    """

    await websocket.accept()

    controller = websocket.app.state.editor

    loop = asyncio.get_running_loop()

    session = controller.session_manager.register()

    try:

        await websocket.send_json(
            {
                "type": "hello",
                "client_id": session.client_id,
            }
        )

        def forward(
            event: dict[str, Any],
        ) -> None:
            """
            Forward a published event to this socket.

            ``EventBus.publish`` is called synchronously, and it can run on a
            worker thread (sync ``def`` endpoints run in the threadpool where
            there is no running event loop). We therefore capture the socket's
            loop up front and use ``loop.call_soon_threadsafe`` to hop back
            onto that loop before creating the send task -- a plain
            ``asyncio.create_task`` / ``get_running_loop`` here would raise
            ``RuntimeError`` on a worker thread and silently drop the event.
            """

            async def _send() -> None:

                try:

                    await websocket.send_json(
                        {
                            "type": "event",
                            "event": event,
                        }
                    )

                except Exception:

                    pass

            def _schedule() -> None:

                try:

                    loop.create_task(
                        _send()
                    )

                except Exception:

                    pass

            try:

                loop.call_soon_threadsafe(
                    _schedule
                )

            except Exception:

                pass

        subscription_id = controller.events.subscribe(
            forward,
        )

        async def _send_sessions() -> None:

            await websocket.send_json(
                {
                    "type": "sessions",
                    "sessions": controller.session_manager.snapshot(),
                }
            )

        await _send_sessions()

        while True:

            raw = await websocket.receive_text()

            try:

                message = json.loads(raw)

            except json.JSONDecodeError:

                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": "Message was not valid JSON.",
                    }
                )

                continue

            message_type = message.get(
                "type"
            )

            if message_type == "open":

                controller.session_manager.update(
                    session.client_id,
                    open_file=message.get(
                        "path"
                    ),
                )

                await websocket.send_json(
                    {
                        "type": "hello",
                        "client_id": session.client_id,
                        "open_file": message.get(
                            "path"
                        ),
                    }
                )

            elif message_type == "dirty":

                controller.session_manager.update(
                    session.client_id,
                    dirty=bool(
                        message.get(
                            "dirty",
                            False,
                        )
                    ),
                )

            elif message_type == "sessions":

                await _send_sessions()

            else:

                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": "Unknown message type: "
                        + str(message_type),
                    }
                )

    except WebSocketDisconnect:

        pass

    except Exception:

        pass

    finally:

        try:

            controller.events.unsubscribe(
                subscription_id  # type: ignore[possibly-undefined]
            )

        except Exception:

            pass

        controller.session_manager.unregister(
            session.client_id
        )
```

---

<!-- ==== 19/44 : interface/static/ai_agent_creator.html ==== -->

### interface/static/ai_agent_creator.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Creator</title>
    <!-- Lucide Icons Library -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root {
            --bg-darkest: #0b0f17;
            --bg-app: #10141e;
            --bg-panel: #131822;
            --bg-card: #1b2130;
            --bg-card-hover: #232a3d;
            --bg-input: #161c28;
            --border-color: #252e3e;
            --border-subtle: #1e2634;
            --text-primary: #e6e8ee;
            --text-secondary: #9aa2b1;
            --text-muted: #626c7d;
            --accent-blue: #3b82f6;
            --accent-blue-hover: #2563eb;
            --accent-glow: rgba(59, 130, 246, 0.15);
            --user-msg-bg: #1e293b;
            --radius-lg: 16px;
            --radius-md: 10px;
            --radius-sm: 6px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        html, body {
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-darkest);
            color: var(--text-primary);
        }

        body {
            display: flex;
            flex-direction: column;
        }

        button, input, select, textarea {
            font-family: inherit;
            color: inherit;
        }

        .app-header {
            height: 54px;
            min-height: 54px;
            background: var(--bg-panel);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            z-index: 20;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .agent-logo {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            box-shadow: 0 0 12px rgba(37, 99, 235, 0.4);
        }

        .app-title {
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: var(--text-primary);
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn-header {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 500;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-header:hover {
            background: var(--bg-card-hover);
            border-color: #3b475c;
        }

        .btn-icon-only {
            padding: 6px;
            border-radius: 50%;
        }

        .app-container {
            flex: 1;
            display: flex;
            overflow: hidden;
            position: relative;
        }

        .panel {
            display: flex;
            flex-direction: column;
            background: var(--bg-app);
            height: 100%;
            transition: transform 0.25s ease, width 0.25s ease;
        }

        .panel-header {
            height: 48px;
            padding: 0 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-subtle);
            background: var(--bg-panel);
        }

        .panel-title {
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
        }

        .panel-sources {
            width: 320px;
            min-width: 280px;
            border-right: 1px solid var(--border-color);
            background: var(--bg-panel);
        }

        .sources-content {
            padding: 16px;
            overflow-y: auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .note-input-box {
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 12px;
        }

        .note-input-box textarea {
            background: transparent;
            border: none;
            outline: none;
            resize: none;
            font-size: 13px;
            color: var(--text-primary);
            min-height: 50px;
        }

        .btn-add-note {
            background: var(--accent-blue);
            color: #fff;
            border: none;
            border-radius: var(--radius-sm);
            padding: 8px 12px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            cursor: pointer;
            transition: background 0.15s;
        }

        .btn-add-note:hover {
            background: var(--accent-blue-hover);
        }

        .notes-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .note-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 10px 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            transition: border-color 0.15s;
        }

        .note-card:hover {
            border-color: var(--border-color);
        }

        .note-text {
            font-size: 13px;
            line-height: 1.45;
            color: var(--text-primary);
            white-space: pre-wrap;
            word-break: break-word;
        }

        .note-actions {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-top: 1px solid var(--border-subtle);
            padding-top: 6px;
        }

        .btn-send-to-chat {
            background: transparent;
            border: none;
            color: var(--accent-blue);
            font-size: 11px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            padding: 2px 4px;
            border-radius: var(--radius-sm);
        }

        .btn-send-to-chat:hover {
            background: var(--accent-glow);
        }

        .btn-delete-note {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 2px 4px;
            border-radius: var(--radius-sm);
        }

        .btn-delete-note:hover {
            color: #ef4444;
        }

        .panel-chat {
            flex: 1;
            background: var(--bg-app);
            display: flex;
            flex-direction: column;
            position: relative;
        }

        .chat-top-status {
            padding: 8px 20px;
            background: var(--bg-panel);
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12px;
        }

        .agent-controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .agent-controls select {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 4px 8px;
            font-size: 12px;
            color: var(--text-primary);
            outline: none;
            cursor: pointer;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--text-secondary);
            font-size: 12px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
        }

        #chatLog {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        #chatLog::-webkit-scrollbar {
            width: 6px;
        }
        #chatLog::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 10px;
        }

        /* Message Cards */
        .msg {
            max-width: 850px;
            width: 100%;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .msg.user {
            align-items: flex-end;
        }

        .msg.user .msg-content-card {
            background: var(--user-msg-bg);
            border: 1px solid #334155;
            border-radius: 18px 18px 4px 18px;
            padding: 12px 18px;
            max-width: 80%;
        }

        .msg.ai, .msg.system {
            align-items: flex-start;
        }

        .msg.ai .msg-content-card {
            background: var(--bg-panel);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 16px;
            width: 100%;
        }

        .msg-label {
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .msg-body {
            font-size: 14px;
            line-height: 1.6;
            color: var(--text-primary);
            white-space: pre-wrap;
            word-break: break-word;
        }

        .msg-actions {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 10px;
            padding-top: 8px;
            border-top: 1px solid var(--border-subtle);
        }

        .btn-msg-action {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            padding: 4px 10px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 12px;
            transition: all 0.15s ease;
        }

        .btn-msg-action:hover {
            background: var(--bg-card-hover);
            color: var(--text-primary);
            border-color: var(--border-color);
        }

        .chat-foot {
            padding: 14px 24px 20px;
            background: var(--bg-app);
            max-width: 900px;
            width: 100%;
            margin: 0 auto;
        }

        .input-container {
            background: var(--bg-panel);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 10px 14px 10px 18px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25);
            transition: border-color 0.2s;
        }

        .input-container:focus-within {
            border-color: #3b82f6;
        }

        #chatInput {
            background: transparent;
            border: none;
            outline: none;
            resize: none;
            font-size: 14px;
            max-height: 140px;
            min-height: 38px;
            color: var(--text-primary);
            line-height: 1.5;
        }

        #chatInput::placeholder {
            color: var(--text-muted);
        }

        .input-bottom-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .input-hint {
            font-size: 11px;
            color: var(--text-muted);
        }

        #chatSend {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: var(--accent-blue);
            border: none;
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: background 0.15s, transform 0.1s;
        }

        #chatSend:hover {
            background: var(--accent-blue-hover);
        }

        #chatSend:active {
            transform: scale(0.94);
        }

        #chatSend:disabled {
            background: var(--bg-card);
            color: var(--text-muted);
            cursor: not-allowed;
        }

        .panel-test {
            width: 330px;
            min-width: 280px;
            border-left: 1px solid var(--border-color);
            background: var(--bg-panel);
            position: relative;
        }

        .test-content {
            padding: 16px;
            overflow-y: auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .test-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .test-func-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            text-align: center;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .test-func-card:hover {
            background: var(--bg-card-hover);
            border-color: var(--accent-blue);
            transform: translateY(-2px);
        }

        .test-func-card i {
            color: var(--accent-blue);
            width: 20px;
            height: 20px;
        }

        .test-func-card span {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .saved-chats-section {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .section-label {
            font-size: 12px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .btn-save-current {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 4px 8px;
            border-radius: var(--radius-sm);
            font-size: 11px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .btn-save-current:hover {
            background: var(--bg-card-hover);
        }

        .saved-chats-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .saved-chat-item {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 10px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            transition: background 0.15s;
        }

        .saved-chat-item:hover {
            background: var(--bg-card-hover);
        }

        .saved-chat-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
            overflow: hidden;
        }

        .saved-chat-title {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .saved-chat-date {
            font-size: 10px;
            color: var(--text-muted);
        }

        /* Toast Feedback */
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--accent-blue);
            color: #fff;
            padding: 8px 16px;
            border-radius: var(--radius-md);
            font-size: 12px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.2s ease;
            pointer-events: none;
            z-index: 100;
        }

        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }

        @media (max-width: 1024px) {
            .panel-test {
                position: absolute;
                right: 0;
                top: 0;
                bottom: 0;
                z-index: 15;
                transform: translateX(100%);
                box-shadow: -10px 0 30px rgba(0,0,0,0.5);
            }
            .panel-test.open {
                transform: translateX(0);
            }
        }

        @media (max-width: 768px) {
            .panel-sources {
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                z-index: 15;
                transform: translateX(-100%);
                box-shadow: 10px 0 30px rgba(0,0,0,0.5);
            }
            .panel-sources.open {
                transform: translateX(0);
            }
        }
    </style>
</head>
<body>

    <header class="app-header">
        <div class="header-left">
            <button class="btn-header btn-icon-only" id="toggleSources" title="Toggle Sources & Notes">
                <i data-lucide="panel-left"></i>
            </button>
            <div class="agent-logo">
                <i data-lucide="bot" style="width:18px; height:18px;"></i>
            </div>
            <h1 class="app-title">AI Agent Creator</h1>
        </div>

        <div class="header-actions">
            <button class="btn-header" onclick="createNewAgent()">
                <i data-lucide="plus" style="width:14px; height:14px;"></i>
                New Agent
            </button>
            <button class="btn-header btn-icon-only" id="toggleTest" title="Toggle Test Panel">
                <i data-lucide="panel-right"></i>
            </button>
        </div>
    </header>

    <div class="app-container">

        <!-- LEFT PANEL: SOURCES & NOTES -->
        <aside class="panel panel-sources" id="panelSources">
            <div class="panel-header">
                <span class="panel-title">Sources & Notes</span>
                <i data-lucide="notebook" style="width:16px; height:16px; color: var(--text-muted);"></i>
            </div>
            <div class="sources-content">
                
                <!-- Add Note Input Section -->
                <div class="note-input-box">
                    <textarea id="newNoteInput" placeholder="Add a note or task list..."></textarea>
                    <button class="btn-add-note" onclick="addNote()">
                        <i data-lucide="plus" style="width:14px;"></i> Add Note
                    </button>
                </div>

                <!-- Notes / To-Do List Container -->
                <div class="notes-list" id="notesList">
                    <!-- Default initial note card -->
                    <div class="note-card">
                        <div class="note-text">Define agent system prompt with tool routing and file system permissions.</div>
                        <div class="note-actions">
                            <button class="btn-send-to-chat" onclick="sendNoteToChat(this)">
                                <i data-lucide="arrow-right-circle" style="width:13px;"></i> Send to Chat
                            </button>
                            <button class="btn-delete-note" onclick="deleteNote(this)" title="Delete note">
                                <i data-lucide="trash-2" style="width:13px;"></i>
                            </button>
                        </div>
                    </div>
                </div>

            </div>
        </aside>

        <!-- CENTER PANEL: CHAT WORKSPACE -->
        <main class="panel panel-chat">

            <!-- Dynamic Status Bar & Agent Selectors -->
            <div class="chat-top-status">
                <div class="agent-controls">
                    <span>Active Agent:</span>
                    <select id="agentSelect" title="Agent selection">
                        <option value="builder">Agent Builder v1</option>
                        <option value="code_executor">Code Executor</option>
                    </select>
                    <select id="modelSelect" title="Model selection">
                        <option value="gemini_flash">Gemini 3 Flash</option>
                        <option value="gemini_pro">Gemini Pro</option>
                    </select>
                </div>
                <div class="status-badge">
                    <span id="statusDot" class="status-dot"></span>
                    <span id="chatStatus">Connected</span>
                </div>
            </div>

            <!-- Main Chat Conversation Feed -->
            <div id="chatLog">
                <div class="msg system">
                    <div class="msg-content-card">
                        <span class="msg-label">SYSTEM</span>
                        <div class="msg-body">AI Agent Creator initialized. Type a message or click 'Send to Chat' on any note in your left sidebar.</div>
                    </div>
                </div>
            </div>

            <!-- Chat Footer & Input Box -->
            <footer class="chat-foot">
                <form id="chatForm">
                    <div class="input-container">
                        <textarea 
                            id="chatInput" 
                            placeholder="Message AI Agent Creator..." 
                            rows="1"
                            autocomplete="off"
                        ></textarea>
                        
                        <div class="input-bottom-row">
                            <span class="input-hint">Enter to send · Shift + Enter for newline</span>
                            <button id="chatSend" type="submit" aria-label="Send message">
                                <i data-lucide="arrow-up" style="width:18px; height:18px;"></i>
                            </button>
                        </div>
                    </div>
                </form>
            </footer>

        </main>

        <!-- RIGHT PANEL: TEST & SAVED CHATS -->
        <aside class="panel panel-test" id="panelTest">
            <div class="panel-header">
                <span class="panel-title">Test</span>
                <i data-lucide="x" style="width:16px; height:16px; color: var(--text-muted); cursor:pointer;" id="closeTest"></i>
            </div>
            <div class="test-content">

                <!-- Interactive Function Buttons Grid -->
                <div class="test-grid">
                    <div class="test-func-card" onclick="runTestFunc('Run Test Suite')">
                        <i data-lucide="play-circle"></i>
                        <span>Run Test Suite</span>
                    </div>
                    <div class="test-func-card" onclick="runTestFunc('Debug Agent')">
                        <i data-lucide="bug"></i>
                        <span>Debug Agent</span>
                    </div>
                    <div class="test-func-card" onclick="runTestFunc('Prompt Inspector')">
                        <i data-lucide="terminal"></i>
                        <span>Prompt Inspector</span>
                    </div>
                    <div class="test-func-card" onclick="runTestFunc('Output Evaluator')">
                        <i data-lucide="check-square"></i>
                        <span>Output Evaluator</span>
                    </div>
                    <div class="test-func-card" onclick="runTestFunc('Benchmark Performance')">
                        <i data-lucide="gauge"></i>
                        <span>Benchmark</span>
                    </div>
                    <div class="test-func-card" onclick="runTestFunc('View API Logs')">
                        <i data-lucide="file-code"></i>
                        <span>API Logs</span>
                    </div>
                </div>

                <!-- Saved Chats Section -->
                <div class="saved-chats-section">
                    <div class="section-label">
                        <span>Saved Chats</span>
                        <button class="btn-save-current" onclick="saveCurrentChat()">
                            <i data-lucide="bookmark" style="width:12px;"></i> Save Session
                        </button>
                    </div>

                    <div class="saved-chats-list" id="savedChatsList">
                        <div class="saved-chat-item" onclick="loadSavedChat('Agent Blueprint Draft')">
                            <div class="saved-chat-info">
                                <div class="saved-chat-title">Agent Blueprint Draft</div>
                                <div class="saved-chat-date">Saved 2 hours ago</div>
                            </div>
                            <i data-lucide="chevron-right" style="width:14px; color:var(--text-muted);"></i>
                        </div>
                    </div>
                </div>

            </div>
        </aside>

    </div>

    <!-- Dynamic Toast Feedback Banner -->
    <div id="toast" class="toast">Action completed!</div>

    <!-- Backend Module Integrations -->
    <script type="module" src="/static/js/chat.js"></script>

    <script>
        // Initialize Icons
        lucide.createIcons();

        // Toast Helper
        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        }

        // Add Note to Left Panel List
        function addNote() {
            const input = document.getElementById('newNoteInput');
            const text = input.value.trim();
            if (!text) return;

            const notesList = document.getElementById('notesList');
            const card = document.createElement('div');
            card.className = 'note-card';
            card.innerHTML = `
                <div class="note-text">${escapeHtml(text)}</div>
                <div class="note-actions">
                    <button class="btn-send-to-chat" onclick="sendNoteToChat(this)">
                        <i data-lucide="arrow-right-circle" style="width:13px;"></i> Send to Chat
                    </button>
                    <button class="btn-delete-note" onclick="deleteNote(this)" title="Delete note">
                        <i data-lucide="trash-2" style="width:13px;"></i>
                    </button>
                </div>
            `;
            notesList.prepend(card);
            input.value = '';
            lucide.createIcons();
            showToast('Note added to list');
        }

        // Send Note Directly to Chat Box
        function sendNoteToChat(btn) {
            const noteText = btn.closest('.note-card').querySelector('.note-text').innerText;
            const chatInput = document.getElementById('chatInput');
            
            chatInput.value = noteText;
            chatInput.focus();
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
            showToast('Note populated into chat input');
        }

        // Delete Note Item
        function deleteNote(btn) {
            btn.closest('.note-card').remove();
            showToast('Note removed');
        }

        // Copy Message Content to Clipboard
        function copyMsg(btn) {
            const bodyText = btn.closest('.msg-content-card').querySelector('.msg-body').innerText;
            
            // execCommand copy implementation for frame safety
            const tempArea = document.createElement('textarea');
            tempArea.value = bodyText;
            document.body.appendChild(tempArea);
            tempArea.select();
            document.execCommand('copy');
            document.body.removeChild(tempArea);

            showToast('Copied to clipboard!');
        }

        // Placeholder Action Handlers
        function msgAction(actionName) {
            showToast(`${actionName} action saved`);
        }

        function runTestFunc(funcName) {
            showToast(`Triggered: ${funcName}`);
        }

        function createNewAgent() {
            showToast('Started new agent project session');
        }

        // Save & Load Chat Functions
        function saveCurrentChat() {
            const savedList = document.getElementById('savedChatsList');
            const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            const item = document.createElement('div');
            item.className = 'saved-chat-item';
            item.onclick = () => loadSavedChat(`Saved Session (${now})`);
            item.innerHTML = `
                <div class="saved-chat-info">
                    <div class="saved-chat-title">Saved Session (${now})</div>
                    <div class="saved-chat-date">Just now</div>
                </div>
                <i data-lucide="chevron-right" style="width:14px; color:var(--text-muted);"></i>
            `;
            savedList.prepend(item);
            lucide.createIcons();
            showToast('Current chat session saved!');
        }

        function loadSavedChat(title) {
            showToast(`Loaded: ${title}`);
        }

        // Textarea Auto-growth and Keyboard handling
        const chatInput = document.getElementById("chatInput");
        const chatForm = document.getElementById("chatForm");
        const chatLog = document.getElementById("chatLog");

        if (chatInput) {
            chatInput.addEventListener("input", () => {
                chatInput.style.height = "auto";
                chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + "px";
            });

            chatInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    if (chatForm) {
                        chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                    }
                }
            });
        }

        // Form Submit Handler
        if (chatForm) {
            chatForm.addEventListener("submit", (e) => {
                e.preventDefault();
                const text = chatInput.value.trim();
                if (!text) return;

                appendMessage("user", text);
                chatInput.value = "";
                chatInput.style.height = "auto";

                // Simulated AI response (if external backend module isn't active)
                setTimeout(() => {
                    appendMessage("ai", `Received agent instructions:\n"${text}"\nReady for function testing.`);
                }, 700);
            });
        }

        function appendMessage(role, text) {
            const msgDiv = document.createElement("div");
            msgDiv.className = `msg ${role}`;

            if (role === "user") {
                msgDiv.innerHTML = `
                    <div class="msg-content-card">
                        <div class="msg-body">${escapeHtml(text)}</div>
                    </div>
                `;
            } else {
                msgDiv.innerHTML = `
                    <div class="msg-content-card">
                        <span class="msg-label">AI AGENT CREATOR</span>
                        <div class="msg-body">${escapeHtml(text)}</div>
                        <div class="msg-actions">
                            <button class="btn-msg-action" onclick="copyMsg(this)">
                                <i data-lucide="copy" style="width:13px;"></i> Copy
                            </button>
                            <button class="btn-msg-action" onclick="msgAction('Save')">
                                <i data-lucide="bookmark" style="width:13px;"></i> Save
                            </button>
                            <button class="btn-msg-action" onclick="msgAction('Fork')">
                                <i data-lucide="git-fork" style="width:13px;"></i> Fork
                            </button>
                        </div>
                    </div>
                `;
            }

            chatLog.appendChild(msgDiv);
            chatLog.scrollTop = chatLog.scrollHeight;
            lucide.createIcons();
        }

        function escapeHtml(str) {
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        // Sidebar Toggles
        document.getElementById("toggleSources")?.addEventListener("click", () => {
            document.getElementById("panelSources").classList.toggle("open");
        });

        document.getElementById("toggleTest")?.addEventListener("click", () => {
            document.getElementById("panelTest").classList.toggle("open");
        });

        document.getElementById("closeTest")?.addEventListener("click", () => {
            document.getElementById("panelTest").classList.remove("open");
        });
    </script>
</body>
</html>
```

---

<!-- ==== 20/44 : interface/static/chat.html ==== -->

### interface/static/chat.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Creator</title>
    <!-- Lucide Icons Library -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root {
            --bg-darkest: #0b0f17;
            --bg-app: #10141e;
            --bg-panel: #131822;
            --bg-card: #1b2130;
            --bg-card-hover: #232a3d;
            --bg-input: #161c28;
            --border-color: #252e3e;
            --border-subtle: #1e2634;
            --text-primary: #e6e8ee;
            --text-secondary: #9aa2b1;
            --text-muted: #626c7d;
            --accent-blue: #3b82f6;
            --accent-blue-hover: #2563eb;
            --accent-glow: rgba(59, 130, 246, 0.15);
            --user-msg-bg: #1e293b;
            --radius-lg: 16px;
            --radius-md: 10px;
            --radius-sm: 6px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        html, body {
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-darkest);
            color: var(--text-primary);
        }

        body {
            display: flex;
            flex-direction: column;
        }

        button, input, select, textarea {
            font-family: inherit;
            color: inherit;
        }

        .app-header {
            height: 52px;
            min-height: 52px;
            background: var(--bg-panel);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            z-index: 20;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .agent-logo {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            box-shadow: 0 0 12px rgba(37, 99, 235, 0.4);
        }

        .app-title {
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: var(--text-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 8px;
            /* Keep these buttons hugging the nav at the far right
               instead of drifting into the middle of the header. */
            margin-left: auto;
        }

        .btn-header {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 500;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-header:hover {
            background: var(--bg-card-hover);
            border-color: #3b475c;
        }

        .btn-icon-only {
            padding: 6px;
            border-radius: 50%;
        }

        .app-container {
            flex: 1;
            display: flex;
            overflow: hidden;
            position: relative;
        }

        .panel {
            display: flex;
            flex-direction: column;
            background: var(--bg-app);
            height: 100%;
            transition: transform 0.25s ease, width 0.25s ease;
        }

        .panel-header {
            height: 48px;
            padding: 0 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-subtle);
            background: var(--bg-panel);
        }

        .panel-title {
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
        }

        .panel-sources {
            width: 320px;
            min-width: 280px;
            border-right: 1px solid var(--border-color);
            background: var(--bg-panel);
        }

        .sources-content {
            padding: 16px;
            overflow-y: auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .note-input-box {
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 12px;
        }

        .note-input-box textarea {
            background: transparent;
            border: none;
            outline: none;
            resize: none;
            font-size: 13px;
            color: var(--text-primary);
            min-height: 50px;
        }

        .btn-add-note {
            background: var(--accent-blue);
            color: #fff;
            border: none;
            border-radius: var(--radius-sm);
            padding: 8px 12px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            cursor: pointer;
            transition: background 0.15s;
        }

        .btn-add-note:hover {
            background: var(--accent-blue-hover);
        }

        .notes-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .note-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 10px 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            transition: border-color 0.15s;
        }

        .note-card:hover {
            border-color: var(--border-color);
        }

        .note-text {
            font-size: 13px;
            line-height: 1.45;
            color: var(--text-primary);
            white-space: pre-wrap;
            word-break: break-word;
        }

        .note-actions {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-top: 1px solid var(--border-subtle);
            padding-top: 6px;
        }

        .btn-send-to-chat {
            background: transparent;
            border: none;
            color: var(--accent-blue);
            font-size: 11px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            padding: 2px 4px;
            border-radius: var(--radius-sm);
        }

        .btn-send-to-chat:hover {
            background: var(--accent-glow);
        }

        .btn-delete-note {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 2px 4px;
            border-radius: var(--radius-sm);
        }

        .btn-delete-note:hover {
            color: #ef4444;
        }

        .panel-chat {
            flex: 1;
            background: var(--bg-app);
            display: flex;
            flex-direction: column;
            position: relative;
        }

        .chat-top-status {
            padding: 8px 20px;
            background: var(--bg-panel);
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12px;
        }

    .agent-controls {
        display: flex;
        gap: 10px;
        align-items: center;
    }

    /* Active agent chip: colored to match that agent's home card */
    .agent-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        color: var(--agent-color, #4fc3f7);
        border: 1px solid var(--agent-color, #4fc3f7);
        background: color-mix(in srgb, var(--agent-color, #4fc3f7) 16%, transparent);
        white-space: nowrap;
    }

    .agent-chip[hidden] {
        display: none;
    }

    .agent-chip-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--agent-color, #4fc3f7);
        box-shadow: 0 0 6px var(--agent-color, #4fc3f7);
    }


        .agent-controls select {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 4px 8px;
            font-size: 12px;
            color: var(--text-primary);
            outline: none;
            cursor: pointer;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--text-secondary);
            font-size: 12px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
        }

        #chatLog {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        #chatLog::-webkit-scrollbar {
            width: 6px;
        }
        #chatLog::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 10px;
        }

        /* Message Cards */
        .msg {
            max-width: 850px;
            width: 100%;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .msg.user {
            align-items: flex-end;
        }

        .msg.user .msg-content-card {
            background: var(--user-msg-bg);
            border: 1px solid #334155;
            border-radius: 18px 18px 4px 18px;
            padding: 12px 18px;
            max-width: 80%;
        }

        .msg.ai, .msg.system {
            align-items: flex-start;
        }

        .msg.ai .msg-content-card {
            background: var(--bg-panel);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 16px;
            width: 100%;
        }

        .msg-label {
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .msg-body {
            font-size: 14px;
            line-height: 1.6;
            color: var(--text-primary);
            white-space: pre-wrap;
            word-break: break-word;
        }

        .msg-actions {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 10px;
            padding-top: 8px;
            border-top: 1px solid var(--border-subtle);
        }

        .btn-msg-action {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            padding: 4px 10px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 12px;
            transition: all 0.15s ease;
        }

        .btn-msg-action:hover {
            background: var(--bg-card-hover);
            color: var(--text-primary);
            border-color: var(--border-color);
        }

        .chat-foot {
            padding: 14px 24px 20px;
            background: var(--bg-app);
            max-width: 900px;
            width: 100%;
            margin: 0 auto;
        }

        .input-container {
            background: var(--bg-panel);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 10px 14px 10px 18px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25);
            transition: border-color 0.2s;
        }

        .input-container:focus-within {
            border-color: #3b82f6;
        }

        #chatInput {
            background: transparent;
            border: none;
            outline: none;
            resize: none;
            font-size: 14px;
            max-height: 140px;
            min-height: 38px;
            color: var(--text-primary);
            line-height: 1.5;
        }

        #chatInput::placeholder {
            color: var(--text-muted);
        }

        .input-bottom-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .input-hint {
            font-size: 11px;
            color: var(--text-muted);
        }

        #chatSend {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: var(--accent-blue);
            border: none;
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: background 0.15s, transform 0.1s;
        }

        #chatSend:hover {
            background: var(--accent-blue-hover);
        }

        #chatSend:active {
            transform: scale(0.94);
        }

        #chatSend:disabled {
            background: var(--bg-card);
            color: var(--text-muted);
            cursor: not-allowed;
        }

        .panel-test {
            width: 330px;
            min-width: 280px;
            border-left: 1px solid var(--border-color);
            background: var(--bg-panel);
            position: relative;
        }

        .test-content {
            padding: 16px;
            overflow-y: auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .test-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .test-func-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            text-align: center;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .test-func-card:hover {
            background: var(--bg-card-hover);
            border-color: var(--accent-blue);
            transform: translateY(-2px);
        }

        .test-func-card i {
            color: var(--accent-blue);
            width: 20px;
            height: 20px;
        }

        .test-func-card span {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .saved-chats-section {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .section-label {
            font-size: 12px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .btn-save-current {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 4px 8px;
            border-radius: var(--radius-sm);
            font-size: 11px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .btn-save-current:hover {
            background: var(--bg-card-hover);
        }

        .saved-chats-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .saved-chat-item {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 10px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            transition: background 0.15s;
        }

        .saved-chat-item:hover {
            background: var(--bg-card-hover);
        }

        .saved-chat-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
            overflow: hidden;
        }

        .saved-chat-title {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .saved-chat-date {
            font-size: 10px;
            color: var(--text-muted);
        }

        /* Toast Feedback */
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--accent-blue);
            color: #fff;
            padding: 8px 16px;
            border-radius: var(--radius-md);
            font-size: 12px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.2s ease;
            pointer-events: none;
            z-index: 100;
        }

        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }

        @media (max-width: 1024px) {
            .panel-test {
                position: absolute;
                right: 0;
                top: 0;
                bottom: 0;
                z-index: 15;
                transform: translateX(100%);
                box-shadow: -10px 0 30px rgba(0,0,0,0.5);
            }
            .panel-test.open {
                transform: translateX(0);
            }
        }

        @media (max-width: 768px) {
            .panel-sources {
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                z-index: 15;
                transform: translateX(-100%);
                box-shadow: 10px 0 30px rgba(0,0,0,0.5);
            }
            .panel-sources.open {
                transform: translateX(0);
            }
        }
    </style>
</head>
<body>

    <header class="app-header" data-pm-header>
        <div class="header-left">
            <button class="btn-header btn-icon-only" id="toggleSources" title="Toggle Sources & Notes">
                <i data-lucide="panel-left"></i>
            </button>
            <div class="agent-logo">
                <i data-lucide="bot" style="width:18px; height:18px;"></i>
            </div>
            <h1 class="app-title">AI Agent Creator</h1>
        </div>

        <div class="header-actions">
            <button class="btn-header" onclick="createNewAgent()">
                <i data-lucide="plus" style="width:14px; height:14px;"></i>
                New Agent
            </button>
            <button class="btn-header btn-icon-only" id="toggleTest" title="Toggle Test Panel">
                <i data-lucide="panel-right"></i>
            </button>
        </div>
    </header>

    <div class="app-container">

        <!-- LEFT PANEL: SOURCES & NOTES -->
        <aside class="panel panel-sources" id="panelSources">
            <div class="panel-header">
                <span class="panel-title">Sources & Notes</span>
                <i data-lucide="notebook" style="width:16px; height:16px; color: var(--text-muted);"></i>
            </div>
            <div class="sources-content">
                
                <!-- Add Note Input Section -->
                <div class="note-input-box">
                    <textarea id="newNoteInput" placeholder="Add a note or task list..."></textarea>
                    <button class="btn-add-note" onclick="addNote()">
                        <i data-lucide="plus" style="width:14px;"></i> Add Note
                    </button>
                </div>

                <!-- Notes / To-Do List Container -->
                <div class="notes-list" id="notesList">
                    <!-- Default initial note card -->
                    <div class="note-card">
                        <div class="note-text">Define agent system prompt with tool routing and file system permissions.</div>
                        <div class="note-actions">
                            <button class="btn-send-to-chat" onclick="sendNoteToChat(this)">
                                <i data-lucide="arrow-right-circle" style="width:13px;"></i> Send to Chat
                            </button>
                            <button class="btn-delete-note" onclick="deleteNote(this)" title="Delete note">
                                <i data-lucide="trash-2" style="width:13px;"></i>
                            </button>
                        </div>
                    </div>
                </div>

            </div>
        </aside>

        <!-- CENTER PANEL: CHAT WORKSPACE -->
        <main class="panel panel-chat">

            <!-- Dynamic Status Bar & Agent Selectors -->
            <div class="chat-top-status">
                <div class="agent-controls">
                    <span>Active Agent:</span>
                    <span id="activeAgentChip" class="agent-chip" hidden>
                        <span class="agent-chip-dot"></span>
                        <span id="activeAgentName">agent</span>
                    </span>
                    <select id="agentSelect" title="Agent selection">
                        <option value="builder">Agent Builder v1</option>
                        <option value="code_executor">Code Executor</option>
                    </select>
                    <select id="modelSelect" title="Model selection">
                        <option value="gemini_flash">Gemini 3 Flash</option>
                        <option value="gemini_pro">Gemini Pro</option>
                    </select>
                </div>
                <div class="status-badge">
                    <span id="statusDot" class="status-dot"></span>
                    <span id="chatStatus">Connected</span>
                </div>
            </div>

            <!-- Main Chat Conversation Feed (populated by chat.js) -->
            <div id="chatLog"></div>

            <!-- Chat Footer & Input Box -->
            <footer class="chat-foot">
                <form id="chatForm">
                    <div class="input-container">
                        <textarea 
                            id="chatInput" 
                            placeholder="Message AI Agent Creator..." 
                            rows="1"
                            autocomplete="off"
                        ></textarea>
                        
                        <div class="input-bottom-row">
                            <span class="input-hint">Enter to send · Shift + Enter for newline</span>
                            <button id="chatSend" type="submit" aria-label="Send message">
                                <i data-lucide="arrow-up" style="width:18px; height:18px;"></i>
                            </button>
                        </div>
                    </div>
                </form>
            </footer>

        </main>

        <!-- RIGHT PANEL: TEST & SAVED CHATS -->
        <aside class="panel panel-test" id="panelTest">
            <div class="panel-header">
                <span class="panel-title">Test</span>
                <i data-lucide="x" style="width:16px; height:16px; color: var(--text-muted); cursor:pointer;" id="closeTest"></i>
            </div>
            <div class="test-content">

                <!-- Interactive Function Buttons Grid -->
                <div class="test-grid">
                    <div class="test-func-card" onclick="runTestFunc('Run Test Suite')">
                        <i data-lucide="play-circle"></i>
                        <span>Run Test Suite</span>
                    </div>
                    <div class="test-func-card" onclick="runTestFunc('Debug Agent')">
                        <i data-lucide="bug"></i>
                        <span>Debug Agent</span>
                    </div>
                    <div class="test-func-card" onclick="runTestFunc('Prompt Inspector')">
                        <i data-lucide="terminal"></i>
                        <span>Prompt Inspector</span>
                    </div>
                    <div class="test-func-card" onclick="runTestFunc('Output Evaluator')">
                        <i data-lucide="check-square"></i>
                        <span>Output Evaluator</span>
                    </div>
                    <div class="test-func-card" onclick="runTestFunc('Benchmark Performance')">
                        <i data-lucide="gauge"></i>
                        <span>Benchmark</span>
                    </div>
                    <div class="test-func-card" onclick="runTestFunc('View API Logs')">
                        <i data-lucide="file-code"></i>
                        <span>API Logs</span>
                    </div>
                    <div class="test-func-card" onclick="wipeChat()" title="Clear the chat history">
                        <i data-lucide="trash-2"></i>
                        <span>Wipe Chat</span>
                    </div>
                </div>

                <!-- Saved Chats Section -->
                <div class="saved-chats-section">
                    <div class="section-label">
                        <span>Saved Chats</span>
                        <button class="btn-save-current" onclick="saveCurrentChat()">
                            <i data-lucide="bookmark" style="width:12px;"></i> Save Session
                        </button>
                    </div>

                    <div class="saved-chats-list" id="savedChatsList">
                        <div class="saved-chat-item" onclick="loadSavedChat('Agent Blueprint Draft')">
                            <div class="saved-chat-info">
                                <div class="saved-chat-title">Agent Blueprint Draft</div>
                                <div class="saved-chat-date">Saved 2 hours ago</div>
                            </div>
                            <i data-lucide="chevron-right" style="width:14px; color:var(--text-muted);"></i>
                        </div>
                    </div>
                </div>

            </div>
        </aside>

    </div>

    <!-- Dynamic Toast Feedback Banner -->
    <div id="toast" class="toast">Action completed!</div>

    <!-- Backend Module Integrations -->
    <script type="module" src="/static/js/chat.js"></script>

    <script>
        // Initialize Icons
        lucide.createIcons();

        // Toast Helper
        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        }

        // Add Note to Left Panel List
        function addNote() {
            const input = document.getElementById('newNoteInput');
            const text = input.value.trim();
            if (!text) return;

            const notesList = document.getElementById('notesList');
            const card = document.createElement('div');
            card.className = 'note-card';
            card.innerHTML = `
                <div class="note-text">${escapeHtml(text)}</div>
                <div class="note-actions">
                    <button class="btn-send-to-chat" onclick="sendNoteToChat(this)">
                        <i data-lucide="arrow-right-circle" style="width:13px;"></i> Send to Chat
                    </button>
                    <button class="btn-delete-note" onclick="deleteNote(this)" title="Delete note">
                        <i data-lucide="trash-2" style="width:13px;"></i>
                    </button>
                </div>
            `;
            notesList.prepend(card);
            input.value = '';
            lucide.createIcons();
            showToast('Note added to list');
        }

        // Send Note Directly to Chat Box
        function sendNoteToChat(btn) {
            const noteText = btn.closest('.note-card').querySelector('.note-text').innerText;
            const chatInput = document.getElementById('chatInput');
            
            chatInput.value = noteText;
            chatInput.focus();
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
            showToast('Note populated into chat input');
        }

        // Delete Note Item
        function deleteNote(btn) {
            btn.closest('.note-card').remove();
            showToast('Note removed');
        }

        // Copy Message Content to Clipboard
        function copyMsg(btn) {
            const bodyText = btn.closest('.msg-content-card').querySelector('.msg-body').innerText;
            
            // execCommand copy implementation for frame safety
            const tempArea = document.createElement('textarea');
            tempArea.value = bodyText;
            document.body.appendChild(tempArea);
            tempArea.select();
            document.execCommand('copy');
            document.body.removeChild(tempArea);

            showToast('Copied to clipboard!');
        }

        // Placeholder Action Handlers
        function msgAction(actionName) {
            showToast(`${actionName} action saved`);
        }

        function runTestFunc(funcName) {
            showToast(`Triggered: ${funcName}`);
        }

        function createNewAgent() {
            if (typeof scaffoldNewAgent === 'function') {
                scaffoldNewAgent();
            } else {
                showToast('Agent creator not ready yet');
            }
        }

        // Save & Load Chat Functions
        function saveCurrentChat() {
            const savedList = document.getElementById('savedChatsList');
            const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            const item = document.createElement('div');
            item.className = 'saved-chat-item';
            item.onclick = () => loadSavedChat(`Saved Session (${now})`);
            item.innerHTML = `
                <div class="saved-chat-info">
                    <div class="saved-chat-title">Saved Session (${now})</div>
                    <div class="saved-chat-date">Just now</div>
                </div>
                <i data-lucide="chevron-right" style="width:14px; color:var(--text-muted);"></i>
            `;
            savedList.prepend(item);
            lucide.createIcons();
            showToast('Current chat session saved!');
        }

        function loadSavedChat(title) {
            showToast(`Loaded: ${title}`);
        }

        // Textarea Auto-growth and Keyboard handling
        const chatInput = document.getElementById("chatInput");
        const chatForm = document.getElementById("chatForm");
        const chatLog = document.getElementById("chatLog");

        if (chatInput) {
            chatInput.addEventListener("input", () => {
                chatInput.style.height = "auto";
                chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + "px";
            });

            chatInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    if (chatForm) {
                        chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                    }
                }
            });
        }

        // Form Submit Handler
        if (chatForm) {
            chatForm.addEventListener("submit", (e) => {
                e.preventDefault();
                const text = chatInput.value.trim();
                if (!text) return;

                appendMessage("user", text);
                chatInput.value = "";
                chatInput.style.height = "auto";

                // Simulated AI response (if external backend module isn't active)
                setTimeout(() => {
                    appendMessage("ai", `Received agent instructions:\n"${text}"\nReady for function testing.`);
                }, 700);
            });
        }

        function appendMessage(role, text) {
            const msgDiv = document.createElement("div");
            msgDiv.className = `msg ${role}`;

            if (role === "user") {
                msgDiv.innerHTML = `
                    <div class="msg-content-card">
                        <div class="msg-body">${escapeHtml(text)}</div>
                    </div>
                `;
            } else {
                msgDiv.innerHTML = `
                    <div class="msg-content-card">
                        <span class="msg-label">AI AGENT CREATOR</span>
                        <div class="msg-body">${escapeHtml(text)}</div>
                        <div class="msg-actions">
                            <button class="btn-msg-action" onclick="copyMsg(this)">
                                <i data-lucide="copy" style="width:13px;"></i> Copy
                            </button>
                            <button class="btn-msg-action" onclick="msgAction('Save')">
                                <i data-lucide="bookmark" style="width:13px;"></i> Save
                            </button>
                            <button class="btn-msg-action" onclick="msgAction('Fork')">
                                <i data-lucide="git-fork" style="width:13px;"></i> Fork
                            </button>
                        </div>
                    </div>
                `;
            }

            chatLog.appendChild(msgDiv);
            chatLog.scrollTop = chatLog.scrollHeight;
            lucide.createIcons();
        }

        function escapeHtml(str) {
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        // Sidebar Toggles
        document.getElementById("toggleSources")?.addEventListener("click", () => {
            document.getElementById("panelSources").classList.toggle("open");
        });

        document.getElementById("toggleTest")?.addEventListener("click", () => {
            document.getElementById("panelTest").classList.toggle("open");
        });

        document.getElementById("closeTest")?.addEventListener("click", () => {
            document.getElementById("panelTest").classList.remove("open");
        });
    </script>
</body>
</html>
```

---

<!-- ==== 21/44 : interface/static/editor.html ==== -->

### interface/static/editor.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Manager Editor</title>

    <style>
        * {
            box-sizing: border-box;
        }

        html, body {
            margin: 0;
            padding: 0;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            font-family: Arial, sans-serif;
            background: #1e1e1e;
            color: #ffffff;
        }

        .topbar {
            height: 52px;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 12px;
            background: #252526;
            border-bottom: 1px solid #3f3f46;
        }

        .title {
            font-weight: bold;
            margin-right: 12px;
        }

        /* Home for this page's own tools; the nav keeps the far right. */
        .topbar-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .spacer {
            flex: 1;
        }

        button {
            border: 1px solid #555;
            background: #333;
            color: #fff;
            padding: 6px 10px;
            border-radius: 4px;
            cursor: pointer;
        }

        button:hover {
            background: #444;
        }

        button.primary {
            background: #0e639c;
            border-color: #1177bb;
        }

        button.danger {
            background: #7f1d1d;
        }

        .workspace {
            display: flex;
            height: calc(100vh - 78px);
            width: 100%;
        }

        .sidebar {
            width: 250px;
            min-width: 180px;
            background: #252526;
            border-right: 1px solid #3f3f46;
            display: flex;
            flex-direction: column;
        }

        .sidebar-header {
            padding: 10px;
            border-bottom: 1px solid #3f3f46;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .resize-handle {
            width: 4px;
            cursor: col-resize;
            background: transparent;
            transition: background 0.2s;
        }

        .resize-handle:hover {
            background: #0e639c;
        }

        .tree {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }

        .tree-item {
            user-select: none;
            cursor: pointer;
            padding: 4px 6px;
            border-radius: 3px;
        }

        .tree-item:hover {
            background: #2a2d2e;
        }

        .tree-item.selected {
            background: #094771;
        }

        .tree-item.folder {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .tree-item.folder .toggle {
            display: inline-block;
            width: 12px;
            font-size: 11px;
            color: #bbb;
            text-align: center;
            flex-shrink: 0;
        }

        .tree-item.folder .label {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* ---- Browser root folders ---- */
        .tree-item.root {
            font-weight: bold;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
            color: #9ca3af;
            margin-top: 4px;
        }

        .tree-item.root.active {
            color: #e5e7eb;
        }

        .tree-item.root.readonly .label {
            color: #6b7280;
        }

        .root-lock {
            margin-left: auto;
            font-size: 11px;
            opacity: 0.7;
        }

        .tree-item.readonly {
            opacity: 0.6;
        }

        #readOnlyIndicator {
            color: #d97706;
            font-size: 11px;
            margin-left: 8px;
        }

        .children {
            margin-left: 12px;
        }

        .children.collapsed {
            display: none;
        }

        .editor-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
            height: 100%;
        }

        .filebar {
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 12px;
            background: #1f1f1f;
            border-bottom: 1px solid #3f3f46;
        }

        #unsavedIndicator {
            color: #e2c08d;
            font-size: 12px;
            font-weight: bold;
            margin-left: 8px;
        }

        #editor {
            flex: 1;
            width: 100%;
            height: 100%;
            background: #1e1e1e;
        }

        .statusbar {
            height: 26px;
            display: flex;
            align-items: center;
            padding: 0 10px;
            background: #007acc;
            color: white;
            font-size: 12px;
        }

        .status-message {
            flex: 1;
        }

        /* ---------------------------------------------------
           AGENT / PIPELINE SIDEBAR
           --------------------------------------------------- */

        .agent-sidebar {
            width: 300px;
            min-width: 240px;
            background: #1f1f1f;
            border-left: 1px solid #3f3f46;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }

        .agent-sidebar.hidden {
            display: none;
        }

        .agent-section {
            padding: 10px;
            border-bottom: 1px solid #3f3f46;
        }

        .agent-section-title {
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 12px;
            color: #bbb;
        }

        .agent-sidebar textarea {
            width: 100%;
            background: #2a2d2e;
            color: #fff;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            padding: 6px;
            font-family: inherit;
            font-size: 12px;
            resize: vertical;
            box-sizing: border-box;
        }

        .agent-sidebar button {
            margin: 4px 2px;
            font-size: 12px;
        }

        .agent-list {
            max-height: 190px;
            overflow-y: auto;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            margin-bottom: 6px;
            padding: 6px;
            font-size: 12px;
        }

        .agent-option {
            display: flex;
            gap: 6px;
            align-items: center;
            padding: 2px 0;
            font-size: 12px;
            cursor: pointer;
        }

        .queue-list {
            max-height: 150px;
            overflow-y: auto;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            margin-bottom: 6px;
            padding: 6px;
            font-size: 12px;
        }

        .queue-item {
            display: flex;
            gap: 4px;
            align-items: center;
            font-size: 12px;
            padding: 2px 0;
        }

        .queue-item .qidx {
            color: #70b7ed;
            min-width: 18px;
        }

        .queue-item button {
            margin: 0;
            padding: 0 6px;
            font-size: 11px;
        }

        .result-box {
            background: #181b24;
            border: 1px solid #292d38;
            border-radius: 6px;
            padding: 8px;
            margin-top: 8px;
            font-size: 12px;
        }

        .step-card-ok {
            color: #72b784;
            font-weight: bold;
        }

        .result-text {
            white-space: pre-wrap;
            word-break: break-word;
            color: #dfe2e8;
            margin-top: 4px;
        }
    </style>

    <!-- Monaco Loader CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js"></script>
</head>
<body>

<div class="topbar" data-pm-header>
    <div class="title">Project Manager</div>

    <div class="topbar-actions" id="pageActions">
        <button id="saveBtn" class="primary" type="button">Save</button>
        <button id="newFileBtn" type="button">+ File</button>
        <button id="newFolderBtn" type="button">+ Folder</button>
        <button id="renameBtn" type="button">Rename</button>
        <button id="deleteBtn" class="danger" type="button">Delete</button>
        <button id="refreshBtn" type="button">Refresh</button>
        <button id="agentCreateBtn" title="Scaffold workspace/agents/&lt;name&gt;/agent.json + agent.md">+ Agent</button>
        <button id="runAgentBtn" title="Run the currently open agent definition">Run Agent</button>
        <button id="pipelineBtn" title="Toggle the pipeline panel">Pipeline</button>
    </div>

    <div class="spacer"></div>
</div>

<div class="workspace">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span>FOLDERS</span>
        </div>
        <div id="tree" class="tree">Loading...</div>
    </div>
    
    <div class="resize-handle" id="resizeHandle"></div>

    <div class="editor-area">
        <div class="filebar">
            <div>
                <span id="currentFile">No file selected</span>
                <span id="unsavedIndicator"></span>
            <span id="readOnlyIndicator"></span>
            </div>
            <div id="language">plaintext</div>
        </div>
        <div id="editor"></div>
    </div>

    <div id="agentPanel" class="agent-sidebar">
        <div class="agent-section">
            <div class="agent-section-title">RUN AGENT</div>
            <div id="runAgentHint" style="font-size:12px;color:#8991a2;margin-bottom:6px;">
                Open an agents/&lt;id&gt;/agent.json or agent.md to run it.
            </div>
            <textarea id="agentPrompt" rows="3" placeholder="Instruction for the agent…"></textarea>
            <button id="runAgentBtnRun" class="primary">Run Agent</button>
            <div id="agentResult"></div>
        </div>

        <div class="agent-section">
            <div class="agent-section-title">PIPELINE · CASCADE</div>
            <div style="font-size:12px;color:#8991a2;margin-bottom:6px;">
                Tick multiple agents, order them, send one message - each agent
                passes its reply to the next.
            </div>
            <div id="pipelineAgents" class="agent-list">Loading agents…</div>
            <div id="pipelineQueue" class="queue-list">Queue empty.</div>
            <button id="pipelineClearBtn">Clear queue</button>
            <select id="modelBox" title="Model override" style="width:100%;margin:4px 0;background:#2a2d2e;color:#fff;border:1px solid #3f3f46;border-radius:4px;padding:4px;"></select>
            <textarea id="pipelinePrompt" rows="3" placeholder="Idea / message to cascade through the queue…"></textarea>
            <button id="pipelineRunBtn" class="primary">Run Pipeline</button>
            <div id="pipelineResult"></div>
        </div>
    </div>
</div>

<div class="statusbar">
    <div id="statusMessage" class="status-message">Initializing...</div>
</div>

<script type="module" src="/static/js/main.js"></script>

</body>
</html>
```

---

<!-- ==== 22/44 : interface/static/home.html ==== -->

### interface/static/home.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Manager</title>

    <style>
        * {
            box-sizing: border-box;
        }

        html, body {
            margin: 0;
            padding: 0;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            font-family: Arial, sans-serif;
            background: #1e1e1e;
            color: #ffffff;
        }

        .topbar {
            height: 52px;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 12px;
            background: #252526;
            border-bottom: 1px solid #3f3f46;
        }

        .title {
            font-weight: bold;
            margin-right: 4px;
        }

        #projectName {
            color: #4fc3f7;
            margin-right: 12px;
            font-weight: bold;
        }

        .spacer {
            flex: 1;
        }

        /* Home for this page's own tools; empty on pages that have none. */
        .topbar-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        button {
            border: 1px solid #555;
            background: #333;
            color: #fff;
            padding: 6px 10px;
            border-radius: 4px;
            cursor: pointer;
        }

        button:hover {
            background: #444;
        }

        button.primary {
            background: #0e639c;
            border-color: #1177bb;
        }

        button.danger {
            background: #7f1d1d;
        }

        .workspace {
            display: flex;
            height: calc(100vh - 78px);
            width: 100%;
        }

        .sidebar {
            width: 280px;
            min-width: 180px;
            background: #252526;
            border-right: 1px solid #3f3f46;
            display: flex;
            flex-direction: column;
        }

        .sidebar-header {
            padding: 10px;
            border-bottom: 1px solid #3f3f46;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .resize-handle {
            width: 4px;
            cursor: col-resize;
            background: transparent;
            transition: background 0.2s;
        }

        .resize-handle:hover {
            background: #0e639c;
        }

        .tree {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }

        /* ---- Browser root folders ---- */
        .tree-item.root {
            font-weight: bold;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
            color: #9ca3af;
            margin-top: 4px;
        }

        .tree-item.root.active {
            color: #e5e7eb;
        }

        .tree-item.root.readonly .label {
            color: #6b7280;
        }

        .root-lock {
            margin-left: auto;
            font-size: 11px;
            opacity: 0.7;
        }

        .tree-item.readonly {
            opacity: 0.6;
        }

        .tree-item {
            user-select: none;
            cursor: pointer;
            padding: 4px 6px;
            border-radius: 3px;
        }

        .tree-item:hover {
            background: #2a2d2e;
        }

        .tree-item.selected {
            background: #094771;
        }

        .tree-item.folder {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .tree-item.folder .toggle {
            display: inline-block;
            width: 12px;
            font-size: 11px;
            color: #bbb;
            text-align: center;
            flex-shrink: 0;
        }

        .tree-item.folder .label {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .children {
            margin-left: 12px;
        }

        .children.collapsed {
            display: none;
        }

        /* ---- Home landing panel (the editor lives on editor.html) ---- */
        .home-panel {
            flex: 1;
            min-width: 0;
            height: 100%;
            overflow-y: auto;
            padding: 40px 32px 48px;
            background: #1e1e1e;
        }

        .home-inner {
            max-width: 1080px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .home-title {
            margin: 0;
            font-size: 34px;
            font-weight: bold;
            letter-spacing: 1px;
            color: #ffffff;
        }

        .home-subtitle {
            margin: 8px 0 28px;
            font-size: 13px;
            color: #9ca3af;
            text-align: center;
        }

        .agent-cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
            gap: 14px;
            width: 100%;
        }

        .agent-card {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
            text-align: left;
            padding: 14px;
            background: #252526;
            border: 1px solid #3f3f46;
            border-left: 4px solid var(--agent-color, #4fc3f7);
            border-radius: 6px;
            cursor: pointer;
            color: #fff;
        }

        .agent-card:hover {
            background: color-mix(in srgb, var(--agent-color, #4fc3f7) 14%, #252526);
            border-color: var(--agent-color, #4fc3f7);
        }

        .agent-card:focus-visible {
            outline: 2px solid var(--agent-color, #4fc3f7);
            outline-offset: 2px;
        }

        .agent-card-head {
            display: flex;
            align-items: center;
            gap: 8px;
            width: 100%;
        }

        .agent-swatch {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            flex-shrink: 0;
            background: var(--agent-color, #4fc3f7);
            box-shadow: 0 0 6px var(--agent-color, #4fc3f7);
        }

        .agent-card-name {
            font-weight: bold;
            font-size: 14px;
        }

        .agent-card-badges {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }

        .agent-badge {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 2px 6px;
            border-radius: 10px;
            border: 1px solid #4b4b4b;
            color: #cbd5e1;
        }

        .agent-badge.mode {
            border-color: var(--agent-color, #4fc3f7);
            color: var(--agent-color, #4fc3f7);
        }

        .agent-card-desc {
            margin: 0;
            font-size: 12px;
            line-height: 1.5;
            color: #b6b6b6;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .agent-cards-empty {
            grid-column: 1 / -1;
            color: #9ca3af;
            font-size: 13px;
            text-align: center;
            padding: 24px 0;
        }

        .statusbar {
            height: 26px;
            display: flex;
            align-items: center;
            padding: 0 10px;
            background: #007acc;
            color: white;
            font-size: 12px;
        }

        .status-message {
            flex: 1;
        }
    </style>
</head>
<body>

<div class="topbar" data-pm-header>
    <div class="title">Project Manager</div>
    <span id="projectName">.</span>

    <!-- Home has no page-specific tools yet. Buttons that belong to
         this page go here so the nav keeps its place at the far right. -->
    <div class="topbar-actions" id="pageActions"></div>

    <div class="spacer"></div>
</div>


<div class="workspace">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span>FOLDERS</span>
        </div>

        <div id="tree" class="tree">Loading...</div>
    </div>

    <div class="resize-handle" id="resizeHandle"></div>

    <div class="home-panel">
        <div class="home-inner">
            <h1 class="home-title">Home</h1>
            <p class="home-subtitle">Choose an agent to start a conversation.</p>
            <div id="agentCards" class="agent-cards">Loading agents...</div>
        </div>
    </div>
</div>

<div class="statusbar">
    <div id="statusMessage" class="status-message">Initializing...</div>
</div>

<script type="module" src="/static/js/main.js"></script>

</body>
</html>
```

---

<!-- ==== 23/44 : interface/static/index.html ==== -->

### interface/static/index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Manager Dashboard</title>

    <style>
        * {
            box-sizing: border-box;
        }

        html, body {
            margin: 0;
            padding: 0;
            width: 100vw;
            height: 100vh;
            font-family: Arial, sans-serif;
            background: #1e1e1e;
            color: #ffffff;
        }

        .topbar {
            height: 48px;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 12px;
            background: #252526;
            border-bottom: 1px solid #3f3f46;
        }

        .title {
            font-weight: bold;
            margin-right: 12px;
        }

        button {
            border: 1px solid #555;
            background: #333;
            color: #fff;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
        }

        button:hover {
            background: #444;
        }

        button.primary {
            background: #0e639c;
            border-color: #1177bb;
        }

        .container {
            padding: 24px;
            max-width: 1200px;
            margin: 0 auto;
        }

        .actions {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
        }

        .card {
            background: #252526;
            border: 1px solid #3f3f46;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 20px;
        }

        .card h2 {
            margin-top: 0;
            margin-bottom: 12px;
            font-size: 18px;
        }

        .tree-item {
            user-select: none;
            cursor: pointer;
            padding: 6px 8px;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .tree-item.folder {
            cursor: pointer;
        }

        .tree-item.folder .toggle {
            display: inline-block;
            width: 12px;
            font-size: 11px;
            color: #bbb;
            text-align: center;
            flex-shrink: 0;
        }

        .tree-item:hover {
            background: #2a2d2e;
        }

        /* ---- Browser root folders ---- */
        .tree-item.root {
            font-weight: bold;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
            color: #9ca3af;
            margin-top: 6px;
        }

        .tree-item.root.readonly .label {
            color: #6b7280;
        }

        .root-lock {
            font-size: 11px;
            opacity: 0.7;
        }

        .tree-item.readonly {
            opacity: 0.6;
        }

        .children {
            margin-left: 16px;
        }

        .children.collapsed {
            display: none;
        }

        .statusbar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 26px;
            display: flex;
            align-items: center;
            padding: 0 10px;
            background: #007acc;
            color: white;
            font-size: 12px;
        }
    </style>
</head>
<body>

<div class="topbar">
    <div class="title">Project Manager Dashboard</div>
    <button class="primary" onclick="openEditor()">Editor</button>
    <button onclick="openEditorPopup()">Editor (Popup)</button>
    <button onclick="refreshProject()">Refresh</button>
</div>

<div class="container">
    <div class="actions">
        <button class="primary" onclick="openEditor()">Open Full Editor</button>
        <button onclick="openEditorPopup()">Launch Editor Window</button>
        <button onclick="submitCreateFilePrompt()">+ New File</button>
        <button onclick="submitCreateFolderPrompt()">+ New Folder</button>
    </div>

    <div class="card">
        <h2>Project Workspace</h2>
        <div id="projectTree">Loading files...</div>
    </div>
</div>

<div class="statusbar">
    <div id="statusMessage">Ready</div>
</div>

<script type="module">
import API from '/static/js/api.js';

let roots = {};

async function loadProject() {
  setStatus('Loading project...');
  try {
    const data = await API.project();
    roots = {};
    for (const node of data.filesystem || []) {
      roots[node.name] = node.writable !== false;
    }
    renderTree(data.filesystem || []);
    setStatus('Project loaded');
  } catch (err) {
    setStatus('Error: ' + err.message);
  }
}

function renderTree(items) {
  const container = document.getElementById('projectTree');
  container.innerHTML = '';
  renderItems(items, container, 0);
}

function renderItems(items, container, depth) {
  items.forEach(item => {
    const div = document.createElement('div');
    div.className = 'tree-item';
    if (item.type === 'directory') {
      div.classList.add('folder');
      div.dataset.path = item.path;
      const isRoot = depth === 0 && item.root;
      if (isRoot) {
        div.classList.add('root');
        if (item.writable === false) div.classList.add('readonly');
      }
      const toggle = document.createElement('span');
      toggle.className = 'toggle';
      toggle.textContent = '+';
      const label = document.createElement('span');
      label.textContent = (isRoot ? '🗂 ' : '📁 ') + item.name;
      label.style.flex = '1';
      label.style.marginLeft = '4px';
      div.appendChild(toggle);
      div.appendChild(label);
      if (isRoot && item.writable === false) {
        const lock = document.createElement('span');
        lock.className = 'root-lock';
        lock.textContent = '🔒';
        lock.title = 'Read-only';
        div.appendChild(lock);
      }
      div.onclick = (e) => {
        e.stopPropagation();
        toggleFolder(div);
      };
      container.appendChild(div);
      if (item.children && item.children.length) {
        const childrenContainer = document.createElement('div');
        childrenContainer.className = 'children collapsed';
        container.appendChild(childrenContainer);
        renderItems(item.children, childrenContainer, depth + 1);
      }
    } else {
      if (item.editable === false) {
        div.classList.add('readonly');
        div.title = 'Read-only';
      }
      const label = document.createElement('span');
      label.textContent = getFileIcon(item.name) + ' ' + item.name;
      div.appendChild(label);
      const btnGroup = document.createElement('div');
      const editBtn = document.createElement('button');
      editBtn.textContent = 'Edit';
      editBtn.onclick = (e) => { e.stopPropagation(); openEditor(item.path); };
      const popupBtn = document.createElement('button');
      popupBtn.textContent = 'Popup';
      popupBtn.style.marginLeft = '4px';
      popupBtn.onclick = (e) => { e.stopPropagation(); openEditorPopup(item.path); };
      btnGroup.appendChild(editBtn);
      btnGroup.appendChild(popupBtn);
      div.appendChild(btnGroup);
      container.appendChild(div);
    }
  });
}

function getFileIcon(name) {
  const ext = name.split('.').pop().toLowerCase();
  const icons = {
    py: '🐍',
    html: '🌐', htm: '🌐',
    css: '🎨',
    js: '🟨', mjs: '🟨', jsx: '🟨',
    ts: '🔷', tsx: '🔷',
    json: '📋',
    md: '📝',
    sql: '🗄️',
    xml: '🧾',
    sh: '⌨️', bat: '⌨️', ps1: '⌨️',
    yaml: '⚙️', yml: '⚙️', toml: '⚙️', ini: '⚙️', cfg: '⚙️', env: '⚙️',
    txt: '📄', csv: '📄'
  };
  return icons[ext] || '📄';
}

function toggleFolder(div) {
  const toggle = div.querySelector('.toggle');
  if (toggle) {
    toggle.classList.toggle('expanded');
    toggle.textContent = toggle.classList.contains('expanded') ? '−' : '+';
  }
  const children = div.nextElementSibling;
  if (children && children.classList.contains('children')) {
    children.classList.toggle('collapsed');
  }
}

async function submitCreateFilePrompt() {
  if (!roots[activeRoot()]) {
    alert(activeRoot() + ' is read-only.');
    return;
  }
  const path = prompt('Enter file path/name:', activeRoot() + '/');
  if (!path) return;
  if (!isWritablePath(path)) return;
  try {
    await API.fileCreate(path, '');
    await loadProject();
    openEditor(path);
  } catch (err) {
    alert(err.message);
  }
}

async function submitCreateFolderPrompt() {
  if (!roots[activeRoot()]) {
    alert(activeRoot() + ' is read-only.');
    return;
  }
  const path = prompt('Enter folder path:', activeRoot() + '/');
  if (!path) return;
  if (!isWritablePath(path)) return;
  try {
    await API.directoryCreate(path);
    await loadProject();
  } catch (err) {
    alert(err.message);
  }
}

function activeRoot() {
  return Object.keys(roots)[0] ?? '';
}

function isWritablePath(path) {
  const head = String(path).split('/')[0];
  if (head in roots && roots[head] === false) {
    alert(head + ' is read-only.');
    return false;
  }
  return true;
}

function openEditor(filePath) {
  let url = '/editor';
  if (filePath) url += '?path=' + encodeURIComponent(filePath);
  const head = filePath ? filePath.split('/')[0] : '';
  if (head) url += '&root=' + encodeURIComponent(head);
  window.location.href = url;
}

function openEditorPopup(filePath) {
  let url = '/editor';
  if (filePath) url += '?path=' + encodeURIComponent(filePath);
  const head = filePath ? filePath.split('/')[0] : '';
  if (head) url += '&root=' + encodeURIComponent(head);
  const width = 1200; const height = 800;
  const left = (window.screen.width - width) / 2;
  const top = (window.screen.height - height) / 2;
  window.open(url, 'ProjectManagerEditorPopup', `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no`);
}

function refreshProject() {
  loadProject();
}

function setStatus(msg) {
  document.getElementById('statusMessage').textContent = msg;
}

window.openEditor = openEditor;
window.openEditorPopup = openEditorPopup;
window.refreshProject = refreshProject;
window.submitCreateFilePrompt = submitCreateFilePrompt;
window.submitCreateFolderPrompt = submitCreateFolderPrompt;

loadProject();
</script>

</body>
</html>
```

---

<!-- ==== 24/44 : interface/static/js/agentCards.js ==== -->

### interface/static/js/agentCards.js

```javascript
/* Agent cards module

   Renders one card per available agent on the home page. Each card
   carries the agent's stable color (see agentColors.js) so the same
   agent is recognizable in the chat header. */

import API from './api.js';
import { assignAgentColors } from './agentColors.js';

function openChatWithAgent(agentId) {
  const width = 1100;
  const height = 740;
  const left = Math.max(0, (window.screen.width - width) / 2);
  const top = Math.max(0, (window.screen.height - height) / 2);
  const target = agentId
    ? `/chat?agent=${encodeURIComponent(agentId)}`
    : '/chat';
  window.open(
    target,
    'ProjectManagerChat',
    `width=${width},height=${height},top=${top},left=${left},` +
    'resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no'
  );
}

function buildCard(agent, color) {
  const card = document.createElement('button');
  card.type = 'button';
  card.className = 'agent-card';
  card.dataset.agent = agent.id;
  card.style.setProperty('--agent-color', color);
  card.title = 'Chat with ' + agent.name;

  const head = document.createElement('div');
  head.className = 'agent-card-head';

  const swatch = document.createElement('span');
  swatch.className = 'agent-swatch';

  const name = document.createElement('span');
  name.className = 'agent-card-name';
  name.textContent = agent.name;

  head.append(swatch, name);

  const badges = document.createElement('div');
  badges.className = 'agent-card-badges';

  const sourceBadge = document.createElement('span');
  sourceBadge.className = 'agent-badge source';
  sourceBadge.textContent = agent.source === 'workspace' ? 'workspace' : 'library';
  badges.appendChild(sourceBadge);

  if (agent.mode) {
    const modeBadge = document.createElement('span');
    modeBadge.className = 'agent-badge mode';
    modeBadge.textContent = agent.mode;
    badges.appendChild(modeBadge);
  }

  const description = document.createElement('p');
  description.className = 'agent-card-desc';
  description.textContent = agent.description || 'No description provided.';

  card.append(head, badges, description);
  return card;
}

function initAgentCards(options = {}) {
  const host = options.host || document.getElementById('agentCards');
  if (!host) return Promise.resolve([]);

  const onOpen = options.onOpen || openChatWithAgent;

  return API.agents().then((data) => {
    const agents = data.agents || [];
    host.innerHTML = '';

    if (!agents.length) {
      const empty = document.createElement('p');
      empty.className = 'agent-cards-empty';
      empty.textContent = 'No agents found. Create one from the editor to get started.';
      host.appendChild(empty);
      return agents;
    }

    const colors = assignAgentColors(agents);
    for (const agent of agents) {
      const card = buildCard(agent, colors.get(agent.id));
      card.addEventListener('click', () => onOpen(agent.id));
      host.appendChild(card);
    }
    return agents;
  });
}

export { initAgentCards, openChatWithAgent };
```

---

<!-- ==== 25/44 : interface/static/js/agentColors.js ==== -->

### interface/static/js/agentColors.js

```javascript
/* Stable per-agent color module

   An agent must show the same color everywhere it appears (home
   card, chat header chip), with nothing persisted between pages.
   Colors are therefore derived from the agent id itself via a
   stable hash, so both pages agree without coordinating.

   The palette is hand-picked to stay legible on both dark themes
   in use: the home page (#1e1e1e) and chat (#131822). */

const AGENT_PALETTE = [
  '#4fc3f7', // sky
  '#81c784', // green
  '#ffb74d', // amber
  '#ba68c8', // violet
  '#f06292', // rose
  '#4dd0e1', // cyan
  '#aed581', // lime
  '#ff8a65', // coral
  '#9575cd', // indigo
  '#ffd54f', // yellow
  '#4db6ac', // teal
  '#e57373'  // red
];

/* FNV-1a: cheap, stable across page loads, and well spread for
   short ids like "rag_assistant". */
function hashId(id) {
  let hash = 0x811c9dc5;
  const text = String(id == null ? '' : id);
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash >>> 0;
}

function agentColor(id) {
  return AGENT_PALETTE[hashId(id) % AGENT_PALETTE.length];
}

/* Hash collisions give two agents the same color. Nudging later
   agents to the next free slot keeps every visible card distinct.
   The result stays deterministic for a given list order, so the
   home page and the chat page always agree.

   Once every slot is taken the search gives up and reuses the
   hashed color, so a list longer than the palette degrades to
   shared colors instead of spinning forever. */
function assignAgentColors(agents) {
  const list = Array.isArray(agents) ? agents : [];
  const taken = new Set();
  const colors = new Map();
  for (const agent of list) {
    const id = agent && agent.id;
    if (id == null || colors.has(id)) continue;
    const start = hashId(id) % AGENT_PALETTE.length;
    let slot = start;
    for (let step = 0; step < AGENT_PALETTE.length; step += 1) {
      if (!taken.has(slot)) break;
      slot = (slot + 1) % AGENT_PALETTE.length;
    }
    taken.add(slot);
    colors.set(id, AGENT_PALETTE[slot]);
  }
  return colors;
}

export { AGENT_PALETTE, agentColor, assignAgentColors };
```

---

<!-- ==== 26/44 : interface/static/js/agents.js ==== -->

### interface/static/js/agents.js

```javascript
/* Agent engine panel for the editor.
 *
 * Two jobs:
 *   1. RUN AGENT  - run the currently open agent definition
 *      (workspace/agents/<id>/agent.json + agent.md) against the engine.
 *   2. RUN PIPELINE - cascade MANY agents one after another: pick multiple,
 *      reorder the queue, send one message; each later agent receives every
 *      earlier agent's reply (feed-forward). Server-side stdout reports
 *      "Agent N (<id>) completed. Tools used: ..." for each step.
 */
import API from './api.js';

const state = {
  agents: [],       // all selectable agents (library + workspace)
  queue: [],        // ordered selected agents
  modelBox: null,
  jsonPath: null,   // run-agent target (workspace-relative)
  mdPath: null,
  ctx: null
};

const $ = (id) => document.getElementById(id);

export function initAgentsPanel(ctx) {
  state.ctx = ctx;

  // + Agent scaffold
  $('agentCreateBtn')?.addEventListener('click', scaffoldAgent);

  // Run Agent (single, current file)
  $('runAgentBtn')?.addEventListener('click', () => {
    if ($('agentPanel').classList.contains('hidden')) togglePanel();
    $('agentPrompt')?.focus();
  });
  $('runAgentBtnRun')?.addEventListener('click', runCurrentAgent);

  // Pipeline
  $('pipelineBtn')?.addEventListener('click', togglePanel);
  $('pipelineRunBtn')?.addEventListener('click', runPipeline);
  $('pipelineClearBtn')?.addEventListener('click', () => {
    state.queue = [];
    renderChecklist();
    renderQueue();
  });

  refreshEnabled();
  loadPanelData();
  updateRunTarget();
}

function togglePanel() {
  const panel = $('agentPanel');
  if (!panel) return;
  panel.classList.toggle('hidden');
  if (state.ctx && state.ctx.editorLayout) state.ctx.editorLayout();
}

function agentLabel(a) {
  return a.source === 'workspace' ? `${a.name} (ws)` : a.name;
}

/* ------------------------------------------------------------
   Panel data: agents + models
   ------------------------------------------------------------ */
async function loadPanelData() {
  try {
    const data = await API.agents();
    state.agents = data.agents || [];
    renderChecklist();
    renderQueue();
    updateRunTarget();
  } catch (e) {
    setPanel('pipelineAgents', 'Failed to load agents: ' + e.message);
  }

  try {
    const data = await API.models();
    const models = data.models || [];
    const box = $('modelBox');
    if (!box) return;
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = 'default model';
    box.appendChild(empty);
    for (const m of models) {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.name;
      box.appendChild(opt);
    }
  } catch (e) {
    // models are optional
  }
}

function activeModel() {
  return $('modelBox') ? $('modelBox').value || null : null;
}

/* ------------------------------------------------------------
   Checklist + queue
   ------------------------------------------------------------ */
function renderChecklist() {
  const host = $('pipelineAgents');
  if (!host) return;
  host.innerHTML = '';
  if (!state.agents.length) {
    host.textContent = 'No agents found.';
    return;
  }
  for (const a of state.agents) {
    const key = a.source === 'workspace' ? a.md_path : a.id;
    const row = document.createElement('label');
    row.className = 'agent-option';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = key;
    cb.checked = state.queue.some(q => q.key === key);
    cb.addEventListener('change', () => toggleAgent(a, cb.checked));
    row.appendChild(cb);
    row.append(agentLabel(a));
    host.appendChild(row);
  }
}

function toggleAgent(a, checked) {
  const key = a.source === 'workspace' ? a.md_path : a.id;
  if (checked) {
    if (!state.queue.some(q => q.key === key)) {
      state.queue.push({
        key,
        id: a.id,
        name: a.name,
        source: a.source,
        json_path: a.json_path || null,
        md_path: a.md_path || null
      });
    }
  } else {
    state.queue = state.queue.filter(q => q.key !== key);
  }
  renderQueue();
}

function moveStep(index, delta) {
  const target = index + delta;
  if (target < 0 || target >= state.queue.length) return;
  const [item] = state.queue.splice(index, 1);
  state.queue.splice(target, 0, item);
  renderQueue();
}

function renderQueue() {
  const host = $('pipelineQueue');
  if (!host) return;
  host.innerHTML = '';
  if (!state.queue.length) {
    host.textContent = 'Queue empty - tick agents above to add them.';
    return;
  }
  state.queue.forEach((q, i) => {
    const row = document.createElement('div');
    row.className = 'queue-item';

    const idx = document.createElement('span');
    idx.className = 'qidx';
    idx.textContent = (i + 1) + '.';
    row.appendChild(idx);

    const label = document.createElement('span');
    label.style.flex = '1';
    label.textContent = q.name;
    label.title = q.id;
    row.appendChild(label);

    const mk = (txt, fn) => {
      const b = document.createElement('button');
      b.textContent = txt;
      b.addEventListener('click', fn);
      row.appendChild(b);
    };
    mk('↑', () => moveStep(i, -1));
    mk('↓', () => moveStep(i, 1));
    mk('✕', () => {
      state.queue = state.queue.filter(x => x.key !== q.key);
      renderChecklist();
      renderQueue();
    });

    host.appendChild(row);
  });
}

/* ------------------------------------------------------------
   Run Agent (current file)
   ------------------------------------------------------------ */
function updateRunTarget() {
  const cf = state.ctx ? state.ctx.getCurrentFile() : null;
  const hint = $('runAgentHint');
  const btn = $('runAgentBtnRun'); // panel button text
  if (!cf) {
    state.jsonPath = state.mdPath = null;
    if (hint) hint.textContent = 'Open an agents/<id>/agent.json or agent.md to run it.';
    if (btn) btn.disabled = true;
    return;
  }
  const m = /^workspace\/agents\/([^/]+)\/(agent\.json|agent\.md)$/.exec(cf);
  if (m) {
    /* The agent-run API takes workspace-relative paths, so these
       stay unprefixed even though the open file is root-qualified. */
    state.jsonPath = `agents/${m[1]}/agent.json`;
    state.mdPath = `agents/${m[1]}/agent.md`;
    if (hint) hint.textContent = `Will run: ${m[1]} (${state.jsonPath})`;
    if (btn) btn.disabled = false;
  } else {
    state.jsonPath = state.mdPath = null;
    if (hint) hint.textContent = 'Open an agents/<id>/agent.json or agent.md to run it.';
    if (btn) btn.disabled = true;
  }
}

async function runCurrentAgent() {
  if (!state.jsonPath) {
    alert('Open an agents/<id>/agent.json or agent.md first.');
    return;
  }
  const message = $('agentPrompt').value.trim();
  if (!message) {
    alert('Enter an instruction for the agent.');
    return;
  }
  // Save the open file first so the run uses the latest edits.
  if (state.ctx && state.ctx.isDirty()) await state.ctx.saveFile();

  setPanel('agentResult', 'Running agent…');
  try {
    const res = await API.agentRun({
      json_path: state.jsonPath,
      md_path: state.mdPath,
      message,
      model: activeModel()
    });
    const tools = (res.tool_events || []).map(t => t.tool).filter(Boolean).join(', ') || 'none';
    renderResult('agentResult', [
      { head: `${res.name || res.agent_id} (${res.model || res.agent_id})`, text: res.reply || '(empty reply)' },
      { head: `Tools used: ${tools}`, text: '' }
    ]);
  } catch (e) {
    setPanel('agentResult', 'Error: ' + e.message);
  }
}

/* ------------------------------------------------------------
   Run Pipeline (cascade)
   ------------------------------------------------------------ */
async function runPipeline() {
  if (!state.queue.length) {
    alert('Tick at least one agent in the pipeline list.');
    return;
  }
  const message = $('pipelinePrompt').value.trim();
  if (!message) {
    alert('Enter the idea/message to cascade through the agents.');
    return;
  }
  if (state.ctx && state.ctx.isDirty()) await state.ctx.saveFile();

  const steps = state.queue.map(q => q.json_path
    ? { json_path: q.json_path, md_path: q.md_path }
    : q.id);

  setPanel('pipelineResult', 'Cascading ' + steps.length + ' agent(s)…');
  try {
    const res = await API.pipelineRun({ steps, message, model: activeModel() });
    const outputs = res.outputs || [];
    const parts = [];
    outputs.forEach((o, i) => {
      const tools = (o.tools_used || []).join(', ') || 'none';
      parts.push({ head: `✓ Agent ${i + 1} (${o.agent_name}) completed - tools: ${tools}`, text: o.output });
    });
    parts.push({ head: 'Final reply', text: res.reply });
    renderResult('pipelineResult', parts);
  } catch (e) {
    setPanel('pipelineResult', 'Error: ' + e.message);
  }
}

/* ------------------------------------------------------------
   Scaffold a new workspace agent
   ------------------------------------------------------------ */
async function scaffoldAgent() {
  const name = prompt('Agent id / folder name (e.g. "doc_writer"):');
  if (!name) return;
  if (!/^[A-Za-z0-9_\-]+$/.test(name)) {
    alert('Use only letters, numbers, underscore or dash.');
    return;
  }
  /* The tree/editor use root-qualified paths; the agent-run API
     uses workspace-relative ones. */
  const rel = `agents/${name}`;
  const full = `workspace/${rel}`;
  const json = JSON.stringify({
    id: name,
    name: name.replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    description: 'A custom agent scaffolded from the editor.',
    mode: 'agent',
    model: '',
    tools: ['map_files', 'read_file', 'write_text_file']
  }, null, 2);
  const md =
    `# ${name}\n` +
    `\n## role\n` +
    `\nYou are ${name}, a helpful Project Manager agent.\n` +
    `\n## purpose\n` +
    `\nDescribe what this agent accomplishes and when it is used.\n` +
    `\n## boundaries\n` +
    `\nState what this agent will not do.\n` +
    `\n## output format\n` +
    `\nDescribe the shape of the reply the agent must produce.\n`;
  try {
    await API.fileCreate(`${full}/agent.json`, json);
    await API.fileCreate(`${full}/agent.md`, md);
    state.queue = state.queue.filter(q => q.json_path !== `${rel}/agent.json`);
    loadPanelData();
    if (state.ctx) {
      await state.ctx.refreshTree();
      await state.ctx.openFile(`${full}/agent.json`);
    }
    setPanel('agentResult', `Created ${full}/agent.json + agent.md`);
  } catch (e) {
    alert('Failed to scaffold agent: ' + e.message);
  }
}

/* ------------------------------------------------------------
   Small rendering helpers
   ------------------------------------------------------------ */
function setPanel(id, text) {
  const el = $(id);
  if (el) {
    el.innerHTML = '';
    el.textContent = text;
  }
}

function renderResult(hostId, items) {
  const host = $(hostId);
  if (!host) return;
  host.innerHTML = '';
  items.forEach(it => {
    const card = document.createElement('div');
    card.className = 'result-box';
    const head = document.createElement('div');
    head.className = 'step-card-ok';
    head.textContent = it.head;
    card.appendChild(head);
    if (it.text) {
      const body = document.createElement('div');
      body.className = 'result-text';
      body.textContent = it.text;
      card.appendChild(body);
    }
    host.appendChild(card);
  });
}

function refreshEnabled() {
  // re-evaluated in updateRunTarget
}

export { updateRunTarget };
```

---

<!-- ==== 27/44 : interface/static/js/api.js ==== -->

### interface/static/js/api.js

```javascript
/* Project Manager API client module */
const API = {
  async request(method, url, body = null) {
    const options = { method };
    if (body) {
      options.headers = { 'Content-Type': 'application/json' };
      options.body = JSON.stringify(body);
    }
    const res = await fetch(url, options);
    if (!res.ok) {
      let detail = '';
      try {
        const err = await res.json();
        detail = err.detail || '';
      } catch (e) {
        detail = '';
      }
      throw new Error(detail || `Request failed: ${res.status}`);
    }
    if (res.status === 204 || !res.headers.get('content-type')?.includes('application/json')) {
      return {};
    }
    return res.json();
  },

  health() {
    return this.request('GET', '/api/health');
  },

  /* ---- Scope handling ----
     A null scope selects the browser view, where paths may carry
     a browser-root prefix (workspace/..., source_files/...). An
     explicit 'workspace' or 'app' keeps the legacy single-root
     view. Omitting the parameter entirely is what makes the API
     return the browser tree. */

  withPath(path, scope) {
    const params = new URLSearchParams({ path });
    if (scope) params.set('scope', scope);
    return params.toString();
  },

  withScope(body, scope) {
    if (!scope) return body;
    return { ...body, scope };
  },

  project(scope = null) {
    const params = new URLSearchParams();
    if (scope) params.set('scope', scope);
    const query = params.toString();
    return this.request('GET', '/api/project' + (query ? `?${query}` : ''));
  },

  fileRead(path, scope = null) {
    return this.request('GET', `/api/file/read?${this.withPath(path, scope)}`);
  },

  fileWrite(path, content, scope = null) {
    return this.request('PUT', '/api/file/write', this.withScope({ path, content }, scope));
  },

  fileCreate(path, content = '', scope = null) {
    return this.request('POST', '/api/file/create', this.withScope({ path, content }, scope));
  },

  fileDelete(path, scope = null) {
    return this.request('DELETE', `/api/file/delete?${this.withPath(path, scope)}`);
  },

  directoryCreate(path, scope = null) {
    return this.request('POST', `/api/directory/create?${this.withPath(path, scope)}`);
  },

  directoryDelete(path, scope = null) {
    return this.request('DELETE', `/api/directory/delete?${this.withPath(path, scope)}`);
  },

  pathRename(oldPath, newPath, scope = null) {
    return this.request('PUT', '/api/path/rename', this.withScope({ old_path: oldPath, new_path: newPath }, scope));
  },

  chatSend(message, agent_id = null, model = null) {
    return this.request('POST', '/api/chat', { message, agent_id, model });
  },

  /* Chat history is scoped per agent. Omitting the agent returns
     the whole log, which is what headless_app expects. */
  chatHistory(limit = 100, agent = null) {
    const params = new URLSearchParams({ limit });
    if (agent) params.set('agent', agent);
    return this.request('GET', `/api/chat?${params.toString()}`);
  },

  chatClear(agent = null) {
    const query = agent ? `?agent=${encodeURIComponent(agent)}` : '';
    return this.request('DELETE', `/api/chat${query}`);
  },

  sessions() {
    return this.request('GET', '/api/sessions');
  },

  /* ---- Agent engine ---- */

  agents() {
    return this.request('GET', '/api/agents');
  },

  agentDefinition(id) {
    return this.request('GET', `/api/agents/${encodeURIComponent(id)}`);
  },

  agentRun(body) {
    return this.request('POST', '/api/agents/run', body);
  },

  pipelineOptions() {
    return this.request('GET', '/api/pipeline');
  },

  pipelineRun(body) {
    return this.request('POST', '/api/pipeline', body);
  },

  models() {
    return this.request('GET', '/api/models');
  }
};

export default API;
```

---

<!-- ==== 28/44 : interface/static/js/chat.js ==== -->

### interface/static/js/chat.js

```javascript
/* Chat popup module */
import API from './api.js';
import Session from './session.js';
import { assignAgentColors } from './agentColors.js';
import { initTopbar } from './topbar.js';

const log = document.getElementById('chatLog');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const sendBtn = document.getElementById('chatSend');
const status = document.getElementById('chatStatus');
const agentSelect = document.getElementById('agentSelect');
const modelSelect = document.getElementById('modelSelect');
const agentChip = document.getElementById('activeAgentChip');
const agentName = document.getElementById('activeAgentName');

/* Agent id requested by the home page card, e.g. /chat?agent=rag_assistant */
const requestedAgent = new URLSearchParams(window.location.search).get('agent');

let agentColorById = new Map();

function appendLine(role, text, meta = '', labelText = null) {
  const line = document.createElement('div');
  line.className = 'msg ' + role;
  const label = document.createElement('span');
  label.className = 'msg-label';
  label.textContent = labelText
    || (role === 'user' ? 'You' : role === 'event' ? 'Event' : 'System');
  const body = document.createElement('span');
  body.className = 'msg-body';
  body.textContent = text;
  line.appendChild(label);
  line.appendChild(body);
  if (meta) {
    const ts = document.createElement('span');
    ts.className = 'msg-meta';
    ts.textContent = meta;
    line.appendChild(ts);
  }
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

function appendTools(tools) {
  if (!tools || !tools.length) return;
  const detail = document.createElement('details');
  detail.className = 'msg event';
  const summary = document.createElement('summary');
  summary.className = 'msg-label';
  summary.textContent = 'Tools used: ' + tools.map(t => t.tool || '').filter(Boolean).join(', ');
  detail.appendChild(summary);
  const body = document.createElement('div');
  body.className = 'msg-body';
  body.textContent = tools.map(t => {
    const args = t.args ? JSON.stringify(t.args).slice(0, 400) : '';
    const ok = t.op_ok ? 'ok' : (t.status || '?');
    return `› ${t.tool} (${ok}) ${args}`;
  }).join('\n');
  detail.appendChild(body);
  log.appendChild(detail);
  log.scrollTop = log.scrollHeight;
}

function setStatus(text) {
  if (status) status.textContent = text;
}

// ---- Agent / model selector population ----

function activeAgentId() {
  return agentSelect && agentSelect.value ? agentSelect.value : null;
}

function agentLabel(id) {
  if (!id) return 'No agent selected';
  const opt = agentSelect ? agentSelect.querySelector(`option[value="${CSS.escape(id)}"]`) : null;
  return opt ? opt.textContent : id;
}

function paintAgentChip() {
  const id = activeAgentId();
  if (!agentChip || !agentName) return;
  if (!id) {
    agentChip.hidden = true;
    return;
  }
  const color = agentColorById.get(id) || '#4fc3f7';
  agentChip.style.setProperty('--agent-color', color);
  agentName.textContent = agentLabel(id);
  agentChip.hidden = false;
  if (input) {
    input.placeholder = `Message ${agentLabel(id)}...`;
  }
}

async function populateAgents() {
  try {
    const data = await API.agents();
    const agents = data.agents || [];
    agentColorById = assignAgentColors(agents);
    const savedAgent = localStorage.getItem('pmAgent');
    agentSelect.innerHTML = '';
    for (const a of agents) {
      const opt = document.createElement('option');
      opt.value = a.id;
      opt.textContent = a.source === 'workspace' ? `${a.name} (ws)` : a.name;
      if (a.id === savedAgent) opt.selected = true;
      agentSelect.appendChild(opt);
    }
    /* An explicit ?agent= from a home card outranks the saved choice. */
    const preferred = agents.some(a => a.id === requestedAgent) ? requestedAgent : savedAgent;
    if (preferred) agentSelect.value = preferred;
    if (!agentSelect.value && agents.length) agentSelect.value = agents[0].id;
    if (agentSelect.value) localStorage.setItem('pmAgent', agentSelect.value);
    paintAgentChip();
  } catch (e) {
    console.warn('Failed to load agents', e);
  }
}

async function populateModels() {
  try {
    const data = await API.models();
    const models = data.models || [];
    const savedModel = localStorage.getItem('pmModel') || '';
    modelSelect.innerHTML = '';
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = 'default model';
    modelSelect.appendChild(empty);
    for (const m of models) {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.name;
      modelSelect.appendChild(opt);
    }
    if (savedModel) modelSelect.value = savedModel;
  } catch (e) {
    console.warn('Failed to load models', e);
  }
}

async function populateSelectors() {
  await populateAgents();
  await populateModels();

  agentSelect.addEventListener('change', async () => {
    localStorage.setItem('pmAgent', agentSelect.value);
    paintAgentChip();
    /* Each agent has its own thread, so swap the transcript. */
    await loadHistory();
  });

  modelSelect.addEventListener('change', () => {
    localStorage.setItem('pmModel', modelSelect.value);
  });
}

async function refreshAgents() {
  await populateAgents();
}

async function loadHistory() {
  try {
    const data = await API.chatHistory(100, activeAgentId());
    const entries = data.entries || [];
    log.innerHTML = '';
    if (!entries.length) {
      const who = agentLabel(activeAgentId());
      appendLine('system', `No messages yet with ${who}. Say hello!`);
      return;
    }
    for (const entry of entries) {
      const ts = entry.ts ? new Date(entry.ts).toLocaleTimeString() : '';
      const who = entry.agent ? agentLabel(entry.agent) : null;
      appendLine(entry.sender === 'user' ? 'user' : 'system', entry.message, ts, who);
    }
  } catch (error) {
    setStatus('Failed to load history: ' + error.message);
  }
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;
  const agentId = activeAgentId();
  input.value = '';
  appendLine('user', message, new Date().toLocaleTimeString());
  setStatus('Running agent…');
  sendBtn.disabled = true;
  try {
    const result = await API.chatSend(
      message,
      agentId,
      modelSelect ? modelSelect.value || null : null
    );
    const who = agentLabel(result.agent_id || agentId);
    appendLine('system', result.reply || '(empty reply)', new Date().toLocaleTimeString(), who);
    appendTools(result.tool_events || []);
    setStatus(`${who} · ${result.model || 'model'} replied.`);
  } catch (error) {
    setStatus('Send failed: ' + error.message);
  } finally {
    sendBtn.disabled = false;
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  sendMessage();
});

sendBtn.addEventListener('click', sendMessage);

Session.onEvent = (msg) => {
  if (msg.type === 'event' && msg.event) {
    const ev = msg.event;
    const what = ev.type || 'event';
    const path = ev.path || '';
    appendLine('event', what + (path ? ': ' + path : ''));
  }
};

/* The agent must be resolved before history loads, otherwise the
   first paint would show the previous agent's thread. */
initTopbar({ page: 'chat' });
populateSelectors()
  .then(loadHistory)
  .catch((e) => setStatus('Failed to start: ' + e.message));
Session.connect();

// ---- New agent scaffold + wipe chat (exposed for inline handlers) ----

async function scaffoldNewAgent() {
  const name = prompt('New agent id / folder name (e.g. "doc_writer"):');
  if (!name) return;
  if (!/^[A-Za-z0-9_\-]+$/.test(name)) {
    alert('Use only letters, numbers, underscore or dash.');
    return;
  }
  const rel = `workspace/agents/${name}`;
  const json = JSON.stringify({
    id: name,
    name: name.replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    description: 'A custom agent scaffolded from the AI Agent Creator.',
    mode: 'agent',
    model: '',
    tools: ['map_files', 'read_file', 'write_text_file']
  }, null, 2);
  const md =
    `# ${name}\n` +
    `\n## role\n` +
    `\nYou are ${name}, a helpful Project Manager agent.\n` +
    `\n## purpose\n` +
    `\nDescribe what this agent accomplishes and when it is used.\n` +
    `\n## boundaries\n` +
    `\nState what this agent will not do.\n` +
    `\n## output format\n` +
    `\nDescribe the shape of the reply the agent must produce.\n`;
  try {
    await API.fileCreate(`${rel}/agent.json`, json);
    await API.fileCreate(`${rel}/agent.md`, md);
    localStorage.setItem('pmAgent', name);
    await refreshAgents();
    window.open(`/editor?path=${encodeURIComponent(`${rel}/agent.json`)}&root=workspace`, '_blank');
    setStatus(`Created ${rel}/agent.json + agent.md`);
    showToast(`Agent '${name}' created`);
  } catch (e) {
    alert('Failed to scaffold agent: ' + e.message);
  }
}

async function wipeChat() {
  const who = agentLabel(activeAgentId());
  if (!confirm(`Wipe the chat history with ${who}? This cannot be undone.`)) return;
  try {
    const res = await API.chatClear(activeAgentId());
    log.innerHTML = '';
    appendLine('system', `Chat history with ${who} wiped${res.cleared ? ` (${res.cleared} entries removed)` : ''}.`);
    setStatus('Chat history cleared');
    showToast('Chat history cleared');
  } catch (e) {
    setStatus('Wipe failed: ' + e.message);
    alert('Failed to clear chat: ' + e.message);
  }
}

window.scaffoldNewAgent = scaffoldNewAgent;
window.wipeChat = wipeChat;
```

---

<!-- ==== 29/44 : interface/static/js/editor.js ==== -->

### interface/static/js/editor.js

```javascript
/* Monaco editor module */
let editor = null;

const Editor = {
  /* The home page has no editor host; it is editor.html's job. */
  hasHost() {
    return !!document.getElementById('editor');
  },

  init() {
    if (!this.hasHost()) {
      return Promise.resolve(null);
    }
    return new Promise((resolve, reject) => {
      if (typeof require === 'undefined') {
        reject(new Error('Monaco loader not found'));
        return;
      }
      require.config({
        paths: {
          vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs'
        }
      });
      require(['vs/editor/editor.main'], () => {
        editor = monaco.editor.create(document.getElementById('editor'), {
          value: '// Select a file from the sidebar to start editing\n',
          language: 'plaintext',
          theme: 'vs-dark',
          automaticLayout: true,
          minimap: { enabled: true },
          wordWrap: 'on',
          fontSize: 14,
          tabSize: 4,
          insertSpaces: true,
          autoIndent: 'full',
          formatOnType: true,
          formatOnPaste: true
        });
        resolve(editor);
      });
    });
  },

  getEditor() {
    return editor;
  },

  setValue(content) {
    if (editor) editor.setValue(content);
  },

  getValue() {
    return editor ? editor.getValue() : '';
  },

  setLanguage(lang) {
    if (editor && monaco && editor.getModel()) {
      monaco.editor.setModelLanguage(editor.getModel(), lang);
    }
  },

  setReadOnly(flag) {
    if (editor) {
      editor.updateOptions({
        readOnly: !!flag,
        domReadOnly: !!flag
      });
    }
  },

  onChange(callback) {
    if (editor) {
      editor.onDidChangeModelContent(callback);
    }
  },

  layout() {
    if (editor) editor.layout();
  }
};

export default Editor;
```

---

<!-- ==== 30/44 : interface/static/js/main.js ==== -->

### interface/static/js/main.js

```javascript
/* Main application wiring */
import API from './api.js';
import Session from './session.js';
import Tree from './tree.js';
import Editor from './editor.js';
import { initAgentsPanel, updateRunTarget } from './agents.js';
import { initAgentCards, openChatWithAgent } from './agentCards.js';
import { initTopbar } from './topbar.js';

let currentFile = null;
let currentLanguage = 'plaintext';
let isDirty = false;
let currentIsFolder = false;
let currentIsReadOnly = false;

/* main.js is shared by home.html and editor.html. Only editor.html
   carries a #editor host, so every editor call is guarded. */
const hasEditor = () => Editor.hasHost();

/* Paths are browser-root-qualified (workspace/..., source_files/...),
   so no scope needs to be tracked or sent. The active folder is the
   root folder selected in the tree. */

function isPathReadOnly(path) {
  const rootName = Tree.rootOf(path);
  if (rootName && Tree.roots[rootName] === false) return true;
  const node = Tree.nodeFor(path);
  if (node && node.editable === false) return true;
  return false;
}

function applyReadOnly() {
  if (hasEditor()) Editor.setReadOnly(currentIsReadOnly);
  const el = document.getElementById('readOnlyIndicator');
  if (el) el.textContent = currentIsReadOnly ? '🔒 READ-ONLY' : '';
}

function getLanguage(filePath) {
  if (!filePath) return 'plaintext';
  const ext = filePath.split('.').pop().toLowerCase();
  const map = {
    py: 'python',
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    html: 'html',
    htm: 'html',
    css: 'css',
    json: 'json',
    md: 'markdown',
    yaml: 'yaml',
    yml: 'yaml',
    sql: 'sql',
    xml: 'xml',
    sh: 'shell',
    bat: 'batch',
    ps1: 'powershell',
    env: 'shell',
    txt: 'plaintext'
  };
  return map[ext] || 'plaintext';
}

function setStatus(msg) {
  const el = document.getElementById('statusMessage');
  if (el) el.textContent = msg;
}

function updateFileDisplay() {
  const cf = document.getElementById('currentFile');
  if (cf) cf.textContent = currentFile ? currentFile : 'No file selected';
  const lang = document.getElementById('language');
  if (lang) lang.textContent = currentLanguage;
  const dirty = document.getElementById('unsavedIndicator');
  if (dirty) dirty.textContent = isDirty ? '● UNSAVED' : '';
  applyReadOnly();
}

async function openFile(filePath) {
  if (isDirty) {
    const proceed = confirm('You have unsaved changes. Open another file?');
    if (!proceed) return;
  }
  /* Home has no editor, so opening a file means handing it to
     editor.html rather than rendering it here. */
  if (!hasEditor()) {
    const root = Tree.rootOf(filePath) || Tree.activeRoot;
    window.location.href =
      `/editor?path=${encodeURIComponent(filePath)}&root=${encodeURIComponent(root)}`;
    return;
  }
  setStatus('Opening ' + filePath + '...');
  try {
    const data = await API.fileRead(filePath);
    currentFile = filePath;
    currentIsFolder = false;
    currentIsReadOnly = isPathReadOnly(filePath);
    currentLanguage = getLanguage(filePath);
    if (hasEditor()) {
      Editor.setValue(data.content || '');
      Editor.setLanguage(currentLanguage);
    }
    isDirty = false;
    updateFileDisplay();
    Tree.setSelected(filePath);
    Tree.reveal(filePath);
    setStatus(currentIsReadOnly
      ? 'Opened ' + filePath + ' (read-only)'
      : 'Opened ' + filePath);
    updateRunTarget();
  } catch (error) {
    setStatus('Error: ' + error.message);
    alert(error.message);
  }
}

function selectFolder(path) {
  currentFile = path;
  currentIsFolder = true;
  updateFileDisplay();
  setStatus('Folder selected: ' + path);
  updateRunTarget();
}

async function saveFile() {
  if (!currentFile) {
    alert('No file is currently open.');
    return;
  }
  if (currentIsFolder) {
    alert('Select a file to save. Folders cannot be saved as files.');
    return;
  }
  if (!hasEditor()) {
    alert('Open the file in the editor to save it.');
    return;
  }
  if (currentIsReadOnly) {
    alert('This file is read-only: ' + currentFile);
    return;
  }
  setStatus('Saving...');
  try {
    await API.fileWrite(currentFile, Editor.getValue());
    isDirty = false;
    updateFileDisplay();
    setStatus('Saved ' + currentFile);
    await Tree.refresh();
  } catch (error) {
    setStatus('Save error: ' + error.message);
    alert(error.message);
  }
}

function requireWritableRoot(path) {
  const rootName = Tree.rootOf(path);
  if (rootName && Tree.roots[rootName] === false) {
    alert(rootName + ' is read-only.');
    return false;
  }
  return true;
}

function isRootFolder(path) {
  return Tree.rootOf(path) === path;
}

async function newFile() {
  if (!Tree.isWritable()) {
    alert(Tree.activeRoot + ' is read-only.');
    return;
  }
  const suggestion = (currentIsFolder ? currentFile : Tree.activeRoot) + '/';
  const fileName = prompt('Enter new file path/name:', suggestion);
  if (!fileName) return;
  if (!requireWritableRoot(fileName)) return;
  try {
    await API.fileCreate(fileName, '');
    await Tree.refresh();
    await openFile(fileName);
    setStatus('Created ' + fileName);
  } catch (error) {
    alert(error.message);
  }
}

async function newFolder() {
  if (!Tree.isWritable()) {
    alert(Tree.activeRoot + ' is read-only.');
    return;
  }
  const suggestion = (currentIsFolder ? currentFile : Tree.activeRoot) + '/';
  const folderPath = prompt('Enter new folder path:', suggestion);
  if (!folderPath) return;
  if (!requireWritableRoot(folderPath)) return;
  try {
    await API.directoryCreate(folderPath);
    await Tree.refresh();
    setStatus('Created folder ' + folderPath);
  } catch (error) {
    alert(error.message);
  }
}

async function renameSelected() {
  if (!currentFile) {
    alert('Select a file or folder first.');
    return;
  }
  if (!requireWritableRoot(currentFile)) return;
  if (isRootFolder(currentFile)) {
    alert('A root folder cannot be renamed.');
    return;
  }
  const newName = prompt('Enter the new name/path:', currentFile);
  if (!newName || newName === currentFile) return;
  if (!requireWritableRoot(newName)) return;
  try {
    await API.pathRename(currentFile, newName);
    currentFile = newName;
    await Tree.refresh();
    if (currentIsFolder) {
      Tree.setSelected(newName);
      setStatus('Renamed folder to ' + newName);
    } else {
      await openFile(newName);
    }
  } catch (error) {
    alert(error.message);
  }
}

async function deleteSelected() {
  if (!currentFile) {
    alert('Select a file or folder first.');
    return;
  }
  if (!requireWritableRoot(currentFile)) return;
  if (isRootFolder(currentFile)) {
    alert('A root folder cannot be deleted.');
    return;
  }
  const confirmed = confirm((currentIsFolder ? 'Delete folder ' : 'Delete file ') + currentFile + '?');
  if (!confirmed) return;
  try {
    if (currentIsFolder) {
      await API.directoryDelete(currentFile);
    } else {
      await API.fileDelete(currentFile);
    }
            currentFile = null;
            currentIsFolder = false;
            currentIsReadOnly = false;
            if (hasEditor()) Editor.setValue('');
            isDirty = false;
    updateFileDisplay();
    await Tree.refresh();
    setStatus('Deleted.');
    updateRunTarget();
  } catch (error) {
    alert(error.message);
  }
}

async function refreshTree() {
  await Tree.refresh();
  setStatus('Refreshed.');
}

function selectRoot(rootName) {
  setStatus('Working in ' + rootName
    + (Tree.roots[rootName] === false ? ' (read-only)' : ''));
}

function openChatPopup(agentId) {
  openChatWithAgent(agentId);
}

function init() {
  Editor.init()
    .then(async () => {
      initTopbar({ page: hasEditor() ? 'editor' : 'home' });

      if (hasEditor()) {
        Editor.onChange(() => {
          if (currentFile) {
            isDirty = true;
            updateFileDisplay();
          }
        });
      }

      Tree.onFileSelect = openFile;
      Tree.onFolderSelect = selectFolder;
      Tree.onRootSelect = selectRoot;

      // ---- Project name ----
      if (document.getElementById('projectName')) {
        try {
          const info = await API.health();
          const name = info.project?.name;
          if (name) document.getElementById('projectName').textContent = name;
        } catch (e) {
          // ignore
        }
      }

      // ---- Top bar actions ----
      /* Page navigation lives in the shared topbar; only this page's
         own tools are wired here. */
      document.getElementById('saveBtn')?.addEventListener('click', saveFile);
      document.getElementById('newFileBtn')?.addEventListener('click', newFile);
      document.getElementById('newFolderBtn')?.addEventListener('click', newFolder);
      document.getElementById('renameBtn')?.addEventListener('click', renameSelected);
      document.getElementById('deleteBtn')?.addEventListener('click', deleteSelected);
      document.getElementById('refreshBtn')?.addEventListener('click', refreshTree);

      document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
          event.preventDefault();
          saveFile();
        }
      });

      const sidebar = document.getElementById('sidebar');
      const resizeHandle = document.getElementById('resizeHandle');
      if (resizeHandle && sidebar) {
        let resizing = false;
        resizeHandle.addEventListener('mousedown', () => { resizing = true; document.body.style.cursor = 'col-resize'; });
        document.addEventListener('mousemove', (e) => {
          if (!resizing) return;
          const width = e.clientX;
          if (width >= 180 && width <= 500) {
            sidebar.style.width = width + 'px';
            Editor.layout();
          }
        });
        document.addEventListener('mouseup', () => { resizing = false; document.body.style.cursor = ''; });
      }

      window.addEventListener('beforeunload', (event) => {
        if (!isDirty) return;
        event.preventDefault();
        event.returnValue = '';
      });

      setStatus('Ready');
      await Tree.load();

      /* Home page: agent cards replace the editor. */
      if (document.getElementById('agentCards')) {
        try {
          await initAgentCards({ onOpen: openChatPopup });
        } catch (e) {
          const host = document.getElementById('agentCards');
          host.textContent = 'Failed to load agents: ' + e.message;
        }
        return;
      }

      initAgentsPanel({
        getCurrentFile: () => currentFile,
        isDirty: () => isDirty,
        saveFile,
        refreshTree,
        openFile,
        editorLayout: () => Editor.layout()
      });
      const urlParams = new URLSearchParams(window.location.search);
      const initialPath = urlParams.get('path');
      const initialRoot = urlParams.get('root');
      if (initialRoot && initialRoot in Tree.roots) {
        Tree.activeRoot = initialRoot;
      }
      if (initialPath) {
        await openFile(initialPath);
      }
    })
    .catch((e) => {
      setStatus('Error: ' + e.message);
    });

  Session.connect();
}

document.addEventListener('DOMContentLoaded', init);

export { openFile, saveFile, newFile, newFolder, renameSelected, deleteSelected, refreshTree, openChatPopup, currentFile, isDirty };
```

---

<!-- ==== 31/44 : interface/static/js/session.js ==== -->

### interface/static/js/session.js

```javascript
/* Project Manager WebSocket session module */
let ws = null;
let wsConnected = false;
let reconnectTimeout = null;

const Session = {
  onEvent: null,
  onConnect: null,
  onDisconnect: null,

  connect() {
    if (ws && wsConnected) return;
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${window.location.host}/api/ws`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      wsConnected = true;
      if (this.onConnect) this.onConnect();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (this.onEvent) this.onEvent(msg);
      } catch (e) {
        console.warn('Failed to parse WS message', e);
      }
    };

    ws.onclose = () => {
      wsConnected = false;
      if (this.onDisconnect) this.onDisconnect();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      reconnectTimeout = setTimeout(() => this.connect(), 2000);
    };

    ws.onerror = (e) => {
      console.error('WebSocket error', e);
    };
  },

  send(msg) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  },

  sendOpen(path) {
    this.send({ type: 'open', path });
  },

  sendDirty(dirty) {
    this.send({ type: 'dirty', dirty });
  },

  sendSessions() {
    this.send({ type: 'sessions' });
  }
};

export default Session;
```

---

<!-- ==== 32/44 : interface/static/js/topbar.js ==== -->

### interface/static/js/topbar.js

```javascript
/* Shared topbar navigation

   Home / Editor / Chat must sit in the same place on every page, so
   the markup and styling live here instead of being copied into each
   page. Each page marks its header with data-pm-header and calls
   initTopbar({ page }).

   The links are rendered as anchors, not buttons, on purpose: home
   and editor apply a bare `button { ... }` rule and chat.html styles
   `.btn-header`, so anchors sidestep both stylesheets and come out
   pixel-identical on all three pages. */

const NAV_ITEMS = [
  { page: 'home', label: 'Home', href: '/' },
  { page: 'editor', label: 'Editor', href: '/editor' },
  { page: 'chat', label: 'Chat', href: '/chat' }
];

const STYLE_ID = 'pmnav-style';

const NAV_CSS = `
.pmnav {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  flex-shrink: 0;
}

.pmnav-link {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #45474d;
  background: #2f3136;
  color: #e5e7eb;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.pmnav-link:hover {
  background: #3a3d44;
  border-color: #565a61;
  color: #ffffff;
}

.pmnav-link.pmnav-current,
.pmnav-link[aria-current="page"] {
  background: #0e639c;
  border-color: #1177bb;
  color: #ffffff;
}

.pmnav-link:focus-visible {
  outline: 2px solid #4fc3f7;
  outline-offset: 2px;
}
`;

function ensureStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = NAV_CSS;
  document.head.appendChild(style);
}

function initTopbar(options = {}) {
  const page = options.page;
  const header = options.header
    || document.querySelector('[data-pm-header]');
  if (!header) return null;

  ensureStyle();

  /* Re-initialising must not stack duplicate nav groups. */
  for (const child of Array.from(header.children)) {
    if (child.classList && child.classList.contains('pmnav')) {
      child.remove();
    }
  }

  const nav = document.createElement('nav');
  nav.className = 'pmnav';
  nav.setAttribute('aria-label', 'Main');

  for (const item of NAV_ITEMS) {
    const link = document.createElement('a');
    link.className = 'pmnav-link';
    link.href = item.href;
    link.textContent = item.label;
    if (item.page === page) {
      link.classList.add('pmnav-current');
      link.setAttribute('aria-current', 'page');
    }
    nav.appendChild(link);
  }

  header.appendChild(nav);
  return nav;
}

export { initTopbar, NAV_ITEMS };
```

---

<!-- ==== 33/44 : interface/static/js/tree.js ==== -->

### interface/static/js/tree.js

```javascript
/* Project tree rendering module */
import API from './api.js';

const Tree = {
  root: [],
  roots: {},
  activeRoot: null,
  selectedPath: null,
  expanded: new Set(),
  onFileSelect: null,
  onFolderSelect: null,
  onRootSelect: null,

  /* The top level of the tree is the set of browser roots, so the
     tree doubles as the folder switcher. Clicking a root folder
     makes it the folder that file operations act on. */

  rootOf(path) {
    if (!path) return null;
    const head = String(path).split('/')[0];
    return head in this.roots ? head : null;
  },

  isWritable() {
    if (this.activeRoot === null) return true;
    return this.roots[this.activeRoot] !== false;
  },

  nodeFor(path, items = this.root) {
    for (const item of items || []) {
      if (item.path === path) return item;
      if (item.children) {
        const hit = this.nodeFor(path, item.children);
        if (hit) return hit;
      }
    }
    return null;
  },

  async load() {
    const data = await API.project();
    this.root = data.filesystem || [];
    this.roots = {};
    for (const node of this.root) {
      this.roots[node.name] = node.writable !== false;
    }
    if (!(this.activeRoot in this.roots)) {
      const firstWritable = this.root.find(n => n.writable !== false);
      this.activeRoot = firstWritable ? firstWritable.name : (this.root[0]?.name ?? null);
    }
    /* Show every root folder expanded so the available folders are
       visible without having to click each one open. */
    for (const node of this.root) {
      this.expanded.add(this.key(node.path));
    }
    this.render();
  },

  key(path) {
    return path;
  },

  render(containerId = 'tree') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    this.renderItems(this.root, container);
  },

  renderItems(items, container, depth = 0) {
    for (const item of items) {
      const row = document.createElement('div');
      row.className = 'tree-item';
      if (item.type === 'directory') {
        row.classList.add('folder');
        row.dataset.path = item.path;
        const isRoot = depth === 0 && item.root;
        if (isRoot) {
          row.classList.add('root');
          if (item.name === this.activeRoot) {
            row.classList.add('active');
          }
          if (item.writable === false) {
            row.classList.add('readonly');
          }
        }
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        const isExpanded = this.expanded.has(this.key(item.path));
        const toggle = document.createElement('span');
        toggle.className = 'toggle' + (isExpanded ? ' expanded' : '');
        toggle.textContent = isExpanded ? '−' : '+';
        const label = document.createElement('span');
        label.className = 'label';
        label.textContent = (isRoot ? '🗂 ' : '📁 ') + item.name;
        row.appendChild(toggle);
        row.appendChild(label);
        if (isRoot && item.writable === false) {
          const lock = document.createElement('span');
          lock.className = 'root-lock';
          lock.textContent = '🔒';
          lock.title = 'Read-only';
          row.appendChild(lock);
        }
        const children = document.createElement('div');
        children.className = 'children' + (isExpanded ? '' : ' collapsed');
        row.onclick = () => {
          this.selectedPath = item.path;
          if (isRoot) {
            const changed = this.activeRoot !== item.name;
            this.activeRoot = item.name;
            if (changed && this.onRootSelect) this.onRootSelect(item.name);
          }
          if (this.onFolderSelect) this.onFolderSelect(item.path);
          this.render();
          this.toggle(item.path);
        };
        container.appendChild(row);
        container.appendChild(children);
        this.renderItems(item.children || [], children, depth + 1);
      } else {
        row.textContent = this.getFileIcon(item.name) + ' ' + item.name;
        if (item.editable === false) {
          row.classList.add('readonly');
          row.title = item.size > 0
            ? 'Read-only: not an editable text file, or too large'
            : 'Read-only';
        }
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        row.onclick = () => {
          this.selectedPath = item.path;
          const rootName = this.rootOf(item.path);
          if (rootName && rootName !== this.activeRoot) {
            this.activeRoot = rootName;
            if (this.onRootSelect) this.onRootSelect(rootName);
          }
          if (this.onFileSelect) this.onFileSelect(item.path);
          this.render();
        };
        container.appendChild(row);
      }
    }
  },

  toggle(path) {
    const key = this.key(path);
    if (this.expanded.has(key)) {
      this.expanded.delete(key);
    } else {
      this.expanded.add(key);
    }
    const container = document.getElementById('tree');
    if (!container) return;
    const row = container.querySelector('.tree-item.folder[data-path="' + path.replace(/"/g, '\\"') + '"]');
    if (!row) return;
    const toggle = row.querySelector('.toggle');
    toggle.classList.toggle('expanded');
    toggle.textContent = toggle.classList.contains('expanded') ? '−' : '+';
    const children = row.nextElementSibling;
    if (children && children.classList.contains('children')) {
      children.classList.toggle('collapsed');
    }
  },

  reveal(path) {
    const parts = path.split('/');
    for (let i = 1; i < parts.length; i++) {
      this.expanded.add(this.key(parts.slice(0, i).join('/')));
    }
    this.render();
  },

  setSelected(path) {
    this.selectedPath = path;
    this.render();
  },

  refresh() {
    return this.load();
  },

  getFileIcon(name) {
    const ext = name.split('.').pop().toLowerCase();
    const icons = {
      py: '🐍',
      html: '🌐', htm: '🌐',
      css: '🎨',
      js: '🟨', mjs: '🟨', jsx: '🟨',
      ts: '🔷', tsx: '🔷',
      json: '📋',
      md: '📝',
      sql: '🗄️',
      xml: '🧾',
      sh: '⌨️', bat: '⌨️', ps1: '⌨️',
      yaml: '⚙️', yml: '⚙️', toml: '⚙️', ini: '⚙️', cfg: '⚙️', env: '⚙️',
      txt: '📄', csv: '📄'
    };
    return icons[ext] || '📄';
  }
};

export default Tree;
```

---

<!-- ==== 34/44 : parameters/__init__.py ==== -->

### parameters/__init__.py

```python
"""Project parameters package.

Holds the Project Manager filesystem owner (filesystem.py) that owns
the managed workspace, plus the project metadata it manages.
"""
```

---

<!-- ==== 35/44 : parameters/filesystem.py ==== -->

### parameters/filesystem.py

```python
"""
Project Manager Filesystem
==========================

This module is responsible for managing the physical
project filesystem.

Responsibilities:
    - Discover the project root.
    - Create the basic project structure.
    - Create/read project.json.
    - Read the project filesystem.
    - Read files.
    - Write files.
    - Create files.
    - Create directories.
    - Rename files/directories.
    - Delete files/directories.
    - Prevent access outside the project root.

The web server does NOT contain filesystem logic.
server.py calls this module.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PARAMETERS_DIR = Path(__file__).resolve().parent

REPO_ROOT = PARAMETERS_DIR.parent

PROJECT_ROOT = REPO_ROOT / "workspace"

PROJECT_JSON = PROJECT_ROOT / "project.json"

SOURCE_FILES_ROOT = REPO_ROOT.parent / "source_files"


# ============================================================
# STANDARD PROJECT FOLDERS
# ============================================================

PROJECT_FOLDERS = [
    "documentation",
    "project_scope",
    "to_do",
    "updates",
    "config",
    "data",
]


# ============================================================
# BROWSER ROOTS
# ============================================================

# The two folders the file browser shows. Add a folder here to
# make it appear in the tree; set ``writable`` to False to make it
# browse-only. Keys are the path prefixes the API understands, so
# ``source_files/AGENTS.md`` and ``workspace/project.json`` resolve
# inside their own root.

BROWSE_ROOTS: dict[str, dict[str, Any]] = {
    "workspace": {
        "path": PROJECT_ROOT,
        "writable": True,
    },
    "source_files": {
        "path": SOURCE_FILES_ROOT,
        "writable": False,
    },
}


# Files above this size open read-only so the browser editor
# never tries to render a multi-megabyte document.

MAX_EDITABLE_BYTES = 512 * 1024


# ============================================================
# FILE TYPES
# ============================================================

TEXT_EXTENSIONS = {
    ".py",
    ".txt",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".sql",
    ".xml",
    ".csv",
    ".env",
}


# ============================================================
# DIRECTORIES TO HIDE
# ============================================================

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
}


# ============================================================
# DEFAULT PROJECT INFORMATION
# ============================================================

DEFAULT_PROJECT = {
    "name": PROJECT_ROOT.name,
    "version": "1.0.0",
    "workspace_version": "1.0",
}


# ============================================================
# PATH SECURITY
# ============================================================

def resolve_project_path(
    relative_path: str,
    root: Path | None = None,
) -> Path:
    """
    Convert a project-relative path into a safe absolute path.

    This prevents paths such as:

        ../../some_file.txt

    from escaping the active project root. The default root is the
    managed workspace; scope-aware callers pass the repository root
    to reach application files.

    Args:
        relative_path:
            Path relative to the active root.
        root:
            Filesystem root the path must stay inside. Defaults to
            the managed workspace.

    Returns:
        Safe absolute Path.

    Raises:
        ValueError:
            If the path is empty or outside the root.
    """

    if root is None:

        root = PROJECT_ROOT

    if not relative_path:

        raise ValueError(
            "A project-relative path is required."
        )

    # Normalize Windows separators.
    relative_path = relative_path.replace(
        "\\",
        "/",
    )

    candidate = (
        root / relative_path
    ).resolve()

    try:

        candidate.relative_to(
            root
        )

    except ValueError:

        raise ValueError(
            "Access outside the project directory "
            "is not allowed."
        )

    return candidate


# ============================================================
# BROWSER ROOT RESOLUTION
# ============================================================

def split_root(
    relative_path: str,
) -> tuple[str | None, str]:
    """
    Split a path into its browser-root name and the remainder.

    Returns:
        ``(root_name, remainder)``. ``root_name`` is None when the
        first segment is not a known root, meaning the caller
        should treat the path as legacy and root-relative.
    """

    normalized = relative_path.replace(
        "\\",
        "/",
    ).strip()

    head, separator, tail = normalized.partition(
        "/"
    )

    if not separator:

        return None, normalized

    if head in BROWSE_ROOTS:

        return head, tail

    return None, normalized


def is_writable_root(
    root_name: str | None,
) -> bool:
    """
    Whether a browser root accepts writes.

    Legacy (root-less) paths are treated as writable so existing
    callers keep working.
    """

    if root_name is None:

        return True

    return bool(
        BROWSE_ROOTS[root_name].get(
            "writable",
            False,
        )
    )


def resolve_browse_target(
    relative_path: str,
    legacy_root: Path | None = None,
) -> tuple[str, Path, str | None]:
    """
    Split a possibly root-qualified path into the arguments the
    filesystem operations expect.

    ``source_files/AGENTS.md`` resolves inside the ``source_files``
    root. Paths without a known root prefix fall back to
    ``legacy_root`` (the managed workspace by default) so existing
    API callers are unaffected.

    Args:
        relative_path:
            Root-qualified or legacy relative path.
        legacy_root:
            Root used when the path carries no root prefix.

    Returns:
        ``(stripped_relative, root, root_name)``. ``root_name`` is
        None for legacy paths.

    Raises:
        ValueError:
            If the path is empty or names a root with no remainder.
    """

    root_name, remainder = split_root(
        relative_path
    )

    if root_name is None:

        return (
            relative_path,
            legacy_root
            if legacy_root is not None
            else PROJECT_ROOT,
            None,
        )

    if not remainder:

        raise ValueError(
            "A path inside "
            f"{root_name} is required."
        )

    return (
        remainder,
        BROWSE_ROOTS[root_name]["path"],
        root_name,
    )


def resolve_browse_path(
    relative_path: str,
    legacy_root: Path | None = None,
) -> tuple[Path, str | None]:
    """
    Resolve a possibly root-qualified path to a safe absolute path.

    Returns:
        ``(absolute_path, root_name)``. ``root_name`` is None for
        legacy paths.

    Raises:
        ValueError:
            If the path is empty or escapes its root.
    """

    stripped, root, root_name = (
        resolve_browse_target(
            relative_path,
            legacy_root,
        )
    )

    return resolve_project_path(
        stripped,
        root,
    ), root_name


def require_writable(
    relative_path: str,
    legacy_root: Path | None = None,
) -> str | None:
    """
    Ensure a path may be written to.

    Args:
        relative_path:
            Root-qualified or legacy relative path.
        legacy_root:
            Root used when the path carries no root prefix.

    Returns:
        The resolved root name (None for legacy paths).

    Raises:
        ValueError:
            If the path targets a read-only root.
    """

    _, root_name = resolve_browse_path(
        relative_path,
        legacy_root,
    )

    if not is_writable_root(root_name):

        raise ValueError(
            f"{root_name} is read-only."
        )

    return root_name


def read_browse_filesystem() -> list[dict[str, Any]]:
    """
    Build the browser tree.

    The top level is always the configured ``BROWSE_ROOTS`` folders,
    so the tree itself acts as the folder switcher. Every node path
    is prefixed with its root name.

    Roots that do not exist on disk are skipped.
    """

    results: list[dict[str, Any]] = []

    for root_name, config in BROWSE_ROOTS.items():

        root_path: Path = config["path"]

        if not root_path.is_dir():

            continue

        results.append(
            {
                "name": root_name,
                "path": root_name,
                "type": "directory",
                "root": root_name,
                "writable": bool(
                    config.get("writable", False)
                ),
                "children": read_filesystem(
                    root_path,
                    _root=root_path,
                    _prefix=root_name,
                ),
            }
        )

    return results


# ============================================================
# PROJECT INITIALIZATION
# ============================================================

def build_project_filesystem() -> None:
    """
    Create the standard Project Manager filesystem.

    Existing files and folders are never deleted.

    Safe to run every time the server starts.
    """

    # --------------------------------------------------------
    # Create standard directories
    # --------------------------------------------------------

    for folder_name in PROJECT_FOLDERS:

        folder_path = (
            PROJECT_ROOT / folder_name
        )

        folder_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    # --------------------------------------------------------
    # Create project.json
    # --------------------------------------------------------

    if not PROJECT_JSON.exists():

        PROJECT_JSON.write_text(
            json.dumps(
                DEFAULT_PROJECT,
                indent=4,
            ),
            encoding="utf-8",
        )


# ============================================================
# PROJECT INFORMATION
# ============================================================

def read_project_info() -> dict[str, Any]:
    """
    Read project.json.

    Returns:
        Project information dictionary.
    """

    if not PROJECT_JSON.exists():

        return DEFAULT_PROJECT.copy()

    try:

        return json.loads(
            PROJECT_JSON.read_text(
                encoding="utf-8"
            )
        )

    except (
        json.JSONDecodeError,
        OSError,
    ):

        return DEFAULT_PROJECT.copy()


# ============================================================
# FILE FILTERING
# ============================================================

def should_ignore(path: Path) -> bool:
    """
    Determine whether a path should be hidden
    from the project browser.
    """

    return any(
        part in IGNORED_DIRECTORIES
        for part in path.parts
    )


def is_text_file(path: Path) -> bool:
    """
    Determine whether a file should be editable.

    Files without extensions are treated as text files.
    """

    if path.suffix == "":
        return True

    return (
        path.suffix.lower()
        in TEXT_EXTENSIONS
    )


def is_oversized(path: Path) -> bool:
    """
    Determine whether a file is too large to edit in the browser.

    Very large files are marked non-editable so the editor does
    not try to render a multi-megabyte document.
    """

    try:

        return path.stat().st_size > MAX_EDITABLE_BYTES

    except OSError:

        return False


# ============================================================
# READ FILESYSTEM
# ============================================================

def read_filesystem(
    directory: Path | None = None,
    _root: Path | None = None,
    _prefix: str = "",
) -> list[dict[str, Any]]:
    """
    Recursively read the project filesystem.

    Args:
        directory:
            Directory to list.
        _root:
            Root the emitted paths are relative to.
        _prefix:
            Prepended to every emitted path. Used by
            :func:`read_browse_filesystem` so each node carries its
            browser-root name (``source_files/AGENTS.md``), which is
            what lets the API resolve the path back to its root.

    Returns:
        JSON-friendly file/folder tree.
    """

    if directory is None:

        directory = PROJECT_ROOT

    if _root is None:

        _root = directory

    results: list[dict[str, Any]] = []

    try:

        children = sorted(
            directory.iterdir(),
            key=lambda item: (
                not item.is_dir(),
                item.name.lower(),
            ),
        )

    except (
        OSError,
        PermissionError,
    ):

        return results

    for child in children:

        if should_ignore(child):

            continue

        relative_path = child.relative_to(
            _root
        )

        relative_path = str(
            relative_path
        ).replace(
            "\\",
            "/",
        )

        if _prefix:

            relative_path = (
                f"{_prefix}/{relative_path}"
            )

        # ----------------------------------------------------
        # DIRECTORY
        # ----------------------------------------------------

        if child.is_dir():

            results.append(
                {
                    "name": child.name,
                    "path": relative_path,
                    "type": "directory",
                    "children": read_filesystem(
                        child,
                        _root=_root,
                        _prefix=_prefix,
                    ),
                }
            )

        # ----------------------------------------------------
        # FILE
        # ----------------------------------------------------

        else:

            try:

                size = child.stat().st_size

            except OSError:

                size = 0

            results.append(
                {
                    "name": child.name,
                    "path": relative_path,
                    "type": "file",
                    "size": size,
                    "editable": (
                        is_text_file(child)
                        and not is_oversized(child)
                    ),
                }
            )

    return results


# ============================================================
# PROJECT STATE
# ============================================================

def get_project_state() -> dict[str, Any]:
    """
    Return complete project information.

    This is the primary function used by server.py.
    """

    return {
        "project": read_project_info(),
        "root": str(PROJECT_ROOT),
        "filesystem": read_filesystem(),
    }


# ============================================================
# READ FILE
# ============================================================

def read_file(
    relative_path: str,
    root: Path | None = None,
) -> str:
    """
    Read a text file.

    Args:
        relative_path:
            Project-relative file path.
        root:
            Filesystem root. Defaults to the managed workspace.

    Returns:
        File contents.

    Raises:
        ValueError:
            Invalid path or file type.
        FileNotFoundError:
            File does not exist.
    """

    file_path = resolve_project_path(
        relative_path,
        root,
    )

    if not file_path.exists():

        raise FileNotFoundError(
            "File not found."
        )

    if not file_path.is_file():

        raise ValueError(
            "Path is not a file."
        )

    if not is_text_file(file_path):

        raise ValueError(
            "This file type is not editable."
        )

    try:

        return file_path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        raise ValueError(
            "File is not a UTF-8 text file."
        )


# ============================================================
# WRITE FILE
# ============================================================

def write_file(
    relative_path: str,
    content: str,
    root: Path | None = None,
) -> None:
    """
    Create or overwrite a text file.

    Parent directories are automatically created.
    """

    file_path = resolve_project_path(
        relative_path,
        root,
    )

    if not is_text_file(file_path):

        raise ValueError(
            "This file type cannot be edited."
        )

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path.write_text(
        content,
        encoding="utf-8",
    )


# ============================================================
# CREATE FILE
# ============================================================

def create_file(
    relative_path: str,
    content: str = "",
    root: Path | None = None,
) -> None:
    """
    Create a new file.

    Refuses to overwrite an existing file.
    """

    file_path = resolve_project_path(
        relative_path,
        root,
    )

    if file_path.exists():

        raise FileExistsError(
            "A file or directory with that "
            "name already exists."
        )

    if not is_text_file(file_path):

        raise ValueError(
            "This file type cannot be created "
            "by the text editor."
        )

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path.write_text(
        content,
        encoding="utf-8",
    )


# ============================================================
# CREATE DIRECTORY
# ============================================================

def create_directory(
    relative_path: str,
    root: Path | None = None,
) -> None:
    """
    Create a directory.
    """

    directory = resolve_project_path(
        relative_path,
        root,
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# RENAME
# ============================================================

def rename_path(
    old_path: str,
    new_path: str,
    root: Path | None = None,
) -> None:
    """
    Rename or move a file/directory within the active root.

    Both paths must remain inside the active root.
    """

    source = resolve_project_path(
        old_path,
        root,
    )

    destination = resolve_project_path(
        new_path,
        root,
    )

    if not source.exists():

        raise FileNotFoundError(
            "The source path does not exist."
        )

    if destination.exists():

        raise FileExistsError(
            "The destination already exists."
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    source.rename(
        destination
    )


# ============================================================
# DELETE
# ============================================================

def delete_path(
    relative_path: str,
    root: Path | None = None,
) -> None:
    """
    Delete a file or directory.

    Directories are deleted recursively.

    The active root itself cannot be deleted.
    """

    target = resolve_project_path(
        relative_path,
        root,
    )

    if target == root or target == PROJECT_ROOT:

        raise ValueError(
            "The project root cannot be deleted."
        )

    if not target.exists():

        raise FileNotFoundError(
            "Path not found."
        )

    if target.is_dir():

        shutil.rmtree(target)

    else:

        target.unlink()


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Initializing Project Manager..."
    )

    build_project_filesystem()

    print()
    print("Project root:")
    print(PROJECT_ROOT)

    print()
    print("Project information:")

    print(
        json.dumps(
            read_project_info(),
            indent=4,
        )
    )

    print()
    print("Project filesystem:")

    print(
        json.dumps(
            read_filesystem(),
            indent=4,
        )
    )
```

---

<!-- ==== 36/44 : README.md ==== -->

### README.md

````markdown
# Project Manager

A lightweight FastAPI workspace server. Browse, edit, chat about, and run AI
agents on your project from a single web dashboard with a Monaco-powered code
editor. The server embeds the headless agent engine, so agents run in-process
against the managed workspace (no separate agent process needed).

## Layout

The repository is split into three pillars plus scripts:

```
├── server.py                Application entry point (FastAPI host)
├── requirements.txt
│
├── interface/               EDITOR INTERFACE
│   ├── static/              Web UI (home.html, chat.html, editor.html, js/)
│   ├── routers/             HTTP API routers (files, dirs, paths, ws, chat, agents)
│   ├── core/                Controller layer (sessions, events, operations)
│   └── clients/             Python client (EditorClient / AsyncEditorClient)
│
├── parameters/              PROJECT PARAMETERS
│   └── filesystem.py        Filesystem owner for the managed workspace
│
├── workspace/               THE MANAGED PROJECT
│   ├── project.json
│   ├── agents/              User agents: agents/<name>/agent.json + agent.md
│   ├── documentation/  project_scope/  to_do/  updates/  config/  data/
│
└── scripts/                 run.bat / run.sh / setup.sh (uses shared ..\.venv)
```

The dashboard and editor operate in two scopes:

- **Workspace** — the managed project (`workspace/`). Default.
- **Dev** — the application's own scripts (`server.py`, `interface/`, …). Reach
  them via the "Dev scripts" quick links in the sidebar or the Dev scope toggle,
  so app code only shows up when you need it.

## Features

- Unified home page: project tree + Monaco editor + scope toggle
- Collapsible folder tree (folders start collapsed, VS Code style)
- Per-file-type icons (Python, HTML, CSS, JS/TS, Markdown, config, …)
- Chat (`/chat`) — agent-backed; send a prompt with an optional agent + model
  selector; replies are logged to `workspace/data/chat.log`
- Agent panel in the editor: create/run a single agent from the current file,
  scaffold a new workspace agent, or queue multiple agents as a **pipeline**
  (cascade) and run them in order
- Cascade pipelines: each agent sees the previous agents' replies; every step
  records which tools it used and prints `Agent N (<id>) completed. Tools used: ...`
  to the terminal, finishing with `PIPELINE COMPLETE (n/n) -> ...`
- Workspace agents: drop `agents/<name>/agent.json` + `agent.md` into the
  workspace to register a new agent (library agents like `feature_planner_agent`,
  `execute_engineer_agent`, and `module_builder_agent` stay available too)
- JSON REST API for filesystem operations (scope-aware) plus agent registry,
  run, and pipeline endpoints
- Python client for AI agents / other programs
- Works on Windows and (Chromebook) Linux

## Requirements

- Python 3.9+
- Network access for the code editor CDN (Monaco, loaded from cdnjs)

## Setup

### Windows

```bat
python -m venv ..\.venv
..\.venv\Scripts\python -m pip install -r requirements.txt
scripts\run.bat
```

The launcher scripts prefer the shared venv (`..\.venv` relative to
`project_manager/`) and fall back to a local one if it is missing. Helpers for
creating/activating the venv live in `scripts/venv.ps1` and `scripts/venv.bat`
(activate with `.venv\Scripts\Activate.ps1`).

### Chromebook (ChromeOS with Linux/Crostini)

Open a Linux terminal and enable the Linux apps if you have not already:

```sh
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

Clone the repo, then:

```sh
cd scripts
./setup.sh
./run.sh
```

Then open `http://127.0.0.1:8000` in the Chrome browser. On ChromeOS the
browser can reach the Linux container through `127.0.0.1`.

## Configuration

The server binds to `127.0.0.1:8000` by default. Override with environment
variables:

```sh
PROJECT_MANAGER_HOST=0.0.0.0 PROJECT_MANAGER_PORT=8080 ./run.sh
```

## API overview

| Method | Path                          | Description                          |
| ------ | ----------------------------- | ------------------------------------ |
| GET    | `/`                           | Unified home UI (tree + editor)      |
| GET    | `/edit`                       | Editor UI (Monaco + agent panel)     |
| GET    | `/chat`                       | Chat UI (agent + model selectors)    |
| GET    | `/api/health`                 | Health + project info                |
| GET    | `/api/project?scope=`         | Project state + tree (ws/app)        |
| GET    | `/api/file/read?path=&scope=` | Read a file                          |
| PUT    | `/api/file/write`             | Write a file                         |
| POST   | `/api/file/create`            | Create a file                        |
| POST   | `/api/directory/create`       | Create a directory                   |
| PUT    | `/api/path/rename`            | Rename/move a path                   |
| DELETE | `/api/file/delete`            | Delete a file                        |
| DELETE | `/api/directory/delete`       | Delete a directory                   |
| GET    | `/api/agents`                 | Agent registry (library + workspace) |
| GET    | `/api/agents/{agent_id}`      | Agent detail (meta + sections)       |
| POST   | `/api/agents/run`             | Run a single agent (json_path/md_path)|
| GET    | `/api/pipeline`               | Pipeline options + default steps     |
| POST   | `/api/pipeline`               | Run a cascade pipeline (steps queue) |
| GET    | `/api/models`                 | Available models (config/models.json)|
| POST   | `/api/chat`                   | Send a chat message (agent-backed)   |
| GET    | `/api/chat`                   | Chat history                         |

Note: The `workspace/` content folders are empty so git does not track
them; the server recreates them automatically on startup.

## Agents & pipelines

Agents come from two places:

- **Library** — bundled with the engine (`headless_app/engine/agent_library/`),
  e.g. `feature_planner_agent`, `execute_engineer_agent`, `module_builder_agent`.
- **Workspace** — your own, kept as `workspace/agents/<name>/agent.json`
  (metadata: id, name, description, mode, model, tools) plus `agent.md`
  (markdown spec with `## role` / `## purpose` sections). Select the *workspace*
  scope in the editor, drop the two files in, and the agent appears in the
  registry automatically.

Run options:

- **Single agent** (`POST /api/agents/run`): the agent's tools have the same
  filesystem authority as the dashboard, so it can read/write files in the
  workspace. From the editor, open a file and hit "Run Agent" in the panel.
- **Pipeline / cascade** (`POST /api/pipeline`): ordered list of steps (agent id
  or `{json_path, md_path}` objects). Each later step receives the earlier
  replies, so agents can hand off work. Results are stored per step (with
  `tools_used`) in `headless_app/data/pipeline_runs.jsonl`.
- **Chat** (`/chat`): pick an agent and model, send a message, and the thread is
  logged to `workspace/data/chat.log`. With no agent selected, the chat uses its
  default message-only behavior.
````

---

<!-- ==== 37/44 : requirements.txt ==== -->

### requirements.txt

```text
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
websockets==13.1
```

---

<!-- ==== 38/44 : scripts/run.bat ==== -->

### scripts/run.bat

```batch
@echo off
rem Project Manager - start the server from the shared virtual environment.

cd /d "%~dp0.."

set "PYTHON="
if exist "..\.venv\Scripts\python.exe" set "PYTHON=..\.venv\Scripts\python.exe"
if not defined PYTHON if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if not defined PYTHON set "PYTHON=python"

echo Starting Project Manager at http://127.0.0.1:8000
echo To stop: press Ctrl+C
echo.

%PYTHON% server.py
```

---

<!-- ==== 39/44 : scripts/run.sh ==== -->

### scripts/run.sh

```bash
#!/usr/bin/env bash
#
# Project Manager - start the server from the virtual environment.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ -x "$PROJECT_DIR/../.venv/bin/python" ]; then
    PYTHON="$PROJECT_DIR/../.venv/bin/python"
elif [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

echo "Starting Project Manager at http://127.0.0.1:8000"
echo "To stop: press Ctrl+C"
echo

"$PYTHON" server.py
```

---

<!-- ==== 40/44 : scripts/setup.sh ==== -->

### scripts/setup.sh

```bash
#!/usr/bin/env bash
#
# Project Manager - one-time setup for (Chromebook) Linux.
# Creates a virtual environment and installs dependencies.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 was not found." >&2
    echo "On ChromeOS, enable Linux and then run:" >&2
    echo "  sudo apt update" >&2
    echo "  sudo apt install -y python3 python3-venv python3-pip" >&2
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

echo "Installing dependencies..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo
echo "Setup complete. Start the server with:  ./run.sh"
echo "Then open:  http://127.0.0.1:8000"
```

---

<!-- ==== 41/44 : server.py ==== -->

### server.py

```python
"""Project Manager Server - application entry point.

Slim FastAPI host. The Project Manager remains the filesystem
authority (parameters.filesystem); this file only assembles the
three pillars and the static workspace:

    parameters          Project parameters (filesystem owner)
    workspace           The managed project content
    interface           Editor interface (core, routers, clients, static)

The controller is the single shared resource responsible for
turning Project Manager operations into HTTP contracts.

    interface/routers/project.py      Project state, health, sessions
    interface/routers/files.py        File CRUD / REST
    interface/routers/directories.py  Directory CRUD
    interface/routers/paths.py        Rename / move
    interface/routers/ws.py           Real-time WebSocket interface
    interface/routers/chat.py         Chat log (stub) interface
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from parameters import filesystem

from interface.routers.project import router as project_router
from interface.routers.files import router as files_router
from interface.routers.directories import router as directories_router
from interface.routers.paths import router as paths_router
from interface.routers.ws import router as ws_router
from interface.routers.chat import router as chat_router
from interface.routers.agents import router as agents_router

from interface.core.defaults import get_interface, get_events, get_sessions


# ============================================================
# CONFIGURATION
# ============================================================

HOST = os.environ.get(
    "PROJECT_MANAGER_HOST",
    "127.0.0.1",
)

PORT = int(
    os.environ.get(
        "PROJECT_MANAGER_PORT",
        "8000",
    )
)

PROJECT_ROOT = Path(__file__).resolve().parent

STATIC_DIR = PROJECT_ROOT / "interface" / "static"

HOME_HTML = STATIC_DIR / "home.html"

EDITOR_HTML = STATIC_DIR / "editor.html"

CHAT_HTML = STATIC_DIR / "chat.html"


# ============================================================
# APPLICATION FACTORY
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Build the basic project filesystem on startup.
    """

    filesystem.build_project_filesystem()

    yield


def create_app() -> FastAPI:
    """
    Assemble the Project Manager application.
    """

    app = FastAPI(
        title="Project Manager Server",
        description="Lightweight Project Manager workspace server.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # --------------------------------------------------------
    # Shared interface state
    # --------------------------------------------------------

    app.state.editor = get_interface()
    app.state.events = get_events()
    app.state.sessions = get_sessions()

    # --------------------------------------------------------
    # Routers
    # --------------------------------------------------------

    app.include_router(project_router)
    app.include_router(files_router)
    app.include_router(directories_router)
    app.include_router(paths_router)
    app.include_router(ws_router)
    app.include_router(chat_router)
    app.include_router(agents_router)

    # --------------------------------------------------------
    # Static workspace
    # --------------------------------------------------------

    if STATIC_DIR.is_dir():

        app.mount(
            "/static",
            StaticFiles(directory=STATIC_DIR),
            name="static",
        )

    @app.get("/")
    def home():
        return FileResponse(HOME_HTML)

    @app.get("/chat")
    def chat():
        return FileResponse(CHAT_HTML)

    @app.get("/editor")
    def editor():
        return FileResponse(EDITOR_HTML)

    return app


# ============================================================
# APPLICATION INSTANCE
# ============================================================

app = create_app()


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
    )
```

---

<!-- ==== 42/44 : workspace/agents/ProjectManager/agent.json ==== -->

### workspace/agents/ProjectManager/agent.json

```json
{
  "id": "test",
  "name": "Project Manager",
  "description": "A custom agent for planning projects.",
  "mode": "agent",
  "model": "",
  "tools": [
    "map_files",
    "read_file",
    "write_text_file"
  ]
}
```

---

<!-- ==== 43/44 : workspace/agents/ProjectManager/agent.md ==== -->

### workspace/agents/ProjectManager/agent.md

```markdown
# test

## role

You are test, a helpful Project Manager agent.

## purpose

Describe what this agent accomplishes and when it is used.

## boundaries

State what this agent will not do.

## output format

Describe the shape of the reply the agent must produce.
```

---

<!-- ==== 44/44 : workspace/project.json ==== -->

### workspace/project.json

```json
{
    "name": "Project Manager",
    "version": "1.0.0",
    "workspace_version": "1.0"
}
```

---

> Generated by `scripts/gen_master_copy.py` on 2026-09-25. Do not edit by hand; regenerate with:
>
> ```bat
> .venv/Scripts/python -m scripts.gen_master_copy
> ```
