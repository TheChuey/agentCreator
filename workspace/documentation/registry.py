"""
tools/registry.py
=================

Central tool registry. Maps tool IDs (strings used in agent.json) to Python
callables. Agents declare which tools they need by ID; the factory resolves
those IDs here into actual functions.

All tool implementations live in tools/project_tools.py; their docstrings are
the schema the LLM sees. This module only wires them to their public IDs.

Binding, not configuration
--------------------------
``resolve_tools(ids, provider)`` returns tools that carry their own filesystem
provider. The provider is activated for the duration of each call (see
``tools.project_tools.using``), so two agents built with different providers -
for example one running inside the Project Manager and one on the local disk -
never overwrite each other's state. A ContextVar makes that binding local to
the running thread/task.

``configure(provider)`` still sets a process-wide default, but it is only a
fallback for callers that do not bind a provider (the standalone CLI, and
``bridge/tools_adapter.py``). The factory does not use it.

Adding a new tool:
    1. Write the function in tools/project_tools.py (with a clear docstring)
    2. Import it below and add it to _TOOL_REGISTRY with its string ID
"""

from typing import Any, Callable

from tools.project_tools import (
    configure as _configure_provider,
    map_files,
    read_file,
    write_text_file,
    delete_files,
    get_current_date,
    tell_me_the_date_and_time,
    search_chat_logs,
    using as _using_provider,
)
from tools.state import FileSession

# ---------------------------------------------------------------------------
# Canonical registry  ->  tool_id -> callable
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


# ---------------------------------------------------------------------------
# Provider binding
# ---------------------------------------------------------------------------

def _bind(func: Callable, provider: Any) -> Callable:
    """Return ``func`` with ``provider`` active for the duration of each call.

    The wrapper is transparent to the LLM: name, docstring, signature and
    annotations are copied from the real tool, so the schema Ollama builds is
    byte-for-byte the same as for an unbound tool.
    """
    import functools
    import inspect as _inspect

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _using_provider(provider):
            return func(*args, **kwargs)

    wrapper.__signature__ = _inspect.signature(func)
    wrapper.__annotations__ = func.__annotations__
    wrapper.__bound_provider__ = provider
    return wrapper


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure(provider=None) -> None:
    """Set the process-wide default provider (or None for local disk).

    Only a fallback: tools resolved with an explicit provider ignore it.
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


def resolve_tools(tool_ids: list[str], provider: Any = None) -> list[Callable]:
    """Map a list of tool ID strings to their callable functions.

    Args:
        tool_ids:  IDs as written in agent.json.
        provider:  filesystem provider bound to every returned tool. None
                   means "use the process default".

    Unknown IDs are silently skipped (with a warning) so that agent
    definitions can reference tools that may not be installed.
    """
    resolved = []
    for tid in tool_ids:
        fn = _TOOL_REGISTRY.get(tid)
        if fn is not None:
            resolved.append(_bind(fn, provider) if provider is not None else fn)
        else:
            print(f"[registry] WARNING: tool '{tid}' not found - skipped.")
    return resolved


def new_session() -> FileSession:
    """Create a FileSession owned by exactly one agent.

    Sessions hold discovered files, read paths, outputs and pending deletions.
    They are per agent so the delete-approval gate cannot be satisfied by a
    different agent's proposal.
    """
    return FileSession()


#: Process-wide default session, kept for callers that predate per-agent
#: sessions (and for the CLI's single-agent runs). The factory never uses it.
_session = FileSession()


def get_session() -> FileSession:
    """Return the shared default FileSession instance."""
    return _session
