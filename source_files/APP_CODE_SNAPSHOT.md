# agentCreator — Code Snapshot

Verbatim copy of every source file in the agentCreator repository, in one document, behind one file structure — the reference copy used for lookup and for rebuilding the code.

| Field | Value |
| ----- | ----- |
| Scope | `agentCreator/` |
| Contains | file contents, verbatim |
| Files | 85 |
| Generated | 2026-09-28 |
| Generator | `scripts/gen_master_copy.py` |
| Regenerate | `.venv/Scripts/python -m scripts.gen_master_copy` |
| Companions | [`headless_app_MASTER_COPY.md`](headless_app_MASTER_COPY.md) — `headless_app/`, [`project_manager_MASTER_COPY.md`](project_manager_MASTER_COPY.md) — `project_manager/` |

## What This Is

A verbatim copy of every source file in this repository, in one document,
behind one file structure. It exists for reference and AI lookup: to answer a
question about the code, or to rebuild it, the exact bytes of every file plus a
map of where everything lives are what is needed, and that is what this
document is.

There is deliberately **no description of what the code does here**. That
lives in the two companion documents, which describe the same tree module by
module:

- [`headless_app_MASTER_COPY.md`](headless_app_MASTER_COPY.md) — the agent
  engine, its tools and its bridge.
- [`project_manager_MASTER_COPY.md`](project_manager_MASTER_COPY.md) — the
  FastAPI server, its editor interface and the managed workspace.

Read the master copy first to learn what a file is for, then come here for its
contents. The File Index below is sized so you can also jump straight to one
file and read only that.

---

## Boot Sequence

### Prerequisites

- Python 3.10 or newer. The virtual environment in this workspace is 3.14.
- Ollama running locally, with at least one model pulled. The picker list in
  `headless_app/config/models.json` names `llama3.1:8b`,
  `nomic-embed-text:latest`, `qwen2.5-coder:latest` and `gemma4:e2b`.
- A web browser. The interface is static HTML, CSS and vanilla JavaScript —
  there is no build step and no bundler.

### Create the environment and run

```bat
rem 1. Virtual environment at the repository root, shared by both halves.
scripts\venv.bat

rem 2. Dependencies. requirements.txt pins the server stack. The engine also
rem    needs ollama and pydantic, which venv.bat installs for you.
.venv\Scripts\python.exe -m pip install -r project_manager\requirements.txt

rem 3. Start the Project Manager: the editor, the chat page and every agent
rem    route are served by this one process.
project_manager\scripts\run.bat
```

Then open <http://127.0.0.1:8000>. The bind address and port come from
`PROJECT_MANAGER_HOST` and `PROJECT_MANAGER_PORT` (`project_manager/server.py`).
The engine also runs without the server:

```bat
cd headless_app
..\.venv\Scripts\python.exe run.py list-agents
..\.venv\Scripts\python.exe run.py run-agent rag_assistant --message "what date is it today?"
```

### Layout requirement

`headless_app/` and `project_manager/` **must be sibling directories**. The
Project Manager imports the engine by putting `<repo>/headless_app` on
`sys.path`, and the chat router walks up three parents from
`interface/routers/chat.py` to find it. Any other layout silently leaves the
server running without the agent engine.


## File Index

All 85 embedded files, with their size, so a reader can decide what to open. The contents are further down, in this same order, each under a `### path` heading and an `<!-- ==== n/total : path ==== -->` marker.

| # | File | Lines | Bytes |
| - | ---- | ----- | ----- |
| 1 | `.gitattributes` | 14 | 254 |
| 2 | `.gitignore` | 34 | 417 |
| 3 | `headless_app/bridge/__init__.py` | 11 | 236 |
| 4 | `headless_app/bridge/client.py` | 910 | 24184 |
| 5 | `headless_app/bridge/providers.py` | 115 | 3584 |
| 6 | `headless_app/bridge/routers/__init__.py` | 1 | 71 |
| 7 | `headless_app/bridge/routers/agents.py` | 558 | 16583 |
| 8 | `headless_app/bridge/routers/chat.py` | 259 | 7007 |
| 9 | `headless_app/bridge/tools_adapter.py` | 68 | 2079 |
| 10 | `headless_app/config/models.json` | 29 | 568 |
| 11 | `headless_app/config/pipeline.json` | 9 | 336 |
| 12 | `headless_app/engine/__init__.py` | 1 | 0 |
| 13 | `headless_app/engine/agent_library/Builder/agent.json` | 13 | 350 |
| 14 | `headless_app/engine/agent_library/Builder/agent.md` | 141 | 7888 |
| 15 | `headless_app/engine/agent_library/Enginner/agent.json` | 11 | 365 |
| 16 | `headless_app/engine/agent_library/Enginner/agent.md` | 59 | 2946 |
| 17 | `headless_app/engine/agent_library/Planner/agent.json` | 9 | 311 |
| 18 | `headless_app/engine/agent_library/Planner/agent.md` | 1 | 0 |
| 19 | `headless_app/engine/agent_library/rag_assistant/agent.json` | 36 | 1396 |
| 20 | `headless_app/engine/agent_library/rag_assistant/agent.md` | 44 | 2794 |
| 21 | `headless_app/engine/agents/__init__.py` | 1 | 0 |
| 22 | `headless_app/engine/agents/factory.py` | 302 | 12428 |
| 23 | `headless_app/engine/agents/loader.py` | 237 | 8492 |
| 24 | `headless_app/engine/agents/registry.py` | 95 | 3579 |
| 25 | `headless_app/engine/agents/roots.py` | 204 | 6208 |
| 26 | `headless_app/engine/core/__init__.py` | 1 | 0 |
| 27 | `headless_app/engine/core/agent.py` | 491 | 21126 |
| 28 | `headless_app/engine/core/llm.py` | 264 | 10220 |
| 29 | `headless_app/engine/core/prompt.py` | 125 | 4345 |
| 30 | `headless_app/engine/pipeline.py` | 190 | 6960 |
| 31 | `headless_app/interface_runner.py` | 316 | 11439 |
| 32 | `headless_app/run.py` | 200 | 6121 |
| 33 | `headless_app/tools/__init__.py` | 1 | 0 |
| 34 | `headless_app/tools/chatlog.py` | 167 | 5663 |
| 35 | `headless_app/tools/project_tools.py` | 705 | 27375 |
| 36 | `headless_app/tools/registry.py` | 155 | 5181 |
| 37 | `headless_app/tools/state.py` | 73 | 2990 |
| 38 | `project_manager/.gitattributes` | 14 | 267 |
| 39 | `project_manager/.gitignore` | 28 | 275 |
| 40 | `project_manager/interface/clients/__init__.py` | 22 | 450 |
| 41 | `project_manager/interface/clients/editor_client.py` | 696 | 16962 |
| 42 | `project_manager/interface/core/__init__.py` | 22 | 572 |
| 43 | `project_manager/interface/core/defaults.py` | 109 | 2437 |
| 44 | `project_manager/interface/core/events.py` | 104 | 2439 |
| 45 | `project_manager/interface/core/operations.py` | 461 | 11873 |
| 46 | `project_manager/interface/core/session.py` | 130 | 3121 |
| 47 | `project_manager/interface/routers/__init__.py` | 59 | 1422 |
| 48 | `project_manager/interface/routers/agents.py` | 558 | 16657 |
| 49 | `project_manager/interface/routers/chat.py` | 787 | 21506 |
| 50 | `project_manager/interface/routers/directories.py` | 86 | 2024 |
| 51 | `project_manager/interface/routers/errors.py` | 73 | 1475 |
| 52 | `project_manager/interface/routers/files.py` | 172 | 3725 |
| 53 | `project_manager/interface/routers/paths.py` | 58 | 1272 |
| 54 | `project_manager/interface/routers/project.py` | 99 | 2082 |
| 55 | `project_manager/interface/routers/ws.py` | 225 | 5759 |
| 56 | `project_manager/interface/static/Agentpromptbuilder.html` | 1126 | 39377 |
| 57 | `project_manager/interface/static/chat.html` | 1044 | 33333 |
| 58 | `project_manager/interface/static/editor.html` | 436 | 11855 |
| 59 | `project_manager/interface/static/home.html` | 374 | 9197 |
| 60 | `project_manager/interface/static/index.html` | 386 | 10707 |
| 61 | `project_manager/interface/static/js/agentCards.js` | 98 | 3009 |
| 62 | `project_manager/interface/static/js/agentColors.js` | 70 | 2178 |
| 63 | `project_manager/interface/static/js/agents.js` | 371 | 11495 |
| 64 | `project_manager/interface/static/js/api.js` | 169 | 5499 |
| 65 | `project_manager/interface/static/js/chat.js` | 536 | 18689 |
| 66 | `project_manager/interface/static/js/editor.js` | 83 | 1899 |
| 67 | `project_manager/interface/static/js/main.js` | 390 | 11758 |
| 68 | `project_manager/interface/static/js/session.js` | 63 | 1448 |
| 69 | `project_manager/interface/static/js/topbar.js` | 159 | 4351 |
| 70 | `project_manager/interface/static/js/tree.js` | 206 | 6627 |
| 71 | `project_manager/parameters/__init__.py` | 6 | 171 |
| 72 | `project_manager/parameters/filesystem.py` | 1163 | 25903 |
| 73 | `project_manager/README.md` | 19 | 1024 |
| 74 | `project_manager/requirements.txt` | 5 | 78 |
| 75 | `project_manager/scripts/run.bat` | 16 | 445 |
| 76 | `project_manager/scripts/run.sh` | 23 | 513 |
| 77 | `project_manager/scripts/setup.sh` | 33 | 882 |
| 78 | `project_manager/server.py` | 233 | 6946 |
| 79 | `project_manager/workspace/agents/ProjectManager/agent.json` | 12 | 235 |
| 80 | `project_manager/workspace/agents/ProjectManager/agent.md` | 18 | 307 |
| 81 | `project_manager/workspace/project.json` | 6 | 95 |
| 82 | `README.md` | 207 | 8446 |
| 83 | `scripts/gen_master_copy.py` | 2124 | 64212 |
| 84 | `scripts/venv.bat` | 35 | 1136 |
| 85 | `scripts/venv.ps1` | 40 | 1691 |
| | **85 files** | **19004** | **581320** |

## File Structure

```text
agentCreator/
├── headless_app/
│   ├── bridge/
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── agents.py
│   │   │   └── chat.py
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── providers.py
│   │   └── tools_adapter.py
│   ├── config/
│   │   ├── models.json
│   │   └── pipeline.json
│   ├── data/   # not embedded: runtime output: chat log, tool log, pipeline run records
│   ├── engine/
│   │   ├── agent_library/
│   │   │   ├── Builder/
│   │   │   │   ├── agent.json
│   │   │   │   └── agent.md
│   │   │   ├── Enginner/
│   │   │   │   ├── agent.json
│   │   │   │   └── agent.md
│   │   │   ├── Planner/
│   │   │   │   ├── agent.json
│   │   │   │   └── agent.md
│   │   │   └── rag_assistant/
│   │   │       ├── agent.json
│   │   │       └── agent.md
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── factory.py
│   │   │   ├── loader.py
│   │   │   ├── registry.py
│   │   │   └── roots.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── llm.py
│   │   │   └── prompt.py
│   │   ├── __init__.py
│   │   └── pipeline.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── chatlog.py
│   │   ├── project_tools.py
│   │   ├── registry.py
│   │   └── state.py
│   ├── interface_runner.py
│   └── run.py
├── project_manager/
│   ├── interface/
│   │   ├── clients/
│   │   │   ├── __init__.py
│   │   │   └── editor_client.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── defaults.py
│   │   │   ├── events.py
│   │   │   ├── operations.py
│   │   │   └── session.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── agents.py
│   │   │   ├── chat.py
│   │   │   ├── directories.py
│   │   │   ├── errors.py
│   │   │   ├── files.py
│   │   │   ├── paths.py
│   │   │   ├── project.py
│   │   │   └── ws.py
│   │   └── static/
│   │       ├── js/
│   │       │   ├── agentCards.js
│   │       │   ├── agentColors.js
│   │       │   ├── agents.js
│   │       │   ├── api.js
│   │       │   ├── chat.js
│   │       │   ├── editor.js
│   │       │   ├── main.js
│   │       │   ├── session.js
│   │       │   ├── topbar.js
│   │       │   └── tree.js
│   │       ├── Agentpromptbuilder.html
│   │       ├── chat.html
│   │       ├── editor.html
│   │       ├── home.html
│   │       └── index.html
│   ├── parameters/
│   │   ├── __init__.py
│   │   └── filesystem.py
│   ├── scripts/
│   │   ├── run.bat
│   │   ├── run.sh
│   │   └── setup.sh
│   ├── workspace/
│   │   ├── agents/
│   │   │   └── ProjectManager/
│   │   │       ├── agent.json
│   │   │       └── agent.md
│   │   ├── config/
│   │   ├── data/   # not embedded: runtime output: chat log and saved chat sessions
│   │   ├── documentation/
│   │   │   └── PromptBuilderFiles/
│   │   │       ├── output/
│   │   │       └── prompt_parts/
│   │   │           └── rules/
│   │   ├── project_scope/
│   │   ├── Tests/
│   │   ├── To Do/
│   │   ├── Tools/
│   │   ├── updates/
│   │   └── project.json
│   ├── .gitattributes
│   ├── .gitignore
│   ├── README.md
│   ├── requirements.txt
│   └── server.py
├── scripts/
│   ├── gen_master_copy.py
│   ├── venv.bat
│   └── venv.ps1
├── source_files/
├── .gitattributes
├── .gitignore
└── README.md
```

## Scope

This document embeds every source file under `agentCreator/`, **85 files** in total, in case-insensitive path order, verbatim and unmodified.

The following are listed in the structure above but deliberately **not** covered:

| Path | Reason |
| ---- | ------ |
| `headless_app/data` | runtime output: chat log, tool log, pipeline run records |
| `project_manager/workspace/data` | runtime output: chat log and saved chat sessions |

