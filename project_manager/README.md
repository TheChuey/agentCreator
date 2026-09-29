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

The `/test` page and the `/api/test/*` routes it uses are served from here, but
the agents they test and the four header questions live outside this package in
[`test_environment/`](../test_environment/agent_test.py), because they are about
the test environment rather than about the workspace.
