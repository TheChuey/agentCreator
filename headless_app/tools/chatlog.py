"""
tools/chatlog.py
================

Headless data store.

The headless runtime keeps its own plain-text records so conversation and
tool history survive reloads and so the agent's ``search_chat_logs`` tool
has a single file to read. Two stores live here:

    data/chatlog/chat.log            - every user turn + agent reply (JSON lines)
    data/toollog/tool_usage.jsonl    - every tool execution event (JSON lines)

The data root is ``headless_app/data`` unless ``AGENT_DATA_DIR`` names
another one, and :func:`use_data_dir` points it somewhere else for the
duration of a block. That is how the test environment keeps its runs out
of the real chat history: a header test prompts an agent four times, and
those four turns are evidence, not conversation with a user.

Both stores are read through the module-level path constants at call time,
so rebinding them with :func:`use_data_dir` redirects every caller at once -
the chat log this module writes, the ``search_chat_logs`` tool that reads
it, and the tool log - with no thread or agent to keep in step.

Nothing in this module requires a server. Writes are fail-safe: a broken
data path or disk error never breaks the agent call that produced the event.
"""

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

#: Environment variable naming an alternative data root.
DATA_DIR_ENV = "AGENT_DATA_DIR"


def default_data_dir() -> Path:
    """The data root this process writes to.

    ``AGENT_DATA_DIR`` when it is set to an existing path, otherwise the
    engine's own ``data`` folder beside this package.
    """
    override = os.environ.get(DATA_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent.parent / "data"


DATA_DIR = default_data_dir()

CHATLOG_DIR = DATA_DIR / "chatlog"
CHATLOG_FILE = CHATLOG_DIR / "chat.log"

TOOLLOG_DIR = DATA_DIR / "toollog"
TOOLLOG_FILE = TOOLLOG_DIR / "tool_usage.jsonl"

MAX_MESSAGE_LENGTH = 2000
DEFAULT_HISTORY_LIMIT = 50
MAX_HISTORY_LIMIT = 500


@contextmanager
def use_data_dir(path: str | Path):
    """Write both logs under ``path`` for the duration of the block.

    The path constants are rebound on entry and restored on exit, so a
    test run cannot leave the real chat log pointing at a test folder
    and a failure inside the block cannot leave it rebound at all.
    """
    global DATA_DIR, CHATLOG_DIR, CHATLOG_FILE, TOOLLOG_DIR, TOOLLOG_FILE

    previous = (DATA_DIR, CHATLOG_DIR, CHATLOG_FILE, TOOLLOG_DIR, TOOLLOG_FILE)
    target = Path(path).expanduser().resolve()

    DATA_DIR = target
    CHATLOG_DIR = target / "chatlog"
    CHATLOG_FILE = CHATLOG_DIR / "chat.log"
    TOOLLOG_DIR = target / "toollog"
    TOOLLOG_FILE = TOOLLOG_DIR / "tool_usage.jsonl"

    try:
        yield target
    finally:
        (DATA_DIR, CHATLOG_DIR, CHATLOG_FILE, TOOLLOG_DIR, TOOLLOG_FILE) = previous


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ==========================================================================
# CHAT LOG
# ==========================================================================

def append_chat(sender: str, message: str, agent: str | None = None) -> dict:
    """Append one timestamped chat entry. Returns the stored entry dict.

    ``agent`` tags the entry with the agent that produced it so a
    caller can keep separate per-agent threads in one log. Callers
    that do not pass it keep the original unscoped behaviour.
    """
    CHATLOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": _iso_ts(), "sender": sender, "message": message}
    if agent:
        entry["agent"] = agent
    with CHATLOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_history(limit: int = DEFAULT_HISTORY_LIMIT, agent: str | None = None) -> list[dict]:
    """Most recent chat entries in chronological order.

    With ``agent`` set, only that agent's entries are returned.
    Entries written before per-agent tagging have no agent key and
    therefore belong to no thread.
    """
    limit = max(1, min(limit, MAX_HISTORY_LIMIT))
    entries: list[dict] = []
    if not CHATLOG_FILE.exists():
        return entries
    with CHATLOG_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if agent and entry.get("agent") != agent:
                continue
            entries.append(entry)
    return entries[-limit:]


def clear_chat(agent: str | None = None) -> int:
    """Wipe the chat log entirely. Returns how many entries were removed.

    With ``agent`` set, only that agent's entries are removed and
    every other thread is preserved.
    """
    if not CHATLOG_FILE.exists():
        return 0
    if not agent:
        removed = 0
        with CHATLOG_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    removed += 1
        CHATLOG_FILE.write_text("", encoding="utf-8")
        return removed

    kept: list[str] = []
    removed = 0
    with CHATLOG_FILE.open("r", encoding="utf-8") as handle:
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
    CHATLOG_FILE.write_text("".join(kept), encoding="utf-8")
    return removed


def search_text(query: str, limit: int = 15) -> str:
    """Case-folded substring search over the chat log, newest first.

    Returns an empty string when nothing matches, otherwise a numbered
    transcript of the matching turns. This is the agent's long-term memory:
    it only ever reads the plain-text chat.log, so no vector DB is needed.
    """
    needle = (query or "").strip().lower()
    if not needle:
        return ""
    if not CHATLOG_FILE.exists():
        return ""
    matches: list[str] = []
    with CHATLOG_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if needle not in line.lower():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            sender = entry.get("sender", "?")
            message = entry.get("message", "")
            matches.append(f"[{sender}] {message}")
    if not matches:
        return ""
    matches = matches[-limit:]
    header = f"--- CHAT LOG SEARCH RESULTS FOR: '{query}' ---"
    return "\n".join([header, *reversed(matches)])


# ==========================================================================
# TOOL LOG
# ==========================================================================

def append_tool_event(event: dict) -> None:
    """Append one JSONL tool-event line. Fail-safe (never raise)."""
    try:
        TOOLLOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with TOOLLOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(event, ensure_ascii=False, default=str) + "\n"
            )
    except Exception:
        pass