Also excluded everywhere: `.git`, `__pycache__/`, virtualenvs, editor and tool caches (`.venv`, `venv`, `.idea`, `.vscode`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`), compiled and runtime artifacts (`*.pyc`, `*.pyo`, `*.log`, `*.dll`).

The three generated documents in `source_files/` are never embedded in each other, so no document can nest inside itself.

Regenerate all three documents with:

```bat
.venv/Scripts/python -m scripts.gen_master_copy
```

Or just this one:

```bat
.venv/Scripts/python -m scripts.gen_master_copy --only agentCreator
```

<!-- ==== 1/85 : .gitattributes ==== -->

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

<!-- ==== 2/85 : .gitignore ==== -->

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

# Logs and runtime data
*.log
*.jsonl
project_manager/workspace/ws_evt_probe.txt
project_manager/workspace/data/

# Local working notes
planSave.txt
```

---

<!-- ==== 3/85 : headless_app/bridge/__init__.py ==== -->

### headless_app/bridge/__init__.py

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

<!-- ==== 4/85 : headless_app/bridge/client.py ==== -->

### headless_app/bridge/client.py

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

<!-- ==== 5/85 : headless_app/bridge/providers.py ==== -->

### headless_app/bridge/providers.py

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

<!-- ==== 6/85 : headless_app/bridge/routers/__init__.py ==== -->

### headless_app/bridge/routers/__init__.py

```python
"""bridge.routers - drop-in FastAPI routers for the Project Manager."""
```

---

<!-- ==== 7/85 : headless_app/bridge/routers/agents.py ==== -->

### headless_app/bridge/routers/agents.py

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

<!-- ==== 8/85 : headless_app/bridge/routers/chat.py ==== -->

### headless_app/bridge/routers/chat.py

```python
"""
bridge/routers/chat.py
======================

Agent-backed Project Manager chat router (drop-in replacement).

The Project Manager keeps a stub chat surface: ``POST /api/chat`` logs a
message and ``GET /api/chat`` fetches history. This router swaps the stub
handler for the agentCreator engine, so the Project Manager becomes a fully
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

<!-- ==== 9/85 : headless_app/bridge/tools_adapter.py ==== -->

### headless_app/bridge/tools_adapter.py

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

<!-- ==== 10/85 : headless_app/config/models.json ==== -->

### headless_app/config/models.json

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

<!-- ==== 11/85 : headless_app/config/pipeline.json ==== -->

### headless_app/config/pipeline.json

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

<!-- ==== 12/85 : headless_app/engine/__init__.py ==== -->

### headless_app/engine/__init__.py

```python
(empty file — 0 bytes)
```

---

<!-- ==== 13/85 : headless_app/engine/agent_library/Builder/agent.json ==== -->

### headless_app/engine/agent_library/Builder/agent.json

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

<!-- ==== 14/85 : headless_app/engine/agent_library/Builder/agent.md ==== -->

### headless_app/engine/agent_library/Builder/agent.md

````markdown
# Module Builder Agent

## role
You are the **Module Builder Agent** (Step 3 of the agentCreator Module Development Pipeline). Your role is to take a Stage 2 Technical Implementation Blueprint provided directly in the user's message and compile it into a single, complete, production-ready Python custom module file.

## purpose
To convert technical blueprints into runnable Python custom module code (`<module_name>.py`) that communicates with the rest of the agentCreator application through the interface framework (`UI_MANIFEST` + `register_routes(app)` FastAPI endpoints + `server.paths` path authority + `InterfaceDispatcher` wiring).

## tools
You have access to exactly **THREE tools** and MUST ONLY use these tools:
1. `read_file`: Reads text and document file contents from disk.
2. `write_text_file`: Writes text files directly to a specified directory on disk.
3. `map_files`: Inspects directory structures and lists file trees on disk.

**Tool Rule**: You MUST ONLY use `read_file`, `write_text_file`, and `map_files`. Do NOT attempt to execute or call any other tools outside of these three.

## do_not_hallucinate
- **Strict Route Encapsulation**: EVERY route decorator (`@app.get(...)`, `@app.post(...)`) MUST be placed INSIDE the top-level `def register_routes(app: FastAPI):` function definition. NEVER write `@app.get` or `@app.post` at the root level of the file, because `app` is only passed to `register_routes(app)` at runtime.
- **Strict Grounding**: Do NOT fabricate or invent non-existent UI action types, ungrounded schema keys, or fake framework decorators. Only use the 4 supported agentCreator UI action patterns (`prompt_input`, `dropdown_menu`, `open_modal`, `qa_survey`) and standard FastAPI decorators (`@app.get`, `@app.post`).
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
- **Strict agentCreator Contracts**: Use exact schema keys (`components`, `target_endpoint`, `indicate_success`, `status`, `message`).
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

<!-- ==== 15/85 : headless_app/engine/agent_library/Enginner/agent.json ==== -->

### headless_app/engine/agent_library/Enginner/agent.json

```json
{
  "id": "execute_engineer_agent",
  "name": "Execute Engineer Agent",
  "description": "Step 2: Uses read_file to inspect ux_module_designer_skills.md and translates Step 1 functional plans into section-by-section pseudo-code and agentCreator Python blueprints.",
  "mode": "agent",
  "model": "qwen2.5-coder:latest",
  "tools": [
    "read_file"
  ]
}
```

---

<!-- ==== 16/85 : headless_app/engine/agent_library/Enginner/agent.md ==== -->

### headless_app/engine/agent_library/Enginner/agent.md

````markdown
# Execute Engineer Agent

## role
You are the **Execute Engineer Agent** (Step 2). Your role is to take the functional feature list from Step 1 and translate it into structured pseudo-code and Python implementation blueprints grounded strictly in the agentCreator skills reference.

## purpose
To bridge functional requirements and code by applying the implementation patterns defined in `skills/ux_module_designer_skills.md`.

## input_contract
Accepts the **Feature Plan** document from Step 1. The Feature Plan for the CURRENT task is always included in your incoming message - never ask for it or wait for it.

## skills
Reference `skills/ux_module_designer_skills.md` for:
1. `UI_MANIFEST` button declarations.
2. Action button logic (`prompt_input`, `dropdown_menu`, `open_modal`, `qa_survey`).
3. Endpoint registration via `register_routes(app)`.
4. Standard status response contracts (`status`, `message`, `indicate_success`).
5. Storage path authority using `server.paths`.

## workflow
0. **Load the Skills Reference ONCE**: call the `read_file` tool on `skills/ux_module_designer_skills.md` by default, and read exactly ONE TIME. If the result of that read is already in the conversation (any earlier `read_file` result message with tool "read_file" and path `ux_module_designer_skills.md`), do NOT call it again - that file never changes during your turn. Ground every decision on what that file actually contains. Never guess or invent patterns not present in it.
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

<!-- ==== 17/85 : headless_app/engine/agent_library/Planner/agent.json ==== -->

### headless_app/engine/agent_library/Planner/agent.json

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

<!-- ==== 18/85 : headless_app/engine/agent_library/Planner/agent.md ==== -->

### headless_app/engine/agent_library/Planner/agent.md

```markdown
(empty file — 0 bytes)
```

---

<!-- ==== 19/85 : headless_app/engine/agent_library/rag_assistant/agent.json ==== -->

### headless_app/engine/agent_library/rag_assistant/agent.json

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

<!-- ==== 20/85 : headless_app/engine/agent_library/rag_assistant/agent.md ==== -->

### headless_app/engine/agent_library/rag_assistant/agent.md

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

<!-- ==== 21/85 : headless_app/engine/agents/__init__.py ==== -->

### headless_app/engine/agents/__init__.py

```python
(empty file — 0 bytes)
```

---

<!-- ==== 22/85 : headless_app/engine/agents/factory.py ==== -->

### headless_app/engine/agents/factory.py

```python
"""
app/agents/factory.py
=====================

Constructs runtime Agents from agent definitions.

    build_agent(agent_id, model, bridge)
        ↓
    loader.load_definition()      (agent.md + agent.json, via agent roots)
        ↓
    registry: resolve tools       (IDs -> Python functions, provider bound)
        ↓
    PromptManager.build()         (sections + tool docstrings -> system prompt)
        ↓
    Agent  (with its own FileSession)

The caller never needs to know where definitions live or how prompts are
composed. Chat-mode agents get an empty tool list, which disables the
tool loop entirely - same Agent class, behavior driven by configuration.

Nothing here is process-wide: each agent gets its own tools (bound to its
own filesystem provider) and its own FileSession, so two agents can be
built and run side by side without sharing state.
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
from tools.registry import new_session, resolve_tools


class AgentDefinitionError(ValueError):
    """A definition parsed, but cannot produce a working agent.

    Distinct from AgentNotFoundError (no definition at all) so callers can
    tell "this agent does not exist" from "this agent is broken".
    """


def _session_aware(func: Callable, session) -> Callable:
    """Wrap a tool so its results are recorded into this agent's FileSession.

    Uses functools.wraps so inspect.signature() (and therefore the schema
    Ollama builds for tool calling) sees the REAL tool signature, not the
    wrapper's (*args, **kwargs).

    Standard tool response shape: {"success", "tool", "data": {...}, "error":}.
    Known data keys are translated into session state:
        files                   -> add_discovered(paths)
        path / path+content     -> record_read(...)
        filename/path (written) -> add_output(path)
        pending_files (delete)  -> mark_for_deletion(paths)

    Safety gate: delete_files(approved=True) can only delete paths that were
    previously PROPOSED (approved=False) and recorded in session.pending_deletion.
    Any path the model fabricates or invents is rejected instead of deleted.
    Because the session belongs to one agent, another agent's proposals can
    never authorize a deletion here.
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
    """Translate a tool result dict into this agent's FileSession state."""
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
    """Shared Agent construction from a parsed definition.

    Two things are deliberately per agent rather than per process:

    * the tools carry ``bridge`` as their own provider, so no build order or
      request ordering can redirect another agent's file operations;
    * the FileSession is created here, so discovered files, outputs and
      pending deletions belong to this agent alone.
    """
    definition = {"meta": meta, "sections": sections}

    mode = (meta.get("mode") or "chat").lower()
    tool_ids = [] if mode == "chat" else (meta.get("tools") or [])
    tools: list[Callable] = resolve_tools(tool_ids, provider=bridge)

    profile = PromptManager.build(definition, tools)

    if not (profile.system_prompt or "").strip():
        raise AgentDefinitionError(
            f"Agent '{agent_id}' has an empty system prompt, so it would "
            f"reply with no instructions. Its agent.md needs at least one "
            f"section the prompt composer reads - '## role', '## purpose', "
            f"'## personality', '## boundaries', '## communication', "
            f"'## principles' or '## decision style' (see "
            f"engine/core/prompt.py KNOWN_SECTIONS)."
        )

    if tools:
        _append_grounding(agent_id, profile, bridge=bridge)

    resolved_model = model or meta.get("model") or None
    session = new_session()
    tools = [_session_aware(fn, session) for fn in tools]
    return Agent(model=resolved_model, tools=tools, profile=profile, session=session)


def build_agent(agent_id: str, model: str | None = None, bridge=None) -> Agent:
    """Build a ready-to-use Agent for the given agent_id.

    Args:
        agent_id: id inside any registered agent root (see
                  engine/agents/roots.py) - the bundled library or the
                  Project Manager workspace.
        model:    explicit model override; when empty, falls back to the
                  agent's own "model" field, then to ask_llm's resolution
                  (config/models.json > first Ollama model).
        bridge:   optional Project Manager bridge (HTTP client or direct
                  filesystem authority). When present, the agent's file tools
                  route through the Project Manager instead of the local disk.
                  It is bound to this agent only.

    Raises AgentNotFoundError if the definition is missing, and
    AgentDefinitionError if it exists but cannot build a usable agent.
    """
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

    Raises AgentNotFoundError if either file is missing/unreadable, and
    AgentDefinitionError if the definition cannot build a usable agent.
    """
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


__all__ = [
    "build_agent",
    "build_agent_from_definition",
    "replay_history",
    "AgentNotFoundError",
    "AgentDefinitionError",
]
```

---

<!-- ==== 23/85 : headless_app/engine/agents/loader.py ==== -->

### headless_app/engine/agents/loader.py

```python
"""
app/agents/loader.py
====================

Locates, reads, and parses one agent definition.

An agent folder contains:
    agent.json  - metadata/configuration (id, name, mode, tools, model)
    agent.md    - behavior sections (## role, ## purpose, ## boundaries, ...)

load_definition() returns:
    {"meta": {...agent.json...}, "sections": {...parsed markdown sections...}}

Where agents live is decided by engine/agents/roots.py: the engine ships
with ``agent_library/``, and a host application may register more roots
(the Project Manager registers ``workspace/agents/``). Lookups here search
every registered root, so an agent is found by id regardless of which root
owns it.

This module does NOT run agents. Its job is only: find, read, parse, return.
"""

import json
import re
from pathlib import Path

from engine.agents import roots
from engine.agents.roots import (  # noqa: F401  (re-exported for callers)
    AGENT_MD_FILE,
    AGENT_META_FILE,
    AgentRoot,
    LIBRARY_ROOT_NAME,
    register_agent_root,
    unregister_agent_root,
)

#: Backwards-compatible alias for the built-in library root directory.
AGENT_LIBRARY_DIR = roots.DEFAULT_LIBRARY_DIR


def agent_dir(agent_id: str) -> Path:
    """The folder for an agent id inside the highest-precedence root.

    Searches every registered root (see engine/agents/roots.py): first the
    literal ``<root>/<agent_id>`` path, then each root's folders matched by
    their ``agent.json`` ``id`` field, so folder names and ids may differ.
    Falls back to the literal library path so callers that create folders
    (``save_markdown``) still work for brand-new agents.
    """
    found = roots.find_agent(agent_id)
    if found is not None:
        return found[1]
    return AGENT_LIBRARY_DIR / agent_id


def agent_root(agent_id: str) -> AgentRoot | None:
    """The registered root that owns ``agent_id``, or None."""
    found = roots.find_agent(agent_id)
    return found[0] if found is not None else None


def agent_json_path(agent_id: str) -> str | None:
    """Workspace-relative ``agent.json`` path for a registered agent."""
    found = roots.find_agent(agent_id)
    if found is None:
        return None
    root, directory = found
    return root.json_path(directory)


def agent_md_path(agent_id: str) -> str | None:
    """Workspace-relative ``agent.md`` path for a registered agent."""
    found = roots.find_agent(agent_id)
    if found is None:
        return None
    root, directory = found
    return root.md_path(directory)


def _resolve_agent_dir(agent_id: str) -> Path | None:
    """Find the on-disk folder for an agent by id across all roots.

    Returns ``None`` when nothing matches so callers can fall back to the
    literal path (which preserves the existing create-folder semantics for
    ``save_markdown`` on genuinely new agents).
    """
    found = roots.find_agent(agent_id)
    return found[1] if found is not None else None


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

<!-- ==== 24/85 : headless_app/engine/agents/registry.py ==== -->

### headless_app/engine/agents/registry.py

```python
"""
app/agents/registry.py
======================

Agent discovery over the registered roots (engine/agents/roots.py).

The filesystem is the source of truth: every folder in a registered root
that contains an agent.json is an available agent. Because roots are
searched most-recently-registered first, a workspace agent shadows a
library agent declaring the same id - which is the same precedence
``loader`` uses when it builds one agent, so discovery and building can
never disagree.

Registering ``workspace/agents/`` (the Project Manager does this at
startup) is therefore all it takes for a newly created agent to appear
in GET /api/agents, in the frontend selector, and in every id-based
lookup: no code changes, no manual lists, no second scanner.
"""

import json

from engine.agents import roots
from engine.agents.loader import AGENT_LIBRARY_DIR  # noqa: F401  (re-exported)


def _read_meta(agent_dir) -> dict | None:
    """Parsed agent.json, or None when missing/unreadable/malformed."""
    meta_file = agent_dir / roots.AGENT_META_FILE
    if not meta_file.exists():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[REGISTRY] skipping {agent_dir}: unreadable agent.json ({exc})")
        return None
    return meta if isinstance(meta, dict) else None


def list_agents() -> list[dict]:
    """One summary per discovered agent, highest-precedence root first.

        [{"id", "name", "description", "mode", "model", "tools",
          "source", "json_path", "md_path", "complete"}, ...]

    Deduplicated by id: the first root that provides an id wins, and
    lower-precedence roots with the same id are skipped. An agent whose
    agent.json parsed but whose agent.md is missing is still returned,
    with ``complete: False``, so the UI can show it as a work in
    progress instead of it silently disappearing.
    """
    summaries: list[dict] = []
    claimed: set[str] = set()

    for root in roots.agent_roots():
        for agent_dir in root.agent_dirs():
            meta = _read_meta(agent_dir)
            if meta is None:
                # No readable agent.json: not an agent folder. A folder
                # with no meta at all is silently ignored, exactly as
                # before, so a half-created folder cannot break the list.
                continue

            agent_id = str(meta.get("id") or agent_dir.name)
            if agent_id in claimed:
                # A higher-precedence root already owns this id.
                continue
            claimed.add(agent_id)

            md_file = agent_dir / roots.AGENT_MD_FILE
            summaries.append({
                "id": agent_id,
                "name": meta.get("name") or agent_dir.name,
                "description": meta.get("description", "") or "",
                "mode": meta.get("mode", "chat") or "chat",
                "model": meta.get("model", "") or "",
                "tools": list(meta.get("tools") or []),
                "source": root.source,
                "json_path": root.json_path(agent_dir),
                "md_path": root.md_path(agent_dir),
                "complete": md_file.exists(),
            })

    return summaries


def get_agent_meta(agent_id: str) -> dict | None:
    """Return the summary for one agent id, or None if not registered."""
    for summary in list_agents():
        if summary["id"] == agent_id:
            return summary
    return None


__all__ = ["list_agents", "get_agent_meta", "AGENT_LIBRARY_DIR"]
```

---

<!-- ==== 25/85 : headless_app/engine/agents/roots.py ==== -->

### headless_app/engine/agents/roots.py

```python
"""
engine/agents/roots.py
======================

Pluggable agent roots.

An *agent root* is a directory whose immediate children are agent folders
(one folder per agent, holding ``agent.json`` + ``agent.md``). The engine
registers exactly one root at import time::

    engine/agent_library/

so the headless runtime keeps working entirely on its own. A host
application may register further roots; the Project Manager registers
``workspace/agents/`` while its server is starting.

Once a root is registered, every lookup in the engine sees its agents -
there is no separate "library mode" and "workspace mode". ``build_agent``,
chat, single runs and pipelines all resolve agent ids through this module,
so an agent becomes runnable the moment its folder is discovered.

Precedence
----------
Roots are searched most-recently-registered first. A workspace agent
therefore shadows a library agent that declares the same ``id``, which is
the precedence the Project Manager already used when it looked up a single
definition. Re-registering a name replaces it and promotes it, so a server
that re-registers its root on every startup stays idempotent.

This module deliberately knows nothing about the Project Manager. The
wiring lives in the host application (see ``project_manager/server.py``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

#: Canonical file names inside an agent folder.
AGENT_META_FILE = "agent.json"
AGENT_MD_FILE = "agent.md"

#: The root the engine ships with.
LIBRARY_ROOT_NAME = "library"

DEFAULT_LIBRARY_DIR = (
    Path(__file__).resolve().parent.parent / "agent_library"
)


# ==========================================================================
# ROOT DESCRIPTOR
# ==========================================================================

@dataclass(frozen=True)
class AgentRoot:
    """One directory of agent folders."""

    name: str
    path: Path
    source: str

    def agent_dirs(self) -> Iterator[Path]:
        """Yield every candidate agent folder, sorted for determinism."""
        if not self.path.is_dir():
            return
        for child in sorted(self.path.iterdir()):
            if not child.is_dir() or child.name.startswith(("_", ".")):
                continue
            yield child

    def json_path(self, agent_dir: Path) -> str:
        """Workspace-relative ``agent.json`` path for the agent API."""
        return str(agent_dir / AGENT_META_FILE).replace("\\", "/")

    def md_path(self, agent_dir: Path) -> str:
        """Workspace-relative ``agent.md`` path for the agent API."""
        return str(agent_dir / AGENT_MD_FILE).replace("\\", "/")


# ==========================================================================
# ROOT REGISTRY
# ==========================================================================

#: Registered roots, lowest precedence first.
_roots: list[AgentRoot] = []


def register_agent_root(
    name: str,
    path: str | Path,
    source: str | None = None,
) -> AgentRoot:
    """Register (or re-register) an agent root and give it top precedence.

    Args:
        name:    unique key, e.g. ``"workspace"``.
        path:    directory holding one folder per agent.
        source:  value reported as each agent's ``source``; defaults to
                 ``name``.

    Returns:
        The registered :class:`AgentRoot`.
    """
    resolved = Path(path).expanduser().resolve()
    root = AgentRoot(name=name, path=resolved, source=source or name)
    unregister_agent_root(name)
    _roots.append(root)
    return root


def unregister_agent_root(name: str) -> bool:
    """Remove a root by name. Returns True when something was removed."""
    for index, existing in enumerate(_roots):
        if existing.name == name:
            del _roots[index]
            return True
    return False


def agent_roots() -> list[AgentRoot]:
    """Registered roots, highest precedence first."""
    return list(reversed(_roots))


def get_root(name: str) -> AgentRoot | None:
    for root in agent_roots():
        if root.name == name:
            return root
    return None


def reset_agent_roots() -> AgentRoot:
    """Drop every root except the built-in library root (used by tests)."""
    _roots.clear()
    return register_agent_root(
        LIBRARY_ROOT_NAME, DEFAULT_LIBRARY_DIR, source="library"
    )


# The engine always has its bundled library available.
reset_agent_roots()


# ==========================================================================
# RESOLUTION
# ==========================================================================

def _read_meta(agent_dir: Path) -> dict | None:
    meta_file = agent_dir / AGENT_META_FILE
    if not meta_file.exists():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return meta if isinstance(meta, dict) else None


def find_agent(agent_id: str) -> tuple[AgentRoot, Path] | None:
    """Locate an agent folder by id across every registered root.

    Two strategies per root, tried highest precedence first:
        1. Literal: ``<root>/<agent_id>`` is a directory.
        2. Scan: read ``agent.json`` in each child folder and match its
           ``id`` field, so folder names and ids may differ (e.g. the
           ``Planner`` folder declaring id ``feature_planner_agent``).

    Returns:
        ``(root, agent_dir)`` for the winning match, else ``None``.
    """
    if not agent_id:
        return None

    for root in agent_roots():
        literal = root.path / agent_id
        if literal.is_dir():
            return root, literal

    for root in agent_roots():
        for child in root.agent_dirs():
            meta = _read_meta(child)
            if meta is not None and meta.get("id") == agent_id:
                return root, child

    return None


__all__ = [
    "AGENT_META_FILE",
    "AGENT_MD_FILE",
    "AgentRoot",
    "DEFAULT_LIBRARY_DIR",
    "LIBRARY_ROOT_NAME",
    "agent_roots",
    "find_agent",
    "get_root",
    "register_agent_root",
    "reset_agent_roots",
    "unregister_agent_root",
]
```

---

<!-- ==== 26/85 : headless_app/engine/core/__init__.py ==== -->

### headless_app/engine/core/__init__.py

```python
(empty file — 0 bytes)
```

---

<!-- ==== 27/85 : headless_app/engine/core/agent.py ==== -->

### headless_app/engine/core/agent.py

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

<!-- ==== 28/85 : headless_app/engine/core/llm.py ==== -->

### headless_app/engine/core/llm.py

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

<!-- ==== 29/85 : headless_app/engine/core/prompt.py ==== -->

### headless_app/engine/core/prompt.py

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

<!-- ==== 30/85 : headless_app/engine/pipeline.py ==== -->

### headless_app/engine/pipeline.py

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

<!-- ==== 31/85 : headless_app/interface_runner.py ==== -->

### headless_app/interface_runner.py

```python
"""
interface_runner.py
===================

The single execution seam of the agentCreator engine.

Every caller - the headless CLI (run.py) and the Project Manager routers -
goes through this module, so build/think/log behaviour cannot drift
between frontends.

    AgentInterface.run_chat(message, agent_id, history=...)
        - one agent resolved by id from any registered root, chat reply.

    AgentInterface.run_single_agent(json_path, md_path, user_input)
        - one ad-hoc agent built from explicit agent.json + agent.md paths.
          When json_path/md_path are omitted the agent is resolved by id.

    AgentInterface.run_pipeline(agent_configs, user_input)
        - an ordered agent chain (feed-forward). Each step receives the
          original message plus every earlier step's reply, labelled; the
          final step's reply is the pipeline result.

    AgentInterface.list_agents() / .get_agent(id)
        - discovery over every registered root.

Every run persists the user turn + agent reply to the plain-text chat log
(data/chatlog/chat.log) *tagged with the agent id*, so per-agent history
survives, is replayed into the next turn, and the agent's own
search_chat_logs tool can recall it. Tool events are recorded to
data/toollog/tool_usage.jsonl.

An optional Project Manager bridge makes the Project Manager server (or its
direct filesystem authority) the filesystem owner for the file tools. The
bridge is bound per agent, so concurrent agents never share file-tool
state.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from engine.agents.factory import (
    build_agent,
    build_agent_from_definition,
    replay_history,
)
from engine.agents.registry import get_agent_meta, list_agents
from engine.pipeline import run_pipeline as _run_pipeline
from tools.chatlog import append_chat, read_history

#: Turns of prior conversation handed to the model, per agent.
DEFAULT_HISTORY_LIMIT = 20


def _as_history(
    agent_id: str | None,
    limit: int | None = DEFAULT_HISTORY_LIMIT,
) -> list[dict] | None:
    """Read one agent's recent turns from the chat log as model messages.

    Scoped by agent id so agents never see each other's conversations.
    Returns None (meaning "no history") when logging is unavailable or
    limit is falsy, so a broken log never blocks a conversation.
    """
    if not limit or limit <= 0:
        return None
    try:
        entries = read_history(limit=limit, agent=agent_id)
    except Exception as exc:  # pragma: no cover - logging must not break runs
        print(f"[INTERFACE] history unavailable: {exc}")
        return None

    history: list[dict] = []
    for entry in entries:
        sender = str(entry.get("sender", ""))
        content = str(entry.get("message", "") or "")
        if not content:
            continue
        history.append({
            "role": "assistant" if sender in ("agent", "ai") else "user",
            "content": content,
        })
    return history or None


class AgentInterface:
    """Thin, stable API over the build/think loop and pipeline chain."""

    def __init__(
        self,
        bridge: Any = None,
        model: str | None = None,
        log_sink: Callable[[dict], None] | None = None,
    ) -> None:
        """Create a runner.

        Args:
            bridge:   optional Project Manager provider (ProjectManagerBridge
                      or DirectProjectIO). When present, the file tools route
                      through the Project Manager filesystem.
            model:    optional default model override for every run.
            log_sink: optional callback receiving every chat log entry as it
                      is written, so a host can mirror the log elsewhere.
        """
        self.bridge = bridge
        self.model = model
        self.log_sink = log_sink

    # ============================================================
    # INTERNAL
    # ============================================================

    def _log(self, sender: str, message: str, agent_id: str) -> dict:
        """Write one chat log entry and hand it to the sink."""
        entry = append_chat(sender, message, agent=agent_id)
        if self.log_sink is not None:
            try:
                self.log_sink(entry)
            except Exception as exc:  # pragma: no cover - sink must not break runs
                print(f"[INTERFACE] log sink failed: {exc}")
        return entry

    def _think(
        self,
        agent: Any,
        message: str,
        agent_id: str,
        history: list[dict] | None,
    ) -> tuple[str, list[dict]]:
        """Replay history, run one turn, and log both sides.

        One place for the build-think-log order, so chat, single-agent
        and pipeline runs behave identically. The current turn is not in
        ``history``; the caller reads the log *before* it is written.
        """
        if history:
            replay_history(agent, history)
        reply = agent.think(message)
        entries = [
            self._log("user", message, agent_id),
            self._log("agent", reply, agent_id),
        ]
        return reply, entries

    # ============================================================
    # CHAT (one agent, resolved by id)
    # ============================================================

    def run_chat(
        self,
        message: str,
        agent_id: str | None = None,
        model: str | None = None,
        history: list[dict] | None = None,
        use_logged_history: bool = True,
    ) -> dict[str, Any]:
        """Run one agent and return its reply.

        agent_id is resolved through the agent roots, so an agent created
        in the Project Manager works exactly like a bundled library agent.
        With no agent_id the first discovered agent is used.

        Args:
            history: explicit prior turns ({role, content}). When None and
                ``use_logged_history`` is set, this agent's own log history
                is replayed (the current turn is logged after the model has
                answered).
        Returns {"reply", "agent_id", "name", "model", "tool_events",
        "entries"}.
        """
        resolved_id = agent_id or self._default_agent_id()
        agent = build_agent(resolved_id, model=model or self.model, bridge=self.bridge)

        if history is None and use_logged_history:
            history = _as_history(resolved_id, DEFAULT_HISTORY_LIMIT)

        reply, entries = self._think(agent, message, resolved_id, history)

        return {
            "reply": reply,
            "agent_id": resolved_id,
            "name": agent.profile.name,
            "model": agent.model,
            "tool_events": agent.tool_events,
            "entries": entries,
        }

    # ============================================================
    # SINGLE AGENT (explicit definition, or by id)
    # ============================================================

    def run_single_agent(
        self,
        user_input: str,
        json_path: str | None = None,
        md_path: str | None = None,
        agent_id: str | None = None,
        model: str | None = None,
        history: list[dict] | None = None,
        use_logged_history: bool = False,
    ) -> dict[str, Any]:
        """Run one agent built from explicit agent.json + agent.md paths.

        This is the headless construction path: the definition can live
        anywhere, not only inside a registered root. When json_path/md_path
        are omitted the agent is resolved by ``agent_id`` instead.

        Returns {"reply", "agent_id", "model", "tool_events", "name",
        "description", "entries"}.
        """
        if json_path and md_path:
            agent = build_agent_from_definition(
                json_path,
                md_path,
                model=model or self.model,
                bridge=self.bridge,
            )
            # A definition loaded from an explicit path may be outside any
            # registered root; use its own id so history stays per-agent.
            resolved_id = str(agent.profile.id)
        elif agent_id:
            resolved_id = agent_id
            agent = build_agent(
                agent_id,
                model=model or self.model,
                bridge=self.bridge,
            )
        else:
            raise ValueError(
                "Provide json_path + md_path, or an agent_id, to run."
            )

        if history is None and use_logged_history:
            history = _as_history(resolved_id, DEFAULT_HISTORY_LIMIT)

        reply, entries = self._think(agent, user_input, resolved_id, history)

        return {
            "reply": reply,
            "agent_id": resolved_id,
            "name": agent.profile.name,
            "description": agent.profile.description,
            "model": agent.model,
            "tool_events": agent.tool_events,
            "entries": entries,
        }

    # ============================================================
    # PIPELINE
    # ============================================================

    def run_pipeline(
        self,
        user_input: str,
        agent_configs: list | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run the ordered agent chain (feed-forward).

        Args:
            agent_configs:
                None  -> load steps from config/pipeline.json.
                list  -> each element is either an agent id (str) or a dict with
                         "json_path" + "md_path" (ad-hoc step agents).

        Returns:
            {"reply", "outputs": [...step outputs...], "tool_events",
             "model", "entries"}.
        """
        result = _run_pipeline(
            user_input,
            model=model or self.model,
            steps=agent_configs,
            bridge=self.bridge,
        )
        # A cascade is not one agent, so the exchange is logged untagged
        # rather than attributed to whichever step happened to run first.
        result["entries"] = [
            self._log("user", user_input, None),
            self._log("agent", result["reply"], None),
        ]
        result["model"] = model or self.model
        return result

    # ============================================================
    # UTILITIES
    # ============================================================

    def _default_agent_id(self) -> str:
        agents = self.list_agents()
        if not agents:
            raise RuntimeError(
                "No agents are registered. Register an agent root "
                "(engine/agents/roots.py) and check that <id>/agent.json "
                "exists in it."
            )
        return agents[0]["id"]

    def list_agents(self) -> list[dict]:
        """Every agent across every registered root (see registry)."""
        return list_agents()

    def get_agent(self, agent_id: str) -> dict | None:
        """Metadata for one agent id, or None when it is not registered."""
        return get_agent_meta(agent_id)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        bridge = getattr(self.bridge, "expose", lambda: None)()
        return (
            f"<AgentInterface model={self.model!r} "
            f"bridge={json.dumps(bridge or {}, default=str) or 'local disk'}>"
        )


__all__ = ["AgentInterface", "DEFAULT_HISTORY_LIMIT"]
```

---

<!-- ==== 32/85 : headless_app/run.py ==== -->

### headless_app/run.py

```python
"""
run.py
======

Command-line entry point for the headless agentCreator engine.

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
        print("No agents found. Register an agent root and check its agent.json files.")
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
    result = runner.run_pipeline(message, agent_configs=steps, model=args.model)
    _print_run(result, args)
    if result.get("outputs"):
        print("\nPIPELINE STEPS")
        for step in result["outputs"]:
            print(f"- {step['agent_id']}: {step['output'][:100]!r}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Headless agentCreator engine runner.",
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

<!-- ==== 33/85 : headless_app/tools/__init__.py ==== -->

### headless_app/tools/__init__.py

```python
(empty file — 0 bytes)
```

---

<!-- ==== 34/85 : headless_app/tools/chatlog.py ==== -->

### headless_app/tools/chatlog.py

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

<!-- ==== 35/85 : headless_app/tools/project_tools.py ==== -->

### headless_app/tools/project_tools.py

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

File tools run against one of three backends, selected per agent (or, for the
standalone CLI, once per process via configure()):

    * a Project Manager bridge (HTTP)          - the Project Manager server
                                                  is the filesystem authority
    * a "direct" Project Manager provider      - in-process filesystem authority
                                                  (used when mounted inside PM)
    * the local disk (default, no provider)    - bare local filesystem

The provider is a small object with a stable surface:

    workspace_root (str)          .relpath(path) -> posix relative (or raises)
    .list_tree() -> nested tree   .read(rel) -> str     .write(rel, content)
    .create(rel, content)         .delete(rel)          .exists(rel) -> bool

Which provider a tool call uses is resolved by current_provider(): the binding
installed for that specific call (tools.registry.resolve_tools) wins over the
process default, so agents running side by side never share filesystem state.

The FileSession (tools/state.py) is per agent, created at build time.
"""

import os
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# DATA STORE (chat memory + tool log)
# ---------------------------------------------------------------------------

from tools.chatlog import search_text as _search_chatlog  # noqa: E402

# ---------------------------------------------------------------------------
# PROVIDER SELECTION
# ---------------------------------------------------------------------------

#: Process-wide default provider (None = operate on the local disk). This is
#: only the fallback for callers that do not bind a provider of their own;
#: per-agent binding goes through the ``_bound_provider`` context variable so
#: two agents can never fight over one module global.
_io: Any = None

#: Provider bound for the duration of a single tool call (see
#: tools.registry.resolve_tools). A ContextVar keeps the binding scoped to
#: the running thread/task, so concurrent agents stay independent.
_bound_provider: ContextVar = ContextVar("tool_provider", default=None)


def configure(provider: Any) -> None:
    """Set the process-wide default provider (None for local disk).

    The provider decides where files live AND how paths are translated. Both
    the HTTP bridge (bridge.client) and the in-process filesystem authority
    (bridge.providers.DirectProjectIO) implement the same surface.

    Prefer per-agent binding (tools.registry.resolve_tools(ids, provider)):
    this global remains for backwards compatibility and for the standalone
    headless CLI.
    """
    global _io
    _io = provider


def current_provider() -> Any:
    """The provider in force right now: the per-call binding, else the default."""
    bound = _bound_provider.get()
    return _io if bound is None else bound


@contextmanager
def using(provider: Any):
    """Activate ``provider`` for the duration of the block."""
    token = _bound_provider.set(provider)
    try:
        yield provider
    finally:
        _bound_provider.reset(token)


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
    io = current_provider()

    if io is not None:
        # Project Manager is the filesystem authority. Plain text is read
        # through the provider; binary documents are converted locally when
        # the file is reachable on this machine, otherwise the provider's
        # own answer (or error) is returned.
        try:
            rel = io.relpath(raw)
        except Exception as exc:
            return {"success": False, "tool": "read_file", "data": {}, "error": str(exc)}

        if _is_plain_text(rel):
            try:
                content = io.read(rel)
                return {
                    "success": True,
                    "tool": "read_file",
                    "data": {
                        "path": str(Path(io.workspace_root) / rel),
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
        local = Path(io.workspace_root) / rel
        if local.is_file():
            try:
                return _read_local_file(local, ocr)
            except Exception as exc:
                pass
        try:
            content = io.read(rel)
            return {
                "success": True,
                "tool": "read_file",
                "data": {
                    "path": str(Path(io.workspace_root) / rel),
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
    io = current_provider()

    if io is not None:
        try:
            base = io.relpath(raw)
        except Exception as exc:
            return {"success": False, "tool": "map_files", "data": {}, "error": str(exc)}
        try:
            flat = _flatten_tree(io.list_tree())
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
                "path": str(Path(io.workspace_root) / rel),
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

    io = current_provider()

    if io is not None:
        try:
            rel_dir = io.relpath(_unquote_path(output_path)).strip("/")
        except Exception as exc:
            return {"success": False, "tool": "write_text_file", "data": {}, "error": str(exc)}
        rel_file = f"{rel_dir}/{_unquote_path(name)}" if rel_dir else f"{_unquote_path(name)}"
        try:
            if overwrite:
                io.write(rel_file, content)
            else:
                io.create(rel_file, content)
        except Exception as exc:
            return {"success": False, "tool": "write_text_file", "data": {}, "error": str(exc)}
        absolute = str(Path(io.workspace_root) / rel_file)
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

    io = current_provider()
    results = {}
    for f_path in file_list:
        try:
            if io is not None:
                rel = io.relpath(f_path)
                if io.exists(rel):
                    io.delete(rel)
                    results[f_path] = "deleted" if not io.exists(rel) else "failed_to_verify"
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

<!-- ==== 36/85 : headless_app/tools/registry.py ==== -->

### headless_app/tools/registry.py

```python
"""
tools/registry.py
=================

Central tool registry. Maps tool IDs (strings used in agent.json) to Python
callables. Agents declare which tools they need by ID; the factory resolves
those IDs here into actual functions.

All tool implementations live in tools/project_tools.py; their docstrings are
the schema the LLM sees. This module only wires them to their public IDs.

Binding, not configuration
--------------------------
``resolve_tools(ids, provider)`` returns tools that carry their own filesystem
provider. The provider is activated for the duration of each call (see
``tools.project_tools.using``), so two agents built with different providers -
for example one running inside the Project Manager and one on the local disk -
never overwrite each other's state. A ContextVar makes that binding local to
the running thread/task.

``configure(provider)`` still sets a process-wide default, but it is only a
fallback for callers that do not bind a provider (the standalone CLI, and
``bridge/tools_adapter.py``). The factory does not use it.

Adding a new tool:
    1. Write the function in tools/project_tools.py (with a clear docstring)
    2. Import it below and add it to _TOOL_REGISTRY with its string ID
"""

from typing import Any, Callable

from tools.project_tools import (
    configure as _configure_provider,
    map_files,
    read_file,
    write_text_file,
    delete_files,
    get_current_date,
    tell_me_the_date_and_time,
    search_chat_logs,
    using as _using_provider,
)
from tools.state import FileSession

# ---------------------------------------------------------------------------
# Canonical registry  ->  tool_id -> callable
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


# ---------------------------------------------------------------------------
# Provider binding
# ---------------------------------------------------------------------------

def _bind(func: Callable, provider: Any) -> Callable:
    """Return ``func`` with ``provider`` active for the duration of each call.

    The wrapper is transparent to the LLM: name, docstring, signature and
    annotations are copied from the real tool, so the schema Ollama builds is
    byte-for-byte the same as for an unbound tool.
    """
    import functools
    import inspect as _inspect

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _using_provider(provider):
            return func(*args, **kwargs)

    wrapper.__signature__ = _inspect.signature(func)
    wrapper.__annotations__ = func.__annotations__
    wrapper.__bound_provider__ = provider
    return wrapper


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure(provider=None) -> None:
    """Set the process-wide default provider (or None for local disk).

    Only a fallback: tools resolved with an explicit provider ignore it.
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


def resolve_tools(tool_ids: list[str], provider: Any = None) -> list[Callable]:
    """Map a list of tool ID strings to their callable functions.

    Args:
        tool_ids:  IDs as written in agent.json.
        provider:  filesystem provider bound to every returned tool. None
                   means "use the process default".

    Unknown IDs are silently skipped (with a warning) so that agent
    definitions can reference tools that may not be installed.
    """
    resolved = []
    for tid in tool_ids:
        fn = _TOOL_REGISTRY.get(tid)
        if fn is not None:
            resolved.append(_bind(fn, provider) if provider is not None else fn)
        else:
            print(f"[registry] WARNING: tool '{tid}' not found - skipped.")
    return resolved


def new_session() -> FileSession:
    """Create a FileSession owned by exactly one agent.

    Sessions hold discovered files, read paths, outputs and pending deletions.
    They are per agent so the delete-approval gate cannot be satisfied by a
    different agent's proposal.
    """
    return FileSession()


#: Process-wide default session, kept for callers that predate per-agent
#: sessions (and for the CLI's single-agent runs). The factory never uses it.
_session = FileSession()


def get_session() -> FileSession:
    """Return the shared default FileSession instance."""
    return _session
```

---

<!-- ==== 37/85 : headless_app/tools/state.py ==== -->

### headless_app/tools/state.py

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

<!-- ==== 38/85 : project_manager/.gitattributes ==== -->

### project_manager/.gitattributes

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

<!-- ==== 39/85 : project_manager/.gitignore ==== -->

### project_manager/.gitignore

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

<!-- ==== 40/85 : project_manager/interface/clients/__init__.py ==== -->

### project_manager/interface/clients/__init__.py

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

<!-- ==== 41/85 : project_manager/interface/clients/editor_client.py ==== -->

### project_manager/interface/clients/editor_client.py

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

<!-- ==== 42/85 : project_manager/interface/core/__init__.py ==== -->

### project_manager/interface/core/__init__.py

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

<!-- ==== 43/85 : project_manager/interface/core/defaults.py ==== -->

### project_manager/interface/core/defaults.py

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

<!-- ==== 44/85 : project_manager/interface/core/events.py ==== -->

### project_manager/interface/core/events.py

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

<!-- ==== 45/85 : project_manager/interface/core/operations.py ==== -->

### project_manager/interface/core/operations.py

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

<!-- ==== 46/85 : project_manager/interface/core/session.py ==== -->

### project_manager/interface/core/session.py

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

<!-- ==== 47/85 : project_manager/interface/routers/__init__.py ==== -->

### project_manager/interface/routers/__init__.py

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

<!-- ==== 48/85 : project_manager/interface/routers/agents.py ==== -->

### project_manager/interface/routers/agents.py

```python
"""
interface/routers/agents.py
===========================

Agent registry, run, and pipeline endpoints for the Project Manager.

Every agent is built and run through ``interface_runner.AgentInterface``,
the same seam the headless CLI uses, so behaviour cannot drift between
frontends. Discovery likewise has a single source of truth: the engine's
agent roots (``engine/agents/roots.py``). The Project Manager registers
``<workspace>/agents/`` as a root at startup, so an agent created in the
workspace behaves exactly like a bundled library agent.

    GET  /api/agents
        -> every agent across every registered root (library +
           workspace), highest-precedence root first.

    GET  /api/agents/{agent_id}
        -> {"source", "meta", "sections"} for one agent, resolved through
           the loader, so the editor can open/read its definition.

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

from engine.agents.loader import AgentNotFoundError  # noqa: E402
from engine.agents.registry import list_agents  # noqa: E402
from engine.pipeline import load_pipeline  # noqa: E402

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
    """Safe absolute path for an agent file path.

    Workspace-relative paths ("agents/demo/agent.json") are the documented
    input. An absolute path is also accepted, but only when it really is
    inside the workspace, so a queue saved from a previous session cannot
    reach outside the project.
    """
    filesystem = _pm_filesystem()
    if filesystem is None:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            return candidate
        raise ValueError(
            "Running outside the Project Manager - a workspace-relative "
            "path cannot be resolved."
        )
    if Path(relative_path).is_absolute():
        resolved = Path(relative_path).resolve()
        try:
            resolved.relative_to(Path(filesystem.PROJECT_ROOT).resolve())
        except ValueError:
            raise ValueError(
                "Access outside the project directory is not allowed."
            )
        return resolved
    return filesystem.resolve_project_path(relative_path)


def _provider() -> Any:
    if DirectProjectIO is None:
        raise RuntimeError(
            "DirectProjectIO is unavailable - the agent router must run "
            "inside the Project Manager package."
        )
    return DirectProjectIO()


def _api_path(path: str | None) -> str | None:
    """Translate an engine path into a workspace-relative API path.

    The engine reports absolute paths (its own truth), but the API contract is
    workspace-relative ("agents/<name>/agent.md") because that is what the
    frontend stores in the pipeline queue and sends back to the run endpoints.
    Returns None for anything outside the workspace (a library agent).
    """
    if not path:
        return None
    workspace = _workspace()
    if workspace is None:
        return None
    try:
        rel = Path(path).resolve().relative_to(Path(workspace).resolve())
    except (ValueError, OSError):
        return None
    return rel.as_posix()


def _agent_payload(summary: dict) -> dict:
    """Shape one registry summary for /api/agents.

    json_path/md_path are present only for workspace agents, matching the
    contract the pipeline queue and editor already depend on.
    """
    payload = {
        "id": summary["id"],
        "name": summary["name"],
        "description": summary["description"],
        "mode": summary["mode"],
        "model": summary["model"],
        "tools": summary["tools"],
        "source": summary["source"],
        "complete": summary["complete"],
    }
    json_path = _api_path(summary.get("json_path"))
    if json_path is not None:
        payload["json_path"] = json_path
        payload["md_path"] = _api_path(summary.get("md_path"))
    return payload


_runner_cache: Any = None


def _runner() -> Any:
    """The shared AgentInterface, the single engine entry point.

    Stateless between requests: each run builds a fresh agent bound to its
    own tools and session, so concurrent agents cannot interfere.
    """
    global _runner_cache
    if _runner_cache is None:
        from interface_runner import AgentInterface  # noqa: E402

        _runner_cache = AgentInterface(
            bridge=_provider(),
            log_sink=_mirror_pm_log,
        )
    return _runner_cache


# ============================================================
# CHAT LOG RECORDING
# ============================================================

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
    Return every runnable agent, from every registered agent root.

    Discovery is the engine's single source of truth
    (engine/agents/registry.py), so the library and workspace agents
    arrive through one code path. Workspace agents include
    json_path/md_path so the frontend can run or open them directly.
    """

    try:

        return {
            "agents": [_agent_payload(a) for a in list_agents()],
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
    Return one agent's metadata + markdown sections.

    Resolution goes through the loader, so a workspace agent wins over
    a library agent with the same id - the same precedence discovery
    and ``build_agent`` use.
    """

    from engine.agents.loader import (
        agent_json_path,
        agent_md_path,
        load_definition,
    )
    from engine.agents.roots import find_agent

    try:

        definition = load_definition(agent_id)

        found = find_agent(agent_id)
        source = found[0].source if found is not None else "library"

        payload = {
            "source": source,
            "meta": definition["meta"],
            "sections": definition["sections"],
        }

        json_path = _api_path(agent_json_path(agent_id))
        if json_path is not None:
            payload["json_path"] = json_path
            payload["md_path"] = _api_path(agent_md_path(agent_id))

        return payload

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
        agent_id:  agent id (any registered root) to run when json_path is
                   not given.
        model:     optional model override.
    """

    message = _validated_message(payload.message)

    try:

        # Workspace-relative paths must become absolute (and stay inside
        # the workspace) before the engine reads them.
        json_file = _resolve(str(payload.json_path)) if payload.json_path else None
        md_file = _resolve(str(payload.md_path)) if payload.md_path else None

        result = _runner().run_single_agent(
            message,
            json_path=str(json_file) if json_file else None,
            md_path=str(md_file) if md_file else None,
            agent_id=payload.agent_id or None,
            model=payload.model,
        )

        entries = result.get("entries") or []

        return {
            "status": "ok",
            "reply": result["reply"],
            "agent_id": result["agent_id"],
            "name": result.get("name", ""),
            "description": result.get("description", ""),
            "model": result.get("model"),
            "tool_events": result.get("tool_events") or [],
            "entry": entries[0] if entries else None,
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
            "candidates": [_agent_payload(a) for a in list_agents()],
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

        result = _runner().run_pipeline(
            message,
            agent_configs=normalized,
            model=payload.model,
        )

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

<!-- ==== 49/85 : project_manager/interface/routers/chat.py ==== -->

### project_manager/interface/routers/chat.py

```python
"""
bridge/routers/chat.py
======================

Agent-backed Project Manager chat router (drop-in replacement).

The Project Manager keeps a stub chat surface: ``POST /api/chat`` logs a
message and ``GET /api/chat`` fetches history. This router swaps the stub
handler for the agentCreator engine, so the Project Manager becomes a fully
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

    DELETE /api/chat  ?agent=
        -> wipe the log, or one agent's thread.

Saved sessions are point-in-time copies of one agent's thread, stored
under workspace/data/chat_sessions/<agent_id>/<session_id>.json:

    GET    /api/chat/sessions?agent=          list sessions, newest first
    POST   /api/chat/sessions                 copy the live thread into one
    GET    /api/chat/sessions/{id}?agent=     reopen a session
    DELETE /api/chat/sessions/{id}?agent=     delete a session
    GET    /api/chat/sessions/{id}/export     download as .md or .json

In-process file tools run through DirectProjectIO, so the Project Manager's
parameters.filesystem stays the single filesystem authority.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response
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


class SessionSave(BaseModel):

    agent_id: str

    title: str | None = None


# ============================================================
# CHAT LOG HELPERS
# ============================================================

MAX_MESSAGE_LENGTH = 2000

DEFAULT_LIMIT = 50

MAX_LIMIT = 500

_provider_cache: Any = None
_runner_cache: Any = None


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


def _runner() -> Any:
    """The shared AgentInterface, the single engine entry point.

    Holds no conversation state: every run builds a fresh agent and
    replays that agent's own log history, so requests stay independent.
    """
    global _runner_cache
    if _runner_cache is None:
        from interface_runner import AgentInterface  # noqa: E402

        _runner_cache = AgentInterface(
            bridge=_provider(),
            log_sink=_mirror_pm_log,
        )
    return _runner_cache


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

    The agent is resolved by id across every registered root, and this
    agent's recent turns are replayed into the model, so the conversation
    continues instead of restarting on every request.
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
                "No agents are registered. Register an agent root and check "
                "that its agent.json files exist."
            )
        )

    try:

        result = _runner().run_chat(
            message,
            agent_id=agent_id,
            model=payload.model,
        )

        entries = result.get("entries") or []

        return {
            "status": "ok",
            "reply": result["reply"],
            "agent_id": result.get("agent_id", agent_id),
            "name": result.get("name", ""),
            "model": result.get("model"),
            "tool_events": result.get("tool_events") or [],
            "entry": entries[0] if entries else None,
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


# ============================================================
# SAVED CHAT SESSIONS
# ============================================================
#
# A session is a point-in-time copy of one agent's thread, so a
# conversation can be kept, reopened, copied out or deleted without
# touching the live chat log. Sessions live under the Project
# Manager's own workspace and are therefore visible in the editor
# tree (workspace -> data -> chat_sessions) and excluded from git
# by the existing workspace/data/ ignore rule.
#
#     workspace/data/chat_sessions/<agent_id>/<session_id>.json

SESSIONS_DIRNAME = "data/chat_sessions"

SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")

MAX_TITLE_LENGTH = 80

EXPORT_FORMATS = ("md", "json")


def _sessions_root() -> Path:
    """Absolute path of the sessions directory inside the workspace."""
    from parameters import filesystem

    return filesystem.resolve_project_path(SESSIONS_DIRNAME)


def _safe_id(value: str, kind: str) -> str:
    """
    Validate an id used as a single path segment.

    Agent and session ids both become directory or file names, so
    anything that could climb out of the sessions directory is
    refused rather than sanitized.
    """

    if not value or not SAFE_ID.match(value):
        raise ValueError(
            f"Invalid {kind}: {value!r}. Use letters, numbers, "
            "underscore or dash only."
        )

    return value


def _new_session_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{datetime.now(timezone.utc).microsecond % 1000:03d}"


def _derive_title(entries: list[dict]) -> str:
    """Title from the first user turn, else a timestamp."""
    for entry in entries:
        if entry.get("sender") == "user":
            text = " ".join(str(entry.get("message", "")).split())
            if text:
                if len(text) > MAX_TITLE_LENGTH:
                    text = text[: MAX_TITLE_LENGTH - 1].rstrip() + "\u2026"
                return text
    return "Session " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _session_file(session_id: str, agent_id: str) -> Path:
    agent = _safe_id(agent_id, "agent id")
    session = _safe_id(session_id, "session id")
    return _sessions_root() / agent / f"{session}.json"


def _summary(record: dict) -> dict:
    """List-view projection of a stored session."""
    return {
        "id": record.get("id", ""),
        "agent_id": record.get("agent_id", ""),
        "title": record.get("title", ""),
        "created": record.get("created", ""),
        "entry_count": len(record.get("entries", [])),
    }


def _read_session(session_id: str, agent_id: str) -> dict:
    path = _session_file(session_id, agent_id)
    if not path.exists():
        raise FileNotFoundError(f"No saved session {session_id!r}.")
    return json.loads(path.read_text(encoding="utf-8"))


def _sole_owner(session_id: str) -> str:
    """The agent that owns a session id, when the id is unique.

    Session ids embed a timestamp, so two agents saving in the same
    millisecond could collide. Callers pass the agent explicitly in
    that case; this helper only resolves the unambiguous case.
    """
    _safe_id(session_id, "session id")
    root = _sessions_root()
    owners = [
        path.parent.name
        for path in root.glob(f"*/{session_id}.json")
    ] if root.is_dir() else []
    if not owners:
        raise FileNotFoundError(f"No saved session {session_id!r}.")
    if len(owners) > 1:
        raise ValueError(
            f"Session {session_id!r} exists for several agents "
            f"({', '.join(sorted(owners))}). Pass the agent explicitly."
        )
    return owners[0]


def _list_sessions(agent_id: str | None) -> list[dict]:
    """Every stored session, newest first.

    With ``agent_id`` set only that agent's sessions are returned,
    which is what the chat panel shows.
    """
    root = _sessions_root()
    if not root.is_dir():
        return []
    wanted = _safe_id(agent_id, "agent id") if agent_id else None
    records: list[dict] = []
    for path in root.glob("*/*.json"):
        if wanted and path.parent.name != wanted:
            continue
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    records.sort(key=lambda r: r.get("created", ""), reverse=True)
    return [_summary(record) for record in records]


def _to_markdown(record: dict) -> str:
    lines = [
        f"# {record.get('title', 'Chat session')}",
        "",
        f"- Agent: {record.get('agent_id', '')}",
        f"- Saved: {record.get('created', '')}",
        f"- Messages: {len(record.get('entries', []))}",
        "",
    ]
    for entry in record.get("entries", []):
        who = (
            "You"
            if entry.get("sender") == "user"
            else entry.get("agent") or "Agent"
        )
        lines.append(f"## {who} - {entry.get('ts', '')}")
        lines.append("")
        lines.append(str(entry.get("message", "")))
        lines.append("")
    return "\n".join(lines)


@router.get("/api/chat/sessions")
def list_saved_sessions(
    request: Request,
    agent: str | None = None,
):
    """
    List saved chat sessions, newest first.

    Query params:
        agent:
            Only this agent's sessions. Omit to list every agent's.
    """

    try:

        return {
            "sessions": _list_sessions(agent),
        }

    except ValueError as error:

        raise project_manager_error(
            ValueError(
                str(error)
            )
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


@router.post("/api/chat/sessions")
def save_chat_session(
    request: Request,
    payload: SessionSave,
):
    """
    Copy the agent's current thread into a saved session.

    Body:
        agent_id (str):  whose thread to save (required).
        title (str?):    optional; defaults to the first user turn.

    The live chat log is left untouched.
    """

    try:

        entries = read_history(MAX_LIMIT, agent=payload.agent_id)

        if not entries:
            raise project_manager_error(
                ValueError(
                    f"Nothing to save: no chat history for agent "
                    f"{payload.agent_id!r}."
                )
            )

        record = {
            "id": _new_session_id(),
            "agent_id": _safe_id(payload.agent_id, "agent id"),
            "title": (payload.title or "").strip() or _derive_title(entries),
            "created": datetime.now(timezone.utc).isoformat(),
            "entries": entries,
        }

        path = _session_file(record["id"], record["agent_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {
            "status": "ok",
            "session": _summary(record),
        }

    except ValueError as error:

        raise project_manager_error(
            ValueError(
                str(error)
            )
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


@router.get("/api/chat/sessions/{session_id}")
def get_saved_session(
    request: Request,
    session_id: str,
    agent: str | None = None,
):
    """
    Return one saved session, entries included.

    Query params:
        agent:
            Required when the session id is not unique across agents.
    """

    try:

        if not agent:
            agent = _sole_owner(session_id)

        return _read_session(session_id, agent)

    except FileNotFoundError as error:

        raise project_manager_error(
            ValueError(
                str(error)
            )
        )

    except ValueError as error:

        raise project_manager_error(
            ValueError(
                str(error)
            )
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


@router.delete("/api/chat/sessions/{session_id}")
def delete_saved_session(
    request: Request,
    session_id: str,
    agent: str | None = None,
):
    """
    Delete one saved session. The live chat log is unaffected.
    """

    try:

        if not agent:
            agent = _sole_owner(session_id)

        path = _session_file(session_id, agent)
        if not path.exists():
            raise project_manager_error(
                ValueError(
                    f"No saved session {session_id!r}."
                )
            )
        path.unlink()

        return {
            "status": "ok",
            "deleted": session_id,
        }

    except ValueError as error:

        raise project_manager_error(
            ValueError(
                str(error)
            )
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


@router.get("/api/chat/sessions/{session_id}/export")
def export_saved_session(
    request: Request,
    session_id: str,
    agent: str | None = None,
    format: str = "md",
):
    """
    Download a saved session as a file.

    Query params:
        agent:
            Required when the session id is not unique across agents.
        format:
            ``md`` (default) or ``json``. The response carries a
            Content-Disposition attachment header, so the browser
            writes the transcript straight to the user's disk.
    """

    try:

        if format not in EXPORT_FORMATS:
            raise ValueError(
                f"Unsupported export format {format!r}. "
                f"Use one of: {', '.join(EXPORT_FORMATS)}."
            )

        if not agent:
            agent = _sole_owner(session_id)

        record = _read_session(session_id, agent)

        if format == "json":
            body = json.dumps(record, ensure_ascii=False, indent=2)
            media_type = "application/json"
            extension = "json"
        else:
            body = _to_markdown(record)
            media_type = "text/markdown; charset=utf-8"
            extension = "md"

        safe_title = re.sub(
            r"[^A-Za-z0-9_-]+",
            "-",
            record.get("title", "chat-session"),
        ).strip("-") or "chat-session"

        filename = f"{safe_title[:60]}-{session_id}.{extension}"

        return Response(
            content=body,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except FileNotFoundError as error:

        raise project_manager_error(
            ValueError(
                str(error)
            )
        )

    except ValueError as error:

        raise project_manager_error(
            ValueError(
                str(error)
            )
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


if __name__ == "__main__":
    print(__doc__)
```

---

<!-- ==== 50/85 : project_manager/interface/routers/directories.py ==== -->

### project_manager/interface/routers/directories.py

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

<!-- ==== 51/85 : project_manager/interface/routers/errors.py ==== -->

### project_manager/interface/routers/errors.py

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

<!-- ==== 52/85 : project_manager/interface/routers/files.py ==== -->

### project_manager/interface/routers/files.py

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

<!-- ==== 53/85 : project_manager/interface/routers/paths.py ==== -->

### project_manager/interface/routers/paths.py

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

<!-- ==== 54/85 : project_manager/interface/routers/project.py ==== -->

### project_manager/interface/routers/project.py

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

<!-- ==== 55/85 : project_manager/interface/routers/ws.py ==== -->

### project_manager/interface/routers/ws.py

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

<!-- ==== 56/85 : project_manager/interface/static/Agentpromptbuilder.html ==== -->

### project_manager/interface/static/Agentpromptbuilder.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Prompt Builder</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#101318;color:#e8edf2}
header{padding:18px 24px;background:#181d24;border-bottom:1px solid #303741}
h1{margin:0 0 5px;font-size:22px}
header p{margin:0;color:#9ca8b5}
main{max-width:1200px;margin:0 auto;padding:20px;display:grid;grid-template-columns:1fr 1fr;gap:20px}
.card{background:#151a20;border:1px solid #303741;border-radius:8px;padding:16px}
.full{grid-column:1 / -1}
h2{margin:0 0 12px;font-size:16px;color:#dfe6ee;border-bottom:1px solid #303741;padding-bottom:8px}
label{display:block;margin:10px 0 6px;font-size:13px;color:#aeb9c5}
.microlabel{display:block;margin:14px 0 5px;font-size:12px;color:#8fa0b3;letter-spacing:.04em}
.catrow{display:flex;align-items:center;gap:8px;margin-top:6px}
.catrow select,.catrow input{flex:1;min-width:0}
.catrow button{flex-shrink:0}
.catrow[hidden]{display:none}
input,textarea,select{width:100%;background:#0d1116;color:#edf2f7;border:1px solid #39424d;border-radius:6px;padding:9px;font-family:inherit}
textarea{min-height:110px;resize:vertical}
#master_prompt{min-height:320px;font-family:Consolas,Menlo,monospace;font-size:13px}
button{border:0;border-radius:6px;padding:10px 14px;cursor:pointer;background:#4c8bf5;color:white;font-size:14px}
button.secondary{background:#303944}
button.danger{background:#7a2f3c}
button.tiny{padding:3px 9px;font-size:12px}
button:disabled{opacity:.45;cursor:not-allowed}
button:hover:not(:disabled){opacity:.92}
.row{display:flex;gap:8px;margin-top:14px}
.row button{flex:1}
.parts-group{margin-bottom:14px}
.parts-group h3{margin:0 0 6px;font-size:13px;color:#8fa0b3;text-transform:uppercase;letter-spacing:.04em;display:flex;align-items:center;gap:8px}
.parts-group h3 .count{color:#5c6774;text-transform:none;letter-spacing:0}
.part-row{display:flex;align-items:center;gap:8px;padding:5px 0;font-size:14px}
.part-row input[type=checkbox]{width:auto}
.part-row .name{margin:0;flex:1;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.part-row .actions{display:flex;gap:6px;flex-shrink:0}
.empty{color:#5c6774;font-size:13px;font-style:italic}
.empty code{font-style:normal;background:#0d1116;padding:2px 6px;border-radius:5px;border:1px solid #39424d}
.status{margin-top:14px;padding:10px;border-radius:6px;background:#1a2129;color:#aeb9c5;font-size:13px;white-space:pre-wrap}
.status.error{color:#ff9b9b}
.status.ok{color:#8fe3a6}
.status.warn{color:#f5c96b}
.folderbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:13px;color:#aeb9c5}
.folderbar code{background:#0d1116;padding:3px 7px;border-radius:5px;border:1px solid #39424d}
.folderbar button{margin-left:auto}
.headrow{display:flex;align-items:center;gap:10px;margin-bottom:4px}
.headrow h2{margin:0;flex:1}
.parts-group h3 .lockbadge{background:#4a2530;color:#ff9b9b;border:1px solid #6b3341;padding:1px 7px;border-radius:9px;font-size:11px;letter-spacing:.02em;cursor:help}
@media(max-width:900px){main{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
<h1>Agent Prompt Builder</h1>
<p>Create reusable prompt parts in categories you can add or remove, select them, and assemble an editable agent.md — written straight into the managed workspace.</p>
</header>

<main>

<div class="card full">
<h2>Parts Folder</h2>
<div class="folderbar">
<span>Parts:</span>
<code id="parts_folder_label">…</code>
<button id="refresh_parts_btn" class="secondary tiny" type="button" disabled title="Re-read the parts folder. Also clears any folder marked as locked after a failed write.">Refresh Parts</button>
</div>
<div id="storage_status" class="status">Connecting to the Project Manager…</div>
</div>

<div class="card">
<h2 id="form_title">Create Prompt Part</h2>

<label>Category</label>
<div class="catrow">
<select id="part_category"></select>
<button id="new_category_btn" class="secondary tiny" type="button" disabled title="Add a category of your own. It becomes a new folder under prompt_parts.">+ Category</button>
<button id="delete_category_btn" class="secondary tiny danger" type="button" disabled title="Delete the selected category and every part inside it.">Delete</button>
</div>

<div class="catrow" id="new_category_row" hidden>
<input id="new_category_name" placeholder="new category name (e.g. memory)" maxlength="40" autocomplete="off">
<button id="create_category_btn" class="secondary tiny" type="button" disabled>Create</button>
</div>
<div class="microlabel">the category list is stored in <code id="categories_file_label">categories.json</code> and is read on every refresh</div>

<label>Name</label>
<input id="part_name" placeholder="e.g. planner">

<label>Text</label>
<textarea id="part_text" placeholder="You are a planning agent..."></textarea>

<div class="row">
<button id="save_part_btn" type="button" disabled>Save Part</button>
<button id="clear_form_btn" class="secondary" type="button" disabled>Clear</button>
</div>

<div id="part_status" class="status">Waiting for the Project Manager…</div>
</div>

<div class="card">
<div class="headrow">
<h2>Available Parts</h2>
<button id="new_part_btn" class="secondary tiny" type="button" disabled>+ New Part</button>
</div>
<div id="parts_list"><div class="empty">Loading parts…</div></div>

<div class="row">
<button id="create_master_btn" type="button" disabled>Create Master Prompt</button>
</div>
</div>

<div class="card full">
<h2>Master Prompt</h2>

<label>Agent ID (folder name for saving)</label>
<input id="agent_id" value="new_agent" style="max-width:320px">

<label>Markdown (editable before saving)</label>
<textarea id="master_prompt" placeholder="Select parts and click 'Create Master Prompt'."></textarea>

<div class="row">
<button id="save_agent_btn" type="button" disabled>Save to documentation</button>
<button id="publish_btn" type="button" disabled>Publish for testing</button>
</div>

<div id="master_status" class="status">Ready.</div>
</div>

</main>

<script type="module">
import API from '/static/js/api.js';

// ============================================================
// CONFIG - the storage locations are fixed, not user-selected.
// ============================================================

/* Every path is browser-root-qualified (workspace/...), which is what
   the file API resolves back to a root. The workspace root is the only
   writable one, so the builder can only ever write inside it - it can
   no longer be pointed at an arbitrary folder on the user's disk. */

const DOC_ROOT = 'workspace/documentation/PromptBuilderFiles';
const PARTS_DIR = DOC_ROOT + '/prompt_parts';
const DOC_OUTPUT_DIR = DOC_ROOT + '/output/agents';
const AGENTS_DIR = 'workspace/agents';

/* The category list is data, not code. It lives in this file next to the
   parts folders so it can be added to and subtracted from in the browser
   - and hand-edited - without touching this script. Array order is the
   order the dropdown, the parts list and the master prompt sections use,
   so there is no separate sort key to keep in sync. It sits outside
   prompt_parts/ so that folder holds nothing but category folders. */
const CATEGORIES_FILE = DOC_ROOT + '/categories.json';
const CATEGORIES_VERSION = 1;

const PART_FILE = '.txt';

/* The starting catalogue, written on the first run only. It is also the
   title lookup: a category typed as "hallucinations" gets the readable
   title from here rather than the id with a capital letter. */
const SEED_CATEGORIES = [
  { id: "role", title: "Role" },
  { id: "rules", title: "Rules" },
  { id: "hallucinations", title: "Hallucination Rules" },
  { id: "tools", title: "Tools" },
  { id: "skills", title: "Skills" },
  { id: "input", title: "Input" },
  { id: "reasoning", title: "Reasoning" },
  { id: "logic", title: "Logic" }
];

// ============================================================
// STATE
// ============================================================

let categories = [];           // [{id, title}] from the manifest, in order
let partIndex = {};            // {category: [{name, path}]}
let textCache = new Map();     // part path -> text
let selected = new Set();      // "category/name" keys that are checked
let lockedCategories = new Set(); // categories that refused a write
let editingCategory = null;    // category the part open in the form belongs to
let workspaceRoot = "";        // absolute, from /api/health
let projectRoot = "";          // the parent of workspaceRoot
let ready = false;             // the parts folder answered at least once
let assembled = null;          // selection signature of the last build

/* The two buttons the panel and the form can reach, so their disabled
   state is always derived from one place. */
const BUTTONS = ["save_part_btn","clear_form_btn","create_master_btn",
                  "save_agent_btn","publish_btn","refresh_parts_btn",
                  "new_part_btn","new_category_btn","create_category_btn",
                  "delete_category_btn"];

function $(id){ return document.getElementById(id); }

function setStatus(id, message, kind){
  const el = $(id);
  el.textContent = message;
  el.className = "status" + (kind ? " " + kind : "");
}

function setReady(value){
  ready = value;
  for (const id of BUTTONS){
    $(id).disabled = !value;
  }
}

/* Buttons stay disabled for the duration of an operation so a double
   click cannot fire two writes at the same file. */
function setBusy(busy){
  if (busy && !ready) return;
  for (const id of BUTTONS){
    $(id).disabled = busy ? true : !ready;
  }
}

function partKey(category, name){ return category + "/" + name; }

function categoryPath(id){
  return PARTS_DIR + "/" + id;
}

function partPath(category, name){
  return categoryPath(category) + "/" + name + PART_FILE;
}

function relativePath(path){
  return path.startsWith(DOC_ROOT + "/")
    ? path.slice(DOC_ROOT.length + 1)
    : path;
}

function safeSlug(value){
  value = (value || "").trim().toLowerCase();
  value = value.replace(/[^a-z0-9_-]+/g, "_");
  value = value.replace(/_+/g, "_").replace(/^_|_$/g, "");
  if (!value) throw new Error("Name cannot be empty.");
  return value;
}

/* A category added in the browser has no entry in the seed, so its id is
   the title unless it is one of the seeded ones. */
function titleFor(id){
  const seeded = SEED_CATEGORIES.find(cat => cat.id === id);
  if (seeded) return seeded.title;
  return id.replace(/[_-]+/g, " ")
           .replace(/\b\w/g, c => c.toUpperCase());
}

/* agent.json needs a human label; derive one from the id rather than
   adding a field the builder would then have to keep in sync. */
function displayName(id){
  return id.replace(/[_-]+/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

// ============================================================
// ERRORS - a raw Python errno is not an explanation
// ============================================================

/* The API reports the absolute server path, so a failure reads as
   "Permission denied: 'E:\agentCreator\project_manager\workspace\...'"
   - a path the user cannot click and does not recognise. Both roots are
   learned once so the same failure can be shown relative. Best effort:
   if the lookup fails the original text is still shown. */
function learnWorkspaceRoot(){
  if (typeof API.health !== "function") return Promise.resolve();
  return API.health()
    .then((data) => {
      workspaceRoot = (data && data.root) || "";
      projectRoot = workspaceRoot
        ? workspaceRoot.replace(/[\\/][^\\/]+[\\/]?$/, "")
        : "";
    })
    .catch(() => {
      workspaceRoot = "";
      projectRoot = "";
    });
}

function isPermissionError(error){
  const message = (error && error.message) || String(error);
  return /permission denied|access is denied|errno 13|winerror 5/i
    .test(message);
}

/* Python quotes the offending path: "... denied: 'C:\\...'". */
function extractFailedPath(message){
  const quoted = String(message).match(/'([^']+)'/);
  return quoted ? quoted[1] : "";
}

function shortenPath(value){
  let out = String(value || "");
  for (const root of [workspaceRoot, projectRoot]){
    if (!root) continue;
    out = out.split(root).join("");
  }
  return out.replace(/^[\\/]+/, "").replace(/\\/g, "/");
}

/* The remedy is the same for every refused write on the same volume, so
   it is named from the drive rather than hard-coded. Pass lowercase to
   embed it inside a sentence. */
function repairHint(lowercase){
  const drive = projectRoot.match(/^([A-Za-z]:)/);
  const target = drive ? drive[1] : "the drive";
  const text = "Repair the drive in an Administrator prompt: chkdsk "
    + target + " /f";
  return lowercase
    ? text.charAt(0).toLowerCase() + text.slice(1)
    : text;
}

function firstUnlockedCategory(){
  const free = categories.find(cat => !lockedCategories.has(cat.id));
  return free ? free.id : null;
}

/* A locked category is disabled in the dropdown rather than hidden, so
   it stays visible that it exists and is why it cannot be used. */
function syncCategoryDropdown(){
  const sel = $("part_category");
  if (!sel) return;
  for (const opt of sel.options){
    opt.disabled = lockedCategories.has(opt.value);
  }
  if (lockedCategories.has(sel.value)){
    const free = firstUnlockedCategory();
    if (free) sel.value = free;
  }
}

function markCategoryLocked(category){
  if (!category) return;
  lockedCategories.add(category);
  syncCategoryDropdown();
  renderParts();
}

/* Turns a thrown error into a sentence the user can act on, and records
   a refused folder so the panel stops offering it. */
function prettyError(error, category){
  const raw = (error && error.message) || String(error);

  if (isPermissionError(error)){
    if (category) markCategoryLocked(category);
    const where = shortenPath(
      extractFailedPath(raw) || "that folder"
    );
    return "Cannot write " + where
      + " - Windows reports \"access denied\". Nothing was saved."
      + " That folder is read-only or damaged: use another category, or "
      + repairHint(true) + ". Then press 'Refresh Parts'.";
  }

  return "Error: " + shortenPath(raw);
}

// ============================================================
// TREE LOOKUP - the /api/project tree is the listing source
// ============================================================

function findNode(items, path){
  for (const item of items || []){
    if (item.path === path) return item;
    if (item.children){
      const hit = findNode(item.children, path);
      if (hit) return hit;
    }
  }
  return null;
}

function childDir(node, name){
  for (const child of (node && node.children) || []){
    if (child.type === "directory" && child.name === name) return child;
  }
  return null;
}

// ============================================================
// FOLDER
// ============================================================

/* Only the parts root is created up front. Category folders appear on
   demand: every file write creates its parent directories, so seeding
   eight empty folders would just be eight pointless API calls - and a
   category with no parts does not need a folder to exist. */
async function ensureStructure(){
  await API.directoryCreate(PARTS_DIR);
  $("parts_folder_label").textContent = relativePath(PARTS_DIR);
  $("categories_file_label").textContent = relativePath(CATEGORIES_FILE);
}

// ============================================================
// CATEGORIES - the manifest is the list
// ============================================================

/* One entry per category, in the order everything else uses. A bad entry
   is dropped and a repeated id keeps its first position, because the
   manifest is a plain text file a person is allowed to edit. */
function normalizeCategories(raw){
  const list = Array.isArray(raw && raw.categories) ? raw.categories : [];
  const seen = new Set();
  const out = [];
  for (const item of list){
    if (!item || typeof item.id !== "string") continue;
    const id = item.id.trim().toLowerCase();
    if (!id || seen.has(id)) continue;
    const title = (typeof item.title === "string" && item.title.trim())
      || titleFor(id);
    seen.add(id);
    out.push({ id, title });
  }
  return out;
}

function manifestText(list){
  return JSON.stringify(
    { version: CATEGORIES_VERSION, categories: list }, null, 2
  ) + "\n";
}

/* Absent means "never set up", so the seed catalogue is written. Present
   but unreadable is an error and is never overwritten: a hand-edit with
   a typo in it has to survive until it is fixed. */
async function readCategories(){
  let text = null;

  try {
    text = (await API.fileRead(CATEGORIES_FILE)).content;
  } catch (error) {
    if (error.status !== 404) throw error;
  }

  if (text === null){
    const seeded = normalizeCategories({ categories: SEED_CATEGORIES });
    await API.fileWrite(CATEGORIES_FILE, manifestText(seeded));
    return seeded;
  }

  try {
    return normalizeCategories(JSON.parse(text));
  } catch (error) {
    throw new Error(relativePath(CATEGORIES_FILE)
      + " is not valid JSON (" + error.message + ")."
      + " Fix it in the editor - it has not been changed.");
  }
}

/* Every change goes through here, and the in-memory list is rebuilt from
   the same normalizer the file is written from, so what the page shows
   is always exactly what is on disk. */
async function writeCategories(list){
  const payload = normalizeCategories({ categories: list });
  await API.fileWrite(CATEGORIES_FILE, manifestText(payload));
  categories = payload;
  return payload;
}

// ============================================================
// PARTS
// ============================================================

function populateCategoryDropdown(){
  const sel = $("part_category");
  const previous = sel.value;
  sel.innerHTML = "";

  /* With every category deleted there is nothing to save a part into, and
     a blank dropdown would read as a bug rather than as that state. */
  if (!categories.length){
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "(no categories - create one)";
    sel.appendChild(none);
  }

  for (const cat of categories){
    const opt = document.createElement("option");
    opt.value = cat.id;
    opt.textContent = cat.title;
    sel.appendChild(opt);
  }

  /* A category that was just deleted is no longer an option, so the old
     value would quietly become the first one instead. */
  if (categories.some(cat => cat.id === previous)){
    sel.value = previous;
  }

  syncCategoryDropdown();
}

async function readPart(path){
  if (textCache.has(path)) return textCache.get(path);
  const data = await API.fileRead(path);
  const text = data.content || "";
  textCache.set(path, text);
  return text;
}

/* Selection is state, not DOM: the list is rebuilt from the tree on
   every refresh, so checked boxes are re-applied from `selected`
   instead of being inherited from the markup that just got replaced. */
async function refreshParts(){
  const data = await API.project();
  const partsNode = findNode(data.filesystem, PARTS_DIR);

  partIndex = {};
  for (const cat of categories){
    const catNode = childDir(partsNode, cat.id);
    const entries = [];
    for (const child of (catNode && catNode.children) || []){
      if (child.type !== "file") continue;
      if (!child.name.endsWith(PART_FILE)) continue;
      entries.push({ name: child.name.slice(0, -PART_FILE.length), path: child.path });
    }
    entries.sort((a, b) => a.name.localeCompare(b.name));
    partIndex[cat.id] = entries;
  }

  /* Drop selections whose part no longer exists, so a later build can
     never reference a file that was deleted or renamed. A category that
     was removed takes its checked parts with it. */
  const live = new Set();
  for (const cat of categories){
    for (const entry of partIndex[cat.id]) live.add(partKey(cat.id, entry.name));
  }
  const dropped = [];
  for (const key of Array.from(selected)){
    if (!live.has(key)){ selected.delete(key); dropped.push(key); }
  }

  renderParts();
  return { total: live.size, dropped };
}

function isChecked(category, name){
  return selected.has(partKey(category, name));
}

function setChecked(category, name, value){
  const key = partKey(category, name);
  if (value) selected.add(key); else selected.delete(key);
}

function markAssembledStale(){
  if (assembled === null) return;
  if (assembled === selectionSignature()) return;
  setStatus("master_status",
    "The selected parts changed. Click 'Create Master Prompt' to rebuild before saving.", "warn");
}

function selectionSignature(){
  return Array.from(selected).sort().join("|");
}

function renderParts(){
  const box = $("parts_list");
  box.innerHTML = "";

  let total = 0;

  for (const cat of categories){
    const id = cat.id;
    const entries = partIndex[id] || [];
    const locked = lockedCategories.has(id);
    total += entries.length;

    const group = document.createElement("div");
    group.className = "parts-group";

    const heading = document.createElement("h3");
    heading.appendChild(document.createTextNode(cat.title));
    heading.title = relativePath(categoryPath(id));

    const count = document.createElement("span");
    count.className = "count";
    count.textContent = "(" + entries.length + ")";
    heading.appendChild(count);

    /* The category is listed but cannot be used, so the panel says so
       instead of showing an empty list as if nothing had ever been
       written there. */
    if (locked){
      const badge = document.createElement("span");
      badge.className = "lockbadge";
      badge.textContent = "locked";
      badge.title = "This folder refused a write, so its parts cannot be"
        + " listed or saved. " + repairHint() + ", then press 'Refresh Parts'.";
      heading.appendChild(badge);
    }

    if (entries.length){
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "secondary tiny";
      toggle.textContent = "all / none";
      toggle.addEventListener("click", () => toggleCategory(id));
      heading.appendChild(toggle);
    }

    group.appendChild(heading);

    if (entries.length === 0){
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = locked
        ? "Folder is not writable right now."
        : "No parts yet.";
      group.appendChild(empty);
    }

    for (const entry of entries){
      group.appendChild(buildPartRow(id, entry));
    }

    box.appendChild(group);
  }

  if (total === 0){
    const hint = document.createElement("div");
    hint.className = "empty";
    hint.innerHTML =
      "No parts in the folder yet. Use \"+ New Part\" above, or add a"
      + " <code>.txt</code> file to <code>"
      + relativePath(PARTS_DIR) + "/&lt;category&gt;/</code> in the editor."
      + " A new category is a new folder there, so the editor works"
      + " without this page too.";
    box.appendChild(hint);
  }
}

function buildPartRow(category, entry){
  const row = document.createElement("div");
  row.className = "part-row";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = "part_" + category + "_" + entry.name;
  checkbox.checked = isChecked(category, entry.name);
  checkbox.addEventListener("change", () => {
    setChecked(category, entry.name, checkbox.checked);
    markAssembledStale();
  });

  const label = document.createElement("label");
  label.className = "name";
  label.htmlFor = checkbox.id;
  label.textContent = entry.name;
  label.title = entry.path;

  const actions = document.createElement("div");
  actions.className = "actions";

  const editBtn = document.createElement("button");
  editBtn.type = "button";
  editBtn.className = "secondary tiny";
  editBtn.textContent = "Edit";
  editBtn.addEventListener("click", () => editPart(category, entry));

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "secondary tiny";
  deleteBtn.textContent = "Delete";
  deleteBtn.addEventListener("click", () => deletePart(category, entry));

  actions.appendChild(editBtn);
  actions.appendChild(deleteBtn);
  row.appendChild(checkbox);
  row.appendChild(label);
  row.appendChild(actions);
  return row;
}

function toggleCategory(category){
  const entries = partIndex[category] || [];
  const allChecked = entries.length > 0
    && entries.every(entry => isChecked(category, entry.name));
  for (const entry of entries){
    setChecked(category, entry.name, !allChecked);
  }
  renderParts();
  markAssembledStale();
}

/* Clearing the fields and reporting "Ready" are separate: a successful
   save clears the form but must keep its own confirmation visible. */
function clearFormFields(){
  $("part_name").value = "";
  $("part_text").value = "";
  $("form_title").textContent = "Create Prompt Part";
  editingCategory = null;
}

function resetForm(){
  clearFormFields();
  setStatus("part_status", "Ready.");
}

function editPart(category, entry){
  setBusy(true);
  readPart(entry.path)
    .then((text) => {
      $("part_category").value = category;
      $("part_name").value = entry.name;
      $("part_text").value = text.replace(/\s+$/, "");
      $("form_title").textContent = "Edit Prompt Part";
      /* Remembered so deleting this category can say the open part goes
         with it, and so a cleared form is not mistaken for a live edit. */
      editingCategory = category;
      setStatus("part_status",
        "Editing " + relativePath(entry.path) + ". Save Part to update it.", "ok");
      $("part_text").focus();
    })
    .catch(error => setStatus("part_status", prettyError(error, category), "error"))
    .finally(() => setBusy(false));
}

function deletePart(category, entry){
  if (!confirm("Delete " + relativePath(entry.path) + "?")) return;
  setBusy(true);
  API.fileDelete(entry.path)
    .then(() => {
      textCache.delete(entry.path);
      selected.delete(partKey(category, entry.name));
      return refreshParts();
    })
    .then(({ total, dropped }) => {
      setStatus("part_status",
        "Deleted " + relativePath(entry.path) + ". " + total + " part(s) left."
        + droppedNote(dropped), "ok");
      markAssembledStale();
    })
    .catch(error => setStatus("part_status", prettyError(error, category), "error"))
    .finally(() => setBusy(false));
}

function droppedNote(dropped){
  if (!dropped.length) return "";
  return " Cleared " + dropped.length + " stale selection(s): " + dropped.join(", ") + ".";
}

// ============================================================
// CATEGORY ACTIONS
// ============================================================

/* The name field is hidden until it is asked for, so the form keeps one
   category selector instead of two near-identical text boxes. */
function toggleNewCategoryRow(open){
  const row = $("new_category_row");
  const show = open === undefined ? row.hidden : open;
  row.hidden = !show;
  $("new_category_btn").textContent = show ? "Cancel" : "+ Category";
  if (show) $("new_category_name").focus();
  else $("new_category_name").value = "";
}

/* Adding a category is a manifest write and nothing else: the folder is
   still created by the first part saved into it, which is the same
   "on demand" rule every other part follows. */
async function addCategory(){
  let id = "";
  try {
    id = safeSlug($("new_category_name").value);
  } catch (error) {
    setStatus("part_status", "Category " + error.message, "error");
    return;
  }

  if (categories.some(cat => cat.id === id)){
    setStatus("part_status",
      "The category '" + id + "' already exists.", "error");
    return;
  }

  setBusy(true);
  try {
    const title = titleFor(id);
    await writeCategories(categories.concat({ id, title }));
    toggleNewCategoryRow(false);
    populateCategoryDropdown();
    $("part_category").value = id;
    renderParts();
    setStatus("part_status", "Added category " + title + " -> "
      + relativePath(categoryPath(id))
      + ". Its folder appears with the first part saved into it.", "ok");
  } catch (error) {
    setStatus("part_status", prettyError(error), "error");
  } finally {
    setBusy(false);
  }
}

/* Everything the deleted folder was referenced by, so no path is left
   pointing at a folder that is gone. */
function forgetCategory(id){
  const prefix = categoryPath(id) + "/";
  for (const path of Array.from(textCache.keys())){
    if (path.startsWith(prefix)) textCache.delete(path);
  }
  for (const key of Array.from(selected)){
    if (key.startsWith(id + "/")) selected.delete(key);
  }
  lockedCategories.delete(id);
}

async function deleteCategory(){
  const id = $("part_category").value;
  const entry = categories.find(cat => cat.id === id);

  if (!entry){
    setStatus("part_status", "There is no category to delete.", "error");
    return;
  }

  const parts = partIndex[id] || [];
  const editing = editingCategory === id;

  /* One confirm says what is destroyed: the folder, every part in it,
     and an open part that otherwise would look like it survived. */
  let message = "Delete the category " + entry.title + " ("
    + relativePath(categoryPath(id)) + ")?";
  message += parts.length
    ? "\n\nThis permanently deletes " + parts.length + " part(s): "
      + parts.map(part => part.name).join(", ") + "."
    : "\n\nIt holds no parts.";
  if (editing){
    message += "\n\nThe part open in the form is one of them.";
  }
  if (!confirm(message)) return;

  setBusy(true);
  try {
    /* The folder goes first. A refused recursive delete then leaves the
       manifest untouched, so the list still matches the disk and the
       delete can simply be tried again - the other order would hide a
       category whose parts are already gone. A category that never had a
       part saved into it has no folder to remove, and a stale tree must
       not be able to skip a folder that does exist, so the answer to
       "is it there" comes from the delete itself. */
    try {
      await API.directoryDelete(categoryPath(id));
    } catch (error) {
      if (error.status !== 404) throw error;
    }
    forgetCategory(id);
    await writeCategories(categories.filter(cat => cat.id !== id));
    populateCategoryDropdown();

    const { total, dropped } = await refreshParts();
    if (editing) resetForm();
    setStatus("part_status", "Deleted category " + entry.title + ". "
      + total + " part(s) left." + droppedNote(dropped), "ok");
    markAssembledStale();
  } catch (error) {
    setStatus("part_status", prettyError(error, id), "error");
  } finally {
    setBusy(false);
  }
}

/* The create button in the panel header hands off to the form rather
   than duplicating it: two editors for one file is how the two drift
   apart. The category is moved off a locked folder first, because the
   first option is otherwise a folder that may refuse the write. */
function startNewPart(){
  if (!categories.length){
    setStatus("part_status",
      "There are no categories yet - use \"+ Category\" to add one first.", "warn");
    return;
  }
  const sel = $("part_category");
  if (lockedCategories.has(sel.value)){
    const free = firstUnlockedCategory();
    if (free) sel.value = free;
  }
  clearFormFields();
  const title = $("form_title");
  if (title && typeof title.scrollIntoView === "function"){
    title.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  $("part_name").focus();
  setStatus("part_status", "Fill in the form to create a new part.", "");
}

async function savePart(){
  const category = $("part_category").value;

  if (!category){
    setStatus("part_status",
      "There are no categories yet - use \"+ Category\" to add one first.", "error");
    return;
  }

  /* Refused up front: a locked folder already answered, so sending the
     write again would only repeat the same error. */
  if (lockedCategories.has(category)){
    setStatus("part_status",
      "Cannot save into " + titleFor(category) + " - that folder refused an"
      + " earlier write. " + repairHint() + ", then press 'Refresh Parts'.",
      "error");
    return;
  }

  setBusy(true);
  try {
    const name = safeSlug($("part_name").value);
    const text = $("part_text").value.trim();
    if (!text) throw new Error("Part text cannot be empty.");

    const path = partPath(category, name);
    /* fileWrite creates or overwrites, so saving an edited part and
       saving a new one are the same call. */
    await API.fileWrite(path, text + "\n");
    textCache.set(path, text + "\n");

    const { total } = await refreshParts();
    setStatus("part_status", "Saved: " + relativePath(path) + ". " + total + " part(s) total.", "ok");
    clearFormFields();
  } catch (error) {
    setStatus("part_status", prettyError(error, category), "error");
  } finally {
    setBusy(false);
  }
}

// ============================================================
// MASTER PROMPT
// ============================================================

function collectSelections(){
  const selections = {};
  for (const cat of categories){
    const names = (partIndex[cat.id] || [])
      .filter(entry => isChecked(cat.id, entry.name))
      .map(entry => entry.name);
    if (names.length) selections[cat.id] = names;
  }
  return selections;
}

async function buildMasterPrompt(){
  const selections = collectSelections();

  if (!Object.keys(selections).length){
    setStatus("master_status", "No parts are selected.", "warn");
    return;
  }

  setBusy(true);
  const missing = [];
  try {
    const lines = ["# Agent Prompt", ""];

    for (const cat of categories){
      const names = selections[cat.id] || [];
      const texts = [];
      for (const name of names){
        const path = partPath(cat.id, name);
        let text = "";
        try {
          text = (await readPart(path)).trim();
        } catch (error) {
          missing.push(partKey(cat.id, name));
          continue;
        }
        if (text) texts.push(text);
      }
      if (texts.length){
        lines.push("## " + cat.title);
        lines.push("");
        lines.push(texts.join("\n\n"));
        lines.push("");
      }
    }

    $("master_prompt").value = lines.join("\n").trim() + "\n";
    assembled = selectionSignature();

    const count = Object.values(selections).reduce((sum, list) => sum + list.length, 0);
    setStatus("master_status",
      "Assembled " + count + " part(s). Edit the markdown if needed, then save."
      + (missing.length ? " Skipped unreadable: " + missing.join(", ") + "." : ""),
      missing.length ? "warn" : "ok");
  } catch (error) {
    setStatus("master_status", "Error: " + error.message, "error");
  } finally {
    setBusy(false);
  }
}

function requireMarkdown(){
  const markdown = $("master_prompt").value.trim();
  if (!markdown) throw new Error("The master prompt is empty - nothing to save.");
  return markdown;
}

async function saveToDocumentation(){
  setBusy(true);
  try {
    const id = safeSlug($("agent_id").value);
    const markdown = requireMarkdown();
    const path = DOC_OUTPUT_DIR + "/" + id + "/agent.md";
    await API.fileWrite(path, markdown + "\n");
    setStatus("master_status", "Saved: " + relativePath(path), "ok");
  } catch (error) {
    setStatus("master_status", prettyError(error), "error");
  } finally {
    setBusy(false);
  }
}

/* "Publish for testing" makes the prompt a real agent: the engine only
   lists folders that hold BOTH agent.json and agent.md
   (engine/agents/registry.py), so the metadata file is created here.
   An existing agent.json is left alone so hand-edited settings - and
   any tests stored in it - are never overwritten. */
async function publishForTesting(){
  setBusy(true);
  try {
    const id = safeSlug($("agent_id").value);
    const markdown = requireMarkdown();
    const dir = AGENTS_DIR + "/" + id;

    await API.fileWrite(dir + "/agent.md", markdown + "\n");

    let metaCreated = false;
    try {
      await API.fileRead(dir + "/agent.json");
    } catch {
      const meta = {
        id,
        name: displayName(id),
        description: "",
        mode: "chat",
        model: "",
        tools: []
      };
      await API.fileCreate(dir + "/agent.json", JSON.stringify(meta, null, 2) + "\n");
      metaCreated = true;
    }

    setStatus("master_status",
      "Published: " + dir + "/agent.md"
      + (metaCreated ? " + agent.json (new)" : " (agent.json kept)")
      + ".\nReload Home to see the agent; pick it on Chat to run it.", "ok");
  } catch (error) {
    setStatus("master_status", prettyError(error), "error");
  } finally {
    setBusy(false);
  }
}

// ============================================================
// INIT
// ============================================================

async function reloadParts(){
  setBusy(true);
  try {
    /* A lock only records that a write was refused, not that the folder
       is still broken, so the explicit refresh drops them and lets a
       repaired folder be used again without reloading the page. */
    lockedCategories.clear();
    syncCategoryDropdown();

    /* Read before the tree: the parts are listed per category, so the
       list has to be known first. A categories.json edited in the
       editor therefore takes effect on 'Refresh Parts'. */
    categories = await readCategories();
    populateCategoryDropdown();

    const { total, dropped } = await refreshParts();
    setStatus("storage_status",
      "Parts folder: " + relativePath(PARTS_DIR) + " - " + total + " part(s)."
      + droppedNote(dropped), "ok");
    setReady(true);
  } catch (error) {
    setReady(false);
    setStatus("storage_status", prettyError(error), "error");
  } finally {
    setBusy(false);
  }
}

function init(){
  $("save_part_btn").addEventListener("click", savePart);
  $("clear_form_btn").addEventListener("click", resetForm);
  $("new_part_btn").addEventListener("click", startNewPart);
  $("new_category_btn").addEventListener("click", () => toggleNewCategoryRow());
  $("create_category_btn").addEventListener("click", addCategory);
  $("delete_category_btn").addEventListener("click", deleteCategory);
  $("new_category_name").addEventListener("keydown", (event) => {
    if (event.key === "Enter") addCategory();
  });
  $("create_master_btn").addEventListener("click", buildMasterPrompt);
  $("save_agent_btn").addEventListener("click", saveToDocumentation);
  $("publish_btn").addEventListener("click", publishForTesting);
  $("refresh_parts_btn").addEventListener("click", reloadParts);

  /* The dropdown is not built here: it is a view of the manifest, and the
     manifest is read by the first reload. Every button is disabled until
     then, so the empty dropdown is never something a user can act on. */
  learnWorkspaceRoot()
    .then(() => ensureStructure())
    .then(() => reloadParts())
    .catch(error => {
      setReady(false);
      setStatus("storage_status", prettyError(error), "error");
      setStatus("part_status", "The parts folder is unavailable.", "error");
    });
}

init();
</script>
</body>
</html>
```

---

<!-- ==== 57/85 : project_manager/interface/static/chat.html ==== -->

### project_manager/interface/static/chat.html

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

        .msg.ai, .msg.system {
            align-items: flex-start;
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
            gap: 8px;
            cursor: pointer;
            transition: background 0.15s;
        }

        .saved-chat-item:hover {
            background: var(--bg-card-hover);
        }

        .saved-chat-actions {
            display: flex;
            align-items: center;
            gap: 4px;
            flex-shrink: 0;
        }

        .btn-row-action {
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            width: 26px;
            height: 26px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s ease;
            text-decoration: none;
        }

        .btn-row-action:hover {
            background: var(--bg-card-hover);
            color: var(--text-primary);
            border-color: var(--border-color);
        }

        .saved-chat-empty {
            font-size: 11px;
            color: var(--text-muted);
            line-height: 1.5;
            padding: 10px 12px;
            background: var(--bg-card);
            border: 1px dashed var(--border-subtle);
            border-radius: var(--radius-md);
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
                        <button class="btn-save-current" onclick="saveCurrentChat()" title="Save the current thread as a named session">
                            <i data-lucide="bookmark" style="width:12px;"></i> Save Session
                        </button>
                    </div>

                    <div class="saved-chats-list" id="savedChatsList"></div>
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

        // Copying lives in chat.js (copyText), which owns the transcript
        // and the saved-session rows.

        // Placeholder Action Handlers
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

        // Textarea Auto-growth and Keyboard handling
        const chatInput = document.getElementById("chatInput");
        const chatForm = document.getElementById("chatForm");

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
        /* Sending lives entirely in chat.js, which owns the real
           /api/chat round trip and the transcript. Nothing is bound
           here: a second listener would echo the message locally and
           answer with a simulated reply. Enter is handled above by
           dispatching the same submit event. */

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

<!-- ==== 58/85 : project_manager/interface/static/editor.html ==== -->

### project_manager/interface/static/editor.html

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

<!-- ==== 59/85 : project_manager/interface/static/home.html ==== -->

### project_manager/interface/static/home.html

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

<!-- ==== 60/85 : project_manager/interface/static/index.html ==== -->

### project_manager/interface/static/index.html

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

<!-- ==== 61/85 : project_manager/interface/static/js/agentCards.js ==== -->

### project_manager/interface/static/js/agentCards.js

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

<!-- ==== 62/85 : project_manager/interface/static/js/agentColors.js ==== -->

### project_manager/interface/static/js/agentColors.js

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

<!-- ==== 63/85 : project_manager/interface/static/js/agents.js ==== -->

### project_manager/interface/static/js/agents.js

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

<!-- ==== 64/85 : project_manager/interface/static/js/api.js ==== -->

### project_manager/interface/static/js/api.js

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
      const error = new Error(detail || `Request failed: ${res.status}`);
      /* The status rides along on the error so a caller can tell
         "not there yet" (404) from "refused" (403/500) without having
         to match on the message text. */
      error.status = res.status;
      throw error;
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

  /* ---- Saved chat sessions ----
     A session is a stored copy of one agent's thread. Sessions are
     per agent, so the agent is sent with every call. */

  chatSessions(agent = null) {
    const query = agent ? `?agent=${encodeURIComponent(agent)}` : '';
    return this.request('GET', `/api/chat/sessions${query}`);
  },

  chatSessionSave(agent, title = null) {
    return this.request('POST', '/api/chat/sessions', { agent_id: agent, title });
  },

  chatSession(id, agent = null) {
    const query = agent ? `?agent=${encodeURIComponent(agent)}` : '';
    return this.request('GET', `/api/chat/sessions/${encodeURIComponent(id)}${query}`);
  },

  chatSessionDelete(id, agent = null) {
    const query = agent ? `?agent=${encodeURIComponent(agent)}` : '';
    return this.request('DELETE', `/api/chat/sessions/${encodeURIComponent(id)}${query}`);
  },

  /* Built as a URL rather than fetched: the endpoint answers with a
     Content-Disposition attachment, and a plain link hands the file
     to the browser's download handling (i.e. the user's disk). */
  chatSessionExportUrl(id, agent = null, format = 'md') {
    const params = new URLSearchParams({ format });
    if (agent) params.set('agent', agent);
    return `/api/chat/sessions/${encodeURIComponent(id)}/export?${params.toString()}`;
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

<!-- ==== 65/85 : project_manager/interface/static/js/chat.js ==== -->

### project_manager/interface/static/js/chat.js

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
const savedChatsList = document.getElementById('savedChatsList');

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
  /* Every real message gets a copy button; the handler is the global
     copyMsg() in chat.html, shared with the saved-session rows. */
  const actions = document.createElement('span');
  actions.className = 'msg-actions';
  const copyBtn = document.createElement('button');
  copyBtn.type = 'button';
  copyBtn.className = 'btn-msg-action';
  copyBtn.title = 'Copy this message';
  copyBtn.innerHTML = '<i data-lucide="copy" style="width:13px;"></i> Copy';
  copyBtn.addEventListener('click', () => copyText(body.textContent, 'Message copied to clipboard'));
  actions.appendChild(copyBtn);
  line.appendChild(actions);
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
  if (window.lucide) window.lucide.createIcons();
}

/* Clipboard write with a textarea fallback, because the async
   clipboard API is unavailable on http:// origins. */
function copyText(text, message) {
  const area = document.createElement('textarea');
  area.value = text;
  document.body.appendChild(area);
  area.select();
  try {
    document.execCommand('copy');
    showToast(message);
  } catch (e) {
    showToast('Copy failed - select the text manually');
  } finally {
    document.body.removeChild(area);
  }
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
    /* Each agent has its own thread and its own saved sessions, so
       swap both. */
    await loadHistory();
    await renderSavedChats();
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
  .then(() => {
    loadHistory();
    renderSavedChats();
  })
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

/* ================================================================
   SAVED CHAT SESSIONS
   ================================================================
   A session is a stored copy of one agent's thread, kept on the
   server under workspace/data/chat_sessions/<agent_id>/. Each row
   can be reopened, copied to the clipboard, downloaded to disk or
   deleted. The live thread is never modified by any of this. */

function sessionText(record) {
  const lines = [
    `# ${record.title || 'Chat session'}`,
    '',
    `Agent: ${record.agent_id}`,
    `Saved: ${record.created || ''}`,
    ''
  ];
  for (const entry of record.entries || []) {
    const who = entry.sender === 'user' ? 'You' : (entry.agent || 'Agent');
    const ts = entry.ts ? new Date(entry.ts).toLocaleString() : '';
    lines.push(`## ${who}${ts ? ' - ' + ts : ''}`, '', entry.message || '', '');
  }
  return lines.join('\n');
}

function sessionStamp(created) {
  if (!created) return '';
  const when = new Date(created);
  if (isNaN(when.getTime())) return created;
  return when.toLocaleString();
}

function rowAction(icon, title, handler) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'btn-row-action';
  btn.title = title;
  btn.setAttribute('aria-label', title);
  btn.innerHTML = `<i data-lucide="${icon}" style="width:13px;"></i>`;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    handler();
  });
  return btn;
}

function sessionRow(session) {
  const agentId = activeAgentId();
  const item = document.createElement('div');
  item.className = 'saved-chat-item';
  item.title = 'Open this saved session';

  const info = document.createElement('div');
  info.className = 'saved-chat-info';
  const title = document.createElement('div');
  title.className = 'saved-chat-title';
  title.textContent = session.title || session.id;
  const meta = document.createElement('div');
  meta.className = 'saved-chat-date';
  const count = session.entry_count === 1 ? '1 message' : `${session.entry_count} messages`;
  meta.textContent = `${count} · ${sessionStamp(session.created)}`;
  info.appendChild(title);
  info.appendChild(meta);

  const actions = document.createElement('div');
  actions.className = 'saved-chat-actions';

  actions.appendChild(rowAction('message-square', 'Open in chat', () => {
    openSavedSession(session.id, agentId);
  }));

  actions.appendChild(rowAction('copy', 'Copy transcript', () => {
    copySavedSession(session.id, agentId);
  }));

  /* An anchor, not a button: the endpoint answers with a
     Content-Disposition attachment, so a plain link hands the file
     to the browser's own download handling and can also be
     right-clicked into "Save as". */
  const download = document.createElement('a');
  download.className = 'btn-row-action';
  download.href = API.chatSessionExportUrl(session.id, agentId, 'md');
  download.download = '';
  download.title = 'Download to disk (.md)';
  download.setAttribute('aria-label', 'Download to disk');
  download.innerHTML = '<i data-lucide="download" style="width:13px;"></i>';
  download.addEventListener('click', (e) => e.stopPropagation());
  actions.appendChild(download);

  const jsonDownload = document.createElement('a');
  jsonDownload.className = 'btn-row-action';
  jsonDownload.href = API.chatSessionExportUrl(session.id, agentId, 'json');
  jsonDownload.download = '';
  jsonDownload.title = 'Download raw data (.json)';
  jsonDownload.setAttribute('aria-label', 'Download raw data');
  jsonDownload.innerHTML = '<i data-lucide="braces" style="width:13px;"></i>';
  jsonDownload.addEventListener('click', (e) => e.stopPropagation());
  actions.appendChild(jsonDownload);

  actions.appendChild(rowAction('trash-2', 'Delete this saved session', () => {
    deleteSavedSession(session, agentId);
  }));

  item.appendChild(info);
  item.appendChild(actions);
  item.addEventListener('click', () => openSavedSession(session.id, agentId));
  return item;
}

function emptySessionRow(text) {
  const item = document.createElement('div');
  item.className = 'saved-chat-empty';
  item.textContent = text;
  return item;
}

async function renderSavedChats() {
  if (!savedChatsList) return;
  const agentId = activeAgentId();
  savedChatsList.innerHTML = '';
  if (!agentId) {
    savedChatsList.appendChild(emptySessionRow('Select an agent to see its saved sessions.'));
    return;
  }
  try {
    const data = await API.chatSessions(agentId);
    const sessions = data.sessions || [];
    if (!sessions.length) {
      savedChatsList.appendChild(
        emptySessionRow(`No saved sessions for ${agentLabel(agentId)} yet. Use Save Session to keep a copy of this thread.`)
      );
      return;
    }
    for (const session of sessions) {
      savedChatsList.appendChild(sessionRow(session));
    }
    if (window.lucide) window.lucide.createIcons();
  } catch (e) {
    savedChatsList.appendChild(emptySessionRow('Could not load saved sessions: ' + e.message));
  }
}

async function saveCurrentChat() {
  const agentId = activeAgentId();
  if (!agentId) {
    showToast('Select an agent first');
    return;
  }
  const suggested = (log.textContent || '').trim().split('\n').pop();
  const title = prompt(
    `Save the current ${agentLabel(agentId)} thread as a named session:`,
    suggested ? suggested.slice(0, 60) : ''
  );
  if (title === null) return;
  try {
    const res = await API.chatSessionSave(agentId, title.trim() || null);
    await renderSavedChats();
    const saved = res.session || {};
    showToast(`Saved "${saved.title || saved.id}" (${saved.entry_count || 0} messages)`);
  } catch (e) {
    alert('Failed to save the session: ' + e.message);
  }
}

function showSession(record) {
  log.innerHTML = '';
  const entries = record.entries || [];
  if (!entries.length) {
    appendLine('system', 'This saved session has no messages.');
    return;
  }
  for (const entry of entries) {
    const ts = entry.ts ? new Date(entry.ts).toLocaleTimeString() : '';
    const who = entry.agent ? agentLabel(entry.agent) : null;
    appendLine(entry.sender === 'user' ? 'user' : 'system', entry.message, ts, who);
  }
  setStatus(`Loaded saved session: ${record.title || record.id}`);
}

async function openSavedSession(sessionId, agentId) {
  try {
    const record = await API.chatSession(sessionId, agentId);
    showSession(record);
    showToast(`Loaded "${record.title || sessionId}"`);
  } catch (e) {
    alert('Failed to open the session: ' + e.message);
  }
}

async function copySavedSession(sessionId, agentId) {
  try {
    const record = await API.chatSession(sessionId, agentId);
    copyText(sessionText(record), 'Session copied to clipboard');
  } catch (e) {
    alert('Failed to copy the session: ' + e.message);
  }
}

async function deleteSavedSession(session, agentId) {
  const label = session.title || session.id;
  if (!confirm(`Delete the saved session "${label}"? The live chat history is not affected.`)) return;
  try {
    await API.chatSessionDelete(session.id, agentId);
    await renderSavedChats();
    showToast('Saved session deleted');
  } catch (e) {
    alert('Failed to delete the session: ' + e.message);
  }
}

window.scaffoldNewAgent = scaffoldNewAgent;
window.wipeChat = wipeChat;
window.saveCurrentChat = saveCurrentChat;
```

---

<!-- ==== 66/85 : project_manager/interface/static/js/editor.js ==== -->

### project_manager/interface/static/js/editor.js

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

<!-- ==== 67/85 : project_manager/interface/static/js/main.js ==== -->

### project_manager/interface/static/js/main.js

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

<!-- ==== 68/85 : project_manager/interface/static/js/session.js ==== -->

### project_manager/interface/static/js/session.js

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

<!-- ==== 69/85 : project_manager/interface/static/js/topbar.js ==== -->

### project_manager/interface/static/js/topbar.js

```javascript
/* Shared topbar navigation

   Home / Editor / Chat must sit in the same place on every page, so
   the markup and styling live here instead of being copied into each
   page. Each page marks its header with data-pm-header and calls
   initTopbar({ page }).

   The links are rendered as anchors, not buttons, on purpose: home
   and editor apply a bare `button { ... }` rule and chat.html styles
   `.btn-header`, so anchors sidestep both stylesheets and come out
   pixel-identical on all three pages. An item flagged `popup` is the
   one exception - it has to be a real button to be operable, so
   .pmnav-button undoes the host pages' button styling instead. */

const NAV_ITEMS = [
  { page: 'home', label: 'Home', href: '/' },
  { page: 'editor', label: 'Editor', href: '/editor' },
  { page: 'chat', label: 'Chat', href: '/chat' },
  {
    page: 'prompt-builder',
    label: 'Prompt Builder',
    href: '/prompt-builder',
    popup: { name: 'PMPromptBuilder', width: 1100, height: 760 }
  }
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

/* A popup item has to be a <button> to be clickable, which means it
   inherits whatever bare button rule the host page applies. These
   declarations put it back in line with the anchors. */

.pmnav-link.pmnav-button {
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
  cursor: pointer;
}
`;

/* Tools open in their own centred window. A named target means a
   second click reuses the window instead of stacking duplicates, the
   same way the agent cards open chat. */
function openPopup(url, spec) {
  const left = Math.max(0, (window.screen.width - spec.width) / 2);
  const top = Math.max(0, (window.screen.height - spec.height) / 2);
  const popup = window.open(
    url,
    spec.name,
    `width=${spec.width},height=${spec.height},top=${top},left=${left},` +
    'resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no'
  );
  if (!popup) {
    window.alert('The popup was blocked. Allow popups for this site and try again.');
  }
  return popup;
}

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

    if (item.popup) {
      const trigger = document.createElement('button');
      trigger.type = 'button';
      trigger.className = 'pmnav-link pmnav-button';
      trigger.textContent = item.label;
      trigger.title = 'Opens in a new window';
      trigger.addEventListener('click', () => openPopup(item.href, item.popup));
      nav.appendChild(trigger);
      continue;
    }

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

export { initTopbar, openPopup, NAV_ITEMS };
```

---

<!-- ==== 70/85 : project_manager/interface/static/js/tree.js ==== -->

### project_manager/interface/static/js/tree.js

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

<!-- ==== 71/85 : project_manager/parameters/__init__.py ==== -->

### project_manager/parameters/__init__.py

```python
"""Project parameters package.

Holds the Project Manager filesystem owner (filesystem.py) that owns
the managed workspace, plus the project metadata it manages.
"""
```

---

<!-- ==== 72/85 : project_manager/parameters/filesystem.py ==== -->

### project_manager/parameters/filesystem.py

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

import errno
import json
import os
import shutil
import time
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
    "To Do",
    "updates",
    "config",
    "data",
    "Tests"
]


# ============================================================
# BROWSER ROOTS
# ============================================================

# The two folders the file browser shows. Add a folder here to
# make it appear in the tree; set ``writable`` to False to make it
# browse-only. Keys are the path prefixes the API understands, so
# ``source_files/APP_CODE_SNAPSHOT.md`` and ``workspace/project.json`` resolve
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

    ``source_files/APP_CODE_SNAPSHOT.md`` resolves inside the
    ``source_files`` root. Paths without a known root prefix fall back to
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
            browser-root name (``source_files/APP_CODE_SNAPSHOT.md``),
            which is what lets the API resolve the path back to its root.

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

    Directories are deleted recursively through
    :func:`remove_tree`, which tolerates a tree that is still
    settling instead of leaving it half-deleted.

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

        remove_tree(target)

    else:

        target.unlink()


# ============================================================
# RECURSIVE DELETE
# ============================================================

# Windows reports a directory that is still changing as WinError 5
# (access denied), 32 (file in use) or 145 (directory not empty).
# Those mean "not settled yet", not "you may not do this", so they are
# retried. Anything else is a real refusal and propagates at once.

TRANSIENT_DELETE_WIN_ERRORS = frozenset({5, 32, 145})

TRANSIENT_DELETE_ERRNOS = frozenset({
    errno.ENOTEMPTY,
    errno.EACCES,
    errno.EPERM,
})

#: Attempts before falling back to a manual bottom-up removal.
DELETE_ATTEMPTS = 3

#: Backoff between attempts, in seconds.
DELETE_BACKOFF = 0.05


def is_transient_delete_error(
    error: OSError,
) -> bool:
    """
    Whether a delete failure is worth retrying.

    Args:
        error:
            The failure raised by the delete attempt.

    Returns:
        True when the failure means "the tree has not settled yet".
    """

    win_error = getattr(
        error,
        "winerror",
        None,
    )

    if win_error is not None:

        return (
            win_error
            in TRANSIENT_DELETE_WIN_ERRORS
        )

    return (
        error.errno
        in TRANSIENT_DELETE_ERRNOS
    )


def remove_tree_manual(
    target: Path,
) -> None:
    """
    Remove a directory tree bottom-up.

    The last resort for :func:`remove_tree`: ``shutil.rmtree`` has
    already failed, so every entry is unlinked individually and each
    directory is then removed empty. Entries that vanished on their own
    are ignored, since a retry race means the work is already done.

    Raises:
        OSError:
            If an entry survives.
    """

    for parent, directories, files in os.walk(
        target,
        topdown=False,
    ):

        for name in files:

            child = Path(parent) / name

            try:

                # A read-only attribute is the usual reason unlink is
                # refused, and clearing it is harmless.
                os.chmod(child, 0o666)

            except OSError:
                pass

            try:

                child.unlink()

            except FileNotFoundError:
                pass

        for name in directories:

            try:

                (Path(parent) / name).rmdir()

            except FileNotFoundError:
                pass

    target.rmdir()


def remove_tree(
    target: Path,
) -> None:
    """
    Delete a directory tree, surviving a tree that is still settling.

    A bare ``shutil.rmtree`` is not enough: on a filesystem without
    transactional deletes (exFAT, for instance) it can fail partway
    with "directory not empty" and leave the tree half-deleted, which
    is how a folder ends up listed but permanently inaccessible. So the
    tree is removed with retries first, then bottom-up by hand, and the
    original error is only reported if entries genuinely survive.

    Args:
        target:
            The directory to remove.

    Raises:
        OSError:
            If the tree could not be fully removed.
    """

    last_error: OSError | None = None

    for attempt in range(DELETE_ATTEMPTS):

        try:

            shutil.rmtree(target)
            return

        except FileNotFoundError:
            return

        except OSError as error:

            if not is_transient_delete_error(error):
                raise

            last_error = error

            if attempt + 1 < DELETE_ATTEMPTS:
                time.sleep(
                    DELETE_BACKOFF * (attempt + 1)
                )

    remove_tree_manual(target)

    if target.exists():

        raise last_error


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

<!-- ==== 73/85 : project_manager/README.md ==== -->

### project_manager/README.md

```markdown
# Project Manager

The server half of [agentCreator](../README.md): a FastAPI workspace server
with a Monaco-powered editor, an agent-backed chat page, and the routes that
run single agents and cascade pipelines. It imports `headless_app/` in-process,
so agents run against the managed workspace with no second server.

- **What agentCreator is, and how to run it** — the [root README](../README.md)
- **Every module, class and function in this folder** —
  [`source_files/project_manager_MASTER_COPY.md`](../source_files/project_manager_MASTER_COPY.md)
- **The full HTTP route table and the editor's API surface** — the Overview
  section of that same master copy
- **The verbatim source of this folder** —
  [`source_files/APP_CODE_SNAPSHOT.md`](../source_files/APP_CODE_SNAPSHOT.md)

Start it with `scripts\run.bat` (Windows) or `scripts/run.sh` (Linux) from this
directory. Note that `scripts/setup.sh` does not install the engine's `ollama`
and `pydantic` dependencies, which the server needs to import at all.
```

---

<!-- ==== 74/85 : project_manager/requirements.txt ==== -->

### project_manager/requirements.txt

```text
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
websockets==13.1
```

---

<!-- ==== 75/85 : project_manager/scripts/run.bat ==== -->

### project_manager/scripts/run.bat

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

<!-- ==== 76/85 : project_manager/scripts/run.sh ==== -->

### project_manager/scripts/run.sh

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

<!-- ==== 77/85 : project_manager/scripts/setup.sh ==== -->

### project_manager/scripts/setup.sh

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

<!-- ==== 78/85 : project_manager/server.py ==== -->

### project_manager/server.py

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
import sys
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

#: Standalone tool page, opened in its own window from the topbar.
PROMPT_BUILDER_HTML = STATIC_DIR / "Agentpromptbuilder.html"

#: Name the engine knows this agent root by. Re-registering the same
#: name replaces it and promotes it, so restarting the server is safe.
WORKSPACE_AGENT_ROOT = "workspace"


# ============================================================
# AGENT ROOT REGISTRATION
# ============================================================

def _ensure_headless_on_path() -> bool:
    """Put headless_app/ on sys.path so the engine can be imported."""
    candidate = (PROJECT_ROOT.parent / "headless_app").resolve()
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
    return candidate.is_dir()


def register_workspace_agent_root() -> bool:
    """Teach the agent engine about ``workspace/agents/``.

    Without this the engine only knows its bundled ``agent_library/``,
    so an agent created in the Project Manager shows up in the UI but
    ``build_agent()`` raises AgentNotFoundError and chat replies 400.
    Registration is idempotent.

    Returns:
        True when the root was registered.
    """
    if not _ensure_headless_on_path():
        return False
    from engine.agents.roots import register_agent_root

    agents_dir = Path(filesystem.PROJECT_ROOT) / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    register_agent_root(
        WORKSPACE_AGENT_ROOT,
        agents_dir,
        source="workspace",
    )
    return True


def unregister_workspace_agent_root() -> None:
    """Drop the workspace root again (used on shutdown)."""
    try:
        from engine.agents.roots import unregister_agent_root
    except ImportError:
        return
    unregister_agent_root(WORKSPACE_AGENT_ROOT)


# ============================================================
# APPLICATION FACTORY
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Build the basic project filesystem on startup and register the
    workspace agent root with the agent engine.
    """

    filesystem.build_project_filesystem()

    if register_workspace_agent_root():
        print("[server] registered agent root: workspace/agents/")
    else:
        print("[server] headless_app/ not found - workspace agents unavailable")

    try:
        yield
    finally:
        unregister_workspace_agent_root()


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

    @app.get("/prompt-builder")
    def prompt_builder():
        return FileResponse(PROMPT_BUILDER_HTML)

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

<!-- ==== 79/85 : project_manager/workspace/agents/ProjectManager/agent.json ==== -->

### project_manager/workspace/agents/ProjectManager/agent.json

```json
{
  "id": "project_manager",
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

<!-- ==== 80/85 : project_manager/workspace/agents/ProjectManager/agent.md ==== -->

### project_manager/workspace/agents/ProjectManager/agent.md

```markdown
# Project Manager

## role

You are Project Manager, a helpful agent for planning projects.

## purpose

Describe what this agent accomplishes and when it is used.

## boundaries

State what this agent will not do.

## output format

Describe the shape of the reply the agent must produce.
```

---

<!-- ==== 81/85 : project_manager/workspace/project.json ==== -->

### project_manager/workspace/project.json

```json
{
    "name": "Project Manager",
    "version": "1.0.0",
    "workspace_version": "1.0"
}
```

---

<!-- ==== 82/85 : README.md ==== -->

### README.md

````markdown
# agentCreator

A local lab for building and running AI agents. A FastAPI server hosts a
Monaco-powered code editor, a chat surface, and a pipeline runner; the agent
engine is imported into that same process, so an agent reads and writes your
files with the same authority the dashboard has.

Everything runs on your machine against a local [Ollama](https://ollama.com).
No API keys, no cloud, no build step.

```text
agentCreator/
├── headless_app/     the agent engine: think/act/observe, tools, bridge
├── project_manager/  the server: editor UI, chat, agent + pipeline routes
├── source_files/     generated documentation (see Documentation)
└── scripts/          venv setup + the documentation generator
```

## Quickstart

### Requirements

- **Python 3.10 or newer.** The engine annotates with `str | None` and
  evaluates those annotations at import time.
- **Ollama**, running, with at least one model pulled:
  ```bat
  ollama serve
  ollama pull qwen2.5-coder:latest
  ```

### Windows

```bat
git clone https://github.com/TheChuey/agentCreator.git
cd agentCreator

scripts\venv.bat
project_manager\scripts\run.bat
```

`scripts\venv.bat` creates the virtual environment at the repository root
(`.venv`, shared by both halves) and installs the dependencies. Then open
<http://127.0.0.1:8000>.

### Linux / Chromebook Linux

`project_manager/scripts/setup.sh` does **not** install the engine's
dependencies, so install them yourself after setup — the server will not start
without them:

```sh
git clone https://github.com/TheChuey/agentCreator.git
cd agentCreator

cd project_manager/scripts
./setup.sh
cd ../..

python3 -m venv .venv
.venv/bin/pip install -r project_manager/requirements.txt
.venv/bin/pip install "ollama>=0.3" "pydantic>=2"

project_manager/scripts/run.sh
```

On ChromeOS, enable Linux first, then
`sudo apt install -y python3 python3-venv python3-pip`. Chrome reaches the
container through `127.0.0.1`.

### Running without the server

The engine also runs standalone:

```bat
cd headless_app
..\.venv\Scripts\python.exe run.py list-agents
..\.venv\Scripts\python.exe run.py run-agent rag_assistant --message "what date is it today?"
```

`run.py` also has `refresh-models` and `run-pipeline`, plus `--base-url` to
point the file tools at a running Project Manager, `--no-bridge` to work
straight off local disk, and `-m/--model` to override an agent's own model.

### Dependencies

`project_manager/requirements.txt` pins the server stack (`fastapi`,
`uvicorn`, `httpx`, `websockets`). The engine additionally needs `ollama` and
`pydantic`, which are **not** in that file — `headless_app/engine/core/llm.py`
imports `ollama` at module level, so the server cannot import without it.
`scripts/venv.bat` installs all six; on Linux, install the last two by hand as
shown above.

The editor loads Monaco from cdnjs, so the first page load needs network
access. Everything else is local.

## Using it

Three pages are served: `/` (tree + editor), `/editor`, and `/chat` (agent and
model selectors). The full HTTP contract is in
[the Project Manager master copy](source_files/project_manager_MASTER_COPY.md).

**Two scopes.** *Workspace* is the managed project in
`project_manager/workspace/` and is writable. *Dev* is agentCreator's own
source, so you can read and edit the app that is running you.

**Agents come from two places.** The engine ships a library
(`headless_app/engine/agent_library/`) and the server registers
`workspace/agents/` at startup. Both are searched newest-registration-first, so
a workspace agent shadows a library agent with the same id — there is no
separate "library mode" and "workspace mode".

An agent is a folder with two files, no Python required:

| File | Holds |
| ---- | ----- |
| `agent.json` | `id`, `name`, `description`, `mode`, `model`, `tools` |
| `agent.md` | the prompt: `## role`, `## purpose`, and the sections the prompt builder folds into the system prompt |

`mode: "agent"` attaches the tools in `agent.json`; `mode: "chat"` attaches
none, so no tool loop can occur. Bundled agents:

| Folder | id | Mode | Model |
| ------ | -- | ---- | ----- |
| `rag_assistant` | `rag_assistant` | agent | `gemma4:e2b` |
| `Planner` | `feature_planner_agent` | chat | `qwen2.5-coder:latest` |
| `Enginner` | `execute_engineer_agent` | agent | `qwen2.5-coder:latest` |
| `Builder` | `module_builder_agent` | agent | `qwen2.5-coder:latest` |

Drop a folder into `workspace/agents/` and it appears in the registry on the
next request — no restart, no registration call.

**Tools.** `map_files`, `read_file`, `write_text_file`, `delete_files` (behind
a two-step approval, so an agent must propose a path before it can remove it),
`get_current_date`, `tell_me_the_date_and_time`, and `search_chat_logs`. Each
is a plain function whose docstring is what the model sees, and the file tools
go through one provider so `parameters/filesystem.py` stays the only code that
touches disk.

**Pipelines.** A cascade is an ordered list of agents where each step receives
the original message plus every earlier reply. The default
(`headless_app/config/pipeline.json`) is one idea → working module:
`feature_planner_agent` → `execute_engineer_agent` → `module_builder_agent`.
Runs append to `headless_app/data/pipeline_runs.jsonl`, and the editor sidebar
lets you reorder the queue and watch each step's reply and tool use.

**The loop is bounded.** An agent gets at most 6 tool rounds, and three
order-independent repeats of the same round trip a guard that tells it to stop
calling tools and answer in prose. A blank final reply falls back to a fixed
message rather than returning nothing.

## Configuration

| Variable | Default | Effect |
| -------- | ------- | ------ |
| `PROJECT_MANAGER_HOST` | `127.0.0.1` | Server bind address |
| `PROJECT_MANAGER_PORT` | `8000` | Server port |
| `PROJECT_MANAGER_BASE_URL` | `http://127.0.0.1:8000` | Where the standalone engine sends file operations |

`headless_app/config/models.json` is the model picker; `refresh_models`
rebuilds it from the local Ollama install. Agent models come from each
`agent.json`, and `MAX_NUM_CTX = 32768` in `engine/core/llm.py` bounds context.

Runtime output goes to `headless_app/data/` (chat log, tool log, pipeline
records) and `project_manager/workspace/data/` (the workspace's own chat log
and saved sessions). Both are gitignored and recreated on demand. The empty
`workspace/` content folders are untracked for the same reason.

## Layout requirement

`headless_app/` and `project_manager/` **must be siblings.** The server puts
`<repo>/headless_app` on `sys.path`, and the chat router reaches it by walking
up three parent directories from `interface/routers/`. Move one and the agent
engine silently stops loading.

## Documentation

`source_files/` holds three generated documents, and they answer different
questions — read the map first, then the code:

| Document | Answers | Size |
| -------- | ------- | ---- |
| [`APP_CODE_SNAPSHOT.md`](source_files/APP_CODE_SNAPSHOT.md) | *What does the code say?* Every source file verbatim, one file structure, plus a file index and a boot sequence. No prose about behavior. | ~550 KB |
| [`headless_app_MASTER_COPY.md`](source_files/headless_app_MASTER_COPY.md) | *What does the engine do?* File structure, then every module, class and function with signatures and the first line of each docstring. | ~55 KB |
| [`project_manager_MASTER_COPY.md`](source_files/project_manager_MASTER_COPY.md) | *What does the server do?* The same format for the server half. | ~55 KB |

All three come from one generator, so they cannot drift from the tree or from
each other. After changing any source file:

```bat
.venv\Scripts\python -m scripts.gen_master_copy
```

The generator also reports the project's retired names on stderr if they
reappear anywhere in the tree, so the codebase keeps exactly one name for
itself. It will not embed a document inside another, and it skips
`__pycache__`, virtualenvs, editor caches and runtime output.

`project_manager/README.md` documents the server half on its own; this file is
the map for the whole repository.

## Requirements at a glance

Python 3.10+, a local Ollama with at least one model, and a browser. Windows
and Linux are both supported; the interface is static HTML, CSS and vanilla
JavaScript with no bundler, so there is nothing to compile and nothing to
install in `node_modules`.
````

---

<!-- ==== 83/85 : scripts/gen_master_copy.py ==== -->

### scripts/gen_master_copy.py

````python
"""
gen_master_copy.py
==================

Deterministic documentation generator for this repository.

Writes exactly three documents into ``source_files/``:

    APP_CODE_SNAPSHOT.md            <- the whole repository, verbatim, one place
    headless_app_MASTER_COPY.md     <- headless_app/ structure + module reference
    project_manager_MASTER_COPY.md  <- project_manager/ structure + module reference

The three documents divide the work so that an AI (or a person) can answer any
question about the code, and rebuild it, from the ``source_files/`` folder
alone:

* the **snapshot** is a copy. Every source file, byte for byte, behind one
  file structure. It deliberately says nothing about what the code does.
* the two **master copies** are a map. File structure plus a description of
  every module, class and function, auto-extracted from the live tree. They
  deliberately contain no file bodies.

Run:
    .venv/Scripts/python -m scripts.gen_master_copy
    .venv/Scripts/python -m scripts.gen_master_copy --only headless_app

The prose lives in this file (the PREAMBLE and OVERVIEW sections) so that a
regeneration is fully deterministic: the same tree always produces the same
documents, byte for byte, apart from the date stamp.

Design rules
------------
1. Three documents, no more. ``source_files/`` must contain exactly the
   snapshot and the two master copies.
2. No self-embedding. A document is never embedded in itself or in a
   sibling, so the output cannot nest.
3. Adaptive fences. Each file's fence is one backtick longer than the
   longest run of backticks inside that file, so content containing ``` fences
   (README.md, HTML pages) still renders correctly.
4. Deterministic order. Files are sorted case-insensitively by their
   root-relative path.
5. One name for the app. ``APP_NAME`` is the only name used for the project.
   :data:`LEGACY_NAME_RE` names the retired names; any occurrence found in
   the tree is reported on stderr so they cannot quietly return. The
   generator skips itself, because it is the one file that has to spell the
   retired names in order to search for them.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterator


# ============================================================
# LAYOUT
# ============================================================

REPO_ROOT = Path(__file__).resolve().parent.parent

SOURCE_FILES_DIR = REPO_ROOT / "source_files"

GENERATOR_RELATIVE_PATH = "scripts/gen_master_copy.py"

REGENERATE_COMMAND = ".venv/Scripts/python -m scripts.gen_master_copy"

APP_NAME = "agentCreator"

#: Retired names for this project, each split in two so the full spelling
#: never appears in this file. None of them may appear in the tree, and
#: this file is itself embedded in the code snapshot, so writing them out
#: in full would ship them. One tuple is one name; case is covered by
#: :data:`LEGACY_NAME_RE` being case-insensitive.
RETIRED_NAME_FRAGMENTS = (
    ("Gen", "V1"),
    ("Gen", "V2"),
    ("Gen", "essis"),
    ("Terminator", "1"),
)

LEGACY_NAME_RE = re.compile(
    "|".join("".join(parts) for parts in RETIRED_NAME_FRAGMENTS),
    re.IGNORECASE,
)

SUMMARY_LIMIT = 150

VALUE_LIMIT = 90


# ============================================================
# NOISE FILTERS
# ============================================================

IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "node_modules",
    ".mypy",
}

IGNORED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".so",
    ".dll",
}

#: Never embed a generated document inside a generated document. Matches the
#: snapshot and the per-application ``<scope>_MASTER_COPY.md`` alike.
GENERATED_DOCUMENTS = {
    "APP_CODE_SNAPSHOT.md",
    "headless_app_MASTER_COPY.md",
    "project_manager_MASTER_COPY.md",
}


# ============================================================
# LANGUAGE TAGS
# ============================================================

LANGUAGES = {
    ".bat": "batch",
    ".cmd": "batch",
    ".css": "css",
    ".html": "html",
    ".htm": "html",
    ".ini": "ini",
    ".js": "javascript",
    ".json": "json",
    ".jsonl": "json",
    ".md": "markdown",
    ".mjs": "javascript",
    ".ps1": "powershell",
    ".py": "python",
    ".sh": "bash",
    ".toml": "toml",
    ".ts": "typescript",
    ".txt": "text",
    ".yaml": "yaml",
    ".yml": "yaml",
}


# ============================================================
# TARGETS
# ============================================================

SNAPSHOT_NAME = "APP_CODE_SNAPSHOT.md"

TARGETS: dict[str, dict[str, Any]] = {
    "snapshot": {
        "mode": "code",
        "output": SOURCE_FILES_DIR / SNAPSHOT_NAME,
        "root": REPO_ROOT,
        "title": f"{APP_NAME} — Code Snapshot",
        "subtitle": (
            "Verbatim copy of every source file in the agentCreator "
            "repository, in one document, behind one file structure — the "
            "reference copy used for lookup and for rebuilding the code."
        ),
        "companions": [
            ("headless_app_MASTER_COPY.md", "`headless_app/`"),
            ("project_manager_MASTER_COPY.md", "`project_manager/`"),
        ],
        "exclude": {
            "headless_app/data": (
                "runtime output: chat log, tool log, pipeline run records"
            ),
            "project_manager/workspace/data": (
                "runtime output: chat log and saved chat sessions"
            ),
        },
    },
    "headless_app": {
        "mode": "reference",
        "output": SOURCE_FILES_DIR / "headless_app_MASTER_COPY.md",
        "root": REPO_ROOT / "headless_app",
        "title": f"{APP_NAME} — Headless App Master Copy",
        "subtitle": (
            "The `headless_app/` half of agentCreator: the agent engine, its "
            "tools, and the bridge that binds them to the Project Manager. "
            "File structure plus a description of every module, class and "
            "function."
        ),
        "companions": [
            (SNAPSHOT_NAME, "the whole repository, verbatim"),
            ("project_manager_MASTER_COPY.md", "`project_manager/`"),
        ],
        "exclude": {
            "data": "runtime output: chat log, tool log, pipeline run records",
        },
    },
    "project_manager": {
        "mode": "reference",
        "output": SOURCE_FILES_DIR / "project_manager_MASTER_COPY.md",
        "root": REPO_ROOT / "project_manager",
        "title": f"{APP_NAME} — Project Manager Master Copy",
        "subtitle": (
            "The `project_manager/` half of agentCreator: the FastAPI "
            "workspace server, its editor interface, and the managed "
            "workspace. File structure plus a description of every module, "
            "class and function."
        ),
        "companions": [
            (SNAPSHOT_NAME, "the whole repository, verbatim"),
            ("headless_app_MASTER_COPY.md", "`headless_app/`"),
        ],
        "exclude": {
            "workspace/data": (
                "runtime output: chat log and saved chat sessions"
            ),
        },
    },
}


# ============================================================
# PREAMBLE — CODE SNAPSHOT
# ============================================================

def snapshot_preamble() -> str:
    return """\
## What This Is

A verbatim copy of every source file in this repository, in one document,
behind one file structure. It exists for reference and AI lookup: to answer a
question about the code, or to rebuild it, the exact bytes of every file plus a
map of where everything lives are what is needed, and that is what this
document is.

There is deliberately **no description of what the code does here**. That
lives in the two companion documents, which describe the same tree module by
module:

- [`headless_app_MASTER_COPY.md`](headless_app_MASTER_COPY.md) — the agent
  engine, its tools and its bridge.
- [`project_manager_MASTER_COPY.md`](project_manager_MASTER_COPY.md) — the
  FastAPI server, its editor interface and the managed workspace.

Read the master copy first to learn what a file is for, then come here for its
contents. The File Index below is sized so you can also jump straight to one
file and read only that.

---

## Boot Sequence

### Prerequisites

- Python 3.10 or newer. The virtual environment in this workspace is 3.14.
- Ollama running locally, with at least one model pulled. The picker list in
  `headless_app/config/models.json` names `llama3.1:8b`,
  `nomic-embed-text:latest`, `qwen2.5-coder:latest` and `gemma4:e2b`.
- A web browser. The interface is static HTML, CSS and vanilla JavaScript —
  there is no build step and no bundler.

### Create the environment and run

```bat
rem 1. Virtual environment at the repository root, shared by both halves.
scripts\\venv.bat

rem 2. Dependencies. requirements.txt pins the server stack. The engine also
rem    needs ollama and pydantic, which venv.bat installs for you.
.venv\\Scripts\\python.exe -m pip install -r project_manager\\requirements.txt

rem 3. Start the Project Manager: the editor, the chat page and every agent
rem    route are served by this one process.
project_manager\\scripts\\run.bat
```

Then open <http://127.0.0.1:8000>. The bind address and port come from
`PROJECT_MANAGER_HOST` and `PROJECT_MANAGER_PORT` (`project_manager/server.py`).
The engine also runs without the server:

```bat
cd headless_app
..\\.venv\\Scripts\\python.exe run.py list-agents
..\\.venv\\Scripts\\python.exe run.py run-agent rag_assistant --message "what date is it today?"
```

### Layout requirement

`headless_app/` and `project_manager/` **must be sibling directories**. The
Project Manager imports the engine by putting `<repo>/headless_app` on
`sys.path`, and the chat router walks up three parents from
`interface/routers/chat.py` to find it. Any other layout silently leaves the
server running without the agent engine.
"""


# ============================================================
# OVERVIEW — HEADLESS APP
# ============================================================

def headless_app_overview() -> str:
    return """\
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
python run.py run-pipeline --message "idea: add a settings screen" \\
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
"""


# ============================================================
# OVERVIEW — PROJECT MANAGER
# ============================================================

def project_manager_overview() -> str:
    return """\
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
| `scripts/`       | `run.bat` / `run.sh` / `setup.sh`, using the shared `..\\.venv`             |

```text
parameters/     Project parameters — filesystem.py is the filesystem owner
interface/      Editor interface — core (controller), routers (HTTP), clients, static
workspace/      The managed project content (project.json, agents/, documentation/, …)
scripts/        run.bat / run.sh / setup.sh, using the shared ..\\.venv
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
| `/api/agents/run`        | POST   | Run one agent. Body: `{json_path, md_path \\| agent_id, message, model?}`.        |
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
"""


OVERVIEWS: dict[str, Callable[[], str]] = {
    "snapshot": snapshot_preamble,
    "headless_app": headless_app_overview,
    "project_manager": project_manager_overview,
}


# ============================================================
# DISCOVERY
# ============================================================

def is_excluded_relative(
    path: Path,
    root: Path,
    excluded: dict[str, str],
) -> bool:
    """
    Whether a path is one of this target's declared exclusions.
    """

    if path.name in GENERATED_DOCUMENTS:
        return True

    if path.is_dir():
        return path.relative_to(root).as_posix() in excluded

    if path.suffix.lower() in IGNORED_SUFFIXES:
        return True

    return path.relative_to(root).as_posix() in excluded


def walk_files(
    root: Path,
    excluded: dict[str, str],
) -> Iterator[Path]:
    """
    Yield every embeddable file under root, deterministically ordered.
    """

    for directory, dirnames, filenames in os.walk(root):
        current = Path(directory)

        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in IGNORED_DIRECTORIES
            and not is_excluded_relative(
                current / name,
                root,
                excluded,
            )
        )

        for name in sorted(filenames):
            path = current / name

            if is_excluded_relative(
                path,
                root,
                excluded,
            ):
                continue

            yield path


def discover(
    target: dict[str, Any],
) -> list[str]:
    """
    The root-relative paths a target covers, in final order.
    """

    root: Path = target["root"]

    excluded: dict[str, str] = target["exclude"]

    relative_paths = [
        path.relative_to(root).as_posix()
        for path in walk_files(root, excluded)
    ]

    return sorted(relative_paths, key=lambda item: item.lower())


def find_legacy_names(
    root: Path,
    excluded: dict[str, str],
) -> list[str]:
    """
    Retired app names still present in the tree, as ``path:line`` strings.
    """

    hits: list[str] = []

    generator = Path(__file__).resolve()

    for path in walk_files(root, excluded):

        if path.resolve() == generator:
            continue

        relative = path.relative_to(root).as_posix()

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            continue

        for number, line in enumerate(text.splitlines(), start=1):

            if LEGACY_NAME_RE.search(line):
                hits.append(f"{relative}:{number}")

    return hits


# ============================================================
# TEXT HELPERS
# ============================================================

def read_text(
    root: Path,
    relative_path: str,
) -> str:
    """
    Read a file as normalized LF text.
    """

    return (
        (root / relative_path)
        .read_text(encoding="utf-8", errors="replace")
        .replace("\r\n", "\n")
        .rstrip("\n")
    )


def flatten(
    text: str,
) -> str:
    """
    Collapse every run of whitespace to a single space.
    """

    return " ".join(str(text).split())


def truncate(
    text: str,
    limit: int = SUMMARY_LIMIT,
) -> str:
    """
    Flatten and clip to limit characters, marking the cut.
    """

    flat = flatten(text)

    if len(flat) <= limit:
        return flat

    return flat[: limit - 1].rstrip() + "…"


BANNER_RE = re.compile(
    r"^(?:[\w.-]+/)*[\w.-]+\.[A-Za-z0-9]+$|^[=\-*#~^+_\s]+$"
)


def clip_words(
    text: str,
    limit: int,
) -> str:
    """
    Clip to limit characters on a word boundary, marking the cut.
    """

    flat = flatten(text)

    if len(flat) <= limit:
        return flat

    head = flat[: limit - 1]

    if " " not in head:
        return head.rstrip() + "…"

    return head[: head.rfind(" ")].rstrip(" ,;:.—-") + "…"


def summarize(
    docstring: str | None,
    limit: int = SUMMARY_LIMIT,
) -> str:
    """
    The first real paragraph of a docstring, or an empty string.

    Many module docstrings open with a banner instead of a description:

        engine/agents/roots.py
        ======================

        Pluggable agent roots.

    The banner and its underline are skipped, and the paragraph is read to
    the first blank line rather than to the first newline, because these
    docstrings are hard-wrapped and a single line is often a fragment.
    """

    if not docstring:
        return ""

    lines = docstring.strip().splitlines()

    start = 0

    while start < len(lines):

        flat = flatten(lines[start])

        if flat and not BANNER_RE.match(flat):
            break

        start += 1

    paragraph: list[str] = []

    for line in lines[start:start + 6]:

        if not line.strip():
            break

        paragraph.append(flatten(line))

    return truncate(" ".join(paragraph), limit)


def language_for(
    relative_path: str,
) -> str:
    """
    The Markdown fence language tag for a path.
    """

    return LANGUAGES.get(
        Path(relative_path).suffix.lower(),
        "text",
    )


def fence_for(
    text: str,
) -> str:
    """
    A fence long enough to contain text, even if text embeds fences.

    The fence is always at least three backticks, and always one backtick
    longer than the longest backtick run inside the text. That makes it
    impossible for a line of the content to close the fence early.
    """

    longest = max(
        (
            len(run)
            for run in re.findall(
                r"`+",
                text,
            )
        ),
        default=0,
    )

    return "`" * max(3, longest + 1)


# ============================================================
# CODE MODE — VERBATIM COPY
# ============================================================

def render_section(
    root: Path,
    relative_path: str,
    index: int,
    total: int,
) -> str:
    """
    Render one embedded file: marker, heading and fenced content.
    """

    text = read_text(root, relative_path)

    fence = fence_for(text)

    body = text or "(empty file — 0 bytes)"

    return "\n".join(
        [
            f"<!-- ==== {index}/{total} : {relative_path} ==== -->",
            "",
            f"### {relative_path}",
            "",
            f"{fence}{language_for(relative_path)}",
            body,
            fence,
        ]
    )


def render_file_index(
    root: Path,
    relative_paths: list[str],
) -> str:
    """
    A sized table of every embedded file, for selective reading.
    """

    lines = [
        "## File Index",
        "",
        f"All {len(relative_paths)} embedded files, with their size, so a "
        "reader can decide what to open. The contents are further down, in "
        "this same order, each under a `### path` heading and an "
        "`<!-- ==== n/total : path ==== -->` marker.",
        "",
        "| # | File | Lines | Bytes |",
        "| - | ---- | ----- | ----- |",
    ]

    total_lines = 0

    total_bytes = 0

    for index, relative in enumerate(relative_paths, start=1):

        raw = (root / relative).read_bytes()

        line_count = raw.count(b"\n") + 1

        total_lines += line_count

        total_bytes += len(raw)

        lines.append(
            f"| {index} | `{relative}` | {line_count} | {len(raw)} |"
        )

    lines.append(
        f"| | **{len(relative_paths)} files** | **{total_lines}** | "
        f"**{total_bytes}** |"
    )

    return "\n".join(lines)


# ============================================================
# REFERENCE MODE — MODULE EXTRACTION
# ============================================================

def literal(
    node: ast.AST | None,
) -> str:
    """
    The printed form of a literal assignment, or an empty string.
    """

    if node is None:
        return ""

    try:
        return truncate(repr(ast.literal_eval(node)), VALUE_LIMIT)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return ""


def decorator_text(
    node: ast.expr,
) -> str:
    """
    ``@name`` for a decorator, so the reference is copy-pasteable.
    """

    text = flatten(ast.unparse(node))

    if not text:
        return text

    return text if text.startswith("@") else f"@{text}"


def signature_of(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    """
    ``name(args)`` for a function or method, types included.
    """

    try:
        return f"{node.name}({ast.unparse(node.args)})"
    except Exception:  # pragma: no cover - defensive
        return f"{node.name}(...)"


def describe_python(
    path: Path,
) -> list[str]:
    """
    The module, class, constant and function surface of a Python file.
    """

    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as error:
        return [f"*(not parseable: {error.msg}, line {error.lineno})*"]

    lines: list[str] = []

    purpose = summarize(ast.get_docstring(tree), 240)

    if purpose:
        lines.append(f"**Purpose.** {purpose}")

    # ---- imports

    imports: list[str] = []

    for node in tree.body:

        if isinstance(node, (ast.Import, ast.ImportFrom)):

            flat = flatten(ast.unparse(node))

            if flat and flat not in imports:
                imports.append(flat)

    if imports:
        lines.append("**Imports**")
        lines.extend(f"- `{item}`" for item in imports)

    # ---- module constants

    constants: list[str] = []

    for node in tree.body:

        targets: list[ast.expr] = []

        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]

        for target in targets:

            if not isinstance(target, ast.Name):
                continue

            if not target.id.isupper():
                continue

            value = literal(node.value)

            constants.append(
                f"- `{target.id}`"
                + (f" = `{value}`" if value else "")
            )

    if constants:
        lines.append("**Constants**")
        lines.extend(constants)

    # ---- classes

    classes: list[str] = []

    for node in tree.body:

        if not isinstance(node, ast.ClassDef):
            continue

        decorators = [
            decorator_text(item)
            for item in node.decorator_list
        ]

        kind = "class"

        if any("dataclass" in item for item in decorators):
            kind = "dataclass"

        if any("router" in item for item in decorators):
            kind = "router"

        bases = ", ".join(
            ast.unparse(base) for base in node.bases
        )

        head = f"- **`{node.name}`**"

        if bases:
            head += f" *({kind}, {bases})*"
        else:
            head += f" *({kind})*"

        doc = summarize(ast.get_docstring(node))

        if doc:
            head += f" — {doc}"

        classes.append(head)

        for decorator in decorators:
            classes.append(f"  - *decorator:* `{decorator}`")
        for member in node.body:

            if isinstance(
                member,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):

                member_kind = (
                    "async method"
                    if isinstance(member, ast.AsyncFunctionDef)
                    else "method"
                )

                entry = f"  - **`{signature_of(member)}`** *{member_kind}*"

                member_doc = summarize(ast.get_docstring(member))

                if member_doc:
                    entry += f" — {member_doc}"

                classes.append(entry)

            elif isinstance(member, ast.ClassDef):

                classes.append(
                    f"  - **`{member.name}`** *inner class*"
                )

            elif isinstance(member, ast.AnnAssign) and isinstance(
                member.target,
                ast.Name,
            ) and member.target.id.isupper():

                value = literal(member.value)

                classes.append(
                    f"  - **`{member.target.id}`** *class constant*"
                    + (f" = `{value}`" if value else "")
                )

    if classes:
        lines.append("**Classes**")
        lines.extend(classes)

    # ---- module functions

    functions: list[str] = []

    for node in tree.body:

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        kind = (
            "async function"
            if isinstance(node, ast.AsyncFunctionDef)
            else "function"
        )

        entry = f"- **`{signature_of(node)}`** *{kind}*"

        doc = summarize(ast.get_docstring(node))

        if doc:
            entry += f" — {doc}"

        functions.append(entry)

        for decorator in node.decorator_list:
            functions.append(
                f"  - *decorator:* `{decorator_text(decorator)}`"
            )

    if functions:
        lines.append("**Functions**")
        lines.extend(functions)

    return lines


JS_TOP_LEVEL = re.compile(
    r"^(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(.*)$"
)

JS_FUNCTION = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"
    r"\s*\(([^)]*)\)"
)

JS_CLASS = re.compile(
    r"^(?:export\s+)?class\s+([A-Za-z_$][\w$]*)"
)

JS_ARROW = re.compile(
    r"^(?:async\s+)?(?:\(([^)]*)\)|([A-Za-z_$][\w$]*))\s*=>"
)

JS_METHOD = re.compile(
    r"^  (?:async\s+)?(?:get\s+|set\s+)?\*?([A-Za-z_$][\w$]*)"
    r"\s*\(([^)]*)\)\s*\{"
)

JS_WIRING = re.compile(
    r"^(?:window|document|globalThis)\.[\w$.]+"
    r"(?:\s*=|\s*\()"
)


def leading_comment(
    text: str,
    prefixes: tuple[str, ...],
) -> str:
    """
    The first block of leading comment lines, as one flattened string.
    """

    collected: list[str] = []

    for line in text.splitlines():

        stripped = line.strip()

        if not stripped:
            if collected:
                break
            continue

        if not stripped.startswith(prefixes):
            break

        cleaned = stripped

        if cleaned[:4].lower() == "rem ":
            cleaned = cleaned[4:]

        cleaned = cleaned.lstrip("/#*;<!- ")

        for suffix in ("*/", "-->", "#", ";", "-", "="):
            while cleaned.endswith(suffix) and len(cleaned) > len(suffix):
                cleaned = cleaned[: -len(suffix)].rstrip()

        if cleaned:
            collected.append(cleaned)

        if len(collected) >= 6:
            break

    return truncate(" ".join(collected), 240)


def describe_javascript(
    path: Path,
) -> list[str]:
    """
    The declared surface of a JavaScript file.
    """

    text = path.read_text(encoding="utf-8", errors="replace")

    lines: list[str] = []

    purpose = leading_comment(text, ("/*", "//"))

    if purpose:
        lines.append(f"**Purpose.** {purpose}")

    declarations: list[str] = []

    object_methods: list[str] = []

    wiring: list[str] = []

    current_object: str | None = None

    object_sizes: dict[str, int] = {}

    for line in text.splitlines():

        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip())

        if indent == 0:
            current_object = None

        if JS_WIRING.match(line):
            wiring.append(flatten(line).rstrip(";"))
            continue

        match = JS_METHOD.match(line)

        if match and current_object:
            object_sizes[current_object] = (
                object_sizes.get(current_object, 0) + 1
            )
            object_methods.append(
                f"- **`{current_object}.{match.group(1)}"
                f"({truncate(match.group(2), 50)})`** *method*"
            )
            continue

        if indent != 0:
            continue

        match = JS_CLASS.match(line)

        if match:
            declarations.append(
                f"- **`{match.group(1)}`** *class*"
            )
            continue

        match = JS_FUNCTION.match(line)

        if match:
            declarations.append(
                f"- **`{match.group(1)}({truncate(match.group(2), 60)})`**"
                " *function*"
            )
            continue

        match = JS_TOP_LEVEL.match(line)

        if not match:
            continue

        name, value = match.group(1), match.group(2).strip()

        arrow = JS_ARROW.match(value)

        if value.startswith("{"):
            current_object = name
            object_sizes.setdefault(name, 0)
        elif arrow:
            parameters = arrow.group(1) or arrow.group(2) or ""
            declarations.append(
                f"- **`{name}({truncate(parameters, 60)})`**"
                " *arrow function*"
            )
        elif value.startswith("["):
            declarations.append(
                f"- **`{name}`** *array* = "
                f"`{truncate(value, VALUE_LIMIT)}`"
            )
        else:
            declarations.append(
                f"- **`{name}`** *constant* = "
                f"`{truncate(value.rstrip(';'), VALUE_LIMIT)}`"
            )

    for name, count in object_sizes.items():
        declarations.append(
            f"- **`{name}`** *object literal, {count} methods*"
        )

    if declarations:
        lines.append("**Declarations**")
        lines.extend(declarations)

    if object_methods:
        lines.append("**Methods**")
        lines.extend(object_methods)

    if wiring:
        lines.append("**Wiring**")
        lines.extend(f"- `{truncate(item, 100)}`" for item in wiring)

    return lines


def describe_html(
    path: Path,
) -> list[str]:
    """
    The title, includes and element ids of an HTML page.
    """

    text = path.read_text(encoding="utf-8", errors="replace")

    lines: list[str] = []

    purpose = leading_comment(text, ("<!--",))

    if purpose:
        lines.append(f"**Purpose.** {purpose}")

    title = re.search(
        r"<title>(.*?)</title>",
        text,
        re.DOTALL,
    )

    if title:
        lines.append(
            f"**Title.** {truncate(title.group(1), 120)}"
        )

    includes: list[str] = []

    for match in re.finditer(
        r'<(?:script|link)[^>]*?(?:src|href)="([^"]+)"',
        text,
    ):
        includes.append(match.group(1))

    if includes:
        lines.append("**Includes**")
        lines.extend(f"- `{item}`" for item in includes)

    ids = [
        match.group(1)
        for match in re.finditer(r'\bid="([^"]+)"', text)
    ]

    if ids:
        shown = ids[:40]
        lines.append(
            f"**Element ids ({len(ids)}).** "
            + ", ".join(f"`{item}`" for item in shown)
            + (f" … +{len(ids) - len(shown)} more" if len(ids) > len(shown) else "")
        )

    return lines


def describe_json(
    path: Path,
) -> list[str]:
    """
    The top-level shape of a JSON document.
    """

    text = path.read_text(encoding="utf-8", errors="replace")

    lines: list[str] = []

    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        return [f"*(not valid JSON: {error.msg} at line {error.lineno})*"]

    if not isinstance(data, dict):
        return [f"**Top level.** {type(data).__name__}"]

    lines.append(f"**Top-level keys ({len(data)}).**")

    for key, value in data.items():

        if isinstance(value, bool) or value is None:
            rendered = repr(value)
        elif isinstance(value, (int, float)):
            rendered = repr(value)
        elif isinstance(value, str):
            rendered = truncate(f'"{value}"', VALUE_LIMIT)
        elif isinstance(value, list):
            if all(
                isinstance(item, (str, int, float, bool))
                for item in value
            ):
                rendered = truncate(json.dumps(value), VALUE_LIMIT)
            else:
                rendered = f"list of {len(value)} objects"
        elif isinstance(value, dict):
            rendered = "{" + ", ".join(list(value)[:8]) + "}"
        else:
            rendered = type(value).__name__

        lines.append(f"- `{key}` = {rendered}")

    return lines


def describe_markdown(
    path: Path,
) -> list[str]:
    """
    The opening paragraph and heading outline of a Markdown document.
    """

    text = path.read_text(encoding="utf-8", errors="replace")

    lines: list[str] = []

    # ---- opening prose, which is the document's purpose

    body: list[str] = []

    for line in text.splitlines():

        stripped = line.strip()

        if stripped.startswith("#"):
            continue

        if not stripped and not body:
            continue

        if not stripped and body:
            break

        if stripped.startswith(("```", "|", ">", "-", "*")):
            break

        body.append(stripped)

    if body:
        purpose = clip_words(" ".join(body[:6]), 240)
        lines.append(f"**Purpose.** {purpose}")

    headings = [
        (len(match.group(1)), flatten(match.group(2)))
        for match in re.finditer(
            r"^(#{1,3})\s+(.+)$",
            text,
            re.MULTILINE,
        )
    ]

    if not headings:
        return lines or ["*(no headings)*"]

    for level, title in headings[:40]:
        lines.append(f"{'#' * level} {title}")

    if len(headings) > 40:
        lines.append(
            f"… and {len(headings) - 40} further headings"
        )

    return lines


def describe_script(
    path: Path,
) -> list[str]:
    """
    The header comment of a shell, batch or PowerShell script.
    """

    text = path.read_text(encoding="utf-8", errors="replace")

    lines: list[str] = []

    purpose = leading_comment(text, ("#", "rem ", "REM ", "::"))

    if purpose:
        lines.append(f"**Purpose.** {purpose}")

    return lines


DESCRIBERS: dict[str, Callable[[Path], list[str]]] = {
    ".py": describe_python,
    ".js": describe_javascript,
    ".mjs": describe_javascript,
    ".html": describe_html,
    ".htm": describe_html,
    ".json": describe_json,
    ".md": describe_markdown,
    ".bat": describe_script,
    ".cmd": describe_script,
    ".sh": describe_script,
    ".ps1": describe_script,
    ".txt": describe_script,
}


def describe_file(
    root: Path,
    relative_path: str,
) -> list[str]:
    """
    The description lines for one file, whatever its type.
    """

    path = root / relative_path

    describe = DESCRIBERS.get(path.suffix.lower())

    if describe is None:
        return ["*(no structured reference for this file type)*"]

    try:
        return describe(path)
    except (OSError, ValueError) as error:
        return [f"*(not readable: {error})*"]


def render_module_reference(
    root: Path,
    relative_paths: list[str],
    snapshot_name: str,
) -> str:
    """
    Every file, with the modules, classes and functions it defines.
    """

    lines = [
        "## Module Reference",
        "",
        "One entry per file, in the same order as the file structure above. "
        "Each entry lists what the file *defines* — its purpose, imports, "
        "constants, classes, methods and functions, with signatures and the "
        "first line of every docstring. File bodies are not repeated here: "
        f"every path below is a heading in [`{snapshot_name}`]"
        f"({snapshot_name}), which holds the verbatim source.",
        "",
    ]

    for relative in relative_paths:

        lines.append(f"### `{relative}`")
        lines.append("")

        body = describe_file(root, relative)

        if not body:
            body = ["*(no symbols extracted)*"]

        lines.extend(body)

        lines.append("")
        lines.append(
            f"*Source: [`{snapshot_name}`]({snapshot_name}) § `{relative}`*"
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ============================================================
# FILE STRUCTURE
# ============================================================

def is_visible(
    path: Path,
    excluded: dict[str, str],
) -> bool:
    """
    Whether a tree entry should appear in the structure listing.

    Structural noise is hidden; declared exclusions are shown and annotated.
    """

    if path.is_dir():

        if path.name in IGNORED_DIRECTORIES:
            return False

        return True

    if path.suffix.lower() in IGNORED_SUFFIXES:
        return False

    if path.name in GENERATED_DOCUMENTS:
        return False

    return True


def render_tree(
    root: Path,
    excluded: dict[str, str],
) -> str:
    """
    Render the directory tree, annotating everything not embedded.
    """

    lines: list[str] = [f"{root.name}/"]

    def walk(
        directory: Path,
        prefix: str,
    ) -> None:
        try:
            children = sorted(
                directory.iterdir(),
                key=lambda item: (
                    item.is_file(),
                    item.name.lower(),
                ),
            )
        except OSError:
            return

        visible = [
            child
            for child in children
            if is_visible(child, excluded)
        ]

        for index, child in enumerate(visible):
            last = index == len(visible) - 1

            connector = "└── " if last else "├── "

            relative = child.relative_to(root).as_posix()

            reason = excluded.get(relative)

            annotation = f"   # not embedded: {reason}" if reason else ""

            if child.is_dir():

                lines.append(
                    f"{prefix}{connector}{child.name}/{annotation}"
                )

                if reason is None:
                    walk(
                        child,
                        prefix + ("    " if last else "│   "),
                    )

            else:

                lines.append(
                    f"{prefix}{connector}{child.name}{annotation}"
                )

    walk(root, "")

    return "\n".join(lines)


# ============================================================
# SHARED SECTIONS
# ============================================================

def render_header(
    target: dict[str, Any],
    total: int,
) -> str:
    """
    The title, description and metadata block.
    """

    companions = ", ".join(
        f"[`{name}`]({name}) — {scope}"
        for name, scope in target["companions"]
    )

    mode = target["mode"]

    return "\n".join(
        [
            f"# {target['title']}",
            "",
            target["subtitle"],
            "",
            "| Field | Value |",
            "| ----- | ----- |",
            f"| Scope | `{target['root'].name}/` |",
            f"| Contains | {'file contents, verbatim' if mode == 'code' else 'structure + module reference, no code'} |",
            f"| Files | {total} |",
            f"| Generated | {date.today().isoformat()} |",
            f"| Generator | `{GENERATOR_RELATIVE_PATH}` |",
            f"| Regenerate | `{REGENERATE_COMMAND}` |",
            f"| Companions | {companions} |",
        ]
    )


def render_structure_section(
    target: dict[str, Any],
) -> str:
    """
    The file structure block.
    """

    return "\n".join(
        [
            "## File Structure",
            "",
            "```text",
            render_tree(
                target["root"],
                target["exclude"],
            ),
            "```",
        ]
    )


def render_exclusions_section(
    target: dict[str, Any],
    relative_paths: list[str],
) -> str:
    """
    Explain what is covered, what is not, and how to regenerate.
    """

    excluded: dict[str, str] = target["exclude"]

    rows = "\n".join(
        f"| `{relative}` | {reason} |"
        for relative, reason in sorted(excluded.items())
    )

    root_name = target["root"].name

    if target["mode"] == "reference":
        covered = (
            f"This document covers every source file under `{root_name}/`, "
            f"**{len(relative_paths)} files** in total, in case-insensitive "
            "path order, and describes each one in the Module Reference "
            "below. No file bodies are embedded: a master copy is a map, and "
            f"the code is in [`{SNAPSHOT_NAME}`]({SNAPSHOT_NAME})."
        )
    else:
        covered = (
            f"This document embeds every source file under `{root_name}/`, "
            f"**{len(relative_paths)} files** in total, in case-insensitive "
            "path order, verbatim and unmodified."
        )

    return "\n".join(
        [
            "## Scope",
            "",
            covered,
            "",
            "The following are listed in the structure above but "
            "deliberately **not** covered:",
            "",
            "| Path | Reason |",
            "| ---- | ------ |",
            rows,
            "",
            "Also excluded everywhere: `.git`, `__pycache__/`, virtualenvs, "
            "editor and tool caches (`.venv`, `venv`, `.idea`, `.vscode`, "
            "`.pytest_cache`, `.mypy_cache`, `.ruff_cache`), compiled and "
            "runtime artifacts (`*.pyc`, `*.pyo`, `*.log`, `*.dll`).",
            "",
            "The three generated documents in `source_files/` are never "
            "embedded in each other, so no document can nest inside itself.",
            "",
            "Regenerate all three documents with:",
            "",
            "```bat",
            REGENERATE_COMMAND,
            "```",
            "",
            "Or just this one:",
            "",
            "```bat",
            f"{REGENERATE_COMMAND} --only {target['root'].name}",
            "```",
        ]
    )


def render_footer(
    target: dict[str, Any],
) -> str:
    """
    The provenance footer.
    """

    return "\n".join(
        [
            "---",
            "",
            f"> Generated by `{GENERATOR_RELATIVE_PATH}` on "
            f"{date.today().isoformat()}. Do not edit by hand; regenerate with:",
            ">",
            "> ```bat",
            f"> {REGENERATE_COMMAND}",
            "> ```",
        ]
    )


# ============================================================
# ASSEMBLY
# ============================================================

def build_snapshot(
    target: dict[str, Any],
    relative_paths: list[str],
) -> str:
    """
    The code snapshot: structure, index, scope, then every file verbatim.
    """

    root: Path = target["root"]

    total = len(relative_paths)

    sections = [
        render_section(root, relative, index, total)
        for index, relative in enumerate(
            relative_paths,
            start=1,
        )
    ]

    return "\n\n".join(
        [
            render_header(target, total),
            snapshot_preamble(),
            render_file_index(root, relative_paths),
            render_structure_section(target),
            render_exclusions_section(target, relative_paths),
            "\n\n---\n\n".join(sections),
            render_footer(target),
        ]
    ) + "\n"


def build_reference(
    key: str,
    target: dict[str, Any],
    relative_paths: list[str],
) -> str:
    """
    A master copy: overview, structure, scope, then the module reference.
    """

    root: Path = target["root"]

    return "\n\n".join(
        [
            render_header(target, len(relative_paths)),
            OVERVIEWS[key](),
            render_structure_section(target),
            render_exclusions_section(target, relative_paths),
            render_module_reference(
                root,
                relative_paths,
                SNAPSHOT_NAME,
            ),
            render_footer(target),
        ]
    ) + "\n"


def build_document(
    key: str,
    target: dict[str, Any],
) -> str:
    """
    Assemble the whole document for one target.
    """

    relative_paths = discover(target)

    if target["mode"] == "code":
        return build_snapshot(target, relative_paths)

    return build_reference(key, target, relative_paths)


# ============================================================
# ENTRY POINT
# ============================================================

def write_document(
    key: str,
    target: dict[str, Any],
) -> Path:
    """
    Build and write one document, returning its path.
    """

    output: Path = target["output"]

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        build_document(key, target),
        encoding="utf-8",
        newline="\n",
    )

    return output


def report_legacy_names() -> int:
    """
    Warn about retired app names still present in the tree.

    Returns the number of offending files.
    """

    problems = 0

    for key, target in TARGETS.items():

        root: Path = target["root"]

        if not root.is_dir():
            continue

        hits = find_legacy_names(root, target["exclude"])

        if not hits:
            continue

        problems += len(hits)

        for hit in hits:
            print(
                f"[gen_master_copy] retired app name in "
                f"{target['root'].name}/{hit} — the only name is "
                f"{APP_NAME}",
                file=sys.stderr,
            )

    return problems


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the code snapshot and the per-application master "
            "copies."
        ),
    )

    parser.add_argument(
        "--only",
        choices=sorted(TARGETS),
        help="Regenerate a single document instead of all of them.",
    )

    arguments = parser.parse_args(argv)

    keys = (
        [arguments.only]
        if arguments.only
        else list(TARGETS)
    )

    for key in keys:
        target = TARGETS[key]

        root: Path = target["root"]

        if not root.is_dir():

            print(
                f"[gen_master_copy] skipped {key}: "
                f"{root} does not exist.",
                file=sys.stderr,
            )

            continue

        output = write_document(key, target)

        covered = len(discover(target))

        print(
            f"[gen_master_copy] {output.relative_to(REPO_ROOT).as_posix()}"
            f"  ({covered} files)"
        )

    report_legacy_names()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
