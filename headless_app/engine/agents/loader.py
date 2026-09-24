"""
app/agents/loader.py
====================

Locates, reads, and parses one agent definition from agent_library/.

An agent folder contains:
    agent.json  - metadata/configuration (id, name, mode, tools, model)
    agent.md    - behavior sections (## role, ## purpose, ## boundaries, ...)

load_definition() returns:
    {"meta": {...agent.json...}, "sections": {...parsed markdown sections...}}

This module does NOT run agents. Its job is only: find, read, parse, return.
"""

import json
import re
from pathlib import Path

AGENT_LIBRARY_DIR = Path(__file__).resolve().parent.parent / "agent_library"
AGENT_META_FILE = "agent.json"
AGENT_MD_FILE = "agent.md"


def agent_dir(agent_id: str) -> Path:
    """The folder for an agent id inside agent_library/.

    First tries the literal ``agent_library/<agent_id>`` path (fast path).
    When that is missing or not a directory, scans ``agent_library/*/agent.json``
    and returns the first folder (sorted) whose ``meta["id"]`` matches, so
    folder names with spaces, kebab-case, etc. all work as long as the
    ``agent.json`` ``id`` field is set. Falls back to the literal path so
    callers that create folders (``save_markdown``) still work for brand-new
    agents.
    """
    resolved = _resolve_agent_dir(agent_id)
    return resolved if resolved is not None else AGENT_LIBRARY_DIR / agent_id


def _resolve_agent_dir(agent_id: str) -> Path | None:
    """Find the on-disk folder for an agent by id.

    Two strategies, tried in order:
        1. Literal: ``AGENT_LIBRARY_DIR / agent_id`` exists and is a directory.
        2. Scan: walk every subfolder of ``AGENT_LIBRARY_DIR``, read its
           ``agent.json``, and return the first (sorted by folder name) whose
           ``meta["id"]`` equals ``agent_id``.

    Returns ``None`` when nothing matches so callers can fall back to the
    literal path (which preserves the existing create-folder semantics for
    ``save_markdown`` on genuinely new agents).
    """
    literal = AGENT_LIBRARY_DIR / agent_id
    if literal.is_dir():
        return literal

    # Scan: read agent.json in each sibling folder, match by "id" field.
    # Folders are sorted for deterministic tie-breaking when (unlikely)
    # multiple folders declare the same id.
    candidates: list[tuple[str, Path]] = []
    if AGENT_LIBRARY_DIR.exists():
        for child in AGENT_LIBRARY_DIR.iterdir():
            if not child.is_dir() or child.name.startswith(("_", ".")):
                continue
            meta_file = child / AGENT_META_FILE
            if not meta_file.exists():
                continue
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if meta.get("id") == agent_id:
                candidates.append((child.name, child))

    candidates.sort(key=lambda t: t[0])
    return candidates[0][1] if candidates else None


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
