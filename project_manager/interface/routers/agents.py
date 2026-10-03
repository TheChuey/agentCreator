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

    GET /api/tools
        -> the tool IDs the registry can resolve, so a frontend that writes
           an agent.json (the Prompt Builder) names tools the engine will
           actually attach, instead of keeping a second copy of the list.

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


def _panel_paths():
    """The control panel's path module, or None when it is unavailable.

    ``parameters.filesystem`` already puts the repository root on
    ``sys.path``, so by the time this runs the panel is importable. It is
    still guarded because a router that cannot load is a server that will
    not start, and losing the agent endpoints over a missing sibling
    directory is a worse outcome than falling back to the filesystem's own
    containment check.
    """
    try:
        from ws_controlPanel import paths as panel_paths
        return panel_paths
    except Exception:
        return None


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

    This used to be a second, independent implementation of the containment
    rule, alongside the one in ``parameters/filesystem``. Two implementations
    of a security rule can drift, and these two already differed in detail.
    It now calls ``ws_controlPanel.paths.resolve_agent_path``, which is the
    single implementation the filesystem itself uses.
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
    panel = _panel_paths()
    if panel is not None:
        return panel.resolve_agent_path(relative_path)
    # The panel is unavailable: fall back to the filesystem's own check
    # rather than to no check at all.
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


# ============================================================
# TOOLS
# ============================================================

@router.get("/api/tools")
def list_tool_ids(
    request: Request,
):
    """
    Return the tool IDs the registry can resolve.

    The registry is the single source of truth for what ``agent.json``'s
    ``tools`` may name (tools/registry.py), so the Prompt Builder asks for
    this list instead of keeping its own copy that could silently drift.

    ``mode: "chat"`` attaches none of these; ``mode: "agent"`` attaches the
    ones an ``agent.json`` lists (engine/agents/factory.py).
    """

    from tools.registry import list_tools

    try:

        return {"tools": list_tools()}

    except Exception as error:

        raise project_manager_error(error)
