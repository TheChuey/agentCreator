"""
Workspace Paths
===============

The single authority on **where the workspace is** and **what may be
reached inside it**.

This module was extracted from
``project_manager/parameters/filesystem.py``, which now re-exports it. Two
things motivated the extraction:

1.  The repository contained *two* implementations of the same containment
    rule -- one here and a second, independent copy in
    ``project_manager/interface/routers/agents.py``. Two implementations of a
    security rule is one too many, so the second one was deleted and its only
    caller points here.
2.  A permission engine needs to reason about roots and containment without
    importing the server package. ``ws_controlPanel`` sits beside
    ``project_manager``, so it cannot reach into it.

The vocabulary the rest of the repository uses:

``ROOTS``
    The folders the file browser shows, and the path prefixes the API
    understands. ``workspace/documentation/tools/registry.py`` resolves inside
    the ``workspace`` root; ``source_files/APP_CODE_SNAPSHOT.md`` resolves
    inside ``source_files``.

root-qualified path
    A relative path that begins with a root name. This is the form every
    path the agent tools exchange takes, and the form
    ``policy.json`` writes its globs in.

legacy path
    A relative path with no known root prefix. It resolves against the
    caller's ``legacy_root``, which defaults to the managed workspace. This
    is what every pre-existing API caller sends.

The traversal check is deliberately paranoid: it resolves symlinks and
junctions before comparing, so a link pointing out of the workspace is
refused rather than followed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


# ============================================================
# ROOT DISCOVERY
# ============================================================

PANEL_DIR = Path(__file__).resolve().parent

#: The git repository root. This package is a repository child, so its own
#: location identifies the whole repository.
AGENTCREATOR_ROOT = PANEL_DIR.parent

#: The application package (the FastAPI server). Named ``REPO_ROOT`` by
#: ``parameters.filesystem`` for historical reasons; here it is spelled
#: out, because "repo root" and "repository root" are different directories
#: in this project and confusing them is how a permission bug starts.
APP_ROOT = AGENTCREATOR_ROOT / "project_manager"

#: The managed project content. It is a repository sibling of the
#: application, not part of it, so it survives a rebuild of the server and is
#: browsable in its own right.
PROJECT_ROOT = AGENTCREATOR_ROOT / "workspace"

#: The isolated test environment. Also a repository sibling. The prompt
#: builder reads its parts from there and publishes agents into it, so it is
#: browsable and writable in its own right.
TEST_ENVIRONMENT_ROOT = AGENTCREATOR_ROOT / "test_environment"

#: Generated documentation. Read-only: it is produced by
#: ``scripts/gen_master_copy.py`` and hand edits would be overwritten by the
#: next regeneration.
SOURCE_FILES_ROOT = AGENTCREATOR_ROOT / "source_files"


# ============================================================
# BROWSER ROOTS
# ============================================================

#: The folders the file browser shows, and the roots a permission decision
#: can be made about. Add a folder here to make it appear in the tree; set
#: ``writable`` to False to make it browse-only.
#:
#: Keys are the path prefixes the API understands, so
#: ``source_files/APP_CODE_SNAPSHOT.md``, ``workspace/project.json`` and
#: ``test_environment/test_agents/demo_agent/agent.md`` each resolve inside
#: their own root.
#:
#: ``writable`` is the **floor**, not the whole policy. It is the one rule
#: that applies to everybody -- the human editing in the browser as well as
#: any agent. ``ws_controlPanel.policy`` sits above it and can only ever be
#: *more* restrictive, never less. See ``gate.require_path``.
ROOTS: dict[str, dict[str, Any]] = {
    "workspace": {
        "path": PROJECT_ROOT,
        "writable": True,
    },
    "test_environment": {
        "path": TEST_ENVIRONMENT_ROOT,
        "writable": True,
    },
    "source_files": {
        "path": SOURCE_FILES_ROOT,
        "writable": False,
    },
    # The application repository itself, so an agent can read the code it is
    # running -- ``headless_app/``, ``project_manager/``, ``ws_controlPanel/``.
    #
    # Read-only for the same reason ``source_files`` is: it is reference
    # material, not a build target, and an agent that could write here could
    # rewrite the permission engine that is refusing it.
    #
    # It is the outermost root and therefore contains the other three.
    # ``to_root_qualified`` matches the longest root first, so
    # ``workspace/notes.md`` still resolves to ``workspace`` and never to
    # ``repo/workspace/notes.md``.
    #
    # Reach is not permission. This root makes the paths *resolvable*; no
    # agent may read them until ``policy.json`` grants ``repo/**`` to it by
    # name, because the policy is default-deny. The browser's ``scope=app``
    # already reached this directory for humans -- this root is what brings
    # agents, the watcher and the documentation index into line with it.
    "repo": {
        "path": AGENTCREATOR_ROOT,
        "writable": False,
    },
}


#: Files above this size open read-only so the browser editor never tries to
#: render a multi-megabyte document.
MAX_EDITABLE_BYTES = 512 * 1024


# ============================================================
# FILE TYPES
# ============================================================

TEXT_EXTENSIONS = {
    ".py",
    ".pyw",
    ".txt",
    ".text",
    ".md",
    ".markdown",
    ".rst",
    ".tex",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".log",
    ".tsv",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".sql",
    ".xml",
    ".csv",
    ".env",
}


# ============================================================
# DIRECTORIES TO HIDE
# ============================================================

#: Display and indexing filters. Note these are *not* a security control: a
#: path inside an ignored directory is still refused by
#: ``resolve_project_path`` if it leaves the root. They exist so the tree,
#: the watcher and the documentation index agree on what counts as noise.
IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
}

#: Directory names ignored only when they sit directly inside a *named* root.
#: See ``should_ignore`` for why these are kept apart from the list above.
#:
#: ``repo/data`` holds the application's own runtime state --
#: ``chatlog/chat.log`` and ``toollog/tool_usage.jsonl``. The ``repo`` root
#: makes the repository readable in principle, and a transcript of everyone's
#: conversations is not reference material an agent should be able to read or
#: index. Keyed by root rather than listed flat, because ``data`` is an
#: ordinary name that a user may well have under ``workspace`` -- a flat list
#: would take their directory away along with ours.
IGNORED_ROOT_CHILDREN: dict[str, set[str]] = {
    "repo": {"data"},
}


# ============================================================
# ROOT LOOKUPS
# ============================================================

def root_names() -> list[str]:
    """Every root name, in declaration order.

    Returns:
        The keys of ``ROOTS``, which is the order the browser tree and the
        policy panel both present them in.
    """

    return list(
        ROOTS.keys()
    )


def root_path(
    root_name: str,
) -> Path:
    """The absolute path a root name refers to.

    Args:
        root_name:
            A key of ``ROOTS``.

    Returns:
        The absolute Path for that root.

    Raises:
        KeyError:
            If the name is not a known root.
    """

    return ROOTS[
        root_name
    ]["path"]


def existing_roots() -> list[str]:
    """Root names whose directory is actually on disk.

    A root can be declared but absent -- a fresh checkout may have no
    ``test_environment/output`` yet. Callers that need to walk the
    filesystem use this so they never stat a directory that does not exist.

    Returns:
        The subset of ``root_names()`` that exists on disk.
    """

    return [
        name
        for name in root_names()
        if root_path(name).is_dir()
    ]


def describe_roots() -> list[dict[str, Any]]:
    """Every root with the facts a UI needs to render it.

    Returns:
        One dict per root, in declaration order, each with ``name``,
        ``path``, ``writable`` and ``exists``.
    """

    return [
        {
            "name": name,
            "path": str(
                config["path"]
            ),
            "writable": bool(
                config.get(
                    "writable",
                    False,
                )
            ),
            "exists": bool(
                config["path"].is_dir()
            ),
        }
        for name, config in ROOTS.items()
    ]


# ============================================================
# CONTAINMENT
# ============================================================

def resolve_project_path(
    relative_path: str,
    root: Path | None = None,
) -> Path:
    """
    Convert a project-relative path into a safe absolute path.

    This prevents paths such as::

        ../../some_file.txt

    from escaping the active project root. Because the candidate is
    resolved *before* the comparison, a symlink or Windows junction
    pointing out of the root is refused rather than followed, and an
    absolute input (``/etc/passwd``, ``C:\\Windows\\...``) is caught by
    the same check because ``root / absolute`` yields the absolute path.

    Args:
        relative_path:
            Path relative to the active root.
        root:
            Filesystem root the path must stay inside. Defaults to
            the managed workspace.

    Returns:
        Safe absolute Path.

    Raises:
        ValueError:
            If the path is empty or outside the root.
    """

    if root is None:

        root = PROJECT_ROOT

    if not relative_path:

        raise ValueError(
            "A project-relative path is required."
        )

    # Normalize Windows separators.
    relative_path = relative_path.replace(
        "\\",
        "/",
    )

    # Resolve the root too, not just the candidate. The two have to be in the
    # same form for relative_to() to mean anything: a caller passing a
    # symlinked or ".."-bearing root would otherwise have a resolved
    # candidate compared against an unresolved root, and a path genuinely
    # inside the root would be refused as an escape. Resolving is
    # non-strict, so a root that does not exist yet is still usable.
    root = root.resolve()

    candidate = (
        root / relative_path
    ).resolve()

    try:

        candidate.relative_to(
            root
        )

    except ValueError:

        raise ValueError(
            "Access outside the project directory "
            "is not allowed."
        )

    return candidate


def should_ignore(path: Path) -> bool:
    """Whether a path falls inside an ignored directory.

    Two tiers, because the names do not all mean the same thing.

