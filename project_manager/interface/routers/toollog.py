"""
interface/routers/toollog.py
============================

Read the headless agent's tool log.

Every tool the headless agents execute appends one JSONL line to
``headless_app/data/toollog/tool_usage.jsonl``. That file used to be
write-only: nothing in this package read it, so the only way to answer
"what did the agent actually call, and did it work?" was to open the file
in an editor.

    GET /api/tool-log?limit=&agent=&tool=
        -> {"events": [...], "count": int, "file": str}

The log is read, never written, and never cleared from here. It is the
runtime's own record of a run, so it is kept separate from the chat log
this package maintains (``/api/chat``): a chat history is what a user is
looking at, the tool log is evidence of what the agent did, and clearing
one must not clear the other.

The events arrive from the engine's ``tools.chatlog``, reached by path
rather than by installation, the same way ``routers/testing.py`` reaches
``test_environment/agent_test.py``: both are repository siblings of this
package, not part of it. Reading through that module also means the file
location rules (the ``AGENT_DATA_DIR`` override, and the redirection the
test runner applies) are honoured in one place instead of being restated
here.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType

from fastapi import APIRouter, Request

from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# TEST ENVIRONMENT BOOTSTRAP
# ============================================================

#: The engine is a repository sibling of this package, so it is reached by
#: walking up from here rather than by being installed.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_HEADLESS_APP = _REPO_ROOT / "headless_app"

if _HEADLESS_APP.is_dir() and str(_HEADLESS_APP) not in sys.path:
    sys.path.insert(0, str(_HEADLESS_APP))


def _clear_tool_events(agent: str | None) -> int:
    """Wipe the whole tool log, or one agent's events."""
    return _chatlog().clear_tool_events(agent=agent)


#: A browsable path that names an agent folder: workspace/agents/<id>/...,
#: agents/<id>/... (bare), or the folder itself.
_AGENT_PATH = re.compile(
    r"(?:^|/)(?:workspace/)?agents/(?P<id>[^/]+)(?:/|$)"
)


def _agent_ids_for_path(path: str) -> list[str]:
    """Agent ids a browser path could belong to.

    Removing an agent happens through the generic directory/file delete:
    the user deletes ``workspace/agents/<folder>`` (the whole agent) or
    ``workspace/agents/<folder>/agent.json`` (which also removes it from
    discovery). The recorded tool-log id is the one in agent.json, which
    normally equals the folder name; both are returned, and clearing an id
    with no events is a no-op.
    """
    if not path:
        return []
    normalized = path.replace("\\", "/").lstrip("/")
    ids: list[str] = []
    for match in _AGENT_PATH.finditer(normalized):
        folder = match.group("id")
        if folder and folder not in ids:
            ids.append(folder)
        json_id = _json_agent_id(folder)
        if json_id and json_id not in ids:
            ids.append(json_id)
    return ids


def _json_agent_id(folder: str) -> str | None:
    """The ``id`` an agent.json declares, when it can be read."""
    try:
        from parameters import filesystem

        json_path = filesystem.resolve_project_path(
            f"agents/{folder}/agent.json"
        )
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return str(data.get("id") or "").strip() or None
    except Exception:
        return None


def clear_agent_tool_events_for_path(path: str) -> int:
    """Drop the tool log for any agent a just-deleted path named.

    Called after a successful file/directory delete so removing an agent
    removes its diagnostics too. Fail-safe: the deletion already happened,
    so a logging problem must not turn a successful delete into an error.
    """
    try:
        removed = 0
        for agent_id in _agent_ids_for_path(path):
            removed += _clear_tool_events(agent_id)
        return removed
    except Exception:
        return 0


def _chatlog() -> ModuleType:
    """Import headless_app/tools/chatlog.py once per process."""
    module = sys.modules.get("tools.chatlog")
    if module is not None:
        return module

    source = _HEADLESS_APP / "tools" / "chatlog.py"
    if not source.is_file():
        raise FileNotFoundError(
            f"Tool log module not found: {source}. The headless engine is "
            "part of the repository; restore it or point the server at a "
            "checkout that has it."
        )

    spec = importlib.util.spec_from_file_location("tools.chatlog", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load the tool log module: {source}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["tools.chatlog"] = module
    spec.loader.exec_module(module)
    return module


# ============================================================
# READ THE TOOL LOG
# ============================================================

@router.get("/api/tool-log")
def read_tool_log(
    request: Request,
    limit: int = 100,
    agent: str | None = None,
    tool: str | None = None,
):
    """
    Return recent tool events, oldest first.

    Query params:
        limit:
            How many events at most (default 100).
        agent:
            Only this agent's events, matched on the recorded agent id.
        tool:
            Only this tool's events, e.g. ``read_file``.

    An empty ``events`` list means the tool log has not been written yet,
    which is different from a run where the agent called no tools.
    """

    try:

        chatlog = _chatlog()
        events = chatlog.read_tool_events(
            limit=limit,
            agent=agent,
            tool=tool,
        )

        return {
            "events": events,
            "count": len(events),
            "file": str(chatlog.TOOLLOG_FILE),
            "log_exists": chatlog.TOOLLOG_FILE.exists(),
        }

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# CLEAR THE TOOL LOG
# ============================================================

@router.delete("/api/tool-log")
def clear_tool_log(
    request: Request,
    agent: str | None = None,
):
    """
    Wipe the tool log, or one agent's events.

    Query params:
        agent:
            Only this agent's events. Omit to clear the whole log.

    This is the diagnostics "Clear" button. It never touches the chat log:
    the tool log is the engine's own evidence of what ran, so clearing
    diagnostics must not erase a conversation.
    """

    try:

        removed = _clear_tool_events(agent)

        return {
            "status": "ok",
            "cleared": removed,
            "agent": agent,
        }

    except Exception as error:

        raise project_manager_error(
            error
        )