````

---

<!-- ==== 84/85 : scripts/venv.bat ==== -->

### scripts/venv.bat

```batch
@echo off
rem Venv setup + activation for the whole agentCreator workspace.
rem Usage:  scripts\venv.bat           (activate; create + install if missing)
rem NOTE the folder is named .venv (dot-prefixed); the manual equivalent is
rem     .venv\Scripts\activate.bat
rem or for one-off commands:
rem     .venv\Scripts\python.exe -m pip install ...

setlocal
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Creating venv at %ROOT%\.venv ...
    python -m venv "%ROOT%\.venv"
    if errorlevel 1 goto :fail
)

if not exist "%ROOT%\.venv\Lib\site-packages\httpx" (
    echo Installing Project Manager + headless engine dependencies...
    "%PYTHON%" -m pip install --upgrade pip
    if errorlevel 1 goto :fail
    "%PYTHON%" -m pip install -r "%ROOT%\project_manager\requirements.txt"
    if errorlevel 1 goto :fail
    "%PYTHON%" -m pip install "httpx>=0.27" "websockets>=13" "fastapi>=0.115" "pydantic>=2" "ollama>=0.3"
    if errorlevel 1 goto :fail
)

call "%ROOT%\.venv\Scripts\activate.bat"
echo Venv active.
exit /b 0

:fail
echo Failed to set up the virtual environment.
exit /b 1
```

