"""
bridge/tools_adapter.py
=======================

Maps the headless agent tools to their Project Manager HTTP surface and
binds a bridge to the tool registry.

The tools themselves live in tools/project_tools.py and branch on the
configured provider; this module is the wiring point that turns a bridge
(or direct provider) into the active filesystem authority for all agents
built afterwards.

TOOL_ENDPOINT_MAP documents, for each tool id, the Project Manager endpoint
the tool ultimately drives when a bridge is connected.
"""

from __future__ import annotations

from typing import Any

import tools.registry as _registry

#: Tool id -> Project Manager endpoint backing it (informational).
TOOL_ENDPOINT_MAP: dict[str, str] = {
    "map_files": "GET /api/project (filesystem tree)",
    "read_file": "GET /api/file/read",
    "write_text_file": "PUT /api/file/write | POST /api/file/create",
    "delete_files": "DELETE /api/file/delete",
    "get_current_date": "(local)",
    "tell_me_the_date_and_time": "(local)",
    "search_chat_logs": "get data/chatlog/chat.log (local store)",
}


def bind_tools(bridge: Any) -> Any:
    """Point the tool registry's file tools at a Project Manager provider.

    Pass either a ProjectManagerBridge (HTTP) or a DirectProjectIO
    (in-process filesystem authority). Returns the same provider for
    convenience, so callers can chain it.

    All agents built AFTER this call route their file tools through the
    provider until configure(None) is called again.
    """
    _registry.configure(bridge)
    print(
        f"[tools_adapter] file tools bound to Project Manager "
        f"(root={getattr(bridge, 'workspace_root', '?')})"
    )
    return bridge


def unbind_tools() -> None:
    """Return the file tools to the local-disk backend."""
    _registry.configure(None)


def describe_tools() -> dict[str, str]:
    """Return the tool-id -> endpoint map for documentation/debugging."""
    return dict(TOOL_ENDPOINT_MAP)


__all__ = [
    "bind_tools",
    "unbind_tools",
    "describe_tools",
    "TOOL_ENDPOINT_MAP",
]