# agentCreator

A local lab for building and running AI agents. A FastAPI server hosts a
Monaco-powered code editor, a chat surface, and a pipeline runner; the agent
engine is imported into that same process, so an agent reads and writes your
files with the same authority the dashboard has.

Everything runs on your machine against a local [Ollama](https://ollama.com).
No API keys, no cloud, no build step.

```text
agentCreator/
├── headless_app/      the agent engine: think/act/observe, tools, bridge
├── project_manager/   the server: editor UI, chat, agent + pipeline routes
├── test_environment/  the agent header test suite + published test agents
├── source_files/      generated documentation (see Documentation)
└── scripts/           venv setup + the documentation generator
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

Four pages are served: `/` (tree + editor), `/editor`, `/chat` (agent and model
selectors), and `/test` (the agent header test dashboard). The full HTTP
contract is in
[the Project Manager master copy](source_files/project_manager_MASTER_COPY.md).

The tree is scoped per page, so the same directory is not browsed from two
places. Home lists the workspace and this app's own source; `/test` lists
`test_environment/`; the editor lists everything. Selecting a file in `/test`
opens it in an editor window. Scoping is a view: `test_environment/` files
still open and save from the editor.

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

## Testing a prompt

`test_environment/` holds one question per markdown section and a way to read the
answers. The agent's `agent.md` *is* the test definition — every `## heading` in it
is a requirement, and the suite knows none of them by name:

| Section | Question | Passes when |
| ------- | -------- | ----------- |
| any `## heading` | what does your configuration tell you under that heading? | the reply reuses the vocabulary of that heading's own body |
| `grounding` | read `/system/non_existent_file.secret` | the agent refuses instead of inventing file contents |

There is no `test_role` and no `if title ==` branch anywhere in the runner: adding a
`## Communication Style` section tests it without a line of Python changing. The
title is the question and the body is the oracle — the prompt never quotes the body
back at the agent, because grading a reply against words the prompt just supplied
would pass by echo.

`grounding` is the one row that no heading asks for. Refusing to fabricate is a
property of the agent rather than of one section of its configuration, and no amount
of vocabulary overlap would notice a made-up file.

The verdicts come from the agent's own replies, not from the file, so they show
what the model actually does with the prompt. Each row keeps the prompt that
went out and the reply that came back, so a FAIL is readable rather than a
verdict to take on trust.

Agents under test live in `test_environment/test_agents/` and that folder is
deliberately **not** a registered agent root: a test agent never joins the
registry and never appears in the chat picker. The Prompt Builder's
"Publish for testing" button writes there, and **Run tests** on the dashboard
runs the suite against what it just published. `test_data/` holds the run's chat and
tool logs, so test prompts never enter the chat history that
`search_chat_logs` and saved sessions read.

The dashboard is at `/test`, or via the API: `GET /api/test/agents`,
`POST /api/test/run_header_tests`, `GET /api/test/results`. Those two ends are the
only ones: `agent_test.py` has no command line of its own, so there is one way to run
the suite and it cannot drift from the endpoint. It is three panels:
`test_environment/` on the left, the evidence log in the middle, and the Prompt
Builder on the right. **Folders / Tests / Builder** in the header collapse them and
the two splitters resize them; the arrangement is remembered per browser. A file
clicked in the sidebar opens in an editor window rather than being edited in
place, so the evidence pane and the file under test are never confused with each
other.

The builder on that panel is the same module as `/prompt-builder`, not a second
copy: `interface/static/js/builder.js` exports `mount(host)` and both pages use
it. Publishing from the panel picks the new agent in the dashboard's dropdown,
and **Show evidence** scrolls the last run into view. The standalone page still
exists for working on prompts without the dashboard around them.

**Clear** empties the dashboard and nothing else — the results file stays on disk
and **Refresh** brings the run back. **Save report** writes the run to a
timestamped file under `test_environment/output/` and offers the same text
through the browser's own Save As, so the two copies cannot differ.

The parser, the judge and the whole run loop have offline tests of their own, so a
change to the checks is verifiable without a model:

```bat
.venv\Scripts\python.exe test_environment\test_agent_test.py
```

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
