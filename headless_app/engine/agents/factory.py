"""
app/agents/factory.py
=====================

Constructs runtime Agents from agent definitions.

    build_agent(agent_id, model)
        ↓
    loader.load_definition()      (agent.md + agent.json)
        ↓
    registry: resolve tools       (IDs -> Python functions)
        ↓
    PromptManager.build()         (sections + tool docstrings -> system prompt)
        ↓
    Agent

The caller never needs to know where definitions live or how prompts are
composed. Chat-mode agents get an empty tool list, which disables the
tool loop entirely - same Agent class, behavior driven by configuration.
"""

from typing import Callable
from pathlib import Path

from engine.agents.loader import (
    load_definition,
    load_definition_from_paths,
    agent_dir,
    AgentNotFoundError,
)
from engine.core.agent import Agent
from engine.core.prompt import PromptManager
from tools.registry import resolve_tools, get_session, configure as configure_tools


def _session_aware(func: Callable, session) -> Callable:
    """Wrap a tool so its results are recorded into the shared FileSession.

    Uses functools.wraps so inspect.signature() (and therefore the schema
    Ollama builds for tool calling) sees the REAL tool signature, not the
    wrapper's (*args, **kwargs).

    Standard tool response shape: {"success", "tool", "data": {...}, "error"}.
    Known data keys are translated into session state:
        files                   -> add_discovered(paths)
        path / path+content     -> record_read(...)
        filename/path (written) -> add_output(path)
        pending_files (delete)  -> mark_for_deletion(paths)

    Safety gate: delete_files(approved=True) can only delete paths that were
    previously PROPOSED (approved=False) and recorded in session.pending_deletion.
    Any path the model fabricates or invents is rejected instead of deleted.
    """
    import functools
    import inspect as _inspect

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if func.__name__ == "delete_files" and session is not None:
            bound, approved, file_list = _bind_delete_args(func, args, kwargs)
            if approved and file_list:
                pending = list(session.pending_deletion or [])
                proposed = [f for f in file_list if f in pending]
                rejected = [f for f in file_list if f not in pending]
                if not proposed:
                    return {
                        "success": False,
                        "tool": "delete_files",
                        "data": {},
                        "error": (
                            "Deletion blocked: none of these paths were previously "
                            "proposed for deletion. Run delete_files with "
                            "approved=False first."
                        ),
                    }
                bound.arguments["file_list"] = proposed
                try:
                    result = func(*bound.args, **bound.kwargs)
                except TypeError:
                    result = None
                if isinstance(result, dict):
                    data = result.get("data") or {}
                    data["rejected"] = rejected
                    if rejected and not result.get("error"):
                        result["error"] = "Some paths were not previously proposed and were skipped."
                    deleted = [k for k, v in data.get("results", {}).items() if v == "deleted"]
                    if deleted:
                        session.pending_deletion = [p for p in session.pending_deletion if p not in deleted]
                return result

        result = func(*args, **kwargs)
        _record_result(result, session)
        return result

    # Belt-and-braces: even if a future consumer uses follow_wrapped=False,
    # the wrapper advertises the real signature and annotations.
    wrapper.__signature__ = _inspect.signature(func)
    wrapper.__annotations__ = func.__annotations__
    return wrapper


def _bind_delete_args(func, args, kwargs):
    """Bind delete_files(*args, **kwargs) into (BoundArguments, approved, file_list)."""
    import inspect as _inspect
    try:
        bound = _inspect.signature(func).bind(*args, **kwargs)
        bound.apply_defaults()
    except TypeError:
        return None, False, []
    return bound, bool(bound.arguments.get("approved")), list(bound.arguments.get("file_list") or [])


def _record_result(result, session) -> None:
    """Translate a tool result dict into shared FileSession state."""
    if not (isinstance(result, dict) and session is not None):
        return
    from tools.state import FileSession
    data = result.get("data") or {}
    if result.get("tool") == "map_files":
        files = data.get("files") or []
        session.add_discovered([f["path"] for f in files])
    elif result.get("tool") == "read_file":
        session.record_read(data.get("path", ""), data.get("extracted_content", ""))
    elif result.get("tool") == "write_text_file" and data.get("path"):
        session.add_output(data["path"])
    elif result.get("tool") == "delete_files" and data.get("pending_files"):
        session.mark_for_deletion(data["pending_files"])


