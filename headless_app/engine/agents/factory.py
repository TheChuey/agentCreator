"""
app/agents/factory.py
=====================

Constructs runtime Agents from agent definitions.

    build_agent(agent_id, model, bridge)
        ↓
    loader.load_definition()      (agent.md + agent.json, via agent roots)
        ↓
    gate.allowed_tools()          (the agent's request → the grants in force)
        ↓
    registry: resolve tools       (IDs -> Python functions, provider bound)
        ↓
    PromptManager.build()         (sections + tool docstrings -> system prompt)
        ↓
    Agent  (with its own FileSession)

The caller never needs to know where definitions live or how prompts are
composed. Chat-mode agents get an empty tool list, which disables the
tool loop entirely - same Agent class, behavior driven by configuration.

Nothing here is process-wide: each agent gets its own tools (bound to its
own filesystem provider) and its own FileSession, so two agents can be
built and run side by side without sharing state.

The permission gate sits between the definition and the registry. An
``agent.json`` names the tools an agent would like; ``ws_controlPanel`` decides
which of those it actually gets. That is the only place a grant is made, so
an agent cannot hold a tool by naming it.
"""

import sys
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
from tools.registry import new_session, resolve_tools


#: The repository root. ``headless_app`` is a repository child, so two levels
#: up from this file is the root the control panel lives in.
_REPO_ROOT = Path(
    __file__
).resolve().parents[3]

#: The control panel's gate, resolved on first agent build rather than at
#: import. Importing it eagerly would make every ``import factory`` depend on
#: ``ws_controlPanel`` being importable, including in the standalone
#: ``run.py`` paths where only the engine is wanted.
_GATE = None


def permission_gate():
    """The workspace control panel's gate module.

    Puts the repository root on ``sys.path`` if it is not already there, then
    imports and caches ``ws_controlPanel.gate``. The repository already does
    this kind of path bootstrap in five places for ``headless_app``; this is
    the engine's copy, for the panel.

    If the panel is genuinely absent the factory falls back to granting
    whatever was requested, and says so loudly. That fallback is a
    deliberate choice: an engine that cannot find its permission file should
    still build agents and run the prompt tests, rather than taking the whole
    application down over a missing sibling directory. A server deployment
    that needs the gate closed should assert on it explicitly.

    Returns:
        The ``ws_controlPanel.gate`` module, or None when unavailable.
    """

    global _GATE

    if _GATE is not None:

        return _GATE

    if str(
        _REPO_ROOT
    ) not in sys.path:

        sys.path.insert(
            0,
            str(_REPO_ROOT),
        )

    try:

        from ws_controlPanel import gate as gate_module

    except Exception as error:

        print(
            "[factory] ws_controlPanel not importable "
            f"({error}); permission gating is OFF and every "
            "requested tool is granted. Check the panel is present."
        )

        return None

    _GATE = gate_module

    return _GATE


class AgentDefinitionError(ValueError):
    """A definition parsed, but cannot produce a working agent.

    Distinct from AgentNotFoundError (no definition at all) so callers can
    tell "this agent does not exist" from "this agent is broken".
    """


def _session_aware(
    func: Callable,
    session,
    agent_id: str = "",
) -> Callable:
    """Wrap a tool so its results are recorded into this agent's FileSession.

    Uses functools.wraps so inspect.signature() (and therefore the schema
    Ollama builds for tool calling) sees the REAL tool signature, not the
    wrapper's (*args, **kwargs).

    Standard tool response shape: {"success", "tool", "data": {...}, "error":}.
    Known data keys are translated into session state:
        files                   -> add_discovered(paths)
        path / path+content     -> record_read(...)
        filename/path (written) -> add_output(path)
        pending_files (delete)  -> mark_for_deletion(paths)

    Three gates live here, and they answer different questions.

    **Which tools** is settled once per agent build, in ``_assemble``, before
    this wrapper exists. An agent never holds a tool the policy refused, so
    there is nothing to check here about the tool itself.

    **Which paths** is settled here, per call, because a tool's path arguments
    are not known until the model supplies them. An agent can hold
    ``read_file`` over ``workspace/documentation/**`` and still be refused
    ``workspace/agents/helper/agent.json``. The refusal comes back in the
    ordinary tool-result shape, so the model reads it as an answer rather than
    a crash, and the wording names the path so it stops rather than retrying.

    **Which deletions** are settled by the two-step protocol below:
    delete_files(approved=True) can only delete paths that were previously
    PROPOSED (approved=False) and recorded in session.pending_deletion. Any path
    the model fabricates or invents is rejected instead of deleted. Because the
    session belongs to one agent, another agent's proposals can never authorize
    a deletion here.
    """
    import functools
    import inspect as _inspect

    tool_name = func.__name__

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Path gate, before anything touches the filesystem.
        targets = _path_arguments(
            func,
            args,
            kwargs,
        )

        if targets:
            refusal = _refuse_paths(
                agent_id,
                tool_name,
                targets,
            )

            if refusal is not None:

                return refusal

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


