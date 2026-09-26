"""
gen_master_copy.py
===================

Deterministic single-file snapshot generator for this repository.

Writes one self-contained Markdown document per application, each embedding
the complete source of that application plus a hand-authored preamble:

    source_files/project_manager_MASTER_COPY.md   <- project_manager/
    source_files/headless_app_MASTER_COPY.md      <- headless_app/

Both documents are generated from the live tree, so they are always in sync
with the code and with each other.

Run:
    .venv/Scripts/python -m scripts.gen_master_copy
    .venv/Scripts/python -m scripts.gen_master_copy --only headless_app

The preamble prose lives in this file (see the PREAMBLE section) so that a
regeneration is fully deterministic: the same tree always produces the same
document, byte for byte, apart from the date stamp.

Design rules
------------
1. No self-embedding. A ``*_MASTER_COPY.md`` file is never embedded in a
   document, so the output cannot nest inside itself.
2. Adaptive fences. Each file's fence is one backtick longer than the longest
   run of backticks inside that file, so content containing ``` fences
   (README.md, HTML pages) still renders correctly.
3. Deterministic order. Files are sorted case-insensitively by their
   project-relative path.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterator


# ============================================================
# LAYOUT
# ============================================================

REPO_ROOT = Path(__file__).resolve().parent.parent

SOURCE_FILES_DIR = REPO_ROOT / "source_files"

GENERATOR_RELATIVE_PATH = "scripts/gen_master_copy.py"

REGENERATE_COMMAND = ".venv/Scripts/python -m scripts.gen_master_copy"


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

#: Never embed a master copy inside a master copy. Matches both the bare
#: ``MASTER_COPY.md`` and the per-application ``<scope>_MASTER_COPY.md``.
SELF_COPY_SUFFIX = "MASTER_COPY.md"


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

TARGETS: dict[str, dict[str, Any]] = {
    "project_manager": {
        "output": SOURCE_FILES_DIR / "project_manager_MASTER_COPY.md",
        "root": REPO_ROOT / "project_manager",
        "title": "Project Manager — MASTER COPY",
        "subtitle": (
            "Single-file snapshot of the complete `project_manager/` source "
            "tree: the FastAPI workspace server, its editor interface, and the "
            "in-process agent engine it hosts."
        ),
        "sister": ("headless_app_MASTER_COPY.md", "headless_app/"),
        "exclude": {
            "workspace/data": "runtime logs written by the server",
            "workspace/ws_evt_probe.txt": "stray WebSocket debug probe",
            "interface/static/chatbackuporiginal.html": (
                "pre-rewrite backup copy of the chat page"
            ),
        },
    },
    "headless_app": {
        "output": SOURCE_FILES_DIR / "headless_app_MASTER_COPY.md",
        "root": REPO_ROOT / "headless_app",
        "title": "Headless App — MASTER COPY",
        "subtitle": (
            "Single-file snapshot of the complete `headless_app/` source tree: "
            "the GenV1 agent engine, its tools, and the bridge that binds them "
            "to Project Manager."
        ),
        "sister": ("project_manager_MASTER_COPY.md", "project_manager/"),
        "exclude": {
            "data": "runtime output: chat log, tool log, pipeline run records",
        },
    },
}


# ============================================================
# PREAMBLE — PROJECT MANAGER
# ============================================================

def project_manager_preamble() -> str:
    return """\
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
| `/api/agents/run`       | POST   | Run one agent. Body: `{json_path, md_path \\| agent_id, message, model?}`. |
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
scripts/        run.bat / run.sh / setup.sh, using the shared ..\\.venv
server.py       Slim FastAPI host: assembles the pillars, mounts the routers
```

`interface/core/defaults.py` builds the single shared controller, event bus
and session pool that every router, the browser and the Python client all use.
`interface/core/operations.py` is the only place operations are defined, and
every filesystem call it makes is delegated to `parameters/filesystem.py` — the
server itself contains no filesystem logic.
"""


# ============================================================
# PREAMBLE — HEADLESS APP
# ============================================================

def headless_app_preamble() -> str:
    return """\
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
python run.py run-pipeline --message "idea: add a settings screen" \\
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
"""


PREAMBLES = {
    "project_manager": project_manager_preamble,
    "headless_app": headless_app_preamble,
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

    if path.is_dir():
        return path.relative_to(root).as_posix() in excluded

    if path.suffix.lower() in IGNORED_SUFFIXES:
        return True

    if path.name.endswith(SELF_COPY_SUFFIX):
        return True

    relative = path.relative_to(root).as_posix()

    return relative in excluded


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
    The project-relative paths embedded by a target, in final order.
    """

    root: Path = target["root"]

    excluded: dict[str, str] = target["exclude"]

    relative_paths = [
        path.relative_to(root).as_posix()
        for path in walk_files(root, excluded)
    ]

    return sorted(relative_paths, key=lambda item: item.lower())


# ============================================================
# RENDERING
# ============================================================

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


def read_text(
    root: Path,
    relative_path: str,
) -> str:
    """
    Read a file as normalized LF text.
    """

    return (
        (root / relative_path)
        .read_text(encoding="utf-8")
        .replace("\r\n", "\n")
        .rstrip("\n")
    )


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


def is_visible(
    path: Path,
    root: Path,
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

    if path.name.endswith(SELF_COPY_SUFFIX):
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
            if is_visible(child, root, excluded)
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


def render_header(
    target: dict[str, Any],
    total: int,
) -> str:
    """
    The title, description and metadata block.
    """

    sister_file, sister_scope = target["sister"]

    return "\n".join(
        [
            f"# {target['title']}",
            "",
            target["subtitle"],
            "",
            "| Field | Value |",
            "| ----- | ----- |",
            f"| Scope | `{target['root'].name}/` |",
            f"| Files embedded | {total} |",
            f"| Generated | {date.today().isoformat()} |",
            f"| Generator | `{GENERATOR_RELATIVE_PATH}` |",
            f"| Regenerate | `{REGENERATE_COMMAND}` |",
            f"| Sister document | [`{sister_file}`]({sister_file}) — {sister_scope} |",
        ]
    )


def render_scope_section(
    target: dict[str, Any],
    relative_paths: list[str],
) -> str:
    """
    Explain what is embedded, what is not, and how to regenerate.
    """

    excluded: dict[str, str] = target["exclude"]

    rows = "\n".join(
        f"| `{relative}` | {reason} |"
        for relative, reason in sorted(excluded.items())
    )

    root_name = target["root"].name

    return "\n".join(
        [
            "## Snapshot Scope",
            "",
            f"This document embeds every source file under `{root_name}/`, "
            f"**{len(relative_paths)} files** in total, in "
            "case-insensitive path order.",
            "",
            "The following are listed in the tree above but deliberately "
            "**not** embedded:",
            "",
            "| Path | Reason |",
            "| ---- | ------ |",
            rows,
            "",
            "Also excluded everywhere: `__pycache__/`, virtualenvs, editor "
            "and tool caches (`__pycache__`, `.venv`, `venv`, `.pytest_cache`, "
            "`.mypy_cache`, `.ruff_cache`, `.idea`, `.vscode`), compiled "
            "artifacts (`*.pyc`, `*.pyo`, `*.log`).",
            "",
            "A master copy is **never** embedded in a master copy, so this "
            "document cannot nest inside itself.",
            "",
            "Regenerate both documents with:",
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


def build_document(
    key: str,
    target: dict[str, Any],
) -> str:
    """
    Assemble the whole document for one target.
    """

    root: Path = target["root"]

    relative_paths = discover(target)

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
            PREAMBLES[key](),
            "## File Structure\n\n```text\n"
            + render_tree(root, target["exclude"])
            + "\n```",
            render_scope_section(target, relative_paths),
            "\n\n---\n\n".join(sections),
            render_footer(target),
        ]
    ) + "\n"


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


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the per-application MASTER_COPY.md snapshots."
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

        embedded = len(discover(target))

        print(
            f"[gen_master_copy] {output.relative_to(REPO_ROOT).as_posix()}"
            f"  ({embedded} files)"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