``IGNORED_DIRECTORIES`` holds names that are tool or version-control
    output wherever they appear -- a ``__pycache__`` is a ``__pycache__`` at
    any depth, and hiding one inside the workspace costs nothing.

    ``IGNORED_ROOT_CHILDREN`` holds ordinary names that are noise only under a
    *specific* root. ``repo/data`` is the case that matters now: the
    application's runtime state lives there and must not be readable or
    indexable, while ``workspace/data`` is perfectly legitimate project
    content. A single flat list would hide both, which is how a safety
    exclusion quietly becomes data loss.

    Args:
        path:
            Any path: absolute, root-qualified, or bare relative. A bare
            relative path is read as workspace-relative, matching the rule
            every other resolution in this module already uses.

    Returns:
        True when the path is inside an ignored directory.
    """

    parts = [
        part
        for part in path.parts
        if part not in (
            "",
            ".",
            "..",
        )
    ]

    if any(
        part in IGNORED_DIRECTORIES
        for part in parts
    ):

        return True

    # Work out which root this path belongs to, and what is left of it inside
    # that root. Three input forms have to be handled, because the tree passes
    # absolute paths, the policy matcher passes root-qualified strings, and
    # both may pass a bare relative path.
    root_name: str | None = None
    remainder: list[str] = parts

    if parts and parts[0] in ROOTS:

        root_name = parts[0]
        remainder = parts[1:]

    elif path.is_absolute():

        resolved = path.resolve()

        # Longest root first, so a nested root wins over the ``repo`` root
        # that contains it.
        for candidate in sorted(
            ROOTS,
            key=lambda name: len(
                str(ROOTS[name]["path"])
            ),
            reverse=True,
        ):

            if is_within(
                resolved,
                ROOTS[candidate]["path"],
            ):

                root_name = candidate
                remainder = [
                    part
                    for part in resolved.relative_to(
                        ROOTS[candidate]["path"].resolve()
                    ).parts
                ]
                break

    else:

        # A bare relative path means the managed workspace, which is the rule
        # resolve_project_path and split_root already apply.
        root_name = "workspace"

    hidden = IGNORED_ROOT_CHILDREN.get(
        root_name or "",
        set(),
    )

    return bool(
        remainder
        and remainder[0] in hidden
    )


# ============================================================
# ROOT RESOLUTION
# ============================================================

def split_root(
    relative_path: str,
) -> tuple[str | None, str]:
    """
    Split a path into its root name and the remainder.

    Args:
        relative_path:
            A root-qualified or legacy relative path.

    Returns:
        ``(root_name, remainder)``. ``root_name`` is None when the first
        segment is not a known root, meaning the caller should treat the
        path as legacy and root-relative.
    """

    normalized = relative_path.replace(
        "\\",
        "/",
    ).strip()

    head, separator, tail = normalized.partition(
        "/"
    )

    if not separator:

        return None, normalized

    if head in ROOTS:

        return head, tail

    return None, normalized


def is_writable_root(
    root_name: str | None,
) -> bool:
    """
    Whether a root accepts writes.

    This is the floor every write must clear, whoever is asking. Legacy
    (root-less) paths resolve against the managed workspace, which is
    writable, so they are allowed -- that is what every pre-existing API
    caller sends, and refusing them would break the editor.

    Args:
        root_name:
            A key of ``ROOTS``, or None for a legacy path.

    Returns:
        True when the target root is writable.

        An unrecognised root name is refused rather than raising. This
        function is reached with a name that came off the wire -- a browse
        request, a tool call -- and "workspce" is exactly the kind of typo a
        client sends. Letting that raise a KeyError would turn a typo into a
        500 and, worse, invite a caller to wrap the call in a broad
        ``except`` that then treats the failure as permission to proceed.
        Unknown means no.
    """

    if root_name is None:

        return True

    root = ROOTS.get(root_name)

    if root is None:

        return False

    return bool(
        root.get(
            "writable",
            False,
        )
    )


def resolve_browse_target(
    relative_path: str,
    legacy_root: Path | None = None,
) -> tuple[str, Path, str | None]:
    """
    Split a possibly root-qualified path into the arguments the
    filesystem operations expect.

    ``source_files/APP_CODE_SNAPSHOT.md`` resolves inside the
    ``source_files`` root. Paths without a known root prefix fall back to
    ``legacy_root`` (the managed workspace by default) so existing
    API callers are unaffected.

    Args:
        relative_path:
            Root-qualified or legacy relative path.
        legacy_root:
            Root used when the path carries no root prefix.

    Returns:
        ``(stripped_relative, root, root_name)``. ``root_name``
        is None for legacy paths.

    Raises:
        ValueError:
            If the path is empty or names a root with no remainder.
    """

    root_name, remainder = split_root(
        relative_path
    )

    if root_name is None:

        return (
            relative_path,
            legacy_root
            if legacy_root is not None
            else PROJECT_ROOT,
            None,
        )

    if not remainder:

        raise ValueError(
            "A path inside "
            f"{root_name} is required."
        )

    return (
        remainder,
        ROOTS[root_name]["path"],
        root_name,
    )


def resolve_browse_path(
    relative_path: str,
    legacy_root: Path | None = None,
) -> tuple[Path, str | None]:
    """
    Resolve a possibly root-qualified path to a safe absolute path.

    Args:
        relative_path:
            Root-qualified or legacy relative path.
        legacy_root:
            Root used when the path carries no root prefix.

    Returns:
        ``(absolute_path, root_name)``. ``root_name`` is None for
        legacy paths.

    Raises:
        ValueError:
            If the path is empty or escapes its root.
    """

    stripped, root, root_name = (
        resolve_browse_target(
            relative_path,
            legacy_root,
        )
    )

    return resolve_project_path(
        stripped,
        root,
    ), root_name


def require_writable(
    relative_path: str,
    legacy_root: Path | None = None,
) -> str | None:
    """
    Ensure a path clears the writability floor.

    This is the base rule, not the whole permission system. It answers one
    question -- *is this root writable by anyone?* -- and it applies to the
    human editing in the browser exactly as it applies to an agent. The
    per-agent, per-tool rules in ``ws_controlPanel.policy`` sit above it and
    are consulted by ``gate.require_path``, never instead of it.

    Args:
        relative_path:
            Root-qualified or legacy relative path.
        legacy_root:
            Root used when the path carries no root prefix.

    Returns:
        The resolved root name (None for legacy paths).

    Raises:
        ValueError:
            If the path targets a read-only root, or escapes it.
    """

    _, root_name = resolve_browse_path(
        relative_path,
        legacy_root,
    )

    if not is_writable_root(root_name):

        raise ValueError(
            f"{root_name} is read-only."
        )

    return root_name


# ============================================================
# ROOT-QUALIFIED FORM
# ============================================================

def to_root_qualified(
    path: str | Path,
    default_root: str = "workspace",
) -> str:
    """
    Put a path into the root-qualified form the tools and the policy share.

    The agent tools exchange absolute Windows paths as often as relative
    ones, and ``policy.json`` is written in root-qualified form
    (``workspace/documentation/**``). Both have to become the same string
    before a rule can match, so this is the one function that does the
    translation.

    An absolute path is matched against every root, longest first, so
    ``E:\\agentCreator\\workspace\\documentation\\x.md`` becomes
    ``workspace/documentation/x.md`` rather than being misfiled under a
    sibling root that happens to share a name prefix.

    A relative path is *resolved* before it is qualified, never merely
    prefixed. This is load-bearing rather than tidiness: a path such as
    ``../../escape.md`` string-prefixed onto its root becomes
    ``workspace/../../escape.md``, which the glob ``workspace/**``
    matches -- so a traversal attempt would be granted by a rule written
    for something else entirely. Resolving first collapses the traversal
    and either lands on a real path inside the root or raises.

    Args:
        path:
            An absolute path, a root-qualified relative path, or a bare
            relative path.
        default_root:
            The root a bare relative path is assumed to live in.

    Returns:
        The path with forward slashes and a root name prefix.

    Raises:
        ValueError:
            If the path is empty, or resolves outside every declared
            root. Such a path has no root-qualified form and therefore no
            rule that could describe it, so it is refused rather than
            guessed at.
    """

    text = str(
        path
    ).strip()

    if not text:

        raise ValueError(
            "A project-relative path is required."
        )

    text = text.replace(
        "\\",
        "/",
    )

    if not Path(text).is_absolute():

        # A path that already names a root is split first, so the
        # remainder is resolved against the root and the prefix is
        # re-attached exactly once. Resolving the whole string would
        # treat the root name as a subfolder and yield
        # 'workspace/workspace/...'.
        declared_root, remainder = split_root(
            text
        )

        if declared_root is not None:

            resolved = resolve_project_path(
                remainder,
                ROOTS[declared_root]["path"],
            )

            return _qualify_resolved(
                resolved,
                fallback=declared_root,
            )

        resolved = resolve_project_path(
            text,
            ROOTS[default_root]["path"]
            if default_root in ROOTS
            else PROJECT_ROOT,
        )

        return _qualify_resolved(
            resolved,
            fallback=default_root,
        )

    candidate = Path(text).resolve()

    return _qualify_resolved(
        candidate,
        fallback=default_root,
    )


def _qualify_resolved(
    resolved: Path,
    fallback: str,
) -> str:
    """Render an already-resolved absolute path in root-qualified form.

    Args:
        resolved:
            An absolute path that has already been checked for
            containment.
        fallback:
            Root name to use when the path is the root itself and so has
            no remainder.

    Returns:
        ``<root>/<remainder>``, or just ``<root>`` at the root itself.

    Raises:
        ValueError:
            If the path lies outside every declared root.
    """

    matches = [
        name
        for name in root_names()
        if is_within(
            resolved,
            root_path(name),
        )
    ]

    if not matches:

        raise ValueError(
            "Access outside the project directory "
            "is not allowed."
        )

    # Longest root first, so nested roots resolve to the innermost match.
    winner = max(
        matches,
        key=lambda name: len(
            str(root_path(name))
        ),
    )

    inside = resolved.relative_to(
        root_path(winner).resolve()
    ).as_posix()

    if not inside or inside == ".":

        return winner

    return f"{winner}/{inside}"


def is_within(
    candidate: Path,
    root: Path,
) -> bool:
    """
    Whether a resolved path sits inside a root directory.

    Public because containment is the question the panel exists to answer
    authoritatively. The gate, the watcher and the future control-panel API
    all need to ask it, and an internal helper would force each of them to
    either catch an exception or reimplement the comparison. This is the
    comparison that has to be right: a string-prefix test would accept
    ``E:\\repo_backup`` as inside ``E:\\repo``.

    Args:
        candidate:
            An already-resolved absolute path.
        root:
            The root to test against. It is resolved here so a root
            expressed through a symlinked ancestor still matches.

    Returns:
        True when ``candidate`` is ``root`` or beneath it.
    """

    try:

        candidate.relative_to(
            root.resolve()
        )

    except ValueError:

        return False

    return True


def resolve_agent_path(
    relative_path: str,
    workspace_root: Path | None = None,
) -> Path:
    """
    Resolve a path an agent asked for, refusing anything outside.

    This replaces the second, independent containment check that used to
    live in ``project_manager/interface/routers/agents.py``. Both that copy
    and this one resolve before comparing and raise the same message, so
    deleting it changes no behaviour -- there is now one implementation of
    the rule instead of two that could drift.

    Args:
        relative_path:
            Workspace-relative (``agents/demo/agent.json``) or absolute.
            An absolute path is accepted only when it really is inside
            the workspace, so a queue saved from a previous session cannot
            reach outside the project.
            A root-qualified path is also accepted, and this function is
            where that matters: ``workspace/agents/demo/agent.json`` is the
            same file as ``agents/demo/agent.json``, so the ``workspace/``
            prefix is stripped rather than prepended. Without that, resolving
            the already-qualified form produced
            ``workspace/workspace/agents/demo/agent.json`` and raised
            "outside the project directory" on a path that was never
            anywhere but inside it.
        workspace_root:
            The workspace boundary. Defaults to the managed workspace.

    Returns:
        Safe absolute Path.

    Raises:
        ValueError:
            If the path is empty, or resolves outside the workspace.
    """

    if not relative_path:

        raise ValueError(
            "A project-relative path is required."
        )

    boundary = (
        workspace_root
        if workspace_root is not None
        else PROJECT_ROOT
    )

    candidate = Path(relative_path)

    if candidate.is_absolute():

        return _require_inside(
            candidate,
            boundary,
        )

    # Agent paths are workspace-relative, so an explicit root prefix is
    # redundant rather than meaningful. Drop it before resolving, otherwise
    # the root is counted twice.
    _, remainder = split_root(relative_path)

    return resolve_project_path(
        remainder,
        boundary,
    )


def _require_inside(
    candidate: Path,
    boundary: Path,
) -> Path:
    """Resolve an absolute path and insist it lands inside the boundary.

    Args:
        candidate:
            The absolute path to check.
        boundary:
            The directory it must stay within.

    Returns:
        The resolved absolute path.

    Raises:
        ValueError:
            If the resolved path is outside the boundary.
    """

    resolved = candidate.resolve()

    try:

        resolved.relative_to(
            boundary.resolve()
        )

    except ValueError:

        raise ValueError(
            "Access outside the project directory "
            "is not allowed."
        )

    return resolved