"""
tools/registry.py
=================

Central tool registry. Maps tool IDs (strings used in agent.json) to Python
callables. Agents declare which tools they need by ID; the factory resolves
those IDs here into actual functions.

All tool implementations live in tools/project_tools.py; their docstrings are
the schema the LLM sees. This module only wires them to their public IDs.

configure(provider) points the file tools at a Project Manager provider so a
bridge-bound headless runtime routes every tool call through the Project
Manager filesystem instead of the local disk.

Adding a new tool:
    1. Write the function in tools/project_tools.py (with a clear docstring)
    2. Import it below and add it to _TOOL_REGISTRY with its string ID
"""

from typing import Callable

from tools.project_tools import (
    configure as _configure_provider,
    map_files,
    read_file,
    write_text_file,
    delete_files,
    get_current_date,
    tell_me_the_date_and_time,
    search_chat_logs,
)
from tools.state import FileSession

# ---------------------------------------------------------------------------
# Canonical registry  –  tool_id -> callable
# ---------------------------------------------------------------------------
_TOOL_REGISTRY: dict[str, Callable] = {
    # File management
    "map_files": map_files,
    "read_file": read_file,
    "write_text_file": write_text_file,
    "delete_files": delete_files,

    # Date/time
    "get_current_date": get_current_date,
    "tell_me_the_date_and_time": tell_me_the_date_and_time,

    # RAG / search
    "search_chat_logs": search_chat_logs,
}

# Shared session instance (created once, shared across agents in a process)
_session = FileSession()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure(provider=None) -> None:
    """Point the file tools at a Project Manager provider (or None for local).

    Called by the factory when an agent is built with a bridge so the tools'
    file operations go through the correct filesystem authority.
    """
    _configure_provider(provider)


def get(tool_name: str) -> Callable | None:
    """Retrieve an executable tool by its registered name."""
    return _TOOL_REGISTRY.get(tool_name)


def list_tools() -> list[str]:
    """Returns a list of all registered tool names."""
    return list(_TOOL_REGISTRY.keys())


def available_tool_ids() -> list[str]:
    """Backward-compatible alias for list_tools()."""
    return list_tools()


def resolve_tools(tool_ids: list[str]) -> list[Callable]:
    """Map a list of tool ID strings to their callable functions.

    Unknown IDs are silently skipped (with a warning) so that agent
    definitions can reference tools that may not be installed.
    """
    resolved = []
    for tid in tool_ids:
        fn = _TOOL_REGISTRY.get(tid)
        if fn is not None:
            resolved.append(fn)
        else:
            print(f"[registry] WARNING: tool '{tid}' not found – skipped.")
    return resolved


def get_session() -> FileSession:
    """Return the shared FileSession instance."""
    return _session
