"""
engine/pipeline.py
==================

Runs the ordered agent chain from config/pipeline.json so a single user idea
can travel Step 1 -> Step 2 -> Step 3 automatically.

Why this exists: chat.html sends one message to ONE agent. A Step-2 agent whose
prompt says "accepts the Feature Plan from Step 1" has nothing to work from when
the user sends it a fresh idea, so it stalls asking for that plan again and
again. The pipeline feeds each later step the OUTPUT of every earlier step as
part of its own message, so the planner's spec reaches the engineer and the
engineer's blueprint reaches the builder without any copy/paste.

Feed-forward messages carry:
    - the ORIGINAL user message (so the module name / scope never gets lost), and
    - each earlier step's final reply, labelled with the producing agent's name.

Every step's tool_events are collected and returned together, so the UI can
render the complete tool usage of a pipeline run in one shot.
"""

import json
from datetime import datetime
from pathlib import Path

from engine.agents.factory import build_agent, build_agent_from_definition
from tools import chatlog

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "pipeline.json"

_STEP_FEED_TEMPLATE = (
    "Below is what the previous pipeline step ({name}) produced.\n"
    "Use it as your required input. Do NOT ask for it again - just act on it.\n"
    "--- {name} OUTPUT ---\n"
    "{output}\n"
    "--- END {name} OUTPUT ---\n"
)


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _records_file() -> Path:
    """pipeline_runs.jsonl inside the active data directory.

    Read from ``tools.chatlog`` at call time rather than recomputed here,
    so pipeline runs follow the same root as the chat and tool logs -
    including the redirect a test run applies with ``use_data_dir``.
    """
    return chatlog.DATA_DIR / "pipeline_runs.jsonl"


def _record_run(snapshot: dict) -> None:
    """Append one JSONL line per pipeline run. Fail-safe: a recording failure
    never breaks the run itself (same philosophy as the tool log)."""
    record = {
        "time": _iso_now(),
        "request": snapshot.get("request", ""),
        "model": snapshot.get("model"),
        "steps": snapshot.get("steps", []),
        "reply": snapshot.get("reply", ""),
    }
    try:
        target = _records_file()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass  # a recording failure never blocks the pipeline


def load_pipeline(config_path=None) -> list:
    """Ordered step configs from config/pipeline.json ([] when missing/broken).

    Missing files return [] so the app degrades gracefully to plain per-agent
    chat instead of crashing on a config problem.
    """
    path = config_path or CONFIG_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data.get("steps") or []


def _build_step(step, model: str | None, bridge=None):
    """Build the Agent for one pipeline step.

    A step is either an agent id (engine/agent_library/) or a dict with
    explicit `json_path` + `md_path` (headless ad-hoc agents).
    """
    if isinstance(step, dict) and step.get("json_path") and step.get("md_path"):
        return build_agent_from_definition(
            step["json_path"],
            step["md_path"],
            model=model,
            bridge=bridge,
        )
    return build_agent(str(step), model=model, bridge=bridge)


def _step_label(step) -> str:
    # A workspace agent's json_path is .../agents/<name>/agent.json, so the
    # agent FOLDER name (not the file stem "agent") is the readable label.
    if isinstance(step, dict):
        json_file = Path(step.get("json_path", ""))
        folder = json_file.parent.name
        return str(step.get("id") or folder or json_file.stem or "custom")
    return str(step)


def run_pipeline(user_message: str, model: str | None = None,
                 config_path=None, steps: list | None = None,
                 bridge=None) -> dict:
    """Run every step in order; return {reply, outputs, tool_events}.

    outputs is a list of {agent_id, agent_name, output, tools_used} - one entry
    per step, so callers can display each stage's contribution separately and
    the cascade's per-agent tool usage.

    Args:
        user_message: the original user idea to run through the chain.
        model:        optional model override for every step.
        config_path:  optional path to a pipeline.json (defaults to the
                      bundled config/pipeline.json).
        steps:        optional explicit step list (agent ids or
                      {json_path, md_path} dicts). Overrides the config file.
        bridge:       optional Project Manager bridge passed to every agent.
    """
    chain = steps if steps is not None else load_pipeline(config_path)
    if not chain:
        return {
            "reply": "(pipeline not configured - add config/pipeline.json or pass steps)",
            "outputs": [],
            "tool_events": [],
        }

    results: list[dict] = []
    tool_events: list[dict] = []

    for index, step in enumerate(chain):
        agent = _build_step(step, model=model, bridge=bridge)

        feed = user_message
        if results:
            chain_text = "\n\n".join(
                _STEP_FEED_TEMPLATE.format(name=r["agent_name"], output=r["output"])
                for r in results
            )
            feed = f"ORIGINAL USER REQUEST:\n{user_message}\n\n{chain_text}"

        reply = agent.think(feed)
        tools_used = sorted({
            e.get("tool")
            for e in agent.tool_events
            if isinstance(e, dict) and e.get("tool")
        })
        results.append({
            "agent_id": _step_label(step),
            "agent_name": agent.profile.name or _step_label(step),
            "output": reply,
            "tools_used": tools_used,
        })
        tool_events.extend(agent.tool_events)
        print(
            f"Agent {index + 1} ({_step_label(step)}) completed. "
            f"Tools used: {', '.join(tools_used) or 'none'}"
        )

    result = {
        "reply": results[-1]["output"],
        "outputs": results,
        "tool_events": tool_events,
    }
    print(
        f"PIPELINE COMPLETE ({len(chain)}/{len(chain)}) -> "
        f"{result['reply'][:80]!r}"
    )
    _record_run({
        "request": user_message,
        "model": model,
        "steps": [
            {
                "agent_id": r["agent_id"],
                "agent_name": r["agent_name"],
                "output": r["output"],
                "tools_used": r["tools_used"],
            }
            for r in results
        ],
        "reply": result["reply"],
    })
    return result