#: Argument names that carry a filesystem path. Matched by name because the
#: tools are plain functions with plain signatures -- there is no annotation
#: that says "this is a path" -- and the alternative, a hardcoded per-tool
#: table, would be a second list of the tools that could drift when a tool is
#: added.
PATH_ARGUMENT_NAMES = ("path", "output_path", "file_list", "paths")


def _path_arguments(
    func: Callable,
    args: tuple,
    kwargs: dict,
) -> list[str]:
    """Pull the filesystem paths out of one tool call's arguments.

    Args:
        func:
            The tool being called.
        args:
            Positional arguments as passed.
        kwargs:
            Keyword arguments as passed.

    Returns:
        Every path-like string argument, flattened out of lists. Empty when
        the tool takes no paths, which is how the no-path tools
        (``get_current_date``) skip the gate entirely.
    """

    import inspect as _inspect

    try:
        bound = _inspect.signature(func).bind(
            *args,
            **kwargs,
        )
        bound.apply_defaults()

    except TypeError:
        # The model produced arguments that do not fit the signature. That
        # is the agent loop's problem to report, not the gate's.
        return []

    found: list[str] = []

    for name, value in bound.arguments.items():

        if name not in PATH_ARGUMENT_NAMES:

            continue

        if isinstance(
            value,
            str,
        ):

            if value.strip():
                found.append(value)

        elif isinstance(
            value,
            (list, tuple, set),
        ):

            found.extend(
                str(item)
                for item in value
                if isinstance(item, str)
                and item.strip()
            )

    return found


