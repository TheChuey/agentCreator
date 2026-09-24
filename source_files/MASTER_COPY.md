# Project Manager — MASTER COPY

Single-file snapshot of the complete Project Manager application source tree.

- **Project:** Project Manager
- **Version:** 1.0.0
- **Workspace version:** 1.0
- **Repo:** https://github.com/TheChuey/project
- **Generated:** 2026-09-23

---

## AI Agent Engine — Entry Point

The chat endpoint is the **AI agent engine entry point** for the project.

This is where an agent / request-model plugs into the application. The editor
interface (and the home page) reach the engine through the exact same stable
HTTP surface, so the engine can be swapped without touching the UI:

| Route       | Method | Purpose                                                    |
| ----------- | ------ | ---------------------------------------------------------- |
| `/api/chat` | POST   | Send a message to the agent engine. Body: `{"message": str, "scope": str?}`. |
| `/api/chat` | GET    | Fetch recent agent conversation history (`?limit=`).        |

The engine lives in `interface/routers/chat.py` and persists history to
`workspace/data/chat.log` (JSON lines). Anything — the home page chat popup,
the editor's chat button, or a future AI/agent process — goes through this one
entry point, keeping the full app decoupled from the engine implementation.

```text
┌────────────────────┐   POST /api/chat   ┌────────────────────────┐
│  editor interface  │ ──────────────────▶│  agent engine          │
│  (home / editor)   │                    │  interface/routers/    │
│                    │ ◀──────────────────│        chat.py         │
└────────────────────┘       reply        └────────────────────────┘
```

---

## Editor Interface — Accessing the Agent Tools

The editor's browser interface reaches the agent engine and the code tools
through `interface/static/js/api.js` and `interface/static/js/session.js`.
Every agent tool the interface can touch is exposed as a small API method:

| Front-end accessor        | Backend route                       | Purpose                          |
| ------------------------- | ----------------------------------- | -------------------------------- |
| `API.chatSend(message)`   | `POST /api/chat`                    | Send a message to the agent      |
| `API.chatHistory(limit)`  | `GET /api/chat?limit=`              | Read agent conversation history  |
| `API.fileRead(path)`      | `GET /api/file/read?path=`          | Open a file in the editor        |
| `API.fileWrite(path, c)`  | `PUT /api/file/write`               | Save the current buffer          |
| `API.project(scope)`      | `GET /api/project?scope=`           | Reload the file tree             |
| `API.pathRename(a, b)`    | `PUT /api/path/rename`              | Rename a file / folder           |
| `API.fileDelete(path)`    | `DELETE /api/file/delete?path=`     | Delete a file                    |
| `API.directoryDelete(p)`  | `DELETE /api/directory/delete?path=`| Delete a folder                  |

The editor toolbar exposes these tools as buttons:

- **Save** (`Ctrl+S`) → `API.fileWrite` on the current file
- **+ File / + Folder / Rename / Delete** → the matching create/rename/delete
  accessors above
- **Chat** button → opens the chat popup, which calls `API.chatSend`
- **Dev links** sidebar → opens app-scope files through `API.fileRead`

For new agent tools, the pattern to follow is: add
`schema -> route -> API.* accessor -> toolbar/popup button`. Nothing else in
the app changes, because every surface already talks to the API client.

---

## File Structure

```text
project/
    ├── interface
    │   ├── clients
    │   ├── core
    │   ├── routers
    │   └── static
    │       └── js
    ├── parameters
    ├── scripts
    └── workspace
        ├── config
        ├── data
        ├── documentation
        ├── project_scope
        ├── to_do
        └── updates
```

---

---

<!-- ==== 1/39 : .gitattributes ==== -->

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

<!-- ==== 2/39 : .gitignore ==== -->

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

<!-- ==== 3/39 : interface/clients/__init__.py ==== -->

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

<!-- ==== 4/39 : interface/clients/editor_client.py ==== -->

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

<!-- ==== 5/39 : interface/core/__init__.py ==== -->

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

<!-- ==== 6/39 : interface/core/defaults.py ==== -->

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

<!-- ==== 7/39 : interface/core/events.py ==== -->

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

<!-- ==== 8/39 : interface/core/operations.py ==== -->

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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Project state: project info, active root and filesystem tree.

        Args:
            scope:
                ``"workspace"`` (default) or ``"app"``.
        """

        try:

            root = _root_for(scope)

            return {
                "scope": scope or "workspace",
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
        scope: str | None = "workspace",
    ) -> str:
        """
        Open a project file and return its contents.

        Args:
            path:
                Root-relative file path.
            scope:
                ``"workspace"`` (default) or ``"app"``.

        Returns:
            The file contents.
        """

        return self.filesystem.read_file(
            path,
            root=_root_for(scope),
        )

    def save(
        self,
        path: str,
        content: str,
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Write file contents back to the project filesystem.

        Publishes a ``saved`` event on success.
        """

        self.filesystem.write_file(
            path,
            content,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Create a new project file.

        Publishes a ``created`` event on success.
        """

        self.filesystem.create_file(
            path,
            content,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Create a new project directory.

        Publishes a ``created`` event on success.
        """

        self.filesystem.create_directory(
            path,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Rename or move a project file/directory.

        Publishes a ``renamed`` event on success.
        """

        self.filesystem.rename_path(
            old_path,
            new_path,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Delete a project file or directory.

        Publishes a ``deleted`` event on success.
        """

        self.filesystem.delete_path(
            path,
            root=_root_for(scope),
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

<!-- ==== 9/39 : interface/core/session.py ==== -->

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

<!-- ==== 10/39 : interface/routers/__init__.py ==== -->

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

def normalize_scope(scope: str | None) -> str:
    """
    Validate and normalize a scope query parameter.

    Raises:
        HTTPException (422):
            If the scope is not a known scope.
    """

    scope = scope or "workspace"

    if scope not in VALID_SCOPES:

        raise HTTPException(
            status_code=422,
            detail=f"Unknown scope: {scope}",
        )

    return scope
```

---

<!-- ==== 11/39 : interface/routers/chat.py ==== -->

### interface/routers/chat.py

```python
"""
Project Manager chat router (stub).
====================================

Chat stub for the interface. Messages are appended to a plaintext
log file inside the managed workspace (``workspace/data/chat.log``)
so history survives reloads. This is a placeholder surface: a real
AI agent can replace the handler later without changing the API
shape (``POST /api/chat`` to send, ``GET /api/chat`` to fetch).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from parameters import filesystem

from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# REQUEST MODELS
# ============================================================

class ChatMessage(BaseModel):

    message: str


# ============================================================
# CHAT LOG HELPERS
# ============================================================

MAX_MESSAGE_LENGTH = 2000

DEFAULT_LIMIT = 50

MAX_LIMIT = 500


def _log_path() -> Any:
    """
    Safe path to the chat log inside the managed workspace.
    """

    return filesystem.resolve_project_path(
        "data/chat.log"
    )


def _append_message(message: str) -> dict[str, Any]:
    """
    Append one timestamped message to the chat log.

    The data directory is created on demand.
    """

    log_path = _log_path()

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sender": "user",
        "message": message,
    }

    with log_path.open(
        "a",
        encoding="utf-8",
    ) as handle:

        handle.write(
            json.dumps(entry) + "\n"
        )

    return entry


def _read_history(limit: int) -> list[dict[str, Any]]:
    """
    Read the most recent chat log entries in chronological order.
    """

    log_path = _log_path()

    if not log_path.exists():

        return []

    entries: list[dict[str, Any]] = []

    with log_path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        for line in handle:

            line = line.strip()

            if not line:
                continue

            try:

                entries.append(
                    json.loads(line)
                )

            except json.JSONDecodeError:
                continue

    return entries[-limit:]


# ============================================================
# SEND MESSAGE
# ============================================================

@router.post("/api/chat")
def send_chat_message(
    request: Request,
    payload: ChatMessage,
):
    """
    Log a chat message.

    The stub currently records the message; a future agent
    provider can reply through the same endpoint.
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

    try:

        entry = _append_message(message)

        return {
            "status": "logged",
            "entry": entry,
        }

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

    limit = max(1, min(limit, MAX_LIMIT))

    try:

        return {
            "entries": _read_history(limit),
        }

    except Exception as error:

        raise project_manager_error(
            error
        )
```

---

<!-- ==== 12/39 : interface/routers/directories.py ==== -->

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
    scope: str = "workspace",
):
    """
    Create a project directory.

    Query params:
        path:
            Root-relative directory path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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
    scope: str = "workspace",
):
    """
    Delete a project directory.

    Query params:
        path:
            Root-relative directory path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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

<!-- ==== 13/39 : interface/routers/errors.py ==== -->

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

<!-- ==== 14/39 : interface/routers/files.py ==== -->

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

    scope: str = "workspace"


class FileCreateRequest(BaseModel):

    path: str

    content: str = ""

    scope: str = "workspace"


# ============================================================
# READ FILE
# ============================================================

@router.get("/api/file/read")
def read_file(
    request: Request,
    path: str,
    scope: str = "workspace",
):
    """
    Read a project text file.

    Query params:
        path:
            Root-relative file path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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
    scope: str = "workspace",
):
    """
    Delete a project file.

    Query params:
        path:
            Root-relative file path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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

<!-- ==== 15/39 : interface/routers/paths.py ==== -->

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

    scope: str = "workspace"


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

<!-- ==== 16/39 : interface/routers/project.py ==== -->

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
    scope: str = "workspace",
):
    """
    Project information and filesystem tree.

    Query params:
        scope:
            ``"workspace"`` (default) or ``"app"``.
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

<!-- ==== 17/39 : interface/routers/ws.py ==== -->

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

    session = controller.sessions.register()

    try:

        await websocket.send_json(
            {
                "type": "hello",
                "client_id": session.client_id,
            }
        )

        async def forward(
            event: dict[str, Any],
        ) -> None:
            """
            Forward a published event to this socket.
            """

            try:

                await websocket.send_json(
                    {
                        "type": "event",
                        "event": event,
                    }
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
                    "sessions": controller.sessions.snapshot(),
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

                controller.sessions.update(
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

                controller.sessions.update(
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

        controller.sessions.unregister(
            session.client_id
        )
```

---

<!-- ==== 18/39 : interface/static/chat.html ==== -->

### interface/static/chat.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Manager Chat</title>

    <style>
        /* =========================================================
           RESET / BASE
           ========================================================= */

        * {
            box-sizing: border-box;
        }

        html,
        body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family:
                Inter,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Arial,
                sans-serif;
            background: #0f1117;
            color: #e6e8ee;
        }

        body {
            display: flex;
            flex-direction: column;
        }

        button,
        textarea {
            font-family: inherit;
        }


        /* =========================================================
           TOP BAR
           ========================================================= */

        .chatbar {
            height: 58px;
            min-height: 58px;

            display: flex;
            align-items: center;
            justify-content: space-between;

            padding: 0 20px;

            background: #151821;
            border-bottom: 1px solid #292d38;
        }

        .chat-title-area {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .chat-icon {
            width: 34px;
            height: 34px;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 9px;

            background: #252a38;
            border: 1px solid #343949;

            font-size: 17px;
        }

        .title {
            font-size: 15px;
            font-weight: 600;
            color: #f1f3f7;
        }

        .subtitle {
            margin-top: 2px;
            font-size: 11px;
            color: #7f8798;
        }

        .status-area {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #777;
        }

        .status {
            font-size: 12px;
            color: #8991a2;
        }


        /* =========================================================
           MAIN CHAT AREA
           ========================================================= */

        #chatLog {
            flex: 1;

            overflow-y: auto;

            padding: 28px 22px 30px;

            display: flex;
            flex-direction: column;
            gap: 14px;

            background:
                radial-gradient(
                    circle at top center,
                    rgba(58, 65, 85, 0.12),
                    transparent 45%
                ),
                #0f1117;
        }

        /* Scrollbar */

        #chatLog::-webkit-scrollbar {
            width: 8px;
        }

        #chatLog::-webkit-scrollbar-track {
            background: transparent;
        }

        #chatLog::-webkit-scrollbar-thumb {
            background: #303543;
            border-radius: 10px;
        }

        #chatLog::-webkit-scrollbar-thumb:hover {
            background: #3b4150;
        }


        /* =========================================================
           MESSAGE CARD
           ========================================================= */

        .msg {
            width: min(850px, 90%);

            display: flex;
            flex-direction: column;
            gap: 6px;

            padding: 13px 15px;

            border-radius: 12px;

            background: #181b24;
            border: 1px solid #292d38;

            box-shadow:
                0 4px 14px rgba(0, 0, 0, 0.12);
        }

        .msg-label {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.02em;
            color: #858d9e;
        }

        .msg-body {
            word-break: break-word;
            white-space: pre-wrap;

            font-size: 14px;
            line-height: 1.55;

            color: #dfe2e8;
        }

        .msg-meta {
            align-self: flex-end;

            font-size: 10px;
            color: #626a7a;
        }


        /* =========================================================
           USER MESSAGE
           ========================================================= */

        .msg.user {
            align-self: flex-end;

            background: #1b2634;
            border-color: #29445e;
        }

        .msg.user .msg-label {
            color: #70b7ed;
        }

        .msg.user .msg-body {
            color: #edf6ff;
        }


        /* =========================================================
           EVENT MESSAGE
           ========================================================= */

        .msg.event {
            width: min(750px, 85%);

            background: #151e19;
            border-color: #27402f;
        }

        .msg.event .msg-label {
            color: #72b784;
        }

        .msg.event .msg-body {
            color: #b9d8bf;
            font-size: 13px;
        }


        /* =========================================================
           SYSTEM MESSAGE
           ========================================================= */

        .msg.system {
            width: min(750px, 85%);

            background: #14161c;
            border-color: #292d35;
        }

        .msg.system .msg-label {
            color: #777f90;
        }

        .msg.system .msg-body {
            color: #9299a8;
            font-size: 13px;
        }


        /* =========================================================
           EMPTY / LOADING MESSAGE
           ========================================================= */

        .msg.system:first-child {
            opacity: 0.85;
        }


        /* =========================================================
           INPUT AREA
           ========================================================= */

        .chatfoot {
            padding: 14px 20px 18px;

            background: #151821;
            border-top: 1px solid #292d38;
        }

        .input-container {
            width: min(900px, 100%);
            margin: 0 auto;

            display: flex;
            align-items: flex-end;
            gap: 10px;

            padding: 9px;

            background: #1b1f29;
            border: 1px solid #303543;
            border-radius: 14px;

            transition:
                border-color 0.2s ease,
                box-shadow 0.2s ease;
        }

        .input-container:focus-within {
            border-color: #3d6d96;

            box-shadow:
                0 0 0 3px rgba(61, 109, 150, 0.12);
        }


        /* =========================================================
           TEXT INPUT
           ========================================================= */

        #chatInput {
            flex: 1;

            min-height: 42px;
            max-height: 160px;

            padding: 10px 11px;

            background: transparent;
            color: #edf0f5;

            border: none;
            outline: none;

            resize: none;

            font-size: 14px;
            line-height: 1.45;
        }

        #chatInput::placeholder {
            color: #697182;
        }


        /* =========================================================
           SEND BUTTON
           ========================================================= */

        #chatSend {
            width: 42px;
            height: 42px;

            display: flex;
            align-items: center;
            justify-content: center;

            flex-shrink: 0;

            border: 1px solid #3c4554;
            border-radius: 10px;

            background: #27303d;
            color: #dce7f2;

            cursor: pointer;

            font-size: 16px;

            transition:
                background 0.15s ease,
                border-color 0.15s ease,
                transform 0.1s ease;
        }

        #chatSend:hover {
            background: #314052;
            border-color: #4b5c70;
        }

        #chatSend:active {
            transform: scale(0.96);
        }

        #chatSend:disabled {
            opacity: 0.45;
            cursor: not-allowed;
        }


        /* =========================================================
           INPUT FOOTER HINT
           ========================================================= */

        .input-hint {
            width: min(900px, 100%);
            margin: 7px auto 0;

            text-align: center;

            font-size: 10px;
            color: #5f6675;
        }


        /* =========================================================
           RESPONSIVE
           ========================================================= */

        @media (max-width: 700px) {

            .chatbar {
                padding: 0 14px;
            }

            .subtitle {
                display: none;
            }

            #chatLog {
                padding: 18px 12px 22px;
            }

            .msg {
                width: 94%;
            }

            .chatfoot {
                padding: 10px 10px 12px;
            }

            .input-hint {
                display: none;
            }
        }
    </style>
</head>

<body>

    <!-- =========================================================
         HEADER
         ========================================================= -->

    <header class="chatbar">

        <div class="chat-title-area">

            <div class="chat-icon">
                💬
            </div>

            <div>
                <div class="title">
                    Project Chat
                </div>

                <div class="subtitle">
                    Project Manager
                </div>
            </div>

        </div>


        <div class="status-area">

            <span id="statusDot" class="status-dot"></span>

            <span id="chatStatus" class="status">
                Connecting…
            </span>

        </div>

    </header>


    <!-- =========================================================
         CHAT MESSAGES
         ========================================================= -->

    <main id="chatLog">

        <div class="msg system">

            <span class="msg-label">
                SYSTEM
            </span>

            <span class="msg-body">
                Loading messages…
            </span>

        </div>

    </main>


    <!-- =========================================================
         CHAT INPUT
         ========================================================= -->

    <footer class="chatfoot">

        <form id="chatForm">

            <div class="input-container">

                <textarea
                    id="chatInput"
                    rows="1"
                    placeholder="Message Project Manager…"
                    autocomplete="off"
                ></textarea>

                <button
                    id="chatSend"
                    type="submit"
                    aria-label="Send message"
                    title="Send message"
                >
                    ↑
                </button>

            </div>

        </form>

        <div class="input-hint">
            Press Enter to send · Shift + Enter for a new line
        </div>

    </footer>


    <!-- =========================================================
         EXISTING CHAT JAVASCRIPT
         ========================================================= -->

    <script type="module" src="/static/js/chat.js"></script>


    <!-- =========================================================
         SMALL UI ENHANCEMENTS
         These do not replace chat.js.
         ========================================================= -->

    <script>

        /*
         * Automatically grow the message box.
         * This does not communicate with the backend.
         */

        const chatInput = document.getElementById("chatInput");

        if (chatInput) {

            chatInput.addEventListener("input", () => {

                chatInput.style.height = "auto";

                chatInput.style.height =
                    Math.min(chatInput.scrollHeight, 160) + "px";

            });


            /*
             * Enter = send
             * Shift + Enter = new line
             *
             * The existing form submission handled by chat.js
             * remains responsible for actually sending the message.
             */

            chatInput.addEventListener("keydown", (event) => {

                if (
                    event.key === "Enter" &&
                    !event.shiftKey
                ) {

                    event.preventDefault();

                    const form =
                        document.getElementById("chatForm");

                    if (form) {
                        form.requestSubmit();
                    }

                }

            });

        }


        /*
         * Automatically keep the newest message visible.
         *
         * MutationObserver watches for messages added by chat.js.
         */

        const chatLog =
            document.getElementById("chatLog");

        if (chatLog) {

            const observer =
                new MutationObserver(() => {

                    chatLog.scrollTop =
                        chatLog.scrollHeight;

                });

            observer.observe(chatLog, {
                childList: true,
                subtree: true
            });

        }

    </script>

</body>
</html>

