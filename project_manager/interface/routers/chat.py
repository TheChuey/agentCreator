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

In-process file tools run through DirectProjectIO, so the Project Manager's
parameters.filesystem stays the single filesystem authority.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
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

from engine.agents.factory import build_agent  # noqa: E402
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


# ============================================================
# CHAT LOG HELPERS
# ============================================================

MAX_MESSAGE_LENGTH = 2000

DEFAULT_LIMIT = 50

MAX_LIMIT = 500

_provider_cache: Any = None


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


def _record_entries(user_message: str, reply: str, agent_id: str) -> list[dict]:
    """Persist user + reply to the headless chat log; mirror to PM's log.

    The agent id is stored on both entries so each agent keeps its own
    conversation in the shared log.
    """
    user_entry = append_chat("user", user_message, agent=agent_id)
    reply_entry = append_chat("agent", reply, agent=agent_id)
    _mirror_pm_log(user_entry)
    _mirror_pm_log(reply_entry)
    return [user_entry, reply_entry]


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
                "No agents are registered in engine/agent_library/."
            )
        )

    try:

        agent = build_agent(
            agent_id,
            model=payload.model,
            bridge=_provider(),
        )

        reply = agent.think(message)

        entries = _record_entries(message, reply, agent_id)

        return {
            "status": "ok",
            "reply": reply,
            "agent_id": agent_id,
            "model": agent.model,
            "tool_events": agent.tool_events,
            "entry": entries[0],
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


if __name__ == "__main__":
    print(__doc__)