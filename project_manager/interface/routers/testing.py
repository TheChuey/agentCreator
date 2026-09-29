"""
interface/routers/testing.py
============================

Agent header test endpoints for the Project Manager.

The tests themselves live in ``test_environment/agent_test.py``, outside
this package, because they are about the test environment rather than about
the workspace. This router is the seam: it resolves a published test agent,
hands it to that module, and reads back the evidence it wrote.

    GET  /api/test/agents
        -> every published test agent in test_environment/test_agents/.

    POST /api/test/run_header_tests
        {"agent_id", "model"?}
        -> run the four header tests against that agent and return
           {"summary", "results"}. Four model turns, so this takes as long
           as the model takes; it is a plain sync endpoint, which FastAPI
           runs off the event loop in its threadpool.

    GET  /api/test/results
        -> the last report written to output/test_results.json, or 404
           when the suite has never run.

Two things are deliberately not shared with the live chat path. The agent
under test lives in the test environment, so it never joins the registry and
never appears in the agent picker. And the run's chat log and tool log are
redirected by the test runner itself into test_environment/test_data/, so its
four prompts and four replies never reach the chat history that
``search_chat_logs`` and the saved sessions read. This router only has to avoid
undoing that: the redirection is applied and unwound inside the runner, next to
the code that writes the logs.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# REQUEST MODELS
# ============================================================

class HeaderTestRequest(BaseModel):

    agent_id: str

    model: str | None = None


# ============================================================
# TEST ENVIRONMENT BOOTSTRAP
# ============================================================

#: The engine and the test environment are repository siblings of
#: this package, so both are reached by walking up from here rather
#: than by being installed.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_HEADLESS_APP = _REPO_ROOT / "headless_app"
_TEST_ENVIRONMENT = _REPO_ROOT / "test_environment"

for _on_path in (_HEADLESS_APP, _TEST_ENVIRONMENT):
    if _on_path.is_dir() and str(_on_path) not in sys.path:
        sys.path.insert(0, str(_on_path))


def _agent_test() -> ModuleType:
    """Import test_environment/agent_test.py once per process.

    Loaded by path rather than by name so the module is found whether
    this runs from the server, from a test client, or from a script in
    another working directory.
    """
    module = sys.modules.get("agent_test")
    if module is not None:
        return module

    source = _TEST_ENVIRONMENT / "agent_test.py"
    if not source.is_file():
        raise FileNotFoundError(
            f"Test runner not found: {source}. The test environment is "
            "part of the repository; restore it or point the server at a "
            "checkout that has it."
        )

    spec = importlib.util.spec_from_file_location("agent_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load the test runner: {source}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_test"] = module
    spec.loader.exec_module(module)
    return module


# ============================================================
# PUBLISHED TEST AGENTS
# ============================================================

@router.get("/api/test/agents")
def list_test_agents(
    request: Request,
):
    """
    Return every published test agent.

    These are the agents in test_environment/test_agents/, not the
    registry: a test agent is not registered as an agent root, so it can
    be tested without ever showing up in the live agent picker.
    """

    try:

        return {"agents": _agent_test().list_test_agents()}

    except Exception as error:

        raise project_manager_error(error)


# ============================================================
# RUN THE FOUR HEADER TESTS
# ============================================================

@router.post("/api/test/run_header_tests")
def run_header_tests(
    request: Request,
    payload: HeaderTestRequest,
):
    """
    Test one published agent against its four headers.

    Body:
        agent_id: a folder in test_environment/test_agents/ holding
                  agent.json + agent.md.
        model:    optional model override.

    Returns {"summary": {agent_id, model, ran_at, passed, failed, total,
    status}, "results": [{section, status, prompt, response, reason}]} and
    writes the same report to output/test_results.json.
    """

    try:

        agent_test = _agent_test()
        json_file, md_file = agent_test.resolve_agent_files(payload.agent_id)

        report = agent_test.run_tests_report(
            str(json_file),
            str(md_file),
            model=payload.model,
            agent_id=str(payload.agent_id),
        )

        # write_report stamps summary.results_file on the report it is
        # given as well as on the file, so the response and the file on
        # disk say the same thing about where the evidence landed.
        agent_test.write_report(report)

        return report

    except Exception as error:

        raise project_manager_error(error)


# ============================================================
# READ THE LAST REPORT
# ============================================================

@router.get("/api/test/results")
def read_results(
    request: Request,
):
    """
    Return the last header test report, or 404 when there is none.

    The file is written by the run endpoint, so a 404 here means the
    suite has not run in this checkout yet, not that a run failed.
    """

    try:

        agent_test = _agent_test()
        report = agent_test.read_report()

        if report is None:
            raise FileNotFoundError(
                "No header test results yet. Publish a test agent and run "
                "the suite, or POST /api/test/run_header_tests."
            )

        return report

    except Exception as error:

        raise project_manager_error(error)