```

---

<!-- ==== 19/39 : interface/static/editor.html ==== -->

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
            height: calc(100vh - 74px);
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
    </style>

    <!-- Monaco Loader CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js"></script>
</head>
<body>

<div class="topbar">
    <div class="title">Project Manager Editor</div>
    <button id="homeBtn" onclick="goHome()">🏠 Home</button>
    <button id="saveBtn" class="primary" onclick="saveFile()">Save</button>
    <button id="newFileBtn" onclick="newFile()">+ File</button>
    <button id="newFolderBtn" onclick="newFolder()">+ Folder</button>
    <button id="renameBtn" onclick="renameSelected()">Rename</button>
    <button id="deleteBtn" class="danger" onclick="deleteSelected()">Delete</button>
    <button id="refreshBtn" onclick="refreshTree()">Refresh</button>
</div>

<div class="workspace">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span>PROJECT FILES</span>
        </div>
        <div id="tree" class="tree">Loading...</div>
    </div>
    
    <div class="resize-handle" id="resizeHandle"></div>

    <div class="editor-area">
        <div class="filebar">
            <div>
                <span id="currentFile">No file selected</span>
                <span id="unsavedIndicator"></span>
            </div>
            <div id="language">plaintext</div>
        </div>
        <div id="editor"></div>
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

<!-- ==== 20/39 : interface/static/home.html ==== -->

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

        .scope-toggle {
            display: flex;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            overflow: hidden;
            margin-right: 12px;
        }

        .scope-toggle button {
            border: none;
            border-radius: 0;
            background: #252526;
            padding: 6px 12px;
        }

        .scope-toggle button.active {
            background: #0e639c;
        }

        .workspace {
            display: flex;
            height: calc(100vh - 74px);
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

        /* ---- Dev scripts quick links ---- */
        .dev-links {
            border-bottom: 1px solid #3f3f46;
            padding: 8px;
        }

        .dev-links-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            font-weight: bold;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }

        .dev-link {
            display: block;
            width: 100%;
            text-align: left;
            background: transparent;
            border: 1px solid transparent;
            color: #d1d5db;
            padding: 4px 6px;
            border-radius: 3px;
            font-size: 12px;
            margin-bottom: 2px;
        }

        .dev-link:hover {
            background: #2a2d2e;
            border-color: #3f3f46;
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
    </style>

    <!-- Monaco Loader CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js"></script>
</head>
<body>

<div class="topbar">
    <div class="title">Project Manager</div>
    <span id="projectName">…</span>

    <div class="scope-toggle" role="group" aria-label="Scope">
        <button id="scopeWs" type="button" class="active">Workspace</button>
        <button id="scopeApp" type="button">Dev</button>
    </div>

    <button id="saveBtn" class="primary" type="button">Save</button>
    <button id="newFileBtn" type="button">+ File</button>
    <button id="newFolderBtn" type="button">+ Folder</button>
    <button id="renameBtn" type="button">Rename</button>
    <button id="deleteBtn" class="danger" type="button">Delete</button>
    <button id="refreshBtn" type="button">Refresh</button>

    <div class="spacer"></div>

    <button id="chatBtn" class="primary" type="button">💬 Chat</button>
    <button id="editorBtn" type="button">📝 Editor</button>
    <a href="/" style="color:#fff; text-decoration:none; font-size:13px;">Home</a>
</div>

<div class="workspace">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span>PROJECT FILES</span>
        </div>

        <div class="dev-links">
            <div class="dev-links-head">
                <span>Dev scripts</span>
                <button id="devLinksToggle" type="button" style="padding:0 6px; font-size:12px;">−</button>
            </div>
            <div id="devLinks"></div>
        </div>

        <div id="tree" class="tree">Loading...</div>
    </div>

    <div class="resize-handle" id="resizeHandle"></div>

    <div class="editor-area">
        <div class="filebar">
            <div>
                <span id="currentFile">No file selected</span>
                <span id="unsavedIndicator"></span>
            </div>
            <div id="language">plaintext</div>
        </div>
        <div id="editor"></div>
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

<!-- ==== 21/39 : interface/static/index.html ==== -->

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

async function loadProject() {
  setStatus('Loading project...');
  try {
    const data = await API.project();
    renderTree(data.filesystem || []);
    setStatus('Project loaded');
  } catch (err) {
    setStatus('Error: ' + err.message);
  }
}

function renderTree(items) {
  const container = document.getElementById('projectTree');
  container.innerHTML = '';
  renderItems(items, container);
}

function renderItems(items, container) {
  items.forEach(item => {
    const div = document.createElement('div');
    div.className = 'tree-item';
    if (item.type === 'directory') {
      div.classList.add('folder');
      div.dataset.path = item.path;
      const toggle = document.createElement('span');
      toggle.className = 'toggle';
      toggle.textContent = '+';
      const label = document.createElement('span');
      label.textContent = '📁 ' + item.name;
      label.style.flex = '1';
      label.style.marginLeft = '4px';
      div.appendChild(toggle);
      div.appendChild(label);
      div.onclick = (e) => {
        e.stopPropagation();
        toggleFolder(div);
      };
      container.appendChild(div);
      if (item.children && item.children.length) {
        const childrenContainer = document.createElement('div');
        childrenContainer.className = 'children collapsed';
        container.appendChild(childrenContainer);
        renderItems(item.children, childrenContainer);
      }
    } else {
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
  const path = prompt('Enter file path/name:');
  if (!path) return;
  try {
    await API.fileCreate(path, '');
    await loadProject();
    openEditor(path);
  } catch (err) {
    alert(err.message);
  }
}

async function submitCreateFolderPrompt() {
  const path = prompt('Enter folder path:');
  if (!path) return;
  try {
    await API.directoryCreate(path);
    await loadProject();
  } catch (err) {
    alert(err.message);
  }
}

function openEditor(filePath) {
  let url = '/editor';
  if (filePath) url += '?path=' + encodeURIComponent(filePath);
  window.location.href = url;
}

function openEditorPopup(filePath) {
  let url = '/editor';
  if (filePath) url += '?path=' + encodeURIComponent(filePath);
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

<!-- ==== 22/39 : interface/static/js/api.js ==== -->

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

  project(scope = 'workspace') {
    return this.request('GET', `/api/project?scope=${encodeURIComponent(scope)}`);
  },

  fileRead(path, scope = 'workspace') {
    return this.request('GET', `/api/file/read?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  fileWrite(path, content, scope = 'workspace') {
    return this.request('PUT', '/api/file/write', { path, content, scope });
  },

  fileCreate(path, content = '', scope = 'workspace') {
    return this.request('POST', '/api/file/create', { path, content, scope });
  },

  fileDelete(path, scope = 'workspace') {
    return this.request('DELETE', `/api/file/delete?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  directoryCreate(path, scope = 'workspace') {
    return this.request('POST', `/api/directory/create?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  directoryDelete(path, scope = 'workspace') {
    return this.request('DELETE', `/api/directory/delete?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  pathRename(oldPath, newPath, scope = 'workspace') {
    return this.request('PUT', '/api/path/rename', { old_path: oldPath, new_path: newPath, scope });
  },

  chatSend(message) {
    return this.request('POST', '/api/chat', { message });
  },

  chatHistory(limit = 100) {
    return this.request('GET', `/api/chat?limit=${limit}`);
  },

  sessions() {
    return this.request('GET', '/api/sessions');
  }
};

export default API;
```

---

<!-- ==== 23/39 : interface/static/js/chat.js ==== -->

### interface/static/js/chat.js

```javascript
/* Chat popup module */
import API from './api.js';
import Session from './session.js';

const log = document.getElementById('chatLog');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const sendBtn = document.getElementById('chatSend');
const status = document.getElementById('chatStatus');

function appendLine(role, text, meta = '') {
  const line = document.createElement('div');
  line.className = 'msg ' + role;
  const label = document.createElement('span');
  label.className = 'msg-label';
  label.textContent = role === 'user' ? 'You' : role === 'event' ? 'Event' : 'System';
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

function setStatus(text) {
  if (status) status.textContent = text;
}

async function loadHistory() {
  try {
    const data = await API.chatHistory();
    const entries = data.entries || [];
    if (!entries.length) {
      appendLine('system', 'No messages yet. Say hello!');
      return;
    }
    for (const entry of entries) {
      const ts = entry.ts ? new Date(entry.ts).toLocaleTimeString() : '';
      appendLine(entry.sender === 'user' ? 'user' : 'system', entry.message, ts);
    }
  } catch (error) {
    setStatus('Failed to load history: ' + error.message);
  }
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  appendLine('user', message, new Date().toLocaleTimeString());
  setStatus('Logging…');
  try {
    await API.chatSend(message);
    setStatus('Message logged.');
  } catch (error) {
    setStatus('Send failed: ' + error.message);
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

loadHistory();
Session.connect();
```

---

<!-- ==== 24/39 : interface/static/js/editor.js ==== -->

### interface/static/js/editor.js

```javascript
/* Monaco editor module */
let editor = null;

const Editor = {
  init() {
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

<!-- ==== 25/39 : interface/static/js/main.js ==== -->

### interface/static/js/main.js

```javascript
/* Main application wiring */
import API from './api.js';
import Session from './session.js';
import Tree from './tree.js';
import Editor from './editor.js';

let currentFile = null;
let currentLanguage = 'plaintext';
let isDirty = false;
let currentIsFolder = false;
let scope = 'workspace';

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
}

async function openFile(filePath) {
  if (isDirty) {
    const proceed = confirm('You have unsaved changes. Open another file?');
    if (!proceed) return;
  }
  setStatus('Opening ' + filePath + '...');
  try {
    const data = await API.fileRead(filePath, scope);
    currentFile = filePath;
    currentIsFolder = false;
    currentLanguage = getLanguage(filePath);
    Editor.setValue(data.content || '');
    Editor.setLanguage(currentLanguage);
    isDirty = false;
    updateFileDisplay();
    Tree.setSelected(filePath);
    Tree.reveal(filePath);
    setStatus('Opened ' + filePath);
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
  setStatus('Saving...');
  try {
    await API.fileWrite(currentFile, Editor.getValue(), scope);
    isDirty = false;
    updateFileDisplay();
    setStatus('Saved ' + currentFile);
    await Tree.refresh();
  } catch (error) {
    setStatus('Save error: ' + error.message);
    alert(error.message);
  }
}

async function newFile() {
  const fileName = prompt('Enter new file path/name:');
  if (!fileName) return;
  try {
    await API.fileCreate(fileName, '', scope);
    await Tree.refresh();
    await openFile(fileName);
    setStatus('Created ' + fileName);
  } catch (error) {
    alert(error.message);
  }
}

async function newFolder() {
  const folderPath = prompt('Enter new folder path:');
  if (!folderPath) return;
  try {
    await API.directoryCreate(folderPath, scope);
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
  const newName = prompt('Enter the new name/path:', currentFile);
  if (!newName || newName === currentFile) return;
  try {
    await API.pathRename(currentFile, newName, scope);
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
  const confirmed = confirm((currentIsFolder ? 'Delete folder ' : 'Delete file ') + currentFile + '?');
  if (!confirmed) return;
  try {
    if (currentIsFolder) {
      await API.directoryDelete(currentFile, scope);
    } else {
      await API.fileDelete(currentFile, scope);
    }
    currentFile = null;
    currentIsFolder = false;
    Editor.setValue('');
    isDirty = false;
    updateFileDisplay();
    await Tree.refresh();
    setStatus('Deleted.');
  } catch (error) {
    alert(error.message);
  }
}

async function refreshTree() {
  await Tree.refresh();
  setStatus('Refreshed.');
}

function updateScopeButtons() {
  const wsBtn = document.getElementById('scopeWs');
  const appBtn = document.getElementById('scopeApp');
  if (wsBtn) wsBtn.classList.toggle('active', scope === 'workspace');
  if (appBtn) appBtn.classList.toggle('active', scope === 'app');
}

async function setScope(nextScope) {
  if (scope === nextScope) return;
  if (isDirty) {
    const proceed = confirm('You have unsaved changes. Switch scope?');
    if (!proceed) return;
  }
  scope = nextScope;
  currentFile = null;
  currentIsFolder = false;
  Editor.setValue('');
  isDirty = false;
  updateFileDisplay();
  updateScopeButtons();
  setStatus(scope === 'app' ? 'Dev mode: application files' : 'Workspace mode: project files');
  try {
    await Tree.load(scope);
  } catch (error) {
    setStatus('Error: ' + error.message);
  }
}

async function openDevLink(link) {
  if (scope !== 'app') {
    scope = 'app';
    updateScopeButtons();
  }
  setStatus('Opening ' + link.path + '...');
  try {
    await Tree.load(scope);
    await openFile(link.path);
  } catch (error) {
    setStatus('Error: ' + error.message);
  }
}

function openChatPopup() {
  const width = 420; const height = 600;
  const left = (window.screen.width - width) / 2;
  const top = (window.screen.height - height) / 2;
  window.open('/chat', 'ProjectManagerChat', `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no`);
}

function goHome() {
  window.location.href = '/';
}

function goEditor() {
  window.location.href = '/editor';
}

function init() {
  Editor.init()
    .then(async () => {
      Editor.onChange(() => {
        if (currentFile) {
          isDirty = true;
          updateFileDisplay();
        }
      });

      Tree.onFileSelect = openFile;
      Tree.onFolderSelect = selectFolder;
      Tree.onDevLink = openDevLink;

      // ---- Dev-script quick links ----
      if (document.getElementById('devLinks')) {
        Tree.renderDevLinks('devLinks');
      }

      const devLinksToggle = document.getElementById('devLinksToggle');
      const devLinksBox = document.getElementById('devLinks');
      if (devLinksToggle && devLinksBox) {
        devLinksToggle.addEventListener('click', () => {
          const hidden = devLinksBox.style.display === 'none';
          devLinksBox.style.display = hidden ? '' : 'none';
          devLinksToggle.textContent = hidden ? '−' : '+';
        });
      }

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

      // ---- Scope toggle ----
      document.getElementById('scopeWs')?.addEventListener('click', () => setScope('workspace'));
      document.getElementById('scopeApp')?.addEventListener('click', () => setScope('app'));
      updateScopeButtons();

      // ---- Top bar actions ----
      document.getElementById('saveBtn')?.addEventListener('click', saveFile);
      document.getElementById('newFileBtn')?.addEventListener('click', newFile);
      document.getElementById('newFolderBtn')?.addEventListener('click', newFolder);
      document.getElementById('renameBtn')?.addEventListener('click', renameSelected);
      document.getElementById('deleteBtn')?.addEventListener('click', deleteSelected);
      document.getElementById('refreshBtn')?.addEventListener('click', refreshTree);
      document.getElementById('chatBtn')?.addEventListener('click', openChatPopup);
      document.getElementById('editorBtn')?.addEventListener('click', goEditor);
      document.getElementById('homeBtn')?.addEventListener('click', goHome);

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
      await Tree.load(scope);
      const urlParams = new URLSearchParams(window.location.search);
      const initialPath = urlParams.get('path');
      const initialScope = urlParams.get('scope');
      if (initialScope === 'app' || initialScope === 'workspace') {
        scope = initialScope;
        updateScopeButtons();
      }
      if (initialPath) {
        if (initialScope === 'app') await Tree.load('app');
        await openFile(initialPath);
      }
    })
    .catch((e) => {
      setStatus('Error: ' + e.message);
    });

  Session.connect();
}

document.addEventListener('DOMContentLoaded', init);

export { openFile, saveFile, newFile, newFolder, renameSelected, deleteSelected, refreshTree, setScope, openDevLink, goHome, goEditor, currentFile, isDirty };
```

---

<!-- ==== 26/39 : interface/static/js/session.js ==== -->

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

<!-- ==== 27/39 : interface/static/js/tree.js ==== -->

### interface/static/js/tree.js

```javascript
/* Project tree rendering module */
import API from './api.js';

/* Curated "important app scripts" shown as quick links in Dev view. */
const DEV_LINKS = [
  { name: 'server.py', icon: '🐍', path: 'server.py' },
  { name: 'README.md', icon: '📝', path: 'README.md' },
  { name: 'requirements.txt', icon: '📄', path: 'requirements.txt' },
  { name: 'parameters/filesystem.py', icon: '⚙️', path: 'parameters/filesystem.py' },
  { name: 'interface/core/operations.py', icon: '🧩', path: 'interface/core/operations.py' },
  { name: 'interface/core/defaults.py', icon: '🧩', path: 'interface/core/defaults.py' },
  { name: 'interface/routers/files.py', icon: '🌐', path: 'interface/routers/files.py' },
  { name: 'interface/routers/chat.py', icon: '🌐', path: 'interface/routers/chat.py' },
  { name: 'interface/clients/editor_client.py', icon: '🔗', path: 'interface/clients/editor_client.py' },
  { name: 'scripts/run.sh', icon: '⌨️', path: 'scripts/run.sh' },
  { name: 'scripts/run.bat', icon: '⌨️', path: 'scripts/run.bat' }
];

const Tree = {
  root: [],
  selectedPath: null,
  scope: 'workspace',
  expanded: new Set(),
  onFileSelect: null,
  onFolderSelect: null,
  onDevLink: null,

  async load(scope = 'workspace') {
    this.scope = scope;
    const data = await API.project(scope);
    this.root = data.filesystem || [];
    this.render();
  },

  key(path) {
    return this.scope + ':' + path;
  },

  render(containerId = 'tree') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    this.renderItems(this.root, container);
  },

  renderItems(items, container) {
    for (const item of items) {
      const row = document.createElement('div');
      row.className = 'tree-item';
      if (item.type === 'directory') {
        row.classList.add('folder');
        row.dataset.path = item.path;
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        const isExpanded = this.expanded.has(this.key(item.path));
        const toggle = document.createElement('span');
        toggle.className = 'toggle' + (isExpanded ? ' expanded' : '');
        toggle.textContent = isExpanded ? '−' : '+';
        const label = document.createElement('span');
        label.className = 'label';
        label.textContent = '📁 ' + item.name;
        row.appendChild(toggle);
        row.appendChild(label);
        const children = document.createElement('div');
        children.className = 'children' + (isExpanded ? '' : ' collapsed');
        row.onclick = () => {
          this.selectedPath = item.path;
          if (this.onFolderSelect) this.onFolderSelect(item.path);
          this.render();
          this.toggle(item.path);
        };
        container.appendChild(row);
        container.appendChild(children);
        this.renderItems(item.children || [], children);
      } else {
        row.textContent = this.getFileIcon(item.name) + ' ' + item.name;
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        row.onclick = () => {
          this.selectedPath = item.path;
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
    return this.load(this.scope);
  },

  renderDevLinks(containerId = 'devLinks') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    for (const link of DEV_LINKS) {
      const row = document.createElement('button');
      row.className = 'dev-link';
      row.type = 'button';
      row.textContent = link.icon + ' ' + link.name;
      row.title = link.path;
      row.onclick = () => {
        if (this.onDevLink) this.onDevLink(link);
      };
      container.appendChild(row);
    }
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

<!-- ==== 28/39 : parameters/__init__.py ==== -->

### parameters/__init__.py

```python
"""Project parameters package.

Holds the Project Manager filesystem owner (filesystem.py) that owns
the managed workspace, plus the project metadata it manages.
"""
```

---

<!-- ==== 29/39 : parameters/filesystem.py ==== -->

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


# ============================================================
# READ FILESYSTEM
# ============================================================

def read_filesystem(
    directory: Path | None = None,
    _root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Recursively read the project filesystem.

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
                    "editable": is_text_file(
                        child
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

<!-- ==== 30/39 : README.md ==== -->

### README.md

```markdown
# Project Manager

A lightweight FastAPI workspace server. Browse, edit, and chat about your
project from a single web dashboard with a Monaco-powered code editor.

## Layout

The repository is split into three pillars plus scripts:

```
├── server.py                Application entry point (FastAPI host)
├── requirements.txt
│
├── interface/               EDITOR INTERFACE
│   ├── static/              Web UI (home.html, chat.html, editor.html, js/)
│   ├── routers/             HTTP API routers (files, dirs, paths, ws, chat)
│   ├── core/                Controller layer (sessions, events, operations)
│   └── clients/             Python client (EditorClient / AsyncEditorClient)
│
├── parameters/              PROJECT PARAMETERS
│   └── filesystem.py        Filesystem owner for the managed workspace
│
├── workspace/               THE MANAGED PROJECT
│   ├── project.json
│   ├── documentation/  project_scope/  to_do/  updates/  config/  data/
│
└── scripts/                 run.bat / run.sh / setup.sh
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
- Chat popup (`/chat`) — stub that logs messages to `workspace/data/chat.log`
- Dev-scripts quick links to the important application files
- JSON REST API for filesystem operations (scope-aware)
- Python client for AI agents / other programs
- Works on Windows and (Chromebook) Linux

## Requirements

- Python 3.9+
- Network access for the code editor CDN (Monaco, loaded from cdnjs)

## Setup

### Windows

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
scripts\run.bat
```

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
| GET    | `/chat`                       | Chat popup UI                        |
| GET    | `/api/health`                 | Health + project info                |
| GET    | `/api/project?scope=`         | Project state + tree (ws/app)        |
| GET    | `/api/file/read?path=&scope=` | Read a file                          |
| PUT    | `/api/file/write`             | Write a file                         |
| POST   | `/api/file/create`            | Create a file                        |
| POST   | `/api/directory/create`       | Create a directory                   |
| PUT    | `/api/path/rename`            | Rename/move a path                   |
| DELETE | `/api/file/delete`            | Delete a file                        |
| DELETE | `/api/directory/delete`       | Delete a directory                   |
| POST   | `/api/chat`                   | Send a chat message (logged)         |
| GET    | `/api/chat`                   | Chat history                         |

Note: The `workspace/` content folders are empty so git does not track
them; the server recreates them automatically on startup.
```

---

<!-- ==== 31/39 : requirements.txt ==== -->

### requirements.txt

```text
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
websockets==13.1
```

---

<!-- ==== 32/39 : scripts/run.bat ==== -->

### scripts/run.bat

```batch
@echo off
rem Project Manager - start the server from the virtual environment.

cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run: python -m venv .venv
    echo Then: .venv\Scripts\python -m pip install -r requirements.txt
    exit /b 1
)

echo Starting Project Manager at http://127.0.0.1:8000
echo To stop: press Ctrl+C
echo.

.venv\Scripts\python server.py
```

---

<!-- ==== 33/39 : scripts/run.sh ==== -->

### scripts/run.sh

```bash
#!/usr/bin/env bash
#
# Project Manager - start the server from the virtual environment.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run ./setup.sh first." >&2
    exit 1
fi

echo "Starting Project Manager at http://127.0.0.1:8000"
echo "To stop: press Ctrl+C"
echo

.venv/bin/python server.py
```

---

<!-- ==== 34/39 : scripts/setup.sh ==== -->

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

<!-- ==== 35/39 : server.py ==== -->

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

<!-- ==== 36/39 : workspace/agent.md ==== -->

### workspace/agent.md

```markdown

```

---

<!-- ==== 37/39 : workspace/documentation/MASTER_COPY.md ==== -->

### workspace/documentation/MASTER_COPY.md

```markdown
# Project Manager — MASTER COPY

Single-file snapshot of the complete Project Manager application source tree.

- **Project:** Project Manager
- **Version:** 1.0.0
- **Workspace version:** 1.0
- **Repo:** https://github.com/TheChuey/project
- **Generated:** 2026-09-23

---

## AI Agent Engine — Entry Point

The chat endpoint is the **AI agent engine entry point** for the project.

This is where an agent / request-model plugs into the application. The editor
interface (and the home page) reach the engine through the exact same stable
HTTP surface, so the engine can be swapped without touching the UI:

| Route       | Method | Purpose                                                    |
| ----------- | ------ | ---------------------------------------------------------- |
| `/api/chat` | POST   | Send a message to the agent engine. Body: `{"message": str, "scope": str?}`. |
| `/api/chat` | GET    | Fetch recent agent conversation history (`?limit=`).        |

The engine lives in `interface/routers/chat.py` and persists history to
`workspace/data/chat.log` (JSON lines). Anything — the home page chat popup,
the editor's chat button, or a future AI/agent process — goes through this one
entry point, keeping the full app decoupled from the engine implementation.

```text
┌────────────────────┐   POST /api/chat   ┌────────────────────────┐
│  editor interface  │ ──────────────────▶│  agent engine          │
│  (home / editor)   │                    │  interface/routers/    │
│                    │ ◀──────────────────│        chat.py         │
└────────────────────┘       reply        └────────────────────────┘
```

---

## Editor Interface — Accessing the Agent Tools

The editor's browser interface reaches the agent engine and the code tools
through `interface/static/js/api.js` and `interface/static/js/session.js`.
Every agent tool the interface can touch is exposed as a small API method:

| Front-end accessor        | Backend route                       | Purpose                          |
| ------------------------- | ----------------------------------- | -------------------------------- |
| `API.chatSend(message)`   | `POST /api/chat`                    | Send a message to the agent      |
| `API.chatHistory(limit)`  | `GET /api/chat?limit=`              | Read agent conversation history  |
| `API.fileRead(path)`      | `GET /api/file/read?path=`          | Open a file in the editor        |
| `API.fileWrite(path, c)`  | `PUT /api/file/write`               | Save the current buffer          |
| `API.project(scope)`      | `GET /api/project?scope=`           | Reload the file tree             |
| `API.pathRename(a, b)`    | `PUT /api/path/rename`              | Rename a file / folder           |
| `API.fileDelete(path)`    | `DELETE /api/file/delete?path=`     | Delete a file                    |
| `API.directoryDelete(p)`  | `DELETE /api/directory/delete?path=`| Delete a folder                  |

The editor toolbar exposes these tools as buttons:

- **Save** (`Ctrl+S`) → `API.fileWrite` on the current file
- **+ File / + Folder / Rename / Delete** → the matching create/rename/delete
  accessors above
- **Chat** button → opens the chat popup, which calls `API.chatSend`
- **Dev links** sidebar → opens app-scope files through `API.fileRead`

For new agent tools, the pattern to follow is: add
`schema -> route -> API.* accessor -> toolbar/popup button`. Nothing else in
the app changes, because every surface already talks to the API client.

---

## File Structure

```text
project/
    ├── interface
    │   ├── clients
    │   ├── core
    │   ├── routers
    │   └── static
    │       └── js
    ├── parameters
    ├── scripts
    └── workspace
        ├── config
        ├── data
        ├── documentation
        ├── project_scope
        ├── to_do
        └── updates
```

---

---

<!-- ==== 1/39 : .gitattributes ==== -->

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

<!-- ==== 2/39 : .gitignore ==== -->

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

<!-- ==== 3/39 : interface/clients/__init__.py ==== -->

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

<!-- ==== 4/39 : interface/clients/editor_client.py ==== -->

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

<!-- ==== 5/39 : interface/core/__init__.py ==== -->

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

<!-- ==== 6/39 : interface/core/defaults.py ==== -->

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

<!-- ==== 7/39 : interface/core/events.py ==== -->

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

<!-- ==== 8/39 : interface/core/operations.py ==== -->

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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Project state: project info, active root and filesystem tree.

        Args:
            scope:
                ``"workspace"`` (default) or ``"app"``.
        """

        try:

            root = _root_for(scope)

            return {
                "scope": scope or "workspace",
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
        scope: str | None = "workspace",
    ) -> str:
        """
        Open a project file and return its contents.

        Args:
            path:
                Root-relative file path.
            scope:
                ``"workspace"`` (default) or ``"app"``.

        Returns:
            The file contents.
        """

        return self.filesystem.read_file(
            path,
            root=_root_for(scope),
        )

    def save(
        self,
        path: str,
        content: str,
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Write file contents back to the project filesystem.

        Publishes a ``saved`` event on success.
        """

        self.filesystem.write_file(
            path,
            content,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Create a new project file.

        Publishes a ``created`` event on success.
        """

        self.filesystem.create_file(
            path,
            content,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Create a new project directory.

        Publishes a ``created`` event on success.
        """

        self.filesystem.create_directory(
            path,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Rename or move a project file/directory.

        Publishes a ``renamed`` event on success.
        """

        self.filesystem.rename_path(
            old_path,
            new_path,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Delete a project file or directory.

        Publishes a ``deleted`` event on success.
        """

        self.filesystem.delete_path(
            path,
            root=_root_for(scope),
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

<!-- ==== 9/39 : interface/core/session.py ==== -->

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

<!-- ==== 10/39 : interface/routers/__init__.py ==== -->

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

def normalize_scope(scope: str | None) -> str:
    """
    Validate and normalize a scope query parameter.

    Raises:
        HTTPException (422):
            If the scope is not a known scope.
    """

    scope = scope or "workspace"

    if scope not in VALID_SCOPES:

        raise HTTPException(
            status_code=422,
            detail=f"Unknown scope: {scope}",
        )

    return scope
```

---

<!-- ==== 11/39 : interface/routers/chat.py ==== -->

### interface/routers/chat.py

```python
"""
Project Manager chat router (stub).
====================================

Chat stub for the interface. Messages are appended to a plaintext
log file inside the managed workspace (``workspace/data/chat.log``)
so history survives reloads. This is a placeholder surface: a real
AI agent can replace the handler later without changing the API
shape (``POST /api/chat`` to send, ``GET /api/chat`` to fetch).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from parameters import filesystem

from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# REQUEST MODELS
# ============================================================

class ChatMessage(BaseModel):

    message: str


# ============================================================
# CHAT LOG HELPERS
# ============================================================

MAX_MESSAGE_LENGTH = 2000

DEFAULT_LIMIT = 50

MAX_LIMIT = 500


def _log_path() -> Any:
    """
    Safe path to the chat log inside the managed workspace.
    """

    return filesystem.resolve_project_path(
        "data/chat.log"
    )


def _append_message(message: str) -> dict[str, Any]:
    """
    Append one timestamped message to the chat log.

    The data directory is created on demand.
    """

    log_path = _log_path()

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sender": "user",
        "message": message,
    }

    with log_path.open(
        "a",
        encoding="utf-8",
    ) as handle:

        handle.write(
            json.dumps(entry) + "\n"
        )

    return entry


def _read_history(limit: int) -> list[dict[str, Any]]:
    """
    Read the most recent chat log entries in chronological order.
    """

    log_path = _log_path()

    if not log_path.exists():

        return []

    entries: list[dict[str, Any]] = []

    with log_path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        for line in handle:

            line = line.strip()

            if not line:
                continue

            try:

                entries.append(
                    json.loads(line)
                )

            except json.JSONDecodeError:
                continue

    return entries[-limit:]


# ============================================================
# SEND MESSAGE
# ============================================================

@router.post("/api/chat")
def send_chat_message(
    request: Request,
    payload: ChatMessage,
):
    """
    Log a chat message.

    The stub currently records the message; a future agent
    provider can reply through the same endpoint.
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

    try:

        entry = _append_message(message)

        return {
            "status": "logged",
            "entry": entry,
        }

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

    limit = max(1, min(limit, MAX_LIMIT))

    try:

        return {
            "entries": _read_history(limit),
        }

    except Exception as error:

        raise project_manager_error(
            error
        )
```

---

<!-- ==== 12/39 : interface/routers/directories.py ==== -->

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
    scope: str = "workspace",
):
    """
    Create a project directory.

    Query params:
        path:
            Root-relative directory path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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
    scope: str = "workspace",
):
    """
    Delete a project directory.

    Query params:
        path:
            Root-relative directory path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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

<!-- ==== 13/39 : interface/routers/errors.py ==== -->

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

<!-- ==== 14/39 : interface/routers/files.py ==== -->

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

    scope: str = "workspace"


class FileCreateRequest(BaseModel):

    path: str

    content: str = ""

    scope: str = "workspace"


# ============================================================
# READ FILE
# ============================================================

@router.get("/api/file/read")
def read_file(
    request: Request,
    path: str,
    scope: str = "workspace",
):
    """
    Read a project text file.

    Query params:
        path:
            Root-relative file path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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
    scope: str = "workspace",
):
    """
    Delete a project file.

    Query params:
        path:
            Root-relative file path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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

<!-- ==== 15/39 : interface/routers/paths.py ==== -->

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

    scope: str = "workspace"


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

<!-- ==== 16/39 : interface/routers/project.py ==== -->

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
    scope: str = "workspace",
):
    """
    Project information and filesystem tree.

    Query params:
        scope:
            ``"workspace"`` (default) or ``"app"``.
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

<!-- ==== 17/39 : interface/routers/ws.py ==== -->

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

    session = controller.sessions.register()

    try:

        await websocket.send_json(
            {
                "type": "hello",
                "client_id": session.client_id,
            }
        )

        async def forward(
            event: dict[str, Any],
        ) -> None:
            """
            Forward a published event to this socket.
            """

            try:

                await websocket.send_json(
                    {
                        "type": "event",
                        "event": event,
                    }
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
                    "sessions": controller.sessions.snapshot(),
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

                controller.sessions.update(
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

                controller.sessions.update(
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

        controller.sessions.unregister(
            session.client_id
        )
```

---

<!-- ==== 18/39 : interface/static/chat.html ==== -->

### interface/static/chat.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Manager Chat</title>

    <style>
        /* =========================================================
           RESET / BASE
           ========================================================= */

        * {
            box-sizing: border-box;
        }

        html,
        body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family:
                Inter,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Arial,
                sans-serif;
            background: #0f1117;
            color: #e6e8ee;
        }

        body {
            display: flex;
            flex-direction: column;
        }

        button,
        textarea {
            font-family: inherit;
        }


        /* =========================================================
           TOP BAR
           ========================================================= */

        .chatbar {
            height: 58px;
            min-height: 58px;

            display: flex;
            align-items: center;
            justify-content: space-between;

            padding: 0 20px;

            background: #151821;
            border-bottom: 1px solid #292d38;
        }

        .chat-title-area {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .chat-icon {
            width: 34px;
            height: 34px;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 9px;

            background: #252a38;
            border: 1px solid #343949;

            font-size: 17px;
        }

        .title {
            font-size: 15px;
            font-weight: 600;
            color: #f1f3f7;
        }

        .subtitle {
            margin-top: 2px;
            font-size: 11px;
            color: #7f8798;
        }

        .status-area {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #777;
        }

        .status {
            font-size: 12px;
            color: #8991a2;
        }


        /* =========================================================
           MAIN CHAT AREA
           ========================================================= */

        #chatLog {
            flex: 1;

            overflow-y: auto;

            padding: 28px 22px 30px;

            display: flex;
            flex-direction: column;
            gap: 14px;

            background:
                radial-gradient(
                    circle at top center,
                    rgba(58, 65, 85, 0.12),
                    transparent 45%
                ),
                #0f1117;
        }

        /* Scrollbar */

        #chatLog::-webkit-scrollbar {
            width: 8px;
        }

        #chatLog::-webkit-scrollbar-track {
            background: transparent;
        }

        #chatLog::-webkit-scrollbar-thumb {
            background: #303543;
            border-radius: 10px;
        }

        #chatLog::-webkit-scrollbar-thumb:hover {
            background: #3b4150;
        }


        /* =========================================================
           MESSAGE CARD
           ========================================================= */

        .msg {
            width: min(850px, 90%);

            display: flex;
            flex-direction: column;
            gap: 6px;

            padding: 13px 15px;

            border-radius: 12px;

            background: #181b24;
            border: 1px solid #292d38;

            box-shadow:
                0 4px 14px rgba(0, 0, 0, 0.12);
        }

        .msg-label {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.02em;
            color: #858d9e;
        }

        .msg-body {
            word-break: break-word;
            white-space: pre-wrap;

            font-size: 14px;
            line-height: 1.55;

            color: #dfe2e8;
        }

        .msg-meta {
            align-self: flex-end;

            font-size: 10px;
            color: #626a7a;
        }


        /* =========================================================
           USER MESSAGE
           ========================================================= */

        .msg.user {
            align-self: flex-end;

            background: #1b2634;
            border-color: #29445e;
        }

        .msg.user .msg-label {
            color: #70b7ed;
        }

        .msg.user .msg-body {
            color: #edf6ff;
        }


        /* =========================================================
           EVENT MESSAGE
           ========================================================= */

        .msg.event {
            width: min(750px, 85%);

            background: #151e19;
            border-color: #27402f;
        }

        .msg.event .msg-label {
            color: #72b784;
        }

        .msg.event .msg-body {
            color: #b9d8bf;
            font-size: 13px;
        }


        /* =========================================================
           SYSTEM MESSAGE
           ========================================================= */

        .msg.system {
            width: min(750px, 85%);

            background: #14161c;
            border-color: #292d35;
        }

        .msg.system .msg-label {
            color: #777f90;
        }

        .msg.system .msg-body {
            color: #9299a8;
            font-size: 13px;
        }


        /* =========================================================
           EMPTY / LOADING MESSAGE
           ========================================================= */

        .msg.system:first-child {
            opacity: 0.85;
        }


        /* =========================================================
           INPUT AREA
           ========================================================= */

        .chatfoot {
            padding: 14px 20px 18px;

            background: #151821;
            border-top: 1px solid #292d38;
        }

        .input-container {
            width: min(900px, 100%);
            margin: 0 auto;

            display: flex;
            align-items: flex-end;
            gap: 10px;

            padding: 9px;

            background: #1b1f29;
            border: 1px solid #303543;
            border-radius: 14px;

            transition:
                border-color 0.2s ease,
                box-shadow 0.2s ease;
        }

        .input-container:focus-within {
            border-color: #3d6d96;

            box-shadow:
                0 0 0 3px rgba(61, 109, 150, 0.12);
        }


        /* =========================================================
           TEXT INPUT
           ========================================================= */

        #chatInput {
            flex: 1;

            min-height: 42px;
            max-height: 160px;

            padding: 10px 11px;

            background: transparent;
            color: #edf0f5;

            border: none;
            outline: none;

            resize: none;

            font-size: 14px;
            line-height: 1.45;
        }

        #chatInput::placeholder {
            color: #697182;
        }


        /* =========================================================
           SEND BUTTON
           ========================================================= */

        #chatSend {
            width: 42px;
            height: 42px;

            display: flex;
            align-items: center;
            justify-content: center;

            flex-shrink: 0;

            border: 1px solid #3c4554;
            border-radius: 10px;

            background: #27303d;
            color: #dce7f2;

            cursor: pointer;

            font-size: 16px;

            transition:
                background 0.15s ease,
                border-color 0.15s ease,
                transform 0.1s ease;
        }

        #chatSend:hover {
            background: #314052;
            border-color: #4b5c70;
        }

        #chatSend:active {
            transform: scale(0.96);
        }

        #chatSend:disabled {
            opacity: 0.45;
            cursor: not-allowed;
        }


        /* =========================================================
           INPUT FOOTER HINT
           ========================================================= */

        .input-hint {
            width: min(900px, 100%);
            margin: 7px auto 0;

            text-align: center;

            font-size: 10px;
            color: #5f6675;
        }


        /* =========================================================
           RESPONSIVE
           ========================================================= */

        @media (max-width: 700px) {

            .chatbar {
                padding: 0 14px;
            }

            .subtitle {
                display: none;
            }

            #chatLog {
                padding: 18px 12px 22px;
            }

            .msg {
                width: 94%;
            }

            .chatfoot {
                padding: 10px 10px 12px;
            }

            .input-hint {
                display: none;
            }
        }
    </style>
</head>

<body>

    <!-- =========================================================
         HEADER
         ========================================================= -->

    <header class="chatbar">

        <div class="chat-title-area">

            <div class="chat-icon">
                💬
            </div>

            <div>
                <div class="title">
                    Project Chat
                </div>

                <div class="subtitle">
                    Project Manager
                </div>
            </div>

        </div>


        <div class="status-area">

            <span id="statusDot" class="status-dot"></span>

            <span id="chatStatus" class="status">
                Connecting…
            </span>

        </div>

    </header>


    <!-- =========================================================
         CHAT MESSAGES
         ========================================================= -->

    <main id="chatLog">

        <div class="msg system">

            <span class="msg-label">
                SYSTEM
            </span>

            <span class="msg-body">
                Loading messages…
            </span>

        </div>

    </main>


    <!-- =========================================================
         CHAT INPUT
         ========================================================= -->

    <footer class="chatfoot">

        <form id="chatForm">

            <div class="input-container">

                <textarea
                    id="chatInput"
                    rows="1"
                    placeholder="Message Project Manager…"
                    autocomplete="off"
                ></textarea>

                <button
                    id="chatSend"
                    type="submit"
                    aria-label="Send message"
                    title="Send message"
                >
                    ↑
                </button>

            </div>

        </form>

        <div class="input-hint">
            Press Enter to send · Shift + Enter for a new line
        </div>

    </footer>


    <!-- =========================================================
         EXISTING CHAT JAVASCRIPT
         ========================================================= -->

    <script type="module" src="/static/js/chat.js"></script>


    <!-- =========================================================
         SMALL UI ENHANCEMENTS
         These do not replace chat.js.
         ========================================================= -->

    <script>

        /*
         * Automatically grow the message box.
         * This does not communicate with the backend.
         */

        const chatInput = document.getElementById("chatInput");

        if (chatInput) {

            chatInput.addEventListener("input", () => {

                chatInput.style.height = "auto";

                chatInput.style.height =
                    Math.min(chatInput.scrollHeight, 160) + "px";

            });


            /*
             * Enter = send
             * Shift + Enter = new line
             *
             * The existing form submission handled by chat.js
             * remains responsible for actually sending the message.
             */

            chatInput.addEventListener("keydown", (event) => {

                if (
                    event.key === "Enter" &&
                    !event.shiftKey
                ) {

                    event.preventDefault();

                    const form =
                        document.getElementById("chatForm");

                    if (form) {
                        form.requestSubmit();
                    }

                }

            });

        }


        /*
         * Automatically keep the newest message visible.
         *
         * MutationObserver watches for messages added by chat.js.
         */

        const chatLog =
            document.getElementById("chatLog");

        if (chatLog) {

            const observer =
                new MutationObserver(() => {

                    chatLog.scrollTop =
                        chatLog.scrollHeight;

                });

            observer.observe(chatLog, {
                childList: true,
                subtree: true
            });

        }

    </script>

</body>
</html>

```

---

<!-- ==== 19/39 : interface/static/editor.html ==== -->

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
            height: calc(100vh - 74px);
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
    </style>

    <!-- Monaco Loader CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js"></script>
</head>
<body>

<div class="topbar">
    <div class="title">Project Manager Editor</div>
    <button id="homeBtn" onclick="goHome()">🏠 Home</button>
    <button id="saveBtn" class="primary" onclick="saveFile()">Save</button>
    <button id="newFileBtn" onclick="newFile()">+ File</button>
    <button id="newFolderBtn" onclick="newFolder()">+ Folder</button>
    <button id="renameBtn" onclick="renameSelected()">Rename</button>
    <button id="deleteBtn" class="danger" onclick="deleteSelected()">Delete</button>
    <button id="refreshBtn" onclick="refreshTree()">Refresh</button>
</div>

<div class="workspace">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span>PROJECT FILES</span>
        </div>
        <div id="tree" class="tree">Loading...</div>
    </div>
    
    <div class="resize-handle" id="resizeHandle"></div>

    <div class="editor-area">
        <div class="filebar">
            <div>
                <span id="currentFile">No file selected</span>
                <span id="unsavedIndicator"></span>
            </div>
            <div id="language">plaintext</div>
        </div>
        <div id="editor"></div>
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

<!-- ==== 20/39 : interface/static/home.html ==== -->

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

        .scope-toggle {
            display: flex;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            overflow: hidden;
            margin-right: 12px;
        }

        .scope-toggle button {
            border: none;
            border-radius: 0;
            background: #252526;
            padding: 6px 12px;
        }

        .scope-toggle button.active {
            background: #0e639c;
        }

        .workspace {
            display: flex;
            height: calc(100vh - 74px);
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

        /* ---- Dev scripts quick links ---- */
        .dev-links {
            border-bottom: 1px solid #3f3f46;
            padding: 8px;
        }

        .dev-links-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            font-weight: bold;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }

        .dev-link {
            display: block;
            width: 100%;
            text-align: left;
            background: transparent;
            border: 1px solid transparent;
            color: #d1d5db;
            padding: 4px 6px;
            border-radius: 3px;
            font-size: 12px;
            margin-bottom: 2px;
        }

        .dev-link:hover {
            background: #2a2d2e;
            border-color: #3f3f46;
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
    </style>

    <!-- Monaco Loader CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js"></script>
</head>
<body>

<div class="topbar">
    <div class="title">Project Manager</div>
    <span id="projectName">…</span>

    <div class="scope-toggle" role="group" aria-label="Scope">
        <button id="scopeWs" type="button" class="active">Workspace</button>
        <button id="scopeApp" type="button">Dev</button>
    </div>

    <button id="saveBtn" class="primary" type="button">Save</button>
    <button id="newFileBtn" type="button">+ File</button>
    <button id="newFolderBtn" type="button">+ Folder</button>
    <button id="renameBtn" type="button">Rename</button>
    <button id="deleteBtn" class="danger" type="button">Delete</button>
    <button id="refreshBtn" type="button">Refresh</button>

    <div class="spacer"></div>

    <button id="chatBtn" class="primary" type="button">💬 Chat</button>
    <button id="editorBtn" type="button">📝 Editor</button>
    <a href="/" style="color:#fff; text-decoration:none; font-size:13px;">Home</a>
</div>

<div class="workspace">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span>PROJECT FILES</span>
        </div>

        <div class="dev-links">
            <div class="dev-links-head">
                <span>Dev scripts</span>
                <button id="devLinksToggle" type="button" style="padding:0 6px; font-size:12px;">−</button>
            </div>
            <div id="devLinks"></div>
        </div>

        <div id="tree" class="tree">Loading...</div>
    </div>

    <div class="resize-handle" id="resizeHandle"></div>

    <div class="editor-area">
        <div class="filebar">
            <div>
                <span id="currentFile">No file selected</span>
                <span id="unsavedIndicator"></span>
            </div>
            <div id="language">plaintext</div>
        </div>
        <div id="editor"></div>
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

<!-- ==== 21/39 : interface/static/index.html ==== -->

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

async function loadProject() {
  setStatus('Loading project...');
  try {
    const data = await API.project();
    renderTree(data.filesystem || []);
    setStatus('Project loaded');
  } catch (err) {
    setStatus('Error: ' + err.message);
  }
}

function renderTree(items) {
  const container = document.getElementById('projectTree');
  container.innerHTML = '';
  renderItems(items, container);
}

function renderItems(items, container) {
  items.forEach(item => {
    const div = document.createElement('div');
    div.className = 'tree-item';
    if (item.type === 'directory') {
      div.classList.add('folder');
      div.dataset.path = item.path;
      const toggle = document.createElement('span');
      toggle.className = 'toggle';
      toggle.textContent = '+';
      const label = document.createElement('span');
      label.textContent = '📁 ' + item.name;
      label.style.flex = '1';
      label.style.marginLeft = '4px';
      div.appendChild(toggle);
      div.appendChild(label);
      div.onclick = (e) => {
        e.stopPropagation();
        toggleFolder(div);
      };
      container.appendChild(div);
      if (item.children && item.children.length) {
        const childrenContainer = document.createElement('div');
        childrenContainer.className = 'children collapsed';
        container.appendChild(childrenContainer);
        renderItems(item.children, childrenContainer);
      }
    } else {
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
  const path = prompt('Enter file path/name:');
  if (!path) return;
  try {
    await API.fileCreate(path, '');
    await loadProject();
    openEditor(path);
  } catch (err) {
    alert(err.message);
  }
}

async function submitCreateFolderPrompt() {
  const path = prompt('Enter folder path:');
  if (!path) return;
  try {
    await API.directoryCreate(path);
    await loadProject();
  } catch (err) {
    alert(err.message);
  }
}

function openEditor(filePath) {
  let url = '/editor';
  if (filePath) url += '?path=' + encodeURIComponent(filePath);
  window.location.href = url;
}

function openEditorPopup(filePath) {
  let url = '/editor';
  if (filePath) url += '?path=' + encodeURIComponent(filePath);
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

<!-- ==== 22/39 : interface/static/js/api.js ==== -->

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

  project(scope = 'workspace') {
    return this.request('GET', `/api/project?scope=${encodeURIComponent(scope)}`);
  },

  fileRead(path, scope = 'workspace') {
    return this.request('GET', `/api/file/read?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  fileWrite(path, content, scope = 'workspace') {
    return this.request('PUT', '/api/file/write', { path, content, scope });
  },

  fileCreate(path, content = '', scope = 'workspace') {
    return this.request('POST', '/api/file/create', { path, content, scope });
  },

  fileDelete(path, scope = 'workspace') {
    return this.request('DELETE', `/api/file/delete?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  directoryCreate(path, scope = 'workspace') {
    return this.request('POST', `/api/directory/create?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  directoryDelete(path, scope = 'workspace') {
    return this.request('DELETE', `/api/directory/delete?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  pathRename(oldPath, newPath, scope = 'workspace') {
    return this.request('PUT', '/api/path/rename', { old_path: oldPath, new_path: newPath, scope });
  },

  chatSend(message) {
    return this.request('POST', '/api/chat', { message });
  },

  chatHistory(limit = 100) {
    return this.request('GET', `/api/chat?limit=${limit}`);
  },

  sessions() {
    return this.request('GET', '/api/sessions');
  }
};

export default API;
```

---

<!-- ==== 23/39 : interface/static/js/chat.js ==== -->

### interface/static/js/chat.js

```javascript
/* Chat popup module */
import API from './api.js';
import Session from './session.js';

const log = document.getElementById('chatLog');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const sendBtn = document.getElementById('chatSend');
const status = document.getElementById('chatStatus');

function appendLine(role, text, meta = '') {
  const line = document.createElement('div');
  line.className = 'msg ' + role;
  const label = document.createElement('span');
  label.className = 'msg-label';
  label.textContent = role === 'user' ? 'You' : role === 'event' ? 'Event' : 'System';
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

function setStatus(text) {
  if (status) status.textContent = text;
}

async function loadHistory() {
  try {
    const data = await API.chatHistory();
    const entries = data.entries || [];
    if (!entries.length) {
      appendLine('system', 'No messages yet. Say hello!');
      return;
    }
    for (const entry of entries) {
      const ts = entry.ts ? new Date(entry.ts).toLocaleTimeString() : '';
      appendLine(entry.sender === 'user' ? 'user' : 'system', entry.message, ts);
    }
  } catch (error) {
    setStatus('Failed to load history: ' + error.message);
  }
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  appendLine('user', message, new Date().toLocaleTimeString());
  setStatus('Logging…');
  try {
    await API.chatSend(message);
    setStatus('Message logged.');
  } catch (error) {
    setStatus('Send failed: ' + error.message);
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

loadHistory();
Session.connect();
```

---

<!-- ==== 24/39 : interface/static/js/editor.js ==== -->

### interface/static/js/editor.js

```javascript
/* Monaco editor module */
let editor = null;

const Editor = {
  init() {
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

<!-- ==== 25/39 : interface/static/js/main.js ==== -->

### interface/static/js/main.js

```javascript
/* Main application wiring */
import API from './api.js';
import Session from './session.js';
import Tree from './tree.js';
import Editor from './editor.js';

let currentFile = null;
let currentLanguage = 'plaintext';
let isDirty = false;
let currentIsFolder = false;
let scope = 'workspace';

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
}

async function openFile(filePath) {
  if (isDirty) {
    const proceed = confirm('You have unsaved changes. Open another file?');
    if (!proceed) return;
  }
  setStatus('Opening ' + filePath + '...');
  try {
    const data = await API.fileRead(filePath, scope);
    currentFile = filePath;
    currentIsFolder = false;
    currentLanguage = getLanguage(filePath);
    Editor.setValue(data.content || '');
    Editor.setLanguage(currentLanguage);
    isDirty = false;
    updateFileDisplay();
    Tree.setSelected(filePath);
    Tree.reveal(filePath);
    setStatus('Opened ' + filePath);
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
  setStatus('Saving...');
  try {
    await API.fileWrite(currentFile, Editor.getValue(), scope);
    isDirty = false;
    updateFileDisplay();
    setStatus('Saved ' + currentFile);
    await Tree.refresh();
  } catch (error) {
    setStatus('Save error: ' + error.message);
    alert(error.message);
  }
}

async function newFile() {
  const fileName = prompt('Enter new file path/name:');
  if (!fileName) return;
  try {
    await API.fileCreate(fileName, '', scope);
    await Tree.refresh();
    await openFile(fileName);
    setStatus('Created ' + fileName);
  } catch (error) {
    alert(error.message);
  }
}

async function newFolder() {
  const folderPath = prompt('Enter new folder path:');
  if (!folderPath) return;
  try {
    await API.directoryCreate(folderPath, scope);
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
  const newName = prompt('Enter the new name/path:', currentFile);
  if (!newName || newName === currentFile) return;
  try {
    await API.pathRename(currentFile, newName, scope);
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
  const confirmed = confirm((currentIsFolder ? 'Delete folder ' : 'Delete file ') + currentFile + '?');
  if (!confirmed) return;
  try {
    if (currentIsFolder) {
      await API.directoryDelete(currentFile, scope);
    } else {
      await API.fileDelete(currentFile, scope);
    }
    currentFile = null;
    currentIsFolder = false;
    Editor.setValue('');
    isDirty = false;
    updateFileDisplay();
    await Tree.refresh();
    setStatus('Deleted.');
  } catch (error) {
    alert(error.message);
  }
}

async function refreshTree() {
  await Tree.refresh();
  setStatus('Refreshed.');
}

function updateScopeButtons() {
  const wsBtn = document.getElementById('scopeWs');
  const appBtn = document.getElementById('scopeApp');
  if (wsBtn) wsBtn.classList.toggle('active', scope === 'workspace');
  if (appBtn) appBtn.classList.toggle('active', scope === 'app');
}

async function setScope(nextScope) {
  if (scope === nextScope) return;
  if (isDirty) {
    const proceed = confirm('You have unsaved changes. Switch scope?');
    if (!proceed) return;
  }
  scope = nextScope;
  currentFile = null;
  currentIsFolder = false;
  Editor.setValue('');
  isDirty = false;
  updateFileDisplay();
  updateScopeButtons();
  setStatus(scope === 'app' ? 'Dev mode: application files' : 'Workspace mode: project files');
  try {
    await Tree.load(scope);
  } catch (error) {
    setStatus('Error: ' + error.message);
  }
}

async function openDevLink(link) {
  if (scope !== 'app') {
    scope = 'app';
    updateScopeButtons();
  }
  setStatus('Opening ' + link.path + '...');
  try {
    await Tree.load(scope);
    await openFile(link.path);
  } catch (error) {
    setStatus('Error: ' + error.message);
  }
}

function openChatPopup() {
  const width = 420; const height = 600;
  const left = (window.screen.width - width) / 2;
  const top = (window.screen.height - height) / 2;
  window.open('/chat', 'ProjectManagerChat', `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no`);
}

function goHome() {
  window.location.href = '/';
}

function goEditor() {
  window.location.href = '/editor';
}

function init() {
  Editor.init()
    .then(async () => {
      Editor.onChange(() => {
        if (currentFile) {
          isDirty = true;
          updateFileDisplay();
        }
      });

      Tree.onFileSelect = openFile;
      Tree.onFolderSelect = selectFolder;
      Tree.onDevLink = openDevLink;

      // ---- Dev-script quick links ----
      if (document.getElementById('devLinks')) {
        Tree.renderDevLinks('devLinks');
      }

      const devLinksToggle = document.getElementById('devLinksToggle');
      const devLinksBox = document.getElementById('devLinks');
      if (devLinksToggle && devLinksBox) {
        devLinksToggle.addEventListener('click', () => {
          const hidden = devLinksBox.style.display === 'none';
          devLinksBox.style.display = hidden ? '' : 'none';
          devLinksToggle.textContent = hidden ? '−' : '+';
        });
      }

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

      // ---- Scope toggle ----
      document.getElementById('scopeWs')?.addEventListener('click', () => setScope('workspace'));
      document.getElementById('scopeApp')?.addEventListener('click', () => setScope('app'));
      updateScopeButtons();

      // ---- Top bar actions ----
      document.getElementById('saveBtn')?.addEventListener('click', saveFile);
      document.getElementById('newFileBtn')?.addEventListener('click', newFile);
      document.getElementById('newFolderBtn')?.addEventListener('click', newFolder);
      document.getElementById('renameBtn')?.addEventListener('click', renameSelected);
      document.getElementById('deleteBtn')?.addEventListener('click', deleteSelected);
      document.getElementById('refreshBtn')?.addEventListener('click', refreshTree);
      document.getElementById('chatBtn')?.addEventListener('click', openChatPopup);
      document.getElementById('editorBtn')?.addEventListener('click', goEditor);
      document.getElementById('homeBtn')?.addEventListener('click', goHome);

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
      await Tree.load(scope);
      const urlParams = new URLSearchParams(window.location.search);
      const initialPath = urlParams.get('path');
      const initialScope = urlParams.get('scope');
      if (initialScope === 'app' || initialScope === 'workspace') {
        scope = initialScope;
        updateScopeButtons();
      }
      if (initialPath) {
        if (initialScope === 'app') await Tree.load('app');
        await openFile(initialPath);
      }
    })
    .catch((e) => {
      setStatus('Error: ' + e.message);
    });

  Session.connect();
}

document.addEventListener('DOMContentLoaded', init);

export { openFile, saveFile, newFile, newFolder, renameSelected, deleteSelected, refreshTree, setScope, openDevLink, goHome, goEditor, currentFile, isDirty };
```

---

<!-- ==== 26/39 : interface/static/js/session.js ==== -->

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

<!-- ==== 27/39 : interface/static/js/tree.js ==== -->

### interface/static/js/tree.js

```javascript
/* Project tree rendering module */
import API from './api.js';

/* Curated "important app scripts" shown as quick links in Dev view. */
const DEV_LINKS = [
  { name: 'server.py', icon: '🐍', path: 'server.py' },
  { name: 'README.md', icon: '📝', path: 'README.md' },
  { name: 'requirements.txt', icon: '📄', path: 'requirements.txt' },
  { name: 'parameters/filesystem.py', icon: '⚙️', path: 'parameters/filesystem.py' },
  { name: 'interface/core/operations.py', icon: '🧩', path: 'interface/core/operations.py' },
  { name: 'interface/core/defaults.py', icon: '🧩', path: 'interface/core/defaults.py' },
  { name: 'interface/routers/files.py', icon: '🌐', path: 'interface/routers/files.py' },
  { name: 'interface/routers/chat.py', icon: '🌐', path: 'interface/routers/chat.py' },
  { name: 'interface/clients/editor_client.py', icon: '🔗', path: 'interface/clients/editor_client.py' },
  { name: 'scripts/run.sh', icon: '⌨️', path: 'scripts/run.sh' },
  { name: 'scripts/run.bat', icon: '⌨️', path: 'scripts/run.bat' }
];

const Tree = {
  root: [],
  selectedPath: null,
  scope: 'workspace',
  expanded: new Set(),
  onFileSelect: null,
  onFolderSelect: null,
  onDevLink: null,

  async load(scope = 'workspace') {
    this.scope = scope;
    const data = await API.project(scope);
    this.root = data.filesystem || [];
    this.render();
  },

  key(path) {
    return this.scope + ':' + path;
  },

  render(containerId = 'tree') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    this.renderItems(this.root, container);
  },

  renderItems(items, container) {
    for (const item of items) {
      const row = document.createElement('div');
      row.className = 'tree-item';
      if (item.type === 'directory') {
        row.classList.add('folder');
        row.dataset.path = item.path;
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        const isExpanded = this.expanded.has(this.key(item.path));
        const toggle = document.createElement('span');
        toggle.className = 'toggle' + (isExpanded ? ' expanded' : '');
        toggle.textContent = isExpanded ? '−' : '+';
        const label = document.createElement('span');
        label.className = 'label';
        label.textContent = '📁 ' + item.name;
        row.appendChild(toggle);
        row.appendChild(label);
        const children = document.createElement('div');
        children.className = 'children' + (isExpanded ? '' : ' collapsed');
        row.onclick = () => {
          this.selectedPath = item.path;
          if (this.onFolderSelect) this.onFolderSelect(item.path);
          this.render();
          this.toggle(item.path);
        };
        container.appendChild(row);
        container.appendChild(children);
        this.renderItems(item.children || [], children);
      } else {
        row.textContent = this.getFileIcon(item.name) + ' ' + item.name;
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        row.onclick = () => {
          this.selectedPath = item.path;
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
    return this.load(this.scope);
  },

  renderDevLinks(containerId = 'devLinks') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    for (const link of DEV_LINKS) {
      const row = document.createElement('button');
      row.className = 'dev-link';
      row.type = 'button';
      row.textContent = link.icon + ' ' + link.name;
      row.title = link.path;
      row.onclick = () => {
        if (this.onDevLink) this.onDevLink(link);
      };
      container.appendChild(row);
    }
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

<!-- ==== 28/39 : parameters/__init__.py ==== -->

### parameters/__init__.py

```python
"""Project parameters package.

Holds the Project Manager filesystem owner (filesystem.py) that owns
the managed workspace, plus the project metadata it manages.
"""
```

---

<!-- ==== 29/39 : parameters/filesystem.py ==== -->

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


# ============================================================
# READ FILESYSTEM
# ============================================================

def read_filesystem(
    directory: Path | None = None,
    _root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Recursively read the project filesystem.

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
                    "editable": is_text_file(
                        child
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

<!-- ==== 30/39 : README.md ==== -->

### README.md

```markdown
# Project Manager

A lightweight FastAPI workspace server. Browse, edit, and chat about your
project from a single web dashboard with a Monaco-powered code editor.

## Layout

The repository is split into three pillars plus scripts:

```
├── server.py                Application entry point (FastAPI host)
├── requirements.txt
│
├── interface/               EDITOR INTERFACE
│   ├── static/              Web UI (home.html, chat.html, editor.html, js/)
│   ├── routers/             HTTP API routers (files, dirs, paths, ws, chat)
│   ├── core/                Controller layer (sessions, events, operations)
│   └── clients/             Python client (EditorClient / AsyncEditorClient)
│
├── parameters/              PROJECT PARAMETERS
│   └── filesystem.py        Filesystem owner for the managed workspace
│
├── workspace/               THE MANAGED PROJECT
│   ├── project.json
│   ├── documentation/  project_scope/  to_do/  updates/  config/  data/
│
└── scripts/                 run.bat / run.sh / setup.sh
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
- Chat popup (`/chat`) — stub that logs messages to `workspace/data/chat.log`
- Dev-scripts quick links to the important application files
- JSON REST API for filesystem operations (scope-aware)
- Python client for AI agents / other programs
- Works on Windows and (Chromebook) Linux

## Requirements

- Python 3.9+
- Network access for the code editor CDN (Monaco, loaded from cdnjs)

## Setup

### Windows

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
scripts\run.bat
```

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
| GET    | `/chat`                       | Chat popup UI                        |
| GET    | `/api/health`                 | Health + project info                |
| GET    | `/api/project?scope=`         | Project state + tree (ws/app)        |
| GET    | `/api/file/read?path=&scope=` | Read a file                          |
| PUT    | `/api/file/write`             | Write a file                         |
| POST   | `/api/file/create`            | Create a file                        |
| POST   | `/api/directory/create`       | Create a directory                   |
| PUT    | `/api/path/rename`            | Rename/move a path                   |
| DELETE | `/api/file/delete`            | Delete a file                        |
| DELETE | `/api/directory/delete`       | Delete a directory                   |
| POST   | `/api/chat`                   | Send a chat message (logged)         |
| GET    | `/api/chat`                   | Chat history                         |

Note: The `workspace/` content folders are empty so git does not track
them; the server recreates them automatically on startup.
```

---

<!-- ==== 31/39 : requirements.txt ==== -->

### requirements.txt

```text
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
websockets==13.1
```

---

<!-- ==== 32/39 : scripts/run.bat ==== -->

### scripts/run.bat

```batch
@echo off
rem Project Manager - start the server from the virtual environment.

cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run: python -m venv .venv
    echo Then: .venv\Scripts\python -m pip install -r requirements.txt
    exit /b 1
)

echo Starting Project Manager at http://127.0.0.1:8000
echo To stop: press Ctrl+C
echo.

.venv\Scripts\python server.py
```

---

<!-- ==== 33/39 : scripts/run.sh ==== -->

### scripts/run.sh

```bash
#!/usr/bin/env bash
#
# Project Manager - start the server from the virtual environment.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run ./setup.sh first." >&2
    exit 1
fi

echo "Starting Project Manager at http://127.0.0.1:8000"
echo "To stop: press Ctrl+C"
echo

.venv/bin/python server.py
```

---

<!-- ==== 34/39 : scripts/setup.sh ==== -->

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

<!-- ==== 35/39 : server.py ==== -->

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

<!-- ==== 36/39 : workspace/agent.md ==== -->

### workspace/agent.md

```markdown

```

---

<!-- ==== 37/39 : workspace/documentation/MASTER_COPY.md ==== -->

### workspace/documentation/MASTER_COPY.md

```markdown
# Project Manager — MASTER COPY

Single-file snapshot of the complete Project Manager application source tree.

- **Project:** Project Manager
- **Version:** 1.0.0
- **Workspace version:** 1.0
- **Repo:** https://github.com/TheChuey/project
- **Generated:** 2026-09-23

---

## AI Agent Engine — Entry Point

The chat endpoint is the **AI agent engine entry point** for the project.

This is where an agent / request-model plugs into the application. The editor
interface (and the home page) reach the engine through the exact same stable
HTTP surface, so the engine can be swapped without touching the UI:

| Route       | Method | Purpose                                                    |
| ----------- | ------ | ---------------------------------------------------------- |
| `/api/chat` | POST   | Send a message to the agent engine. Body: `{"message": str, "scope": str?}`. |
| `/api/chat` | GET    | Fetch recent agent conversation history (`?limit=`).        |

The engine lives in `interface/routers/chat.py` and persists history to
`workspace/data/chat.log` (JSON lines). Anything — the home page chat popup,
the editor's chat button, or a future AI/agent process — goes through this one
entry point, keeping the full app decoupled from the engine implementation.

```text
┌────────────────────┐   POST /api/chat   ┌────────────────────────┐
│  editor interface  │ ──────────────────▶│  agent engine          │
│  (home / editor)   │                    │  interface/routers/    │
│                    │ ◀──────────────────│        chat.py         │
└────────────────────┘       reply        └────────────────────────┘
```

---

## Editor Interface — Accessing the Agent Tools

The editor's browser interface reaches the agent engine and the code tools
through `interface/static/js/api.js` and `interface/static/js/session.js`.
Every agent tool the interface can touch is exposed as a small API method:

| Front-end accessor        | Backend route                       | Purpose                          |
| ------------------------- | ----------------------------------- | -------------------------------- |
| `API.chatSend(message)`   | `POST /api/chat`                    | Send a message to the agent      |
| `API.chatHistory(limit)`  | `GET /api/chat?limit=`              | Read agent conversation history  |
| `API.fileRead(path)`      | `GET /api/file/read?path=`          | Open a file in the editor        |
| `API.fileWrite(path, c)`  | `PUT /api/file/write`               | Save the current buffer          |
| `API.project(scope)`      | `GET /api/project?scope=`           | Reload the file tree             |
| `API.pathRename(a, b)`    | `PUT /api/path/rename`              | Rename a file / folder           |
| `API.fileDelete(path)`    | `DELETE /api/file/delete?path=`     | Delete a file                    |
| `API.directoryDelete(p)`  | `DELETE /api/directory/delete?path=`| Delete a folder                  |

The editor toolbar exposes these tools as buttons:

- **Save** (`Ctrl+S`) → `API.fileWrite` on the current file
- **+ File / + Folder / Rename / Delete** → the matching create/rename/delete
  accessors above
- **Chat** button → opens the chat popup, which calls `API.chatSend`
- **Dev links** sidebar → opens app-scope files through `API.fileRead`

For new agent tools, the pattern to follow is: add
`schema -> route -> API.* accessor -> toolbar/popup button`. Nothing else in
the app changes, because every surface already talks to the API client.

---

## File Structure

```text
project/
    ├── interface
    │   ├── clients
    │   ├── core
    │   ├── routers
    │   └── static
    │       └── js
    ├── parameters
    ├── scripts
    └── workspace
        ├── config
        ├── data
        ├── documentation
        ├── project_scope
        ├── to_do
        └── updates
```

---

---

<!-- ==== 1/39 : .gitattributes ==== -->

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

<!-- ==== 2/39 : .gitignore ==== -->

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

<!-- ==== 3/39 : interface/clients/__init__.py ==== -->

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

<!-- ==== 4/39 : interface/clients/editor_client.py ==== -->

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

<!-- ==== 5/39 : interface/core/__init__.py ==== -->

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

<!-- ==== 6/39 : interface/core/defaults.py ==== -->

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

<!-- ==== 7/39 : interface/core/events.py ==== -->

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

<!-- ==== 8/39 : interface/core/operations.py ==== -->

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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Project state: project info, active root and filesystem tree.

        Args:
            scope:
                ``"workspace"`` (default) or ``"app"``.
        """

        try:

            root = _root_for(scope)

            return {
                "scope": scope or "workspace",
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
        scope: str | None = "workspace",
    ) -> str:
        """
        Open a project file and return its contents.

        Args:
            path:
                Root-relative file path.
            scope:
                ``"workspace"`` (default) or ``"app"``.

        Returns:
            The file contents.
        """

        return self.filesystem.read_file(
            path,
            root=_root_for(scope),
        )

    def save(
        self,
        path: str,
        content: str,
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Write file contents back to the project filesystem.

        Publishes a ``saved`` event on success.
        """

        self.filesystem.write_file(
            path,
            content,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Create a new project file.

        Publishes a ``created`` event on success.
        """

        self.filesystem.create_file(
            path,
            content,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Create a new project directory.

        Publishes a ``created`` event on success.
        """

        self.filesystem.create_directory(
            path,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Rename or move a project file/directory.

        Publishes a ``renamed`` event on success.
        """

        self.filesystem.rename_path(
            old_path,
            new_path,
            root=_root_for(scope),
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
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Delete a project file or directory.

        Publishes a ``deleted`` event on success.
        """

        self.filesystem.delete_path(
            path,
            root=_root_for(scope),
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

<!-- ==== 9/39 : interface/core/session.py ==== -->

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

<!-- ==== 10/39 : interface/routers/__init__.py ==== -->

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

def normalize_scope(scope: str | None) -> str:
    """
    Validate and normalize a scope query parameter.

    Raises:
        HTTPException (422):
            If the scope is not a known scope.
    """

    scope = scope or "workspace"

    if scope not in VALID_SCOPES:

        raise HTTPException(
            status_code=422,
            detail=f"Unknown scope: {scope}",
        )

    return scope
```

---

<!-- ==== 11/39 : interface/routers/chat.py ==== -->

### interface/routers/chat.py

```python
"""
Project Manager chat router (stub).
====================================

Chat stub for the interface. Messages are appended to a plaintext
log file inside the managed workspace (``workspace/data/chat.log``)
so history survives reloads. This is a placeholder surface: a real
AI agent can replace the handler later without changing the API
shape (``POST /api/chat`` to send, ``GET /api/chat`` to fetch).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from parameters import filesystem

from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# REQUEST MODELS
# ============================================================

class ChatMessage(BaseModel):

    message: str


# ============================================================
# CHAT LOG HELPERS
# ============================================================

MAX_MESSAGE_LENGTH = 2000

DEFAULT_LIMIT = 50

MAX_LIMIT = 500


def _log_path() -> Any:
    """
    Safe path to the chat log inside the managed workspace.
    """

    return filesystem.resolve_project_path(
        "data/chat.log"
    )


def _append_message(message: str) -> dict[str, Any]:
    """
    Append one timestamped message to the chat log.

    The data directory is created on demand.
    """

    log_path = _log_path()

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sender": "user",
        "message": message,
    }

    with log_path.open(
        "a",
        encoding="utf-8",
    ) as handle:

        handle.write(
            json.dumps(entry) + "\n"
        )

    return entry


def _read_history(limit: int) -> list[dict[str, Any]]:
    """
    Read the most recent chat log entries in chronological order.
    """

    log_path = _log_path()

    if not log_path.exists():

        return []

    entries: list[dict[str, Any]] = []

    with log_path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        for line in handle:

            line = line.strip()

            if not line:
                continue

            try:

                entries.append(
                    json.loads(line)
                )

            except json.JSONDecodeError:
                continue

    return entries[-limit:]


# ============================================================
# SEND MESSAGE
# ============================================================

@router.post("/api/chat")
def send_chat_message(
    request: Request,
    payload: ChatMessage,
):
    """
    Log a chat message.

    The stub currently records the message; a future agent
    provider can reply through the same endpoint.
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

    try:

        entry = _append_message(message)

        return {
            "status": "logged",
            "entry": entry,
        }

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

    limit = max(1, min(limit, MAX_LIMIT))

    try:

        return {
            "entries": _read_history(limit),
        }

    except Exception as error:

        raise project_manager_error(
            error
        )
```

---

<!-- ==== 12/39 : interface/routers/directories.py ==== -->

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
    scope: str = "workspace",
):
    """
    Create a project directory.

    Query params:
        path:
            Root-relative directory path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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
    scope: str = "workspace",
):
    """
    Delete a project directory.

    Query params:
        path:
            Root-relative directory path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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

<!-- ==== 13/39 : interface/routers/errors.py ==== -->

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

<!-- ==== 14/39 : interface/routers/files.py ==== -->

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

    scope: str = "workspace"


class FileCreateRequest(BaseModel):

    path: str

    content: str = ""

    scope: str = "workspace"


# ============================================================
# READ FILE
# ============================================================

@router.get("/api/file/read")
def read_file(
    request: Request,
    path: str,
    scope: str = "workspace",
):
    """
    Read a project text file.

    Query params:
        path:
            Root-relative file path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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
    scope: str = "workspace",
):
    """
    Delete a project file.

    Query params:
        path:
            Root-relative file path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
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

<!-- ==== 15/39 : interface/routers/paths.py ==== -->

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

    scope: str = "workspace"


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

<!-- ==== 16/39 : interface/routers/project.py ==== -->

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
    scope: str = "workspace",
):
    """
    Project information and filesystem tree.

    Query params:
        scope:
            ``"workspace"`` (default) or ``"app"``.
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

<!-- ==== 17/39 : interface/routers/ws.py ==== -->

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

    session = controller.sessions.register()

    try:

        await websocket.send_json(
            {
                "type": "hello",
                "client_id": session.client_id,
            }
        )

        async def forward(
            event: dict[str, Any],
        ) -> None:
            """
            Forward a published event to this socket.
            """

            try:

                await websocket.send_json(
                    {
                        "type": "event",
                        "event": event,
                    }
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
                    "sessions": controller.sessions.snapshot(),
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

                controller.sessions.update(
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

                controller.sessions.update(
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

        controller.sessions.unregister(
            session.client_id
        )
```

---

<!-- ==== 18/39 : interface/static/chat.html ==== -->

### interface/static/chat.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Manager Chat</title>

    <style>
        /* =========================================================
           RESET / BASE
           ========================================================= */

        * {
            box-sizing: border-box;
        }

        html,
        body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family:
                Inter,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Arial,
                sans-serif;
            background: #0f1117;
            color: #e6e8ee;
        }

        body {
            display: flex;
            flex-direction: column;
        }

        button,
        textarea {
            font-family: inherit;
        }


        /* =========================================================
           TOP BAR
           ========================================================= */

        .chatbar {
            height: 58px;
            min-height: 58px;

            display: flex;
            align-items: center;
            justify-content: space-between;

            padding: 0 20px;

            background: #151821;
            border-bottom: 1px solid #292d38;
        }

        .chat-title-area {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .chat-icon {
            width: 34px;
            height: 34px;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 9px;

            background: #252a38;
            border: 1px solid #343949;

            font-size: 17px;
        }

        .title {
            font-size: 15px;
            font-weight: 600;
            color: #f1f3f7;
        }

        .subtitle {
            margin-top: 2px;
            font-size: 11px;
            color: #7f8798;
        }

        .status-area {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #777;
        }

        .status {
            font-size: 12px;
            color: #8991a2;
        }


        /* =========================================================
           MAIN CHAT AREA
           ========================================================= */

        #chatLog {
            flex: 1;

            overflow-y: auto;

            padding: 28px 22px 30px;

            display: flex;
            flex-direction: column;
            gap: 14px;

            background:
                radial-gradient(
                    circle at top center,
                    rgba(58, 65, 85, 0.12),
                    transparent 45%
                ),
                #0f1117;
        }

        /* Scrollbar */

        #chatLog::-webkit-scrollbar {
            width: 8px;
        }

        #chatLog::-webkit-scrollbar-track {
            background: transparent;
        }

        #chatLog::-webkit-scrollbar-thumb {
            background: #303543;
            border-radius: 10px;
        }

        #chatLog::-webkit-scrollbar-thumb:hover {
            background: #3b4150;
        }


        /* =========================================================
           MESSAGE CARD
           ========================================================= */

        .msg {
            width: min(850px, 90%);

            display: flex;
            flex-direction: column;
            gap: 6px;

            padding: 13px 15px;

            border-radius: 12px;

            background: #181b24;
            border: 1px solid #292d38;

            box-shadow:
                0 4px 14px rgba(0, 0, 0, 0.12);
        }

        .msg-label {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.02em;
            color: #858d9e;
        }

        .msg-body {
            word-break: break-word;
            white-space: pre-wrap;

            font-size: 14px;
            line-height: 1.55;

            color: #dfe2e8;
        }

        .msg-meta {
            align-self: flex-end;

            font-size: 10px;
            color: #626a7a;
        }


        /* =========================================================
           USER MESSAGE
           ========================================================= */

        .msg.user {
            align-self: flex-end;

            background: #1b2634;
            border-color: #29445e;
        }

        .msg.user .msg-label {
            color: #70b7ed;
        }

        .msg.user .msg-body {
            color: #edf6ff;
        }


        /* =========================================================
           EVENT MESSAGE
           ========================================================= */

        .msg.event {
            width: min(750px, 85%);

            background: #151e19;
            border-color: #27402f;
        }

        .msg.event .msg-label {
            color: #72b784;
        }

        .msg.event .msg-body {
            color: #b9d8bf;
            font-size: 13px;
        }


        /* =========================================================
           SYSTEM MESSAGE
           ========================================================= */

        .msg.system {
            width: min(750px, 85%);

            background: #14161c;
            border-color: #292d35;
        }

        .msg.system .msg-label {
            color: #777f90;
        }

        .msg.system .msg-body {
            color: #9299a8;
            font-size: 13px;
        }


        /* =========================================================
           EMPTY / LOADING MESSAGE
           ========================================================= */

        .msg.system:first-child {
            opacity: 0.85;
        }


        /* =========================================================
           INPUT AREA
           ========================================================= */

        .chatfoot {
            padding: 14px 20px 18px;

            background: #151821;
            border-top: 1px solid #292d38;
        }

        .input-container {
            width: min(900px, 100%);
            margin: 0 auto;

            display: flex;
            align-items: flex-end;
            gap: 10px;

            padding: 9px;

            background: #1b1f29;
            border: 1px solid #303543;
            border-radius: 14px;

            transition:
                border-color 0.2s ease,
                box-shadow 0.2s ease;
        }

        .input-container:focus-within {
            border-color: #3d6d96;

            box-shadow:
                0 0 0 3px rgba(61, 109, 150, 0.12);
        }


        /* =========================================================
           TEXT INPUT
           ========================================================= */

        #chatInput {
            flex: 1;

            min-height: 42px;
            max-height: 160px;

            padding: 10px 11px;

            background: transparent;
            color: #edf0f5;

            border: none;
            outline: none;

            resize: none;

            font-size: 14px;
            line-height: 1.45;
        }

        #chatInput::placeholder {
            color: #697182;
        }


        /* =========================================================
           SEND BUTTON
           ========================================================= */

        #chatSend {
            width: 42px;
            height: 42px;

            display: flex;
            align-items: center;
            justify-content: center;

            flex-shrink: 0;

            border: 1px solid #3c4554;
            border-radius: 10px;

            background: #27303d;
            color: #dce7f2;

            cursor: pointer;

            font-size: 16px;

            transition:
                background 0.15s ease,
                border-color 0.15s ease,
                transform 0.1s ease;
        }

        #chatSend:hover {
            background: #314052;
            border-color: #4b5c70;
        }

        #chatSend:active {
            transform: scale(0.96);
        }

        #chatSend:disabled {
            opacity: 0.45;
            cursor: not-allowed;
        }


        /* =========================================================
           INPUT FOOTER HINT
           ========================================================= */

        .input-hint {
            width: min(900px, 100%);
            margin: 7px auto 0;

            text-align: center;

            font-size: 10px;
            color: #5f6675;
        }


        /* =========================================================
           RESPONSIVE
           ========================================================= */

        @media (max-width: 700px) {

            .chatbar {
                padding: 0 14px;
            }

            .subtitle {
                display: none;
            }

            #chatLog {
                padding: 18px 12px 22px;
            }

            .msg {
                width: 94%;
            }

            .chatfoot {
                padding: 10px 10px 12px;
            }

            .input-hint {
                display: none;
            }
        }
    </style>
</head>

<body>

    <!-- =========================================================
         HEADER
         ========================================================= -->

    <header class="chatbar">

        <div class="chat-title-area">

            <div class="chat-icon">
                💬
            </div>

            <div>
                <div class="title">
                    Project Chat
                </div>

                <div class="subtitle">
                    Project Manager
                </div>
            </div>

        </div>


        <div class="status-area">

            <span id="statusDot" class="status-dot"></span>

            <span id="chatStatus" class="status">
                Connecting…
            </span>

        </div>

    </header>


    <!-- =========================================================
         CHAT MESSAGES
         ========================================================= -->

    <main id="chatLog">

        <div class="msg system">

            <span class="msg-label">
                SYSTEM
            </span>

            <span class="msg-body">
                Loading messages…
            </span>

        </div>

    </main>


    <!-- =========================================================
         CHAT INPUT
         ========================================================= -->

    <footer class="chatfoot">

        <form id="chatForm">

            <div class="input-container">

                <textarea
                    id="chatInput"
                    rows="1"
                    placeholder="Message Project Manager…"
                    autocomplete="off"
                ></textarea>

                <button
                    id="chatSend"
                    type="submit"
                    aria-label="Send message"
                    title="Send message"
                >
                    ↑
                </button>

            </div>

        </form>

        <div class="input-hint">
            Press Enter to send · Shift + Enter for a new line
        </div>

    </footer>


    <!-- =========================================================
         EXISTING CHAT JAVASCRIPT
         ========================================================= -->

    <script type="module" src="/static/js/chat.js"></script>


    <!-- =========================================================
         SMALL UI ENHANCEMENTS
         These do not replace chat.js.
         ========================================================= -->

    <script>

        /*
         * Automatically grow the message box.
         * This does not communicate with the backend.
         */

        const chatInput = document.getElementById("chatInput");

        if (chatInput) {

            chatInput.addEventListener("input", () => {

                chatInput.style.height = "auto";

                chatInput.style.height =
                    Math.min(chatInput.scrollHeight, 160) + "px";

            });


            /*
             * Enter = send
             * Shift + Enter = new line
             *
             * The existing form submission handled by chat.js
             * remains responsible for actually sending the message.
             */

            chatInput.addEventListener("keydown", (event) => {

                if (
                    event.key === "Enter" &&
                    !event.shiftKey
                ) {

                    event.preventDefault();

                    const form =
                        document.getElementById("chatForm");

                    if (form) {
                        form.requestSubmit();
                    }

                }

            });

        }


        /*
         * Automatically keep the newest message visible.
         *
         * MutationObserver watches for messages added by chat.js.
         */

        const chatLog =
            document.getElementById("chatLog");

        if (chatLog) {

            const observer =
                new MutationObserver(() => {

                    chatLog.scrollTop =
                        chatLog.scrollHeight;

                });

            observer.observe(chatLog, {
                childList: true,
                subtree: true
            });

        }

    </script>

</body>
</html>

```

---

<!-- ==== 19/39 : interface/static/editor.html ==== -->

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
            height: calc(100vh - 74px);
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
    </style>

    <!-- Monaco Loader CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js"></script>
</head>
<body>

<div class="topbar">
    <div class="title">Project Manager Editor</div>
    <button id="homeBtn" onclick="goHome()">🏠 Home</button>
    <button id="saveBtn" class="primary" onclick="saveFile()">Save</button>
    <button id="newFileBtn" onclick="newFile()">+ File</button>
    <button id="newFolderBtn" onclick="newFolder()">+ Folder</button>
    <button id="renameBtn" onclick="renameSelected()">Rename</button>
    <button id="deleteBtn" class="danger" onclick="deleteSelected()">Delete</button>
    <button id="refreshBtn" onclick="refreshTree()">Refresh</button>
</div>

<div class="workspace">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span>PROJECT FILES</span>
        </div>
        <div id="tree" class="tree">Loading...</div>
    </div>
    
    <div class="resize-handle" id="resizeHandle"></div>

    <div class="editor-area">
        <div class="filebar">
            <div>
                <span id="currentFile">No file selected</span>
                <span id="unsavedIndicator"></span>
            </div>
            <div id="language">plaintext</div>
        </div>
        <div id="editor"></div>
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

<!-- ==== 20/39 : interface/static/home.html ==== -->

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

        .scope-toggle {
            display: flex;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            overflow: hidden;
            margin-right: 12px;
        }

        .scope-toggle button {
            border: none;
            border-radius: 0;
            background: #252526;
            padding: 6px 12px;
        }

        .scope-toggle button.active {
            background: #0e639c;
        }

        .workspace {
            display: flex;
            height: calc(100vh - 74px);
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

        /* ---- Dev scripts quick links ---- */
        .dev-links {
            border-bottom: 1px solid #3f3f46;
            padding: 8px;
        }

        .dev-links-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            font-weight: bold;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }

        .dev-link {
            display: block;
            width: 100%;
            text-align: left;
            background: transparent;
            border: 1px solid transparent;
            color: #d1d5db;
            padding: 4px 6px;
            border-radius: 3px;
            font-size: 12px;
            margin-bottom: 2px;
        }

        .dev-link:hover {
            background: #2a2d2e;
            border-color: #3f3f46;
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
    </style>

    <!-- Monaco Loader CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js"></script>
</head>
<body>

<div class="topbar">
    <div class="title">Project Manager</div>
    <span id="projectName">…</span>

    <div class="scope-toggle" role="group" aria-label="Scope">
        <button id="scopeWs" type="button" class="active">Workspace</button>
        <button id="scopeApp" type="button">Dev</button>
    </div>

    <button id="saveBtn" class="primary" type="button">Save</button>
    <button id="newFileBtn" type="button">+ File</button>
    <button id="newFolderBtn" type="button">+ Folder</button>
    <button id="renameBtn" type="button">Rename</button>
    <button id="deleteBtn" class="danger" type="button">Delete</button>
    <button id="refreshBtn" type="button">Refresh</button>

    <div class="spacer"></div>

    <button id="chatBtn" class="primary" type="button">💬 Chat</button>
    <button id="editorBtn" type="button">📝 Editor</button>
    <a href="/" style="color:#fff; text-decoration:none; font-size:13px;">Home</a>
</div>

<div class="workspace">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span>PROJECT FILES</span>
        </div>

        <div class="dev-links">
            <div class="dev-links-head">
                <span>Dev scripts</span>
                <button id="devLinksToggle" type="button" style="padding:0 6px; font-size:12px;">−</button>
            </div>
            <div id="devLinks"></div>
        </div>

        <div id="tree" class="tree">Loading...</div>
    </div>

    <div class="resize-handle" id="resizeHandle"></div>

    <div class="editor-area">
        <div class="filebar">
            <div>
                <span id="currentFile">No file selected</span>
                <span id="unsavedIndicator"></span>
            </div>
            <div id="language">plaintext</div>
        </div>
        <div id="editor"></div>
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

<!-- ==== 21/39 : interface/static/index.html ==== -->

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

async function loadProject() {
  setStatus('Loading project...');
  try {
    const data = await API.project();
    renderTree(data.filesystem || []);
    setStatus('Project loaded');
  } catch (err) {
    setStatus('Error: ' + err.message);
  }
}

function renderTree(items) {
  const container = document.getElementById('projectTree');
  container.innerHTML = '';
  renderItems(items, container);
}

function renderItems(items, container) {
  items.forEach(item => {
    const div = document.createElement('div');
    div.className = 'tree-item';
    if (item.type === 'directory') {
      div.classList.add('folder');
      div.dataset.path = item.path;
      const toggle = document.createElement('span');
      toggle.className = 'toggle';
      toggle.textContent = '+';
      const label = document.createElement('span');
      label.textContent = '📁 ' + item.name;
      label.style.flex = '1';
      label.style.marginLeft = '4px';
      div.appendChild(toggle);
      div.appendChild(label);
      div.onclick = (e) => {
        e.stopPropagation();
        toggleFolder(div);
      };
      container.appendChild(div);
      if (item.children && item.children.length) {
        const childrenContainer = document.createElement('div');
        childrenContainer.className = 'children collapsed';
        container.appendChild(childrenContainer);
        renderItems(item.children, childrenContainer);
      }
    } else {
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
  const path = prompt('Enter file path/name:');
  if (!path) return;
  try {
    await API.fileCreate(path, '');
    await loadProject();
    openEditor(path);
  } catch (err) {
    alert(err.message);
  }
}

async function submitCreateFolderPrompt() {
  const path = prompt('Enter folder path:');
  if (!path) return;
  try {
    await API.directoryCreate(path);
    await loadProject();
  } catch (err) {
    alert(err.message);
  }
}

function openEditor(filePath) {
  let url = '/editor';
  if (filePath) url += '?path=' + encodeURIComponent(filePath);
  window.location.href = url;
}

function openEditorPopup(filePath) {
  let url = '/editor';
  if (filePath) url += '?path=' + encodeURIComponent(filePath);
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

<!-- ==== 22/39 : interface/static/js/api.js ==== -->

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

  project(scope = 'workspace') {
    return this.request('GET', `/api/project?scope=${encodeURIComponent(scope)}`);
  },

  fileRead(path, scope = 'workspace') {
    return this.request('GET', `/api/file/read?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  fileWrite(path, content, scope = 'workspace') {
    return this.request('PUT', '/api/file/write', { path, content, scope });
  },

  fileCreate(path, content = '', scope = 'workspace') {
    return this.request('POST', '/api/file/create', { path, content, scope });
  },

  fileDelete(path, scope = 'workspace') {
    return this.request('DELETE', `/api/file/delete?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  directoryCreate(path, scope = 'workspace') {
    return this.request('POST', `/api/directory/create?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  directoryDelete(path, scope = 'workspace') {
    return this.request('DELETE', `/api/directory/delete?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  pathRename(oldPath, newPath, scope = 'workspace') {
    return this.request('PUT', '/api/path/rename', { old_path: oldPath, new_path: newPath, scope });
  },

  chatSend(message) {
    return this.request('POST', '/api/chat', { message });
  },

  chatHistory(limit = 100) {
    return this.request('GET', `/api/chat?limit=${limit}`);
  },

  sessions() {
    return this.request('GET', '/api/sessions');
  }
};

export default API;
```

---

<!-- ==== 23/39 : interface/static/js/chat.js ==== -->

### interface/static/js/chat.js

```javascript
/* Chat popup module */
import API from './api.js';
import Session from './session.js';

const log = document.getElementById('chatLog');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const sendBtn = document.getElementById('chatSend');
const status = document.getElementById('chatStatus');

function appendLine(role, text, meta = '') {
  const line = document.createElement('div');
  line.className = 'msg ' + role;
  const label = document.createElement('span');
  label.className = 'msg-label';
  label.textContent = role === 'user' ? 'You' : role === 'event' ? 'Event' : 'System';
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

function setStatus(text) {
  if (status) status.textContent = text;
}

async function loadHistory() {
  try {
    const data = await API.chatHistory();
    const entries = data.entries || [];
    if (!entries.length) {
      appendLine('system', 'No messages yet. Say hello!');
      return;
    }
    for (const entry of entries) {
      const ts = entry.ts ? new Date(entry.ts).toLocaleTimeString() : '';
      appendLine(entry.sender === 'user' ? 'user' : 'system', entry.message, ts);
    }
  } catch (error) {
    setStatus('Failed to load history: ' + error.message);
  }
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  appendLine('user', message, new Date().toLocaleTimeString());
  setStatus('Logging…');
  try {
    await API.chatSend(message);
    setStatus('Message logged.');
  } catch (error) {
    setStatus('Send failed: ' + error.message);
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

loadHistory();
Session.connect();
```

---

<!-- ==== 24/39 : interface/static/js/editor.js ==== -->

### interface/static/js/editor.js

```javascript
/* Monaco editor module */
let editor = null;

const Editor = {
  init() {
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

<!-- ==== 25/39 : interface/static/js/main.js ==== -->

### interface/static/js/main.js

```javascript
/* Main application wiring */
import API from './api.js';
import Session from './session.js';
import Tree from './tree.js';
import Editor from './editor.js';

let currentFile = null;
let currentLanguage = 'plaintext';
let isDirty = false;
let currentIsFolder = false;
let scope = 'workspace';

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
}

async function openFile(filePath) {
  if (isDirty) {
    const proceed = confirm('You have unsaved changes. Open another file?');
    if (!proceed) return;
  }
  setStatus('Opening ' + filePath + '...');
  try {
    const data = await API.fileRead(filePath, scope);
    currentFile = filePath;
    currentIsFolder = false;
    currentLanguage = getLanguage(filePath);
    Editor.setValue(data.content || '');
    Editor.setLanguage(currentLanguage);
    isDirty = false;
    updateFileDisplay();
    Tree.setSelected(filePath);
    Tree.reveal(filePath);
    setStatus('Opened ' + filePath);
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
  setStatus('Saving...');
  try {
    await API.fileWrite(currentFile, Editor.getValue(), scope);
    isDirty = false;
    updateFileDisplay();
    setStatus('Saved ' + currentFile);
    await Tree.refresh();
  } catch (error) {
    setStatus('Save error: ' + error.message);
    alert(error.message);
  }
}

async function newFile() {
  const fileName = prompt('Enter new file path/name:');
  if (!fileName) return;
  try {
    await API.fileCreate(fileName, '', scope);
    await Tree.refresh();
    await openFile(fileName);
    setStatus('Created ' + fileName);
  } catch (error) {
    alert(error.message);
  }
}

async function newFolder() {
  const folderPath = prompt('Enter new folder path:');
  if (!folderPath) return;
  try {
    await API.directoryCreate(folderPath, scope);
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
  const newName = prompt('Enter the new name/path:', currentFile);
  if (!newName || newName === currentFile) return;
  try {
    await API.pathRename(currentFile, newName, scope);
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
  const confirmed = confirm((currentIsFolder ? 'Delete folder ' : 'Delete file ') + currentFile + '?');
  if (!confirmed) return;
  try {
    if (currentIsFolder) {
      await API.directoryDelete(currentFile, scope);
    } else {
      await API.fileDelete(currentFile, scope);
    }
    currentFile = null;
    currentIsFolder = false;
    Editor.setValue('');
    isDirty = false;
    updateFileDisplay();
    await Tree.refresh();
    setStatus('Deleted.');
  } catch (error) {
    alert(error.message);
  }
}

async function refreshTree() {
  await Tree.refresh();
  setStatus('Refreshed.');
}

function updateScopeButtons() {
  const wsBtn = document.getElementById('scopeWs');
  const appBtn = document.getElementById('scopeApp');
  if (wsBtn) wsBtn.classList.toggle('active', scope === 'workspace');
  if (appBtn) appBtn.classList.toggle('active', scope === 'app');
}

async function setScope(nextScope) {
  if (scope === nextScope) return;
  if (isDirty) {
    const proceed = confirm('You have unsaved changes. Switch scope?');
    if (!proceed) return;
  }
  scope = nextScope;
  currentFile = null;
  currentIsFolder = false;
  Editor.setValue('');
  isDirty = false;
  updateFileDisplay();
  updateScopeButtons();
  setStatus(scope === 'app' ? 'Dev mode: application files' : 'Workspace mode: project files');
  try {
    await Tree.load(scope);
  } catch (error) {
    setStatus('Error: ' + error.message);
  }
}

async function openDevLink(link) {
  if (scope !== 'app') {
    scope = 'app';
    updateScopeButtons();
  }
  setStatus('Opening ' + link.path + '...');
  try {
    await Tree.load(scope);
    await openFile(link.path);
  } catch (error) {
    setStatus('Error: ' + error.message);
  }
}

function openChatPopup() {
  const width = 420; const height = 600;
  const left = (window.screen.width - width) / 2;
  const top = (window.screen.height - height) / 2;
  window.open('/chat', 'ProjectManagerChat', `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no`);
}

function goHome() {
  window.location.href = '/';
}

function goEditor() {
  window.location.href = '/editor';
}

function init() {
  Editor.init()
    .then(async () => {
      Editor.onChange(() => {
        if (currentFile) {
          isDirty = true;
          updateFileDisplay();
        }
      });

      Tree.onFileSelect = openFile;
      Tree.onFolderSelect = selectFolder;
      Tree.onDevLink = openDevLink;

      // ---- Dev-script quick links ----
      if (document.getElementById('devLinks')) {
        Tree.renderDevLinks('devLinks');
      }

      const devLinksToggle = document.getElementById('devLinksToggle');
      const devLinksBox = document.getElementById('devLinks');
      if (devLinksToggle && devLinksBox) {
        devLinksToggle.addEventListener('click', () => {
          const hidden = devLinksBox.style.display === 'none';
          devLinksBox.style.display = hidden ? '' : 'none';
          devLinksToggle.textContent = hidden ? '−' : '+';
        });
      }

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

      // ---- Scope toggle ----
      document.getElementById('scopeWs')?.addEventListener('click', () => setScope('workspace'));
      document.getElementById('scopeApp')?.addEventListener('click', () => setScope('app'));
      updateScopeButtons();

      // ---- Top bar actions ----
      document.getElementById('saveBtn')?.addEventListener('click', saveFile);
      document.getElementById('newFileBtn')?.addEventListener('click', newFile);
      document.getElementById('newFolderBtn')?.addEventListener('click', newFolder);
      document.getElementById('renameBtn')?.addEventListener('click', renameSelected);
      document.getElementById('deleteBtn')?.addEventListener('click', deleteSelected);
      document.getElementById('refreshBtn')?.addEventListener('click', refreshTree);
      document.getElementById('chatBtn')?.addEventListener('click', openChatPopup);
      document.getElementById('editorBtn')?.addEventListener('click', goEditor);
      document.getElementById('homeBtn')?.addEventListener('click', goHome);

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
      await Tree.load(scope);
      const urlParams = new URLSearchParams(window.location.search);
      const initialPath = urlParams.get('path');
      const initialScope = urlParams.get('scope');
      if (initialScope === 'app' || initialScope === 'workspace') {
        scope = initialScope;
        updateScopeButtons();
      }
      if (initialPath) {
        if (initialScope === 'app') await Tree.load('app');
        await openFile(initialPath);
      }
    })
    .catch((e) => {
      setStatus('Error: ' + e.message);
    });

  Session.connect();
}

document.addEventListener('DOMContentLoaded', init);

export { openFile, saveFile, newFile, newFolder, renameSelected, deleteSelected, refreshTree, setScope, openDevLink, goHome, goEditor, currentFile, isDirty };
```

---

<!-- ==== 26/39 : interface/static/js/session.js ==== -->

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

<!-- ==== 27/39 : interface/static/js/tree.js ==== -->

### interface/static/js/tree.js

```javascript
/* Project tree rendering module */
import API from './api.js';

/* Curated "important app scripts" shown as quick links in Dev view. */
const DEV_LINKS = [
  { name: 'server.py', icon: '🐍', path: 'server.py' },
  { name: 'README.md', icon: '📝', path: 'README.md' },
  { name: 'requirements.txt', icon: '📄', path: 'requirements.txt' },
  { name: 'parameters/filesystem.py', icon: '⚙️', path: 'parameters/filesystem.py' },
  { name: 'interface/core/operations.py', icon: '🧩', path: 'interface/core/operations.py' },
  { name: 'interface/core/defaults.py', icon: '🧩', path: 'interface/core/defaults.py' },
  { name: 'interface/routers/files.py', icon: '🌐', path: 'interface/routers/files.py' },
  { name: 'interface/routers/chat.py', icon: '🌐', path: 'interface/routers/chat.py' },
  { name: 'interface/clients/editor_client.py', icon: '🔗', path: 'interface/clients/editor_client.py' },
  { name: 'scripts/run.sh', icon: '⌨️', path: 'scripts/run.sh' },
  { name: 'scripts/run.bat', icon: '⌨️', path: 'scripts/run.bat' }
];

const Tree = {
  root: [],
  selectedPath: null,
  scope: 'workspace',
  expanded: new Set(),
  onFileSelect: null,
  onFolderSelect: null,
  onDevLink: null,

  async load(scope = 'workspace') {
    this.scope = scope;
    const data = await API.project(scope);
    this.root = data.filesystem || [];
    this.render();
  },

  key(path) {
    return this.scope + ':' + path;
  },

  render(containerId = 'tree') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    this.renderItems(this.root, container);
  },

  renderItems(items, container) {
    for (const item of items) {
      const row = document.createElement('div');
      row.className = 'tree-item';
      if (item.type === 'directory') {
        row.classList.add('folder');
        row.dataset.path = item.path;
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        const isExpanded = this.expanded.has(this.key(item.path));
        const toggle = document.createElement('span');
        toggle.className = 'toggle' + (isExpanded ? ' expanded' : '');
        toggle.textContent = isExpanded ? '−' : '+';
        const label = document.createElement('span');
        label.className = 'label';
        label.textContent = '📁 ' + item.name;
        row.appendChild(toggle);
        row.appendChild(label);
        const children = document.createElement('div');
        children.className = 'children' + (isExpanded ? '' : ' collapsed');
        row.onclick = () => {
          this.selectedPath = item.path;
          if (this.onFolderSelect) this.onFolderSelect(item.path);
          this.render();
          this.toggle(item.path);
        };
        container.appendChild(row);
        container.appendChild(children);
        this.renderItems(item.children || [], children);
      } else {
        row.textContent = this.getFileIcon(item.name) + ' ' + item.name;
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        row.onclick = () => {
          this.selectedPath = item.path;
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
    return this.load(this.scope);
  },

  renderDevLinks(containerId = 'devLinks') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    for (const link of DEV_LINKS) {
      const row = document.createElement('button');
      row.className = 'dev-link';
      row.type = 'button';
      row.textContent = link.icon + ' ' + link.name;
      row.title = link.path;
      row.onclick = () => {
        if (this.onDevLink) this.onDevLink(link);
      };
      container.appendChild(row);
    }
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

<!-- ==== 28/39 : parameters/__init__.py ==== -->

### parameters/__init__.py

```python
"""Project parameters package.

Holds the Project Manager filesystem owner (filesystem.py) that owns
the managed workspace, plus the project metadata it manages.
"""
```

---

<!-- ==== 29/39 : parameters/filesystem.py ==== -->

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


# ============================================================
# READ FILESYSTEM
# ============================================================

def read_filesystem(
    directory: Path | None = None,
    _root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Recursively read the project filesystem.

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
                    "editable": is_text_file(
                        child
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

<!-- ==== 30/39 : README.md ==== -->

### README.md

```markdown
# Project Manager

A lightweight FastAPI workspace server. Browse, edit, and chat about your
project from a single web dashboard with a Monaco-powered code editor.

## Layout

The repository is split into three pillars plus scripts:

```
├── server.py                Application entry point (FastAPI host)
├── requirements.txt
│
├── interface/               EDITOR INTERFACE
│   ├── static/              Web UI (home.html, chat.html, editor.html, js/)
│   ├── routers/             HTTP API routers (files, dirs, paths, ws, chat)
│   ├── core/                Controller layer (sessions, events, operations)
│   └── clients/             Python client (EditorClient / AsyncEditorClient)
│
├── parameters/              PROJECT PARAMETERS
│   └── filesystem.py        Filesystem owner for the managed workspace
│
├── workspace/               THE MANAGED PROJECT
│   ├── project.json
│   ├── documentation/  project_scope/  to_do/  updates/  config/  data/
│
└── scripts/                 run.bat / run.sh / setup.sh
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
- Chat popup (`/chat`) — stub that logs messages to `workspace/data/chat.log`
- Dev-scripts quick links to the important application files
- JSON REST API for filesystem operations (scope-aware)
- Python client for AI agents / other programs
- Works on Windows and (Chromebook) Linux

## Requirements

- Python 3.9+
- Network access for the code editor CDN (Monaco, loaded from cdnjs)

## Setup

### Windows

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
scripts\run.bat
```

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
| GET    | `/chat`                       | Chat popup UI                        |
| GET    | `/api/health`                 | Health + project info                |
| GET    | `/api/project?scope=`         | Project state + tree (ws/app)        |
| GET    | `/api/file/read?path=&scope=` | Read a file                          |
| PUT    | `/api/file/write`             | Write a file                         |
| POST   | `/api/file/create`            | Create a file                        |
| POST   | `/api/directory/create`       | Create a directory                   |
| PUT    | `/api/path/rename`            | Rename/move a path                   |
| DELETE | `/api/file/delete`            | Delete a file                        |
| DELETE | `/api/directory/delete`       | Delete a directory                   |
| POST   | `/api/chat`                   | Send a chat message (logged)         |
| GET    | `/api/chat`                   | Chat history                         |

Note: The `workspace/` content folders are empty so git does not track
them; the server recreates them automatically on startup.
```

---

<!-- ==== 31/39 : requirements.txt ==== -->

### requirements.txt

```text
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
websockets==13.1
```

---

<!-- ==== 32/39 : scripts/run.bat ==== -->

### scripts/run.bat

```batch
@echo off
rem Project Manager - start the server from the virtual environment.

cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run: python -m venv .venv
    echo Then: .venv\Scripts\python -m pip install -r requirements.txt
    exit /b 1
)

echo Starting Project Manager at http://127.0.0.1:8000
echo To stop: press Ctrl+C
echo.

.venv\Scripts\python server.py
```

---

<!-- ==== 33/39 : scripts/run.sh ==== -->

### scripts/run.sh

```bash
#!/usr/bin/env bash
#
# Project Manager - start the server from the virtual environment.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run ./setup.sh first." >&2
    exit 1
fi

echo "Starting Project Manager at http://127.0.0.1:8000"
echo "To stop: press Ctrl+C"
echo

.venv/bin/python server.py
```

---

<!-- ==== 34/39 : scripts/setup.sh ==== -->

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

<!-- ==== 35/39 : server.py ==== -->

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

<!-- ==== 36/39 : workspace/agent.md ==== -->

### workspace/agent.md

```markdown

```

---

<!-- ==== 37/39 : workspace/documentation/MASTER_COPY.md ==== -->

### workspace/documentation/MASTER_COPY.md

```markdown
# Project Manager — Master Copy

Single-file backup of the complete application source code and file structure.

- **Project:** Project Manager
- **Version:** 1.0.0
- **Workspace version:** 1.0
- **Repo:** https://github.com/TheChuey/project
- **Generated:** 2026-09-23

---

## File Structure

```text
project/
    ├── documentation
    │   ├── MASTER_COPY.md
    │   └── PLAN_editor_interface.md
    ├── editor
    │   ├── __init__.py
    │   ├── events.py
    │   ├── operations.py
    │   └── session.py
    ├── projectConfiguration
    │   ├── __init__.py
    │   ├── project.json
    │   └── Project_files.py
    ├── routers
    │   ├── __init__.py
    │   ├── directories.py
    │   ├── errors.py
    │   ├── files.py
    │   ├── paths.py
    │   └── project.py
    ├── run_at_first_use
    │   ├── run.bat
    │   ├── run.sh
    │   └── setup.sh
    ├── static
    │   ├── editor.html
    │   └── index.html
    ├── .gitattributes
    ├── .gitignore
    ├── editor_client.py
    ├── README.md
    ├── requirements.txt
    └── server.py
```

---

## File Contents

### README.md

````markdown
# Project Manager

A lightweight FastAPI workspace server. Browse and edit project files from a
web dashboard with a Monaco-powered code editor.

## Features

- Project tree browser (browse, open, create, rename, delete)
- In-browser code editor with syntax highlighting
- JSON REST API for filesystem operations
- Works on Windows and (Chromebook) Linux

## Requirements

- Python 3.9+
- Network access for the code editor CDN (Monaco, loaded from cdnjs)

## Setup

### Windows

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
run.bat
```

### Chromebook (ChromeOS with Linux/Crostini)

Open a Linux terminal and enable the Linux apps if you have not already:

```sh
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

Clone the repo, then:

```sh
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

| Method | Path                       | Description                |
| ------ | -------------------------- | -------------------------- |
| GET    | `/`                        | Dashboard UI               |
| GET    | `/editor`                  | Standalone editor UI       |
| GET    | `/api/health`              | Health + project info      |
| GET    | `/api/project`             | Project state + tree       |
| GET    | `/api/file/read?path=...`  | Read a file                |
| PUT    | `/api/file/write`          | Write a file               |
| POST   | `/api/file/create`         | Create a file              |
| POST   | `/api/directory/create`    | Create a directory         |
| PUT    | `/api/path/rename`         | Rename/move a path         |
| DELETE | `/api/file/delete?path=...`| Delete a file              |
| DELETE | `/api/directory/delete?path=...` | Delete a directory         |

Note: The `data/`, `config/`, `documentation/`, etc. folders are empty so git
does not track them; the server recreates them automatically on startup.
````
---

### requirements.txt

`text
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
websockets==13.1

`
---

### server.py

`python
"""
Project Manager Server
======================

Lightweight FastAPI server for the Project Manager workspace.

Responsibilities:
    - Start the project.
    - Initialize the filesystem.
    - Serve the browser interface.
    - Provide project information.
    - Provide filesystem information.
    - Read files.
    - Write files.
    - Create files.
    - Create directories.
    - Rename files/directories.
    - Delete files/directories.

Filesystem operations are handled by project_files.py.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import Project_files


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

STATIC_DIR = PROJECT_ROOT / "static"

INDEX_HTML = STATIC_DIR / "index.html"

EDITOR_HTML = STATIC_DIR / "editor.html"


# ============================================================
# FASTAPI APPLICATION
# ============================================================

@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    Build the basic project filesystem when
    the server starts.
    """

    Project_files.build_project_filesystem()

    yield


app = FastAPI(
    title="Project Manager Server",
    description="Lightweight Project Manager workspace server.",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# REQUEST MODELS
# ============================================================

class FileWriteRequest(BaseModel):

    path: str

    content: str


class FileCreateRequest(BaseModel):

    path: str

    content: str = ""


class RenameRequest(BaseModel):

    old_path: str

    new_path: str


# ============================================================
# ERROR HELPER
# ============================================================

def filesystem_error(
    error: Exception,
) -> HTTPException:
    """
    Convert filesystem exceptions into HTTP errors.
    """

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

    return HTTPException(
        status_code=500,
        detail=str(error),
    )


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    """
    Display the main project interface.
    """

    if not INDEX_HTML.exists():

        raise HTTPException(
            status_code=404,
            detail="static/index.html was not found.",
        )

    return FileResponse(
        INDEX_HTML
    )


# ============================================================
# EDITOR
# ============================================================

@app.get("/editor")
def editor():
    """
    Display the standalone editor.
    """

    if not EDITOR_HTML.exists():

        raise HTTPException(
            status_code=404,
            detail="static/editor.html was not found.",
        )

    return FileResponse(
        EDITOR_HTML
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():
    """
    Check server health.
    """

    return {
        "status": "healthy",
        "project": Project_files.read_project_info(),
    }


# ============================================================
# PROJECT STATE
# ============================================================

@app.get("/api/project")
def get_project():
    """
    Return project information and filesystem tree.
    """

    return Project_files.get_project_state()


# ============================================================
# READ FILE
# ============================================================

@app.get("/api/file/read")
def read_file(path: str):
    """
    Read a project text file.
    """

    try:

        content = Project_files.read_file(
            path
        )

        return {
            "path": path,
            "content": content,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# WRITE FILE
# ============================================================

@app.put("/api/file/write")
def write_file(
    request: FileWriteRequest,
):
    """
    Create or overwrite a project text file.
    """

    try:

        Project_files.write_file(
            request.path,
            request.content,
        )

        return {
            "status": "saved",
            "path": request.path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# CREATE FILE
# ============================================================

@app.post("/api/file/create")
def create_file(
    request: FileCreateRequest,
):
    """
    Create a new project file.
    """

    try:

        Project_files.create_file(
            request.path,
            request.content,
        )

        return {
            "status": "created",
            "path": request.path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# CREATE DIRECTORY
# ============================================================

@app.post("/api/directory/create")
def create_directory(
    path: str,
):
    """
    Create a project directory.
    """

    try:

        Project_files.create_directory(
            path
        )

        return {
            "status": "created",
            "path": path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# RENAME
# ============================================================

@app.put("/api/path/rename")
def rename_path(
    request: RenameRequest,
):
    """
    Rename or move a project file/directory.
    """

    try:

        Project_files.rename_path(
            request.old_path,
            request.new_path,
        )

        return {
            "status": "renamed",
            "old_path": request.old_path,
            "new_path": request.new_path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# DELETE FILE
# ============================================================

@app.delete("/api/file/delete")
def delete_file(
    path: str,
):
    """
    Delete a project file.
    """

    try:

        target = Project_files.resolve_project_path(
            path
        )

        if not target.exists():

            raise FileNotFoundError(
                "File not found."
            )

        if not target.is_file():

            raise ValueError(
                "Path is not a file."
            )

        Project_files.delete_path(
            path
        )

        return {
            "status": "deleted",
            "path": path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# DELETE DIRECTORY
# ============================================================

@app.delete("/api/directory/delete")
def delete_directory(
    path: str,
):
    """
    Delete a project directory.
    """

    try:

        target = Project_files.resolve_project_path(
            path
        )

        if not target.exists():

            raise FileNotFoundError(
                "Directory not found."
            )

        if not target.is_dir():

            raise ValueError(
                "Path is not a directory."
            )

        Project_files.delete_path(
            path
        )

        return {
            "status": "deleted",
            "path": path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


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

`
---

### projectConfiguration/project.json

`json
{
    "name": "Project Manager",
    "version": "1.0.0",
    "workspace_version": "1.0"
}
`
---

### projectConfiguration/Project_files.py

`python
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

PROJECT_CONFIG_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = PROJECT_CONFIG_DIR.parent

PROJECT_JSON = PROJECT_CONFIG_DIR / "project.json"


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

def resolve_project_path(relative_path: str) -> Path:
    """
    Convert a project-relative path into a safe absolute path.

    This prevents paths such as:

        ../../some_file.txt

    from escaping the project directory.

    Args:
        relative_path:
            Path relative to the project root.

    Returns:
        Safe absolute Path.

    Raises:
        ValueError:
            If the path is empty or outside the project.
    """

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
        PROJECT_ROOT / relative_path
    ).resolve()

    try:

        candidate.relative_to(
            PROJECT_ROOT
        )

    except ValueError:

        raise ValueError(
            "Access outside the project directory "
            "is not allowed."
        )

    return candidate


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


# ============================================================
# READ FILESYSTEM
# ============================================================

def read_filesystem(
    directory: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Recursively read the project filesystem.

    Returns:
        JSON-friendly file/folder tree.
    """

    if directory is None:

        directory = PROJECT_ROOT

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
            PROJECT_ROOT
        )

        relative_path = str(
            relative_path
        ).replace(
            "\\",
            "/",
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
                        child
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
                    "editable": is_text_file(
                        child
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
) -> str:
    """
    Read a text file.

    Args:
        relative_path:
            Project-relative file path.

    Returns:
        File contents.

    Raises:
        ValueError:
            Invalid path or file type.
        FileNotFoundError:
            File does not exist.
    """

    file_path = resolve_project_path(
        relative_path
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
) -> None:
    """
    Create or overwrite a text file.

    Parent directories are automatically created.
    """

    file_path = resolve_project_path(
        relative_path
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
) -> None:
    """
    Create a new file.

    Refuses to overwrite an existing file.
    """

    file_path = resolve_project_path(
        relative_path
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
) -> None:
    """
    Create a directory.
    """

    directory = resolve_project_path(
        relative_path
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
) -> None:
    """
    Rename or move a file/directory within the project.

    Both paths must remain inside PROJECT_ROOT.
    """

    source = resolve_project_path(
        old_path
    )

    destination = resolve_project_path(
        new_path
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
) -> None:
    """
    Delete a file or directory.

    Directories are deleted recursively.

    The project root itself cannot be deleted.
    """

    target = resolve_project_path(
        relative_path
    )

    if target == PROJECT_ROOT:

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

`
---

### run_at_first_use/setup.sh

`bash
#!/usr/bin/env bash
#
# Project Manager - one-time setup for (Chromebook) Linux.
# Creates a virtual environment and installs dependencies.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
`
---

### run_at_first_use/run.sh

`bash
#!/usr/bin/env bash
#
# Project Manager - start the server from the virtual environment.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run ./setup.sh first." >&2
    exit 1
fi

echo "Starting Project Manager at http://127.0.0.1:8000"
echo "To stop: press Ctrl+C"
echo

.venv/bin/python server.py
`
---

### run_at_first_use/run.bat

`dosbatch
@echo off
rem Project Manager - start the server from the virtual environment.

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run: python -m venv .venv
    echo Then: .venv\Scripts\python -m pip install -r requirements.txt
    exit /b 1
)

echo Starting Project Manager at http://127.0.0.1:8000
echo To stop: press Ctrl+C
echo.

.venv\Scripts\python server.py
`
---

### static/index.html

`html
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

        .tree-item:hover {
            background: #2a2d2e;
        }

        .children {
            margin-left: 16px;
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

<script>
/* ============================================================
   NAVIGATION & EDITOR LAUNCHERS
   ============================================================ */

// Opens editor in the current window
function openEditor(filePath) {
    let url = "/editor";
    if (filePath) {
        url += "?path=" + encodeURIComponent(filePath);
    }
    window.location.href = url;
}

// Opens editor in a floating popup window
function openEditorPopup(filePath) {
    let url = "/editor";
    if (filePath) {
        url += "?path=" + encodeURIComponent(filePath);
    }

    const width = 1200;
    const height = 800;
    const left = (window.screen.width - width) / 2;
    const top = (window.screen.height - height) / 2;

    window.open(
        url,
        "ProjectManagerEditorPopup",
        `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no`
    );
}

/* ============================================================
   PROJECT TREE & API CALLS
   ============================================================ */

async function loadProject() {
    setStatus("Loading project...");
    try {
        const response = await fetch("/api/project");
        if (!response.ok) throw new Error("Could not load project");

        const data = await response.json();
        renderTree(data.filesystem || []);
        setStatus("Project loaded");
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

function renderTree(items) {
    const container = document.getElementById("projectTree");
    container.innerHTML = "";
    renderItems(items, container);
}

function renderItems(items, container) {
    items.forEach(item => {
        const div = document.createElement("div");
        div.className = "tree-item";
        
        const label = document.createElement("span");
        label.textContent = (item.type === "directory" ? "📁 " : "📄 ") + item.name;
        div.appendChild(label);

        if (item.type === "file") {
            const btnGroup = document.createElement("div");
            
            const editBtn = document.createElement("button");
            editBtn.textContent = "Edit";
            editBtn.onclick = (e) => {
                e.stopPropagation();
                openEditor(item.path);
            };

            const popupBtn = document.createElement("button");
            popupBtn.textContent = "Popup";
            popupBtn.style.marginLeft = "4px";
            popupBtn.onclick = (e) => {
                e.stopPropagation();
                openEditorPopup(item.path);
            };

            btnGroup.appendChild(editBtn);
            btnGroup.appendChild(popupBtn);
            div.appendChild(btnGroup);
        }

        container.appendChild(div);

        if (item.type === "directory" && item.children) {
            const childrenContainer = document.createElement("div");
            childrenContainer.className = "children";
            container.appendChild(childrenContainer);
            renderItems(item.children, childrenContainer);
        }
    });
}

async function submitCreateFilePrompt() {
    const path = prompt("Enter file path/name:");
    if (!path) return;

    try {
        const res = await fetch("/api/file/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: path, content: "" })
        });
        if (!res.ok) throw new Error("Failed to create file");
        await loadProject();
        openEditor(path);
    } catch (err) {
        alert(err.message);
    }
}

async function submitCreateFolderPrompt() {
    const path = prompt("Enter folder path:");
    if (!path) return;

    try {
        const res = await fetch("/api/directory/create?path=" + encodeURIComponent(path), {
            method: "POST"
        });
        if (!res.ok) throw new Error("Failed to create folder");
        await loadProject();
    } catch (err) {
        alert(err.message);
    }
}

function refreshProject() {
    loadProject();
}

function setStatus(msg) {
    document.getElementById("statusMessage").textContent = msg;
}

// Initial Load
loadProject();
</script>

</body>
</html>
`
---

### static/editor.html

`html
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
            height: calc(100vh - 74px);
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

        .children {
            margin-left: 12px;
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
    </style>

    <!-- Monaco Loader CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js"></script>
</head>
<body>

<div class="topbar">
    <div class="title">Project Manager Editor</div>
    <button onclick="goHome()">🏠 Home</button>
    <button class="primary" onclick="saveFile()">Save</button>
    <button onclick="newFile()">+ File</button>
    <button onclick="newFolder()">+ Folder</button>
    <button onclick="renameSelected()">Rename</button>
    <button class="danger" onclick="deleteSelected()">Delete</button>
    <button onclick="refreshTree()">Refresh</button>
</div>

<div class="workspace">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span>PROJECT FILES</span>
        </div>
        <div id="tree" class="tree">Loading...</div>
    </div>
    
    <div class="resize-handle" id="resizeHandle"></div>

    <div class="editor-area">
        <div class="filebar">
            <div>
                <span id="currentFile">No file selected</span>
                <span id="unsavedIndicator"></span>
            </div>
            <div id="language">plaintext</div>
        </div>
        <div id="editor"></div>
    </div>
</div>

<div class="statusbar">
    <div id="statusMessage" class="status-message">Initializing...</div>
</div>

<script>
/* ============================================================
   GLOBAL STATE
   ============================================================ */

let editor = null;
let currentFile = null;
let currentLanguage = "plaintext";
let isDirty = false;
let projectTree = [];

/* ============================================================
   NAVIGATION
   ============================================================ */

function goHome() {
    if (isDirty) {
        const proceed = confirm("You have unsaved changes. Return to home?");
        if (!proceed) return;
    }
    window.location.href = "/";
}

/* ============================================================
   LANGUAGE DETECTION MAP
   ============================================================ */

function getLanguage(filePath) {
    if (!filePath) return "plaintext";
    const ext = filePath.split(".").pop().toLowerCase();
    const map = {
        py: "python",
        js: "javascript",
        jsx: "javascript",
        ts: "typescript",
        tsx: "typescript",
        html: "html",
        htm: "html",
        css: "css",
        json: "json",
        md: "markdown",
        yaml: "yaml",
        yml: "yaml",
        sql: "sql",
        xml: "xml",
        sh: "shell",
        env: "shell",
        txt: "plaintext"
    };
    return map[ext] || "plaintext";
}

/* ============================================================
   MONACO INITIALIZATION
   ============================================================ */

if (typeof require !== 'undefined') {
    require.config({
        paths: {
            vs: "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs"
        }
    });

    require(["vs/editor/editor.main"], function () {
        editor = monaco.editor.create(document.getElementById("editor"), {
            value: "// Select a file from the sidebar to start editing\n",
            language: "plaintext",
            theme: "vs-dark",
            automaticLayout: true,
            minimap: { enabled: true },
            wordWrap: "on",
            fontSize: 14,
            
            // Indentation & Auto-formatting controls
            tabSize: 4,
            insertSpaces: true,
            autoIndent: "full",
            formatOnType: true,
            formatOnPaste: true
        });

        editor.onDidChangeModelContent(function () {
            if (!currentFile) return;
            isDirty = true;
            updateDirtyIndicator();
        });

        setStatus("Ready");

        loadProject().then(() => {
            const urlParams = new URLSearchParams(window.location.search);
            const initialPath = urlParams.get("path");
            if (initialPath) {
                openFile(initialPath);
            }
        });
    });
} else {
    setStatus("Error: Could not load Monaco CDN loader script.");
}

/* ============================================================
   PROJECT TREE & FILESYSTEM OPERATIONS
   ============================================================ */

async function loadProject() {
    setStatus("Loading project...");
    try {
        const response = await fetch("/api/project");
        if (!response.ok) throw new Error("Could not load project.");

        const data = await response.json();
        projectTree = data.filesystem || [];
        renderTree();
        setStatus("Project loaded.");
    } catch (error) {
        setStatus("Error: " + error.message);
    }
}

function renderTree() {
    const tree = document.getElementById("tree");
    tree.innerHTML = "";
    renderItems(projectTree, tree);
}

function renderItems(items, container) {
    for (const item of items) {
        const row = document.createElement("div");
        row.className = "tree-item";

        if (item.type === "directory") {
            row.classList.add("folder");
            row.textContent = "📁 " + item.name;
            container.appendChild(row);

            const children = document.createElement("div");
            children.className = "children";
            container.appendChild(children);

            renderItems(item.children || [], children);
        } else {
            row.textContent = "📄 " + item.name;
            if (currentFile === item.path) {
                row.classList.add("selected");
            }

            row.onclick = function () {
                openFile(item.path);
            };

            container.appendChild(row);
        }
    }
}

async function openFile(filePath) {
    if (isDirty) {
        const proceed = confirm("You have unsaved changes. Open another file?");
        if (!proceed) return;
    }

    setStatus("Opening " + filePath + "...");

    try {
        const response = await fetch("/api/file/read?path=" + encodeURIComponent(filePath));
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not read file.");
        }

        const data = await response.json();
        currentFile = filePath;
        currentLanguage = getLanguage(filePath);

        if (editor) {
            editor.setValue(data.content);
            monaco.editor.setModelLanguage(editor.getModel(), currentLanguage);
        }

        isDirty = false;
        updateFileDisplay();
        renderTree();
        setStatus("Opened " + filePath);
    } catch (error) {
        setStatus("Error: " + error.message);
        alert(error.message);
    }
}

async function saveFile() {
    if (!currentFile || !editor) {
        alert("No file is currently open.");
        return;
    }

    setStatus("Saving...");

    try {
        const response = await fetch("/api/file/write", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                path: currentFile,
                content: editor.getValue()
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not save file.");
        }

        isDirty = false;
        updateDirtyIndicator();
        setStatus("Saved " + currentFile);
        await refreshTree();
    } catch (error) {
        setStatus("Save error: " + error.message);
        alert(error.message);
    }
}

async function newFile() {
    const fileName = prompt("Enter new file path/name:");
    if (!fileName) return;

    try {
        const response = await fetch("/api/file/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                path: fileName,
                content: ""
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not create file.");
        }

        await refreshTree();
        await openFile(fileName);
        setStatus("Created " + fileName);
    } catch (error) {
        alert(error.message);
    }
}

async function newFolder() {
    const folderPath = prompt("Enter new folder path:");
    if (!folderPath) return;

    try {
        const response = await fetch("/api/directory/create?path=" + encodeURIComponent(folderPath), {
            method: "POST"
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not create folder.");
        }

        await refreshTree();
        setStatus("Created folder " + folderPath);
    } catch (error) {
        alert(error.message);
    }
}

async function renameSelected() {
    if (!currentFile) {
        alert("Select a file first.");
        return;
    }

    const newName = prompt("Enter the new file path:", currentFile);
    if (!newName || newName === currentFile) return;

    try {
        const response = await fetch("/api/path/rename", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                old_path: currentFile,
                new_path: newName
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not rename file.");
        }

        currentFile = newName;
        await refreshTree();
        await openFile(newName);
    } catch (error) {
        alert(error.message);
    }
}

async function deleteSelected() {
    if (!currentFile) {
        alert("Select a file first.");
        return;
    }

    const confirmed = confirm("Delete " + currentFile + "?");
    if (!confirmed) return;

    try {
        const response = await fetch("/api/file/delete?path=" + encodeURIComponent(currentFile), {
            method: "DELETE"
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not delete file.");
        }

        currentFile = null;
        editor.setValue("");
        isDirty = false;
        updateFileDisplay();
        await refreshTree();
        setStatus("File deleted.");
    } catch (error) {
        alert(error.message);
    }
}

async function refreshTree() {
    await loadProject();
}

/* ============================================================
   UI UPDATES & UTILITIES
   ============================================================ */

function updateFileDisplay() {
    document.getElementById("currentFile").textContent = currentFile ? currentFile : "No file selected";
    document.getElementById("language").textContent = currentLanguage;
    updateDirtyIndicator();
}

function updateDirtyIndicator() {
    document.getElementById("unsavedIndicator").textContent = isDirty ? "● UNSAVED" : "";
}

function setStatus(message) {
    document.getElementById("statusMessage").textContent = message;
}

/* ============================================================
   KEYBOARD SHORTCUTS & SIDEBAR RESIZE
   ============================================================ */

document.addEventListener("keydown", function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        saveFile();
    }
});

const sidebar = document.getElementById("sidebar");
const resizeHandle = document.getElementById("resizeHandle");
let resizing = false;

resizeHandle.addEventListener("mousedown", function () {
    resizing = true;
    document.body.style.cursor = "col-resize";
});

document.addEventListener("mousemove", function (event) {
    if (!resizing) return;
    const width = event.clientX;
    if (width >= 180 && width <= 500) {
        sidebar.style.width = width + "px";
        if (editor) editor.layout();
    }
});

document.addEventListener("mouseup", function () {
    resizing = false;
    document.body.style.cursor = "";
});

window.addEventListener("beforeunload", function (event) {
    if (!isDirty) return;
    event.preventDefault();
    event.returnValue = "";
});
</script>

</body>
</html>
`
---

### gitattributes

`git-attrs
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
`
---

### gitignore

`gitignore
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
`
---

*End of master copy.*
```

---

<!-- ==== 38/39 : workspace/documentation/PLAN_editor_interface.md ==== -->

### workspace/documentation/PLAN_editor_interface.md

```markdown
# Plan: Project Manager Interface

Python module + organized server CRUD + modular UI.

## Goal

Keep the application as a **Project Manager** while adding a proper interface that allows AI agents and other Python programs to communicate with the Project Manager.

The Project Manager remains responsible for:

- project files
- directories
- file editing
- project configuration
- filesystem safety
- project initialization
- web UI

The new interface becomes another way to interact with those existing Project Manager capabilities.

The interface must **not bypass `Project_files.py`**.

## Architecture

```text
                         PROJECT MANAGER
                               │
              ┌────────────────┴────────────────┐
              │                                 │
        Web Interface                    Python Interface
              │                                 │
        Browser / Monaco                 AI Agents / Scripts
              │                                 │
              └────────────────┬────────────────┘
                               │
                        Project Manager
                        operation layer
                               │
                        Project_files.py
                               │
                        Project filesystem
```

The important principle is:

> There is one Project Manager and multiple interfaces to it.

## Target Structure

```text
project/
├── documentation/
│   └── MASTER_COPY.md
│
├── editor/
│   ├── __init__.py
│   ├── events.py
│   ├── session.py
│   └── operations.py
│
├── routers/
│   ├── __init__.py
│   ├── project.py
│   ├── files.py
│   ├── directories.py
│   ├── paths.py
│   └── ws.py
│
├── projectConfiguration/
│   ├── __init__.py
│   ├── Project_files.py
│   └── project.json
│
├── static/
│   ├── index.html
│   ├── editor.html
│   └── js/
│       ├── api.js
│       ├── session.js
│       ├── tree.js
│       ├── editor.js
│       └── main.js
│
├── editor_client.py
├── server.py
├── requirements.txt
└── ...
```

## Components

### 1. `editor/` — Project Manager operation/interface layer

This is the internal layer between the HTTP API and the filesystem.

It is **not a replacement for the Project Manager**.

It provides a clean set of operations that multiple interfaces can use.

#### `operations.py`

Create a controller such as `EditorInterface`.

It provides operations such as:

```text
open()
save()
create_file()
create_directory()
rename()
delete()
tree()
sessions()
```

Every filesystem mutation eventually goes through `Project_files.py`.

The controller should not implement its own filesystem logic.

Conceptually:

```text
Router
   ↓
Project Manager Interface
   ↓
Project_files
   ↓
Filesystem
```

### 2. `events.py` — Project Manager event system

Create a small event bus for changes occurring inside the Project Manager.

Example events:

```text
saved
created
renamed
deleted
tree_changed
```

Example:

```json
{
    "type": "saved",
    "path": "app.py"
}
```

The event system allows the browser and future agents to receive information about changes without directly monitoring the filesystem.

### 3. `session.py` — Interface sessions

Create:

```text
EditorSession
EditorManager
```

`EditorSession` tracks a connected interface client.

Possible state:

```text
client_id
open_file
dirty
last_modified
```

`EditorManager` maintains the active in-memory sessions.

It should also provide:

```text
register()
unregister()
update()
snapshot()
```

This is initially an in-memory system. Do not introduce a database for sessions.

### 4. `routers/` — Project Manager HTTP API

Split the existing API into resource-oriented routers.

#### `project.py`

```text
GET /api/project
GET /api/health
GET /api/sessions
```

#### `files.py`

```text
GET    /api/file/read
PUT    /api/file/write
POST   /api/file/create
DELETE /api/file/delete
```

#### `directories.py`

```text
POST   /api/directory/create
DELETE /api/directory/delete
```

#### `paths.py`

```text
PUT /api/path/rename
```

#### `ws.py`

```text
WS /api/ws
```

The existing REST paths and contracts remain unchanged.

### 5. WebSocket Interface

Add:

```text
/api/ws
```

The WebSocket provides real-time Project Manager events.

On connection:

```text
register session
```

Client messages may include:

```text
open
dirty
tree
```

Server events may include:

```text
saved
created
renamed
deleted
tree_changed
```

Example:

```json
{
    "type": "created",
    "path": "config/settings.json"
}
```

The browser can then update itself without requiring a complete page reload.

### 6. `editor_client.py` — Python Project Manager Interface

Create a Python client that allows another Python program or AI agent to communicate with the running Project Manager.

```python
from editor_client import EditorClient

client = EditorClient("http://127.0.0.1:8000")

client.tree()

client.open("app.py")

client.save(
    "app.py",
    "print('Hello World')"
)
```

Supported operations:

```text
open()
save()
create_file()
create_directory()
rename()
delete()
tree()
health()
sessions()
```

The client communicates with the Project Manager API. It must **not directly access the Project Manager filesystem**. This is important because the Project Manager remains the authority over filesystem operations.

### 7. Async Client

Provide an asynchronous client for AI-agent workflows:

```text
AsyncEditorClient
```

with asynchronous versions of the Project Manager operations.

Also provide:

```text
subscribe()
```

for receiving Project Manager events through WebSockets. This allows future agents to react to changes.

Example concept:

```text
AI Agent
   │
   ├── save file
   │
   ▼
Project Manager
   │
   ├── filesystem change
   │
   └── event
          │
          ▼
       Agent
```

### 8. Frontend Organization

The Project Manager UI remains visually and functionally the same. The JavaScript is reorganized into vanilla ES modules.

```text
static/js/
├── api.js
├── session.js
├── tree.js
├── editor.js
└── main.js
```

#### `api.js`

Central location for API requests. Responsible for:

```text
health
project
file operations
directory operations
rename
delete
sessions
```

#### `tree.js`

Responsible for:

- rendering the project tree
- selecting files
- refreshing the tree
- responding to tree-change events

#### `editor.js`

Responsible for Monaco. Move the existing Monaco initialization and behavior here with the goal of preserving it verbatim where practical. Keep:

- Monaco configuration
- editor initialization
- syntax highlighting
- save behavior
- Ctrl+S
- dirty state
- theme
- sidebar behavior

#### `session.js`

Responsible for:

- WebSocket connection
- connection state
- sending session events
- receiving Project Manager events
- applying live changes

#### `main.js`

Responsible for application startup and wiring the modules together.

### 9. `server.py`

After the reorganization, `server.py` becomes the application entry point:

```text
create FastAPI application
        ↓
configure lifespan
        ↓
register routers
        ↓
serve static files
        ↓
start server
```

It should not become the location for Project Manager business logic.

## Requirements

Add:

```text
httpx
websockets
```

to `requirements.txt`. Keep the existing FastAPI and Uvicorn dependencies.

## What Does NOT Change

The following remain Project Manager responsibilities:

```text
Project_files.py
project.json
project initialization
filesystem safety
dashboard
Monaco editor
existing REST endpoints
project structure
Windows support
Linux/ChromeOS support
```

The interface adds capability; it does not replace these systems.

## Interface Principle

The interface must provide agents with a controlled Project Manager API. An agent should think in terms of:

```text
open project file
read project file
save project file
create project file
create directory
rename path
delete path
inspect project tree
```

rather than:

```text
open arbitrary filesystem path
write arbitrary filesystem path
delete arbitrary filesystem path
```

The Project Manager remains the authority.

## Verification

### 1. Application startup

```text
python server.py
```

Verify the server starts successfully.

### 2. Existing API

Verify all existing contracts continue working:

```text
/api/health
/api/project
/api/file/read
/api/file/write
/api/file/create
/api/file/delete
/api/directory/create
/api/directory/delete
/api/path/rename
```

### 3. Browser

Verify:

- dashboard loads
- project tree loads
- files open
- Monaco works
- editing works
- Ctrl+S works
- file creation works
- rename works
- deletion works

The UI should remain visually/functionally equivalent.

### 4. Real-Time Events

Open the Project Manager in a browser, then modify the project through another client. Verify the browser receives the appropriate event.

Examples:

```text
create → created
save → saved
rename → renamed
delete → deleted
```

### 5. Python Client

Run a test script:

```text
health
tree
create
open
save
rename
delete
```

Verify each operation goes through the Project Manager.

### 6. Filesystem Authority

Confirm that `editor_client.py`, `routers/`, `editor/` do not bypass `Project_files.py` for Project Manager filesystem operations.

## Final Architecture

```text
                    ┌─────────────────────┐
                    │   Project Manager   │
                    │       Server        │
                    └──────────┬──────────┘
                               │
                    Project Manager Core
                               │
                    ┌──────────▼──────────┐
                    │    Project_files    │
                    │  Filesystem Owner   │
                    └──────────┬──────────┘
                               │
                         Project Root
                               ▲
                               │
              ┌────────────────┴────────────────┐
              │                                 │
       Browser Interface                 Python Interface
              │                                 │
       Monaco / Dashboard                 editor_client.py
              │                                 │
              │                           AI Agents
              │                           Python Scripts
              │                                 │
              └──────────────┬──────────────────┘
                             │
                       Project Manager
                         HTTP / WS API
```

The central idea is:

> **Project Manager first. Interface second.**
```

---

<!-- ==== 39/39 : workspace/project.json ==== -->

### workspace/project.json

```json
{
    "name": "Project Manager",
    "version": "1.0.0",
    "workspace_version": "1.0"
}
```

---

> Generated by `scripts/gen_master_copy.py` on 2026-09-23. Do not edit by hand; regenerate with:
>
> `.venv/Scripts/python -m scripts.gen_master_copy`
```

---

<!-- ==== 38/39 : workspace/documentation/PLAN_editor_interface.md ==== -->

### workspace/documentation/PLAN_editor_interface.md

```markdown
# Plan: Project Manager Interface

Python module + organized server CRUD + modular UI.

## Goal

Keep the application as a **Project Manager** while adding a proper interface that allows AI agents and other Python programs to communicate with the Project Manager.

The Project Manager remains responsible for:

- project files
- directories
- file editing
- project configuration
- filesystem safety
- project initialization
- web UI

The new interface becomes another way to interact with those existing Project Manager capabilities.

The interface must **not bypass `Project_files.py`**.

## Architecture

```text
                         PROJECT MANAGER
                               │
              ┌────────────────┴────────────────┐
              │                                 │
        Web Interface                    Python Interface
              │                                 │
        Browser / Monaco                 AI Agents / Scripts
              │                                 │
              └────────────────┬────────────────┘
                               │
                        Project Manager
                        operation layer
                               │
                        Project_files.py
                               │
                        Project filesystem
```

The important principle is:

> There is one Project Manager and multiple interfaces to it.

## Target Structure

```text
project/
├── documentation/
│   └── MASTER_COPY.md
│
├── editor/
│   ├── __init__.py
│   ├── events.py
│   ├── session.py
│   └── operations.py
│
├── routers/
│   ├── __init__.py
│   ├── project.py
│   ├── files.py
│   ├── directories.py
│   ├── paths.py
│   └── ws.py
│
├── projectConfiguration/
│   ├── __init__.py
│   ├── Project_files.py
│   └── project.json
│
├── static/
│   ├── index.html
│   ├── editor.html
│   └── js/
│       ├── api.js
│       ├── session.js
│       ├── tree.js
│       ├── editor.js
│       └── main.js
│
├── editor_client.py
├── server.py
├── requirements.txt
└── ...
```

## Components

### 1. `editor/` — Project Manager operation/interface layer

This is the internal layer between the HTTP API and the filesystem.

It is **not a replacement for the Project Manager**.

It provides a clean set of operations that multiple interfaces can use.

#### `operations.py`

Create a controller such as `EditorInterface`.

It provides operations such as:

```text
open()
save()
create_file()
create_directory()
rename()
delete()
tree()
sessions()
```

Every filesystem mutation eventually goes through `Project_files.py`.

The controller should not implement its own filesystem logic.

Conceptually:

```text
Router
   ↓
Project Manager Interface
   ↓
Project_files
   ↓
Filesystem
```

### 2. `events.py` — Project Manager event system

Create a small event bus for changes occurring inside the Project Manager.

Example events:

```text
saved
created
renamed
deleted
tree_changed
```

Example:

```json
{
    "type": "saved",
    "path": "app.py"
}
```

The event system allows the browser and future agents to receive information about changes without directly monitoring the filesystem.

### 3. `session.py` — Interface sessions

Create:

```text
EditorSession
EditorManager
```

`EditorSession` tracks a connected interface client.

Possible state:

```text
client_id
open_file
dirty
last_modified
```

`EditorManager` maintains the active in-memory sessions.

It should also provide:

```text
register()
unregister()
update()
snapshot()
```

This is initially an in-memory system. Do not introduce a database for sessions.

### 4. `routers/` — Project Manager HTTP API

Split the existing API into resource-oriented routers.

#### `project.py`

```text
GET /api/project
GET /api/health
GET /api/sessions
```

#### `files.py`

```text
GET    /api/file/read
PUT    /api/file/write
POST   /api/file/create
DELETE /api/file/delete
```

#### `directories.py`

```text
POST   /api/directory/create
DELETE /api/directory/delete
```

#### `paths.py`

```text
PUT /api/path/rename
```

#### `ws.py`

```text
WS /api/ws
```

The existing REST paths and contracts remain unchanged.

### 5. WebSocket Interface

Add:

```text
/api/ws
```

The WebSocket provides real-time Project Manager events.

On connection:

```text
register session
```

Client messages may include:

```text
open
dirty
tree
```

Server events may include:

```text
saved
created
renamed
deleted
tree_changed
```

Example:

```json
{
    "type": "created",
    "path": "config/settings.json"
}
```

The browser can then update itself without requiring a complete page reload.

### 6. `editor_client.py` — Python Project Manager Interface

Create a Python client that allows another Python program or AI agent to communicate with the running Project Manager.

```python
from editor_client import EditorClient

client = EditorClient("http://127.0.0.1:8000")

client.tree()

client.open("app.py")

client.save(
    "app.py",
    "print('Hello World')"
)
```

Supported operations:

```text
open()
save()
create_file()
create_directory()
rename()
delete()
tree()
health()
sessions()
```

The client communicates with the Project Manager API. It must **not directly access the Project Manager filesystem**. This is important because the Project Manager remains the authority over filesystem operations.

### 7. Async Client

Provide an asynchronous client for AI-agent workflows:

```text
AsyncEditorClient
```

with asynchronous versions of the Project Manager operations.

Also provide:

```text
subscribe()
```

for receiving Project Manager events through WebSockets. This allows future agents to react to changes.

Example concept:

```text
AI Agent
   │
   ├── save file
   │
   ▼
Project Manager
   │
   ├── filesystem change
   │
   └── event
          │
          ▼
       Agent
```

### 8. Frontend Organization

The Project Manager UI remains visually and functionally the same. The JavaScript is reorganized into vanilla ES modules.

```text
static/js/
├── api.js
├── session.js
├── tree.js
├── editor.js
└── main.js
```

#### `api.js`

Central location for API requests. Responsible for:

```text
health
project
file operations
directory operations
rename
delete
sessions
```

#### `tree.js`

Responsible for:

- rendering the project tree
- selecting files
- refreshing the tree
- responding to tree-change events

#### `editor.js`

Responsible for Monaco. Move the existing Monaco initialization and behavior here with the goal of preserving it verbatim where practical. Keep:

- Monaco configuration
- editor initialization
- syntax highlighting
- save behavior
- Ctrl+S
- dirty state
- theme
- sidebar behavior

#### `session.js`

Responsible for:

- WebSocket connection
- connection state
- sending session events
- receiving Project Manager events
- applying live changes

#### `main.js`

Responsible for application startup and wiring the modules together.

### 9. `server.py`

After the reorganization, `server.py` becomes the application entry point:

```text
create FastAPI application
        ↓
configure lifespan
        ↓
register routers
        ↓
serve static files
        ↓
start server
```

It should not become the location for Project Manager business logic.

## Requirements

Add:

```text
httpx
websockets
```

to `requirements.txt`. Keep the existing FastAPI and Uvicorn dependencies.

## What Does NOT Change

The following remain Project Manager responsibilities:

```text
Project_files.py
project.json
project initialization
filesystem safety
dashboard
Monaco editor
existing REST endpoints
project structure
Windows support
Linux/ChromeOS support
```

The interface adds capability; it does not replace these systems.

## Interface Principle

The interface must provide agents with a controlled Project Manager API. An agent should think in terms of:

```text
open project file
read project file
save project file
create project file
create directory
rename path
delete path
inspect project tree
```

rather than:

```text
open arbitrary filesystem path
write arbitrary filesystem path
delete arbitrary filesystem path
```

The Project Manager remains the authority.

## Verification

### 1. Application startup

```text
python server.py
```

Verify the server starts successfully.

### 2. Existing API

Verify all existing contracts continue working:

```text
/api/health
/api/project
/api/file/read
/api/file/write
/api/file/create
/api/file/delete
/api/directory/create
/api/directory/delete
/api/path/rename
```

### 3. Browser

Verify:

- dashboard loads
- project tree loads
- files open
- Monaco works
- editing works
- Ctrl+S works
- file creation works
- rename works
- deletion works

The UI should remain visually/functionally equivalent.

### 4. Real-Time Events

Open the Project Manager in a browser, then modify the project through another client. Verify the browser receives the appropriate event.

Examples:

```text
create → created
save → saved
rename → renamed
delete → deleted
```

### 5. Python Client

Run a test script:

```text
health
tree
create
open
save
rename
delete
```

Verify each operation goes through the Project Manager.

### 6. Filesystem Authority

Confirm that `editor_client.py`, `routers/`, `editor/` do not bypass `Project_files.py` for Project Manager filesystem operations.

## Final Architecture

```text
                    ┌─────────────────────┐
                    │   Project Manager   │
                    │       Server        │
                    └──────────┬──────────┘
                               │
                    Project Manager Core
                               │
                    ┌──────────▼──────────┐
                    │    Project_files    │
                    │  Filesystem Owner   │
                    └──────────┬──────────┘
                               │
                         Project Root
                               ▲
                               │
              ┌────────────────┴────────────────┐
              │                                 │
       Browser Interface                 Python Interface
              │                                 │
       Monaco / Dashboard                 editor_client.py
              │                                 │
              │                           AI Agents
              │                           Python Scripts
              │                                 │
              └──────────────┬──────────────────┘
                             │
                       Project Manager
                         HTTP / WS API
```

The central idea is:

> **Project Manager first. Interface second.**
```

---

<!-- ==== 39/39 : workspace/project.json ==== -->

### workspace/project.json

```json
{
    "name": "Project Manager",
    "version": "1.0.0",
    "workspace_version": "1.0"
}
```

---

> Generated by `scripts/gen_master_copy.py` on 2026-09-23. Do not edit by hand; regenerate with:
>
> `.venv/Scripts/python -m scripts.gen_master_copy`
```

---

<!-- ==== 38/39 : workspace/documentation/PLAN_editor_interface.md ==== -->

### workspace/documentation/PLAN_editor_interface.md

```markdown
# Plan: Project Manager Interface

Python module + organized server CRUD + modular UI.

## Goal

Keep the application as a **Project Manager** while adding a proper interface that allows AI agents and other Python programs to communicate with the Project Manager.

The Project Manager remains responsible for:

- project files
- directories
- file editing
- project configuration
- filesystem safety
- project initialization
- web UI

The new interface becomes another way to interact with those existing Project Manager capabilities.

The interface must **not bypass `Project_files.py`**.

## Architecture

```text
                         PROJECT MANAGER
                               │
              ┌────────────────┴────────────────┐
              │                                 │
        Web Interface                    Python Interface
              │                                 │
        Browser / Monaco                 AI Agents / Scripts
              │                                 │
              └────────────────┬────────────────┘
                               │
                        Project Manager
                        operation layer
                               │
                        Project_files.py
                               │
                        Project filesystem
```

The important principle is:

> There is one Project Manager and multiple interfaces to it.

## Target Structure

```text
project/
├── documentation/
│   └── MASTER_COPY.md
│
├── editor/
│   ├── __init__.py
│   ├── events.py
│   ├── session.py
│   └── operations.py
│
├── routers/
│   ├── __init__.py
│   ├── project.py
│   ├── files.py
│   ├── directories.py
│   ├── paths.py
│   └── ws.py
│
├── projectConfiguration/
│   ├── __init__.py
│   ├── Project_files.py
│   └── project.json
│
├── static/
│   ├── index.html
│   ├── editor.html
│   └── js/
│       ├── api.js
│       ├── session.js
│       ├── tree.js
│       ├── editor.js
│       └── main.js
│
├── editor_client.py
├── server.py
├── requirements.txt
└── ...
```

## Components

### 1. `editor/` — Project Manager operation/interface layer

This is the internal layer between the HTTP API and the filesystem.

It is **not a replacement for the Project Manager**.

It provides a clean set of operations that multiple interfaces can use.

#### `operations.py`

Create a controller such as `EditorInterface`.

It provides operations such as:

```text
open()
save()
create_file()
create_directory()
rename()
delete()
tree()
sessions()
```

Every filesystem mutation eventually goes through `Project_files.py`.

The controller should not implement its own filesystem logic.

Conceptually:

```text
Router
   ↓
Project Manager Interface
   ↓
Project_files
   ↓
Filesystem
```

### 2. `events.py` — Project Manager event system

Create a small event bus for changes occurring inside the Project Manager.

Example events:

```text
saved
created
renamed
deleted
tree_changed
```

Example:

```json
{
    "type": "saved",
    "path": "app.py"
}
```

The event system allows the browser and future agents to receive information about changes without directly monitoring the filesystem.

### 3. `session.py` — Interface sessions

Create:

```text
EditorSession
EditorManager
```

`EditorSession` tracks a connected interface client.

Possible state:

```text
client_id
open_file
dirty
last_modified
```

`EditorManager` maintains the active in-memory sessions.

It should also provide:

```text
register()
unregister()
update()
snapshot()
```

This is initially an in-memory system. Do not introduce a database for sessions.

### 4. `routers/` — Project Manager HTTP API

Split the existing API into resource-oriented routers.

#### `project.py`

```text
GET /api/project
GET /api/health
GET /api/sessions
```

#### `files.py`

```text
GET    /api/file/read
PUT    /api/file/write
POST   /api/file/create
DELETE /api/file/delete
```

#### `directories.py`

```text
POST   /api/directory/create
DELETE /api/directory/delete
```

#### `paths.py`

```text
PUT /api/path/rename
```

#### `ws.py`

```text
WS /api/ws
```

The existing REST paths and contracts remain unchanged.

### 5. WebSocket Interface

Add:

```text
/api/ws
```

The WebSocket provides real-time Project Manager events.

On connection:

```text
register session
```

Client messages may include:

```text
open
dirty
tree
```

Server events may include:

```text
saved
created
renamed
deleted
tree_changed
```

Example:

```json
{
    "type": "created",
    "path": "config/settings.json"
}
```

The browser can then update itself without requiring a complete page reload.

### 6. `editor_client.py` — Python Project Manager Interface

Create a Python client that allows another Python program or AI agent to communicate with the running Project Manager.

```python
from editor_client import EditorClient

client = EditorClient("http://127.0.0.1:8000")

client.tree()

client.open("app.py")

client.save(
    "app.py",
    "print('Hello World')"
)
```

Supported operations:

```text
open()
save()
create_file()
create_directory()
rename()
delete()
tree()
health()
sessions()
```

The client communicates with the Project Manager API. It must **not directly access the Project Manager filesystem**. This is important because the Project Manager remains the authority over filesystem operations.

### 7. Async Client

Provide an asynchronous client for AI-agent workflows:

```text
AsyncEditorClient
```

with asynchronous versions of the Project Manager operations.

Also provide:

```text
subscribe()
```

for receiving Project Manager events through WebSockets. This allows future agents to react to changes.

Example concept:

```text
AI Agent
   │
   ├── save file
   │
   ▼
Project Manager
   │
   ├── filesystem change
   │
   └── event
          │
          ▼
       Agent
```

### 8. Frontend Organization

The Project Manager UI remains visually and functionally the same. The JavaScript is reorganized into vanilla ES modules.

```text
static/js/
├── api.js
├── session.js
├── tree.js
├── editor.js
└── main.js
```

#### `api.js`

Central location for API requests. Responsible for:

```text
health
project
file operations
directory operations
rename
delete
sessions
```

#### `tree.js`

Responsible for:

- rendering the project tree
- selecting files
- refreshing the tree
- responding to tree-change events

#### `editor.js`

Responsible for Monaco. Move the existing Monaco initialization and behavior here with the goal of preserving it verbatim where practical. Keep:

- Monaco configuration
- editor initialization
- syntax highlighting
- save behavior
- Ctrl+S
- dirty state
- theme
- sidebar behavior

#### `session.js`

Responsible for:

- WebSocket connection
- connection state
- sending session events
- receiving Project Manager events
- applying live changes

#### `main.js`

Responsible for application startup and wiring the modules together.

### 9. `server.py`

After the reorganization, `server.py` becomes the application entry point:

```text
create FastAPI application
        ↓
configure lifespan
        ↓
register routers
        ↓
serve static files
        ↓
start server
```

It should not become the location for Project Manager business logic.

## Requirements

Add:

```text
httpx
websockets
```

to `requirements.txt`. Keep the existing FastAPI and Uvicorn dependencies.

## What Does NOT Change

The following remain Project Manager responsibilities:

```text
Project_files.py
project.json
project initialization
filesystem safety
dashboard
Monaco editor
existing REST endpoints
project structure
Windows support
Linux/ChromeOS support
```

The interface adds capability; it does not replace these systems.

## Interface Principle

The interface must provide agents with a controlled Project Manager API. An agent should think in terms of:

```text
open project file
read project file
save project file
create project file
create directory
rename path
delete path
inspect project tree
```

rather than:

```text
open arbitrary filesystem path
write arbitrary filesystem path
delete arbitrary filesystem path
```

The Project Manager remains the authority.

## Verification

### 1. Application startup

```text
python server.py
```

Verify the server starts successfully.

### 2. Existing API

Verify all existing contracts continue working:

```text
/api/health
/api/project
/api/file/read
/api/file/write
/api/file/create
/api/file/delete
/api/directory/create
/api/directory/delete
/api/path/rename
```

### 3. Browser

Verify:

- dashboard loads
- project tree loads
- files open
- Monaco works
- editing works
- Ctrl+S works
- file creation works
- rename works
- deletion works

The UI should remain visually/functionally equivalent.

### 4. Real-Time Events

Open the Project Manager in a browser, then modify the project through another client. Verify the browser receives the appropriate event.

Examples:

```text
create → created
save → saved
rename → renamed
delete → deleted
```

### 5. Python Client

Run a test script:

```text
health
tree
create
open
save
rename
delete
```

Verify each operation goes through the Project Manager.

### 6. Filesystem Authority

Confirm that `editor_client.py`, `routers/`, `editor/` do not bypass `Project_files.py` for Project Manager filesystem operations.

## Final Architecture

```text
                    ┌─────────────────────┐
                    │   Project Manager   │
                    │       Server        │
                    └──────────┬──────────┘
                               │
                    Project Manager Core
                               │
                    ┌──────────▼──────────┐
                    │    Project_files    │
                    │  Filesystem Owner   │
                    └──────────┬──────────┘
                               │
                         Project Root
                               ▲
                               │
              ┌────────────────┴────────────────┐
              │                                 │
       Browser Interface                 Python Interface
              │                                 │
       Monaco / Dashboard                 editor_client.py
              │                                 │
              │                           AI Agents
              │                           Python Scripts
              │                                 │
              └──────────────┬──────────────────┘
                             │
                       Project Manager
                         HTTP / WS API
```

The central idea is:

> **Project Manager first. Interface second.**
```

---

<!-- ==== 39/39 : workspace/project.json ==== -->

### workspace/project.json

```json
{
    "name": "Project Manager",
    "version": "1.0.0",
    "workspace_version": "1.0"
}
```

---

> Generated by `scripts/gen_master_copy.py` on 2026-09-23. Do not edit by hand; regenerate with:
>
> `.venv/Scripts/python -m scripts.gen_master_copy`
