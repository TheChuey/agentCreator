"""
bridge/routers/chat.py
======================

Agent-backed Project Manager chat router (drop-in replacement).

The Project Manager keeps a stub chat surface: ``POST /api/chat`` logs a
message and ``GET /api/chat`` fetches history. This router swaps the stub
handler for the GenV1 agent engine, so the Project Manager becomes a fully
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