"""
interface/routers/logs.py
=========================

One place to read every log the project writes.

Four writers record what an agent did, in four files in three folders:

    chat      data/chatlog/chat.log               (engine, JSONL)
    tool      data/toollog/tool_usage.jsonl       (engine, JSONL)
    pipeline  data/pipeline_runs.jsonl            (engine, JSONL)
    test      test_environment/output/test_results.json (test suite)

Before this router the only way to see them together was to open the
files by hand, and the test report was not surfaced anywhere. Each source
is normalised into the same row shape so one page can show them:

    {id, ts, source, agent, level, message, detail, pinned}

The ``id`` is a content hash rather than an index, because the logs are
append-only and a line number would move the moment one is cleared. That
makes it stable enough to pin a row in ``data/log_pins.json``.

    GET    /api/logs?limit=&source=&agent=&level=
    POST   /api/logs/pin  {"id", "pinned"}
    DELETE /api/logs?source=

This router reads the engine's own stores through the same module the
engine writes them with (``tools.chatlog``), so the ``AGENT_DATA_DIR``
override and the test runner's ``use_data_dir`` redirect are honoured in
one place. It reads the test report through ``agent_test.py`` for the same
reason. Clearing a source reuses the engine's own clear functions, except
the chat log, whose wipe is applied to the workspace mirror as well.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .errors import project_manager_error
from .testing import _agent_test
from .toollog import _chatlog


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()

#: The sources this page knows how to read, in display order.
SOURCES = ("chat", "tool", "pipeline", "test")

DEFAULT_LIMIT = 200
MAX_LIMIT = 1000

#: Column used by the test report for the per-section runs.
TEST_RESULTS_KEY = "results"


# ============================================================
# REQUEST MODELS
# ============================================================

class PinRequest(BaseModel):

    id: str

    pinned: bool = True


# ============================================================
# ROW HELPERS
# ============================================================

def _row(
    source: str,
    ts: str,
    agent: str,
    level: str,
    message: str,
    detail: Any = None,
) -> dict:
    """One normalised log row.

    ``id`` hashes the fields that identify the entry, so the same entry
    hashes the same across reads and a stored pin still matches it. A pin
    is only as durable as the entry: editing or clearing the underlying
    line changes or removes the hash, which is the honest outcome.
    """
    key = f"{source}|{ts}|{agent}|{message}"
    digest = hashlib.sha1(key.encode("utf-8", errors="replace")).hexdigest()
    return {
        "id": digest[:16],
        "ts": ts or "",
        "source": source,
        "agent": agent or "",
        "level": level,
        "message": message,
        "detail": detail if detail is not None else {},
        "pinned": False,
    }


def _event_ok(event: dict) -> bool:
    """Whether a tool event's operation succeeded.

    Mirrors diagnostic.js: prefer the explicit ``ok``/``op_ok`` verdict,
    falling back to ``status`` for events written before those fields.
    """
    ok = event.get("ok")
    if ok is None:
        ok = event.get("op_ok")
    if ok is not None:
        return ok is True
    return event.get("status") not in ("error", "missing")


def _tool_agent(event: dict) -> str:
    return str(event.get("agent_id") or event.get("agentId") or "")


def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file, skipping blank and unparseable lines."""
    records: list[dict] = []
    if not path.is_file():
        return records
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict):
                    records.append(record)
    except OSError:
        return records
    return records


# ============================================================
# EACH SOURCE
# ============================================================

def _chat_rows(limit: int, agent: str | None) -> list[dict]:
    rows: list[dict] = []
    for entry in _chatlog().read_history(limit=limit, agent=agent):
        sender = str(entry.get("sender") or "?")
        rows.append(_row(
            source="chat",
            ts=str(entry.get("ts") or ""),
            agent=str(entry.get("agent") or ""),
            level="INFO",
            message=f"[{sender}] {entry.get('message', '')}",
            detail=entry,
        ))
    return rows


def _tool_rows(limit: int, agent: str | None) -> list[dict]:
    rows: list[dict] = []
    for event in _chatlog().read_tool_events(limit=limit, agent=agent):
        tool = str(event.get("tool") or "tool")
        summary = str(event.get("summary") or "")
        ok = _event_ok(event)
        message = f"{tool} - {summary}" if summary else tool
        rows.append(_row(
            source="tool",
            ts=str(event.get("ts") or event.get("time") or ""),
            agent=_tool_agent(event),
            level="INFO" if ok else "ERROR",
            message=message,
            detail=event,
        ))
    return rows


def _pipeline_rows(limit: int) -> list[dict]:
    path = _chatlog().DATA_DIR / "pipeline_runs.jsonl"
    rows: list[dict] = []
    for record in _read_jsonl(path)[-limit:]:
        step_names = []
        for step in record.get("steps") or []:
            if isinstance(step, dict):
                step_names.append(str(step.get("name") or step.get("agent") or "?"))
            else:
                step_names.append(str(step))
        request = str(record.get("request") or "")
        reply = str(record.get("reply") or "")
        prefix = " -> ".join(step_names) if step_names else "pipeline"
        message = f"{prefix}: {request or reply or '(run)'}"
        rows.append(_row(
            source="pipeline",
            ts=str(record.get("time") or ""),
            agent="pipeline",
            level="INFO",
            message=message,
            detail=record,
        ))
    return rows


