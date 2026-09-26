"""
app/agents/loader.py
====================

Locates, reads, and parses one agent definition.

An agent folder contains:
    agent.json  - metadata/configuration (id, name, mode, tools, model)
    agent.md    - behavior sections (## role, ## purpose, ## boundaries, ...)

load_definition() returns:
    {"meta": {...agent.json...}, "sections": {...parsed markdown sections...}}

Where agents live is decided by engine/agents/roots.py: the engine ships
with ``agent_library/``, and a host application may register more roots
(the Project Manager registers ``workspace/agents/``). Lookups here search
every registered root, so an agent is found by id regardless of which root
owns it.

This module does NOT run agents. Its job is only: find, read, parse, return.
"""

import json
import re
from pathlib import Path

from engine.agents import roots
from engine.agents.roots import (  # noqa: F401  (re-exported for callers)
    AGENT_MD_FILE,
    AGENT_META_FILE,
    AgentRoot,
    LIBRARY_ROOT_NAME,
    register_agent_root,
    unregister_agent_root,
)

#: Backwards-compatible alias for the built-in library root directory.
AGENT_LIBRARY_DIR = roots.DEFAULT_LIBRARY_DIR


def agent_dir(agent_id: str) -> Path:
    """The folder for an agent id inside the highest-precedence root.

    Searches every registered root (see engine/agents/roots.py): first the
    literal ``<root>/<agent_id>`` path, then each root's folders matched by
    their ``agent.json`` ``id`` field, so folder names and ids may differ.
    Falls back to the literal library path so callers that create folders
    (``save_markdown``) still work for brand-new agents.
    """
    found = roots.find_agent(agent_id)
    if found is not None:
        return found[1]
    return AGENT_LIBRARY_DIR / agent_id


def agent_root(agent_id: str) -> AgentRoot | None:
    """The registered root that owns ``agent_id``, or None."""
    found = roots.find_agent(agent_id)
    return found[0] if found is not None else None


def agent_json_path(agent_id: str) -> str | None:
    """Workspace-relative ``agent.json`` path for a registered agent."""
    found = roots.find_agent(agent_id)
    if found is None:
        return None
    root, directory = found
    return root.json_path(directory)


def agent_md_path(agent_id: str) -> str | None:
    """Workspace-relative ``agent.md`` path for a registered agent."""
    found = roots.find_agent(agent_id)
    if found is None:
        return None
    root, directory = found
    return root.md_path(directory)


def _resolve_agent_dir(agent_id: str) -> Path | None:
    """Find the on-disk folder for an agent by id across all roots.

    Returns ``None`` when nothing matches so callers can fall back to the
    literal path (which preserves the existing create-folder semantics for
    ``save_markdown`` on genuinely new agents).
    """
    found = roots.find_agent(agent_id)
    return found[1] if found is not None else None


def save_meta(agent_id: str, meta: dict) -> dict:
    """Merge `meta` into the agent's agent.json (top-level keys only) and
    write it back pretty-printed. Unknown keys survive untouched."""
    agent_path = agent_dir(agent_id)
    meta_file = agent_path / AGENT_META_FILE
    if not meta_file.exists():
        raise AgentNotFoundError(f"Agent config not found: {meta_file}")

    stored = json.loads(meta_file.read_text(encoding="utf-8"))
    stored.update(meta)
    meta_file.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return stored


def save_markdown(agent_id: str, markdown: str) -> str:
    """Write the agent's behavior prose to agent.md."""
    agent_path = agent_dir(agent_id)
    agent_path.mkdir(parents=True, exist_ok=True)
    md_file = agent_path / AGENT_MD_FILE
    md_file.write_text(str(markdown), encoding="utf-8")
    return str(markdown)


def save_tests(agent_id: str, tests: list) -> list:
    """Store the agent's own chat tests under agent.json#tests.

    Tests are scoped by their location, so any stored `agentId` is dropped;
    ensures every test keeps a unique id.
    """
    normalized = []
    for test in tests or []:
        if not isinstance(test, dict):
            continue
        entry = dict(test)
        entry.pop("agentId", None)
        if not entry.get("id"):
            entry["id"] = "t-" + json.dumps(entry, sort_keys=True)[:8]
        normalized.append(entry)
    save_meta(agent_id, {"tests": normalized})
    return normalized


class AgentNotFoundError(FileNotFoundError):
    """Raised when an agent folder or its required files are missing."""


def _parse_sections(text: str) -> dict:
    """Split agent.md into '## <name>' sections (section name lowercased)."""
    sections = {}
    current = None
    buffer = []
    for line in text.splitlines(keepends=True):
        match = re.match(r"^\s*##\s+(.+?)\s*$", line)
        if match:
            if current is not None:
                sections[current] = "".join(buffer)
            current, buffer = match.group(1).strip().lower(), []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "".join(buffer)
    return sections


def _clean_body(text: str) -> str:
    """Trim blank lines and '---' separators from the edges of a section body."""
    lines = text.splitlines()
    while lines and (not lines[0].strip() or lines[0].strip() in ("---", "***")):
        lines.pop(0)
    while lines and (not lines[-1].strip() or lines[-1].strip() in ("---", "***")):
        lines.pop()
    return "\n".join(lines).strip("\n")


def load_definition(agent_id: str) -> dict:
    """Load one agent definition from agent_library/{agent_id}/.

    Returns {"meta": dict, "sections": dict}. Raises AgentNotFoundError
    when the folder or either required file is missing/unreadable.
    """
    agent_dir = _resolve_agent_dir(agent_id)
    if agent_dir is None:
        agent_dir = AGENT_LIBRARY_DIR / agent_id
    json_file = agent_dir / AGENT_META_FILE
    md_file = agent_dir / AGENT_MD_FILE

    if not json_file.exists():
        raise AgentNotFoundError(f"Agent not found: {json_file}")
    if not md_file.exists():
        raise AgentNotFoundError(f"Agent not found: {md_file}")

    try:
        meta = json.loads(json_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentNotFoundError(f"Agent config unreadable: {json_file} ({exc})")

    try:
        md_text = md_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise AgentNotFoundError(f"Agent markdown unreadable: {md_file} ({exc})")

    raw_sections = _parse_sections(md_text)
    # The '# Title' line before the first section is ignored; every
    # '## section' body gets whitespace/separator cleanup.
    sections = {name: _clean_body(body) for name, body in raw_sections.items()}

    return {"meta": meta, "sections": sections}


def load_definition_from_paths(
    json_path: str | Path,
    md_path: str | Path,
) -> dict:
    """Load one agent definition from explicit agent.json + agent.md paths.

    This is the headless entry point used when an agent's definition comes
    from arbitrary locations (e.g. ad-hoc agents built by run_single_agent)
    instead of the bundled engine/agent_library/.

    Returns {"meta": dict, "sections": dict}. Raises AgentNotFoundError
    when either file is missing/unreadable.
    """
    json_file = Path(json_path)
    md_file = Path(md_path)

    if not json_file.exists():
        raise AgentNotFoundError(f"Agent config not found: {json_file}")
    if not md_file.exists():
        raise AgentNotFoundError(f"Agent markdown not found: {md_file}")

    try:
        meta = json.loads(json_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentNotFoundError(f"Agent config unreadable: {json_file} ({exc})")

    try:
        md_text = md_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise AgentNotFoundError(f"Agent markdown unreadable: {md_file} ({exc})")

    raw_sections = _parse_sections(md_text)
    sections = {name: _clean_body(body) for name, body in raw_sections.items()}

    return {"meta": meta, "sections": sections}
