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
            "test_environment/output": (
                "runtime output: header test results"
            ),
            "test_environment/test_data": (
                "runtime output: chat log and tool log of test runs"
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
