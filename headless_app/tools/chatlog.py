"""
tools/chatlog.py
================

Headless data store.

The headless runtime keeps its own plain-text records so conversation and
tool history survive reloads and so the agent's ``search_chat_logs`` tool
has a single file to read. Two stores live here:

    data/chatlog/chat.log            - every user turn + agent reply (JSON lines)
    data/toollog/tool_usage.jsonl    - every tool execution event (JSON lines)

The data root is the repository's ``data`` folder unless ``AGENT_DATA_DIR``
names another one, and :func:`use_data_dir` points it somewhere else for the
duration of a block. That is how the test environment keeps its runs out
of the real chat history: a header test prompts an agent four times, and
those four turns are evidence, not conversation with a user.

Both stores are read through the module-level path constants at call time,
so rebinding them with :func:`use_data_dir` redirects every caller at once -
the chat log this module writes, the ``search_chat_logs`` tool that reads
it, and the tool log - with no thread or agent to keep in step.

Both stores are readable as well as writable: :func:`read_history` and
:func:`read_tool_events` are how a UI (or a person) inspects what a run
actually did without opening the files by hand.

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
    repository's own ``data`` folder, so every writer lands in one place
    (``<repo>/data``) instead of beside this package.
    """
    override = os.environ.get(DATA_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "data"


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

#: Tool arguments whose values are the whole file body. Logging them verbatim
#: turns the tool log into a second copy of every file the agent writes, so
#: they are replaced by a length record instead.
VOLUMINOUS_ARG_KEYS = ("content", "text", "body")


def summarize_args(args: dict) -> dict:
    """Copy ``args`` with bulky text payloads replaced by length counts.

    ``write_text_file`` is called with the entire file content, so an
    unredacted log grows by a full copy of every write and buries the
    metadata that makes the log useful. The recorded size and shape of the
    payload are what a reader actually needs; the bytes are in the file.

    Idempotent: an argument that already carries its ``<key>_chars`` record
    is left alone, so applying this twice cannot count the placeholder.
    """
    if not isinstance(args, dict):
        return args
    summary = {}
    for key, value in args.items():
        already = key in VOLUMINOUS_ARG_KEYS and f"{key}_chars" in args
        if key in VOLUMINOUS_ARG_KEYS and isinstance(value, str) and not already:
            summary[key] = f"<{len(value)} chars elided>"
            summary[f"{key}_chars"] = len(value)
            summary[f"{key}_bytes"] = len(value.encode("utf-8", errors="replace"))
        else:
            summary[key] = value
    return summary


def append_tool_event(event: dict) -> bool:
    """Append one JSONL tool-event line.

    Bulky text in ``args`` is elided here rather than in the caller, so the
    redaction is a property of the log file itself: no writer can add a
    second copy of a written file by forgetting to call
    :func:`summarize_args` first.

    Returns True when the line reached disk. The call never raises - a
    broken data path must not break the tool call that produced the event -
    but it reports failure instead of swallowing it, so a caller can warn
    about a log that is not being written rather than discovering it later.
    """
    try:
        if isinstance(event.get("args"), dict):
            event = {**event, "args": summarize_args(event["args"])}
        TOOLLOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False, default=str)
        with TOOLLOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return True
    except Exception:
        return False


def read_tool_events(
    limit: int = DEFAULT_HISTORY_LIMIT,
    agent: str | None = None,
    tool: str | None = None,
) -> list[dict]:
    """Most recent tool events in chronological order.

    The counterpart to :func:`append_tool_event`: without it the tool log is
    write-only and the only way to see a run is to open the JSONL by hand.

    ``agent`` and ``tool`` filter; events are matched on the ``agent_id``/
    ``agentId`` and ``tool`` keys, so events written before those keys
    existed are still returned for unfiltered reads.
    """
    limit = max(1, min(limit, MAX_HISTORY_LIMIT))
    events: list[dict] = []
    if not TOOLLOG_FILE.exists():
        return events
    with TOOLLOG_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if agent and str(event.get("agent_id") or event.get("agentId") or "") != agent:
                continue
            if tool and str(event.get("tool") or "") != tool:
                continue
            events.append(event)
    return events[-limit:]


def clear_tool_events(agent: str | None = None) -> int:
    """Wipe the tool log, or one agent's events. Returns the count removed."""
    if not TOOLLOG_FILE.exists():
        return 0
    if not agent:
        removed = 0
        with TOOLLOG_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    removed += 1
        TOOLLOG_FILE.write_text("", encoding="utf-8")
        return removed

    kept: list[str] = []
    removed = 0
    with TOOLLOG_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(event.get("agent_id") or event.get("agentId") or "") == agent:
                removed += 1
                continue
            kept.append(line if line.endswith("\n") else line + "\n")
    TOOLLOG_FILE.write_text("".join(kept), encoding="utf-8")
    return removed