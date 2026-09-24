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