def _append_grounding(agent_id: str, profile, bridge=None) -> None:
    """Append a compact grounding block to a tool-armed agent's system prompt.

    Small local models routinely call path tools with invented paths, bare
    filenames, or literally '/path/to/...' placeholders copied from a prompt.
    Pinning a real WORKSPACE ROOT plus the agent's own folder and skills dir
    gives the model deterministic places to start with map_files, and an
    explicit instruction to stop guessing once a lookup fails.

    When a Project Manager bridge is present it is the filesystem authority,
    so its workspace root becomes the grounding root instead of the local app.
    """
    from pathlib import Path

    if bridge is not None:
        workspace_root = str(getattr(bridge, "workspace_root", ""))
        if not workspace_root:
            bridge_health = getattr(bridge, "health", lambda: {})()
            workspace_root = str((bridge_health or {}).get("root", ""))
    else:
        workspace_root = str(Path(__file__).resolve().parents[2].resolve())

    root = Path(workspace_root)
    skill_dir = Path(__file__).resolve().parents[2] / "skills"
    skills = ", ".join(sorted(p.name for p in skill_dir.glob("*.md"))) if skill_dir.is_dir() else ""

    block = [
        "GROUNDING (read this before you call any file tool)",
        f"- WORKSPACE ROOT: {workspace_root}",
        f"- THIS AGENT FOLDER: {str(agent_dir(agent_id).resolve())}",
    ]
    if skills:
        block.append(f"- SKILLS DIRECTORY: {str(skill_dir.resolve())} (files: {skills})")
    block += [
        "- Use file paths relative to WORKSPACE ROOT. Start by calling map_files on the",
        "  root, then read_file only on a path map_files returned.",
        "- Never call readonly tools on a bare filename, a '/path/to/...' placeholder, or any",
        "  path you invented. If a tool reports 'not found', DO NOT guess another filename:",
        "  run map_files on WORKSPACE ROOT / THIS AGENT FOLDER first and read what exists.",
    ]
    profile.system_prompt = profile.system_prompt + "\n\n" + "\n".join(block)


def _assemble(
    meta: dict,
    sections: dict,
    agent_id: str,
    model: str | None,
    bridge=None,
) -> Agent:
    """Shared Agent construction from a parsed definition."""
    definition = {"meta": meta, "sections": sections}

    mode = (meta.get("mode") or "chat").lower()
    tool_ids = [] if mode == "chat" else (meta.get("tools") or [])
    tools: list[Callable] = resolve_tools(tool_ids)

    profile = PromptManager.build(definition, tools)
    if tools:
        _append_grounding(agent_id, profile, bridge=bridge)

    resolved_model = model or meta.get("model") or None
    session = get_session()
    tools = [_session_aware(fn, session) for fn in tools]
    return Agent(model=resolved_model, tools=tools, profile=profile, session=session)


def build_agent(agent_id: str, model: str | None = None, bridge=None) -> Agent:
    """Build a ready-to-use Agent for the given agent_id.

    Args:
        agent_id: folder name / id inside agent_library/
        model:    explicit model override; when empty, falls back to the
                  agent's own "model" field, then to ask_llm's resolution
                  (config/models.json > first Ollama model).
        bridge:   optional Project Manager bridge (HTTP client or direct
                  filesystem authority). When present, the agent's file tools
                  route through the Project Manager instead of the local disk.

    Raises AgentNotFoundError if the definition is missing.
    """
    if bridge is not None:
        configure_tools(bridge)
    definition = load_definition(agent_id)
    return _assemble(
        definition["meta"],
        definition["sections"],
        agent_id,
        model,
        bridge=bridge,
    )


def build_agent_from_definition(
    json_path: str,
    md_path: str,
    model: str | None = None,
    bridge=None,
) -> Agent:
    """Build a ready-to-use Agent from explicit agent.json + agent.md paths.

    This is the headless construction path (run_single_agent, pipelines that
    take raw configs): the definition is loaded from any location, not only
    engine/agent_library/.

    Raises AgentNotFoundError if either file is missing/unreadable.
    """
    if bridge is not None:
        configure_tools(bridge)
    definition = load_definition_from_paths(json_path, md_path)
    meta = definition["meta"]
    agent_id = str(meta.get("id") or Path(json_path).parent.name or "custom")
    return _assemble(
        meta,
        definition["sections"],
        agent_id,
        model,
        bridge=bridge,
    )


def replay_history(agent: Agent, history: list[dict] | None) -> None:
    """Replay prior frontend turns ({role, content}) into the agent's history."""
    for m in (history or []):
        role = "assistant" if m.get("role") == "ai" else m.get("role", "user")
        content = m.get("content", "")
        if not content:
            continue
        agent.messages.append({"role": role, "content": content})


__all__ = ["build_agent", "build_agent_from_definition", "replay_history", "AgentNotFoundError"]