---

<!-- ==== 85/85 : scripts/venv.ps1 ==== -->

### scripts/venv.ps1

```powershell
# Venv setup + activation for the whole agentCreator workspace.
# Usage:  .\scripts\venv.ps1            (activate; create + install if missing)
#         .\scripts\venv.ps1 -Recreate  (wipe and rebuild the venv)
#
# NOTE the folder is named .venv (dot-prefixed), so the manual equivalent is:
#     .\.venv\Scripts\Activate.ps1
# or, for one-off commands:
#     .\.venv\Scripts\python.exe -m pip install ...
param([switch]$Recreate)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if ($Recreate) {
    if (Test-Path (Join-Path $root ".venv")) {
        Write-Host "Removing old venv..." -ForegroundColor Yellow
        Remove-Item -LiteralPath (Join-Path $root ".venv") -Recurse -Force
    }
}

if (-not (Test-Path $python)) {
    Write-Host "Creating venv at $root\.venv ..." -ForegroundColor Cyan
    python -m venv (Join-Path $root ".venv")
    if (-not $?) { throw "Failed to create the virtual environment." }
}

if ($Recreate -or -not (Test-Path (Join-Path $root ".venv\Lib\site-packages\httpx"))) {
    Write-Host "Installing Project Manager + headless engine dependencies..." -ForegroundColor Cyan
    & $python -m pip install --upgrade pip
    & $python -m pip install -r (Join-Path $root "project_manager\requirements.txt")
    & $python -m pip install "httpx>=0.27" "websockets>=13" "fastapi>=0.115" "pydantic>=2" "ollama>=0.3"
}

# Activate with ExecutionPolicy bypass so Activate.ps1 is never blocked.
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& (Join-Path $root ".venv\Scripts\Activate.ps1")

Write-Host ""
Write-Host "Venv active. Python: $($python)" -ForegroundColor Green
```

---

> Generated by `scripts/gen_master_copy.py` on 2026-09-28. Do not edit by hand; regenerate with:
>
> ```bat
> .venv/Scripts/python -m scripts.gen_master_copy
> ```
