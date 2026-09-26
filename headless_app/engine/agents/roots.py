"""
engine/agents/roots.py
======================

Pluggable agent roots.

An *agent root* is a directory whose immediate children are agent folders
(one folder per agent, holding ``agent.json`` + ``agent.md``). The engine
registers exactly one root at import time::

    engine/agent_library/

so the headless runtime keeps working entirely on its own. A host
application may register further roots; the Project Manager registers
``workspace/agents/`` while its server is starting.

Once a root is registered, every lookup in the engine sees its agents -
there is no separate "library mode" and "workspace mode". ``build_agent``,
chat, single runs and pipelines all resolve agent ids through this module,
so an agent becomes runnable the moment its folder is discovered.

Precedence
----------
Roots are searched most-recently-registered first. A workspace agent
therefore shadows a library agent that declares the same ``id``, which is
the precedence the Project Manager already used when it looked up a single
definition. Re-registering a name replaces it and promotes it, so a server
that re-registers its root on every startup stays idempotent.

This module deliberately knows nothing about the Project Manager. The
wiring lives in the host application (see ``project_manager/server.py``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

#: Canonical file names inside an agent folder.
AGENT_META_FILE = "agent.json"
AGENT_MD_FILE = "agent.md"

#: The root the engine ships with.
LIBRARY_ROOT_NAME = "library"

DEFAULT_LIBRARY_DIR = (
    Path(__file__).resolve().parent.parent / "agent_library"
)


# ==========================================================================
# ROOT DESCRIPTOR
# ==========================================================================

@dataclass(frozen=True)
class AgentRoot:
    """One directory of agent folders."""

    name: str
    path: Path
    source: str

    def agent_dirs(self) -> Iterator[Path]:
        """Yield every candidate agent folder, sorted for determinism."""
        if not self.path.is_dir():
            return
        for child in sorted(self.path.iterdir()):
            if not child.is_dir() or child.name.startswith(("_", ".")):
                continue
            yield child

    def json_path(self, agent_dir: Path) -> str:
        """Workspace-relative ``agent.json`` path for the agent API."""
        return str(agent_dir / AGENT_META_FILE).replace("\\", "/")

    def md_path(self, agent_dir: Path) -> str:
        """Workspace-relative ``agent.md`` path for the agent API."""
        return str(agent_dir / AGENT_MD_FILE).replace("\\", "/")


# ==========================================================================
# ROOT REGISTRY
# ==========================================================================

#: Registered roots, lowest precedence first.
_roots: list[AgentRoot] = []


def register_agent_root(
    name: str,
    path: str | Path,
    source: str | None = None,
) -> AgentRoot:
    """Register (or re-register) an agent root and give it top precedence.

    Args:
        name:    unique key, e.g. ``"workspace"``.
        path:    directory holding one folder per agent.
        source:  value reported as each agent's ``source``; defaults to
                 ``name``.

    Returns:
        The registered :class:`AgentRoot`.
    """
    resolved = Path(path).expanduser().resolve()
    root = AgentRoot(name=name, path=resolved, source=source or name)
    unregister_agent_root(name)
    _roots.append(root)
    return root


def unregister_agent_root(name: str) -> bool:
    """Remove a root by name. Returns True when something was removed."""
    for index, existing in enumerate(_roots):
        if existing.name == name:
            del _roots[index]
            return True
    return False


def agent_roots() -> list[AgentRoot]:
    """Registered roots, highest precedence first."""
    return list(reversed(_roots))


def get_root(name: str) -> AgentRoot | None:
    for root in agent_roots():
        if root.name == name:
            return root
    return None


def reset_agent_roots() -> AgentRoot:
    """Drop every root except the built-in library root (used by tests)."""
    _roots.clear()
    return register_agent_root(
        LIBRARY_ROOT_NAME, DEFAULT_LIBRARY_DIR, source="library"
    )


# The engine always has its bundled library available.
reset_agent_roots()


# ==========================================================================
# RESOLUTION
# ==========================================================================

def _read_meta(agent_dir: Path) -> dict | None:
    meta_file = agent_dir / AGENT_META_FILE
    if not meta_file.exists():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return meta if isinstance(meta, dict) else None


def find_agent(agent_id: str) -> tuple[AgentRoot, Path] | None:
    """Locate an agent folder by id across every registered root.

    Two strategies per root, tried highest precedence first:
        1. Literal: ``<root>/<agent_id>`` is a directory.
        2. Scan: read ``agent.json`` in each child folder and match its
           ``id`` field, so folder names and ids may differ (e.g. the
           ``Planner`` folder declaring id ``feature_planner_agent``).

    Returns:
        ``(root, agent_dir)`` for the winning match, else ``None``.
    """
    if not agent_id:
        return None

    for root in agent_roots():
        literal = root.path / agent_id
        if literal.is_dir():
            return root, literal

    for root in agent_roots():
        for child in root.agent_dirs():
            meta = _read_meta(child)
            if meta is not None and meta.get("id") == agent_id:
                return root, child

    return None


__all__ = [
    "AGENT_META_FILE",
    "AGENT_MD_FILE",
    "AgentRoot",
    "DEFAULT_LIBRARY_DIR",
    "LIBRARY_ROOT_NAME",
    "agent_roots",
    "find_agent",
    "get_root",
    "register_agent_root",
    "reset_agent_roots",
    "unregister_agent_root",
]
