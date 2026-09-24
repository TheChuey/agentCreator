"""
app/agents/registry.py
======================

Automatic agent discovery.

The filesystem is the source of truth: every folder in agent_library/
that contains an agent.json is an available agent. Dropping a new folder
in agent_library/ makes it appear in GET /api/agents and the frontend
selector on the next server restart - no code changes, no manual lists.
"""

import json
from pathlib import Path

from engine.agents.loader import AGENT_LIBRARY_DIR


def list_agents() -> list[dict]:
    """Scan agent_library/ and return one summary per discovered agent:

        [{"id", "name", "description", "mode", "model"}, ...]

    Folders without a readable agent.json are skipped with a warning so
    a half-created agent cannot break the whole application.
    """
    agents = []
    if not AGENT_LIBRARY_DIR.exists():
        print(f"[REGISTRY] agent_library not found at {AGENT_LIBRARY_DIR}")
        return agents

    for agent_dir in sorted(AGENT_LIBRARY_DIR.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name.startswith(("_", ".")):
            continue

        meta_file = agent_dir / "agent.json"
        if not meta_file.exists():
            print(f"[REGISTRY] skipping {agent_dir.name}: no agent.json")
            continue

        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[REGISTRY] skipping {agent_dir.name}: unreadable agent.json ({exc})")
            continue

        # Fall back to the folder name when metadata is incomplete, so the
        # agent still shows up in the frontend.
        agents.append({
            "id": meta.get("id") or agent_dir.name,
            "name": meta.get("name") or agent_dir.name,
            "description": meta.get("description", ""),
            "mode": meta.get("mode", "chat"),
            "model": meta.get("model", "") or "",
        })

    return agents


def get_agent_meta(agent_id: str) -> dict | None:
    """Return the summary for one agent id, or None if not registered."""
    for summary in list_agents():
        if summary["id"] == agent_id:
            return summary
    return None
