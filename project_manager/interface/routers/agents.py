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