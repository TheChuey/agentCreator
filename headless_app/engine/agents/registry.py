"""
app/agents/registry.py
======================

Agent discovery over the registered roots (engine/agents/roots.py).

The filesystem is the source of truth: every folder in a registered root
that contains an agent.json is an available agent. Because roots are
searched most-recently-registered first, a workspace agent shadows a
library agent declaring the same id - which is the same precedence
``loader`` uses when it builds one agent, so discovery and building can
never disagree.

Registering ``workspace/agents/`` (the Project Manager does this at
startup) is therefore all it takes for a newly created agent to appear
in GET /api/agents, in the frontend selector, and in every id-based
lookup: no code changes, no manual lists, no second scanner.
"""

import json

from engine.agents import roots
from engine.agents.loader import AGENT_LIBRARY_DIR  # noqa: F401  (re-exported)


def _read_meta(agent_dir) -> dict | None:
    """Parsed agent.json, or None when missing/unreadable/malformed."""
    meta_file = agent_dir / roots.AGENT_META_FILE
    if not meta_file.exists():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[REGISTRY] skipping {agent_dir}: unreadable agent.json ({exc})")
        return None
    return meta if isinstance(meta, dict) else None


def list_agents() -> list[dict]:
    """One summary per discovered agent, highest-precedence root first.

        [{"id", "name", "description", "mode", "model", "tools",
          "source", "json_path", "md_path", "complete"}, ...]

    Deduplicated by id: the first root that provides an id wins, and
    lower-precedence roots with the same id are skipped. An agent whose
    agent.json parsed but whose agent.md is missing is still returned,
    with ``complete: False``, so the UI can show it as a work in
    progress instead of it silently disappearing.
    """
    summaries: list[dict] = []
    claimed: set[str] = set()

    for root in roots.agent_roots():
        for agent_dir in root.agent_dirs():
            meta = _read_meta(agent_dir)
            if meta is None:
                # No readable agent.json: not an agent folder. A folder
                # with no meta at all is silently ignored, exactly as
                # before, so a half-created folder cannot break the list.
                continue

            agent_id = str(meta.get("id") or agent_dir.name)
            if agent_id in claimed:
                # A higher-precedence root already owns this id.
                continue
            claimed.add(agent_id)

            md_file = agent_dir / roots.AGENT_MD_FILE
            summaries.append({
                "id": agent_id,
                "name": meta.get("name") or agent_dir.name,
                "description": meta.get("description", "") or "",
                "mode": meta.get("mode", "chat") or "chat",
                "model": meta.get("model", "") or "",
                "tools": list(meta.get("tools") or []),
                "source": root.source,
                "json_path": root.json_path(agent_dir),
                "md_path": root.md_path(agent_dir),
                "complete": md_file.exists(),
            })

    return summaries


def get_agent_meta(agent_id: str) -> dict | None:
    """Return the summary for one agent id, or None if not registered."""
    for summary in list_agents():
        if summary["id"] == agent_id:
            return summary
    return None


__all__ = ["list_agents", "get_agent_meta", "AGENT_LIBRARY_DIR"]