def _refuse_paths(
    agent_id: str,
    tool_name: str,
    targets: list[str],
):
    """Ask the gate about one call's paths, or None when it permits them.

    Args:
        agent_id:
            The agent making the call.
        tool_name:
            The tool name.
        targets:
            The paths the call involves.

    Returns:
        None when the call may proceed, or a tool-result dict describing the
        refusal. Never raises: a permission problem is a result, not an
        exception, because the model has to be able to read it and react.
    """

    if not agent_id:

        return None

    gate = permission_gate()

    if gate is None:

        return None

    try:
        decision = gate.check_path(
            agent_id,
            tool_name,
            targets,
        )

    except Exception as error:
        # A gate that cannot answer must not become a gate that says yes.
        return {
            "success": False,
            "tool": tool_name,
            "data": {},
            "error": (
                f"Permission check failed and the call was refused: {error}"
            ),
        }

    if decision.allowed:

        return None

    return {
        "success": False,
        "tool": tool_name,
        "data": {"refused_paths": list(targets)},
        "error": decision.reason,
    }


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
    """Translate a tool result dict into this agent's FileSession state."""
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
    Pinning the real browse roots plus the agent's own folder and skills dir
    gives the model deterministic places to start with map_files, and an
    explicit instruction to stop guessing once a lookup fails.

    When a Project Manager bridge is present it is the filesystem authority,
    so its browse roots become the grounding roots instead of the local app.
    Every path the file tools exchange is root-qualified (``workspace/...``),
    so the block names the roots the way the tools spell them rather than
    describing a single root the model would then prefix by guesswork.
    """
    from pathlib import Path

    if bridge is not None:
        workspace_root = str(getattr(bridge, "workspace_root", ""))
        if not workspace_root:
            bridge_health = getattr(bridge, "health", lambda: {})()
            workspace_root = str((bridge_health or {}).get("root", ""))
        roots = _provider_roots(bridge)
    else:
        workspace_root = str(Path(__file__).resolve().parents[2].resolve())
        roots = []

    root = Path(workspace_root)
    skill_dir = Path(__file__).resolve().parents[2] / "skills"
    skills = ", ".join(sorted(p.name for p in skill_dir.glob("*.md"))) if skill_dir.is_dir() else ""

    block = [
        "GROUNDING (read this before you call any file tool)",
    ]
    if roots:
        block.append("- BROWSE ROOTS (every path you pass is prefixed with one of these):")
        for name, path, writable in roots:
            block.append(
                f"    {name}/  ->  {path}  ({'read/write' if writable else 'READ ONLY'})"
            )
        block.append(f"- WORKSPACE ROOT (absolute): {workspace_root}")
    else:
        block.append(f"- WORKSPACE ROOT: {workspace_root}")
    block.append(f"- THIS AGENT FOLDER: {str(agent_dir(agent_id).resolve())}")
    if skills:
        block.append(f"- SKILLS DIRECTORY: {str(skill_dir.resolve())} (files: {skills})")
    block += [
        "- Paths are root-qualified: write 'workspace/agents/agent.json', never",
        "  'workspace/source_files/...' (source_files is its own root, not a folder",
        "  inside workspace). Start by calling map_files on the root you need, then",
        "  read_file only on a path map_files returned.",
        "- Never call readonly tools on a bare filename, a '/path/to/...' placeholder, or any",
        "  path you invented. If a tool reports 'not found', DO NOT guess another filename:",
        "  run map_files on the root first and read what exists.",
    ]
    profile.system_prompt = profile.system_prompt + "\n\n" + "\n".join(block)


def _provider_roots(bridge) -> list[tuple[str, str, bool]]:
    """(name, absolute path, writable) for each Project Manager browse root.

    Best-effort: a bridge that cannot report its roots (an older server, a
    provider mounted differently) simply yields nothing, and the grounding
    block falls back to describing the workspace root alone.
    """
    try:
        raw = getattr(bridge, "roots", None)
        if callable(raw):
            raw = raw()
        roots = []
        for entry in raw or []:
            name = str(entry.get("name", "")).strip()
            path = str(entry.get("path", "")).strip()
            if not name or not path:
                continue
            roots.append((name, path, bool(entry.get("writable", False))))
        return roots
    except Exception:
        return []


def _assemble(
    meta: dict,
    sections: dict,
    agent_id: str,
    model: str | None,
    bridge=None,
) -> Agent:
    """Shared Agent construction from a parsed definition.

    Three things are deliberately per agent rather than per process:

    * the tools carry ``bridge`` as their own provider, so no build order or
      request ordering can redirect another agent's file operations;
    * the FileSession is created here, so discovered files, outputs and
      pending deletions belong to this agent alone;
    * the permission gate runs here, so a tool the agent was never granted is
      never built, never advertised to the model and never callable.
    """
    definition = {"meta": meta, "sections": sections}

    mode = (meta.get("mode") or "chat").lower()
    tool_ids = [] if mode == "chat" else (meta.get("tools") or [])

    # An agent.json 'tools' array is a *request*, not a grant. This is where
    # it becomes one: the panel's policy decides what this agent id may hold,
    # and anything it may not is dropped before resolve_tools sees it. Doing
    # the filter here rather than per call means a refusal costs nothing on
    # every subsequent tool round.
    if tool_ids:
        gate = permission_gate()

        if gate is None:
            # No panel: honour the request rather than silently handing the
            # agent an empty tool list, which would look like a broken agent.
            pass

        else:
            tool_ids, refused = gate.allowed_tools(
                agent_id,
                tool_ids,
            )
            gate.log_refusals(
                agent_id,
                refused,
            )

    tools: list[Callable] = resolve_tools(tool_ids, provider=bridge)

    profile = PromptManager.build(definition, tools)

    if not (profile.system_prompt or "").strip():
        raise AgentDefinitionError(
            f"Agent '{agent_id}' has an empty system prompt, so it would "
            f"reply with no instructions. Its agent.md needs at least one "
            f"section the prompt composer reads - '## role', '## purpose', "
            f"'## personality', '## boundaries', '## communication', "
            f"'## principles' or '## decision style' (see "
            f"engine/core/prompt.py KNOWN_SECTIONS)."
        )

    if tools:
        _append_grounding(agent_id, profile, bridge=bridge)

    resolved_model = model or meta.get("model") or None
    session = new_session()
    tools = [
        _session_aware(fn, session, agent_id)
        for fn in tools
    ]
    return Agent(model=resolved_model, tools=tools, profile=profile, session=session)


def build_agent(agent_id: str, model: str | None = None, bridge=None) -> Agent:
    """Build a ready-to-use Agent for the given agent_id.

    Args:
        agent_id: id inside any registered agent root (see
                  engine/agents/roots.py) - the bundled library or the
                  Project Manager workspace.
        model:    explicit model override; when empty, falls back to the
                  agent's own "model" field, then to ask_llm's resolution
                  (config/models.json > first Ollama model).
        bridge:   optional Project Manager bridge (HTTP client or direct
                  filesystem authority). When present, the agent's file tools
                  route through the Project Manager instead of the local disk.
                  It is bound to this agent only.

    Raises AgentNotFoundError if the definition is missing, and
    AgentDefinitionError if it exists but cannot build a usable agent.
    """
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

    Raises AgentNotFoundError if either file is missing/unreadable, and
    AgentDefinitionError if the definition cannot build a usable agent.
    """
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


__all__ = [
    "build_agent",
    "build_agent_from_definition",
    "replay_history",
    "AgentNotFoundError",
    "AgentDefinitionError",
]