def _test_rows(limit: int) -> list[dict]:
    report = _agent_test().read_report()
    if not report:
        return []
    summary = report.get("summary") or {}
    ran_at = str(summary.get("ran_at") or "")
    agent = str(summary.get("agent_id") or "")
    rows: list[dict] = []
    for result in (report.get(TEST_RESULTS_KEY) or [])[-limit:]:
        status = str(result.get("status") or "").upper()
        level = "INFO" if status == "PASS" else "ERROR"
        section = str(result.get("section") or "(section)")
        reason = str(result.get("reason") or "")
        message = f"{section}: {reason}" if reason else section
        rows.append(_row(
            source="test",
            ts=ran_at,
            agent=agent,
            level=level,
            message=message,
            detail=result,
        ))
    return rows


def _collect(
    limit: int,
    source: str | None,
    agent: str | None,
) -> list[dict]:
    """Merge the requested sources into one list, newest first."""
    wanted = [s.strip() for s in source.split(",")] if source else list(SOURCES)
    wanted = [s for s in wanted if s in SOURCES]

    rows: list[dict] = []
    if "chat" in wanted:
        rows += _chat_rows(limit, agent)
    if "tool" in wanted:
        rows += _tool_rows(limit, agent)
    if "pipeline" in wanted:
        rows += _pipeline_rows(limit)
    if "test" in wanted:
        rows += _test_rows(limit)

    rows.sort(key=_sort_key, reverse=True)
    return rows


def _sort_key(row: dict) -> float:
    """Sort mixed ISO timestamps; a missing one sorts oldest."""
    ts = str(row.get("ts") or "").replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts).timestamp()
    except ValueError:
        return 0.0


# ============================================================
# PINS
# ============================================================

def _pins_path() -> Path:
    return _chatlog().DATA_DIR / "log_pins.json"


def _read_pins() -> set[str]:
    path = _pins_path()
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if isinstance(data, list):
        return {str(item) for item in data}
    return set()


def _write_pins(pins: set[str]) -> None:
    path = _pins_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(sorted(pins), indent=2),
        encoding="utf-8",
    )


# ============================================================
# READ
# ============================================================

@router.get("/api/logs")
def read_logs(
    request: Request,
    limit: int = DEFAULT_LIMIT,
    source: str | None = None,
    agent: str | None = None,
    level: str | None = None,
):
    """
    Return recent log rows from one or more sources, newest first.

    Query params:
        limit:   How many rows at most (default 200).
        source:  Comma-separated subset of chat,tool,pipeline,test.
        agent:   Only this agent's rows (where an agent is recorded).
        level:   Only this level, e.g. ERROR.

    Each row carries ``pinned`` so the page can show which entries are
    saved. ``pinned`` in the response is the total number of stored pins,
    which may exceed the pins visible in this page of rows.
    """

    try:

        limit = max(1, min(limit, MAX_LIMIT))
        rows = _collect(limit, source, agent)

        if agent:
            rows = [
                row for row in rows
                if row.get("agent", "") == agent
            ]

        if level:
            wanted = level.strip().lower()
            rows = [
                row for row in rows
                if row.get("level", "").lower() == wanted
            ]

        pins = _read_pins()
        for row in rows:
            row["pinned"] = row["id"] in pins

        return {
            "rows": rows[:limit],
            "count": len(rows[:limit]),
            "total": len(rows),
            "pinned": len(pins),
            "sources": list(SOURCES),
        }

    except Exception as error:

        raise project_manager_error(error)


# ============================================================
# PIN
# ============================================================

@router.post("/api/logs/pin")
def pin_log(
    request: Request,
    payload: PinRequest,
):
    """
    Save or unsave one log row.

    Body:
        id:     the row id returned by GET /api/logs.
        pinned: True to save, False to unsave (default True).
    """

    try:

        pin_id = str(payload.id or "").strip()
        if not pin_id:
            raise ValueError("A row id is required to save a log entry.")

        pins = _read_pins()
        if payload.pinned:
            pins.add(pin_id)
        else:
            pins.discard(pin_id)
        _write_pins(pins)

        return {
            "status": "ok",
            "id": pin_id,
            "pinned": payload.pinned,
            "count": len(pins),
        }

    except Exception as error:

        raise project_manager_error(error)


# ============================================================
# CLEAR
# ============================================================

def _clear_pipeline() -> int:
    path = _chatlog().DATA_DIR / "pipeline_runs.jsonl"
    if not path.is_file():
        return 0
    removed = sum(1 for record in _read_jsonl(path))
    path.write_text("", encoding="utf-8")
    return removed


def _clear_test() -> int:
    agent_test = _agent_test()
    report = agent_test.read_report()
    target = Path(agent_test.RESULTS_FILE)
    if not target.is_file():
        return 0
    removed = len((report or {}).get(TEST_RESULTS_KEY) or []) or 1
    target.unlink()
    return removed


@router.delete("/api/logs")
def clear_logs(
    request: Request,
    source: str | None = None,
):
    """
    Wipe one source, or every source when omitted.

    Query params:
        source: chat | tool | pipeline | test. Omitted clears all four.

    The chat wipe is mirrored onto the workspace's own chat.log, the same
    way DELETE /api/chat does, so the two copies do not drift apart.
    """

    try:

        wanted = [source] if source else list(SOURCES)
        cleared: dict[str, int] = {}

        for name in wanted:
            if name == "chat":
                removed = _chatlog().clear_chat()
                try:
                    from .chat import _clear_mirror  # noqa: PLC0415

                    _clear_mirror(None)
                except Exception:  # pragma: no cover - mirror is best-effort
                    pass
                cleared["chat"] = removed
            elif name == "tool":
                cleared["tool"] = _chatlog().clear_tool_events()
            elif name == "pipeline":
                cleared["pipeline"] = _clear_pipeline()
            elif name == "test":
                cleared["test"] = _clear_test()

        return {
            "status": "ok",
            "cleared": cleared,
        }

    except Exception as error:

        raise project_manager_error(error)
