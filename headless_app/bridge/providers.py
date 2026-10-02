"""
bridge/providers.py
===================

In-process Project Manager filesystem authority.

Used when the agent engine is mounted INSIDE a running Project Manager
server (the agent-backed /api/chat router). In that case a separate HTTP
loop-back bridge is unnecessary, so this provider drives the SAME
parameters.filesystem module the Project Manager itself uses - keeping the
Project Manager as the single filesystem owner even in-process.

It implements the provider surface the headless file tools expect, exactly
like the HTTP ProjectManagerBridge does:

    workspace_root (str)    .relpath(path) -> root-qualified rel (or raises)
    .list_tree() -> nested  .read(rel) -> str    .write(rel, content)
    .create(rel, content)   .delete(rel)         .exists(rel) -> bool
    .abspath(rel) -> str    .roots() -> root info

Every relative path the tools exchange is *root-qualified*: ``workspace/...``,
``test_environment/...`` or ``source_files/...``. That is the vocabulary the
Project Manager browser tree already speaks (see ``read_browse_filesystem``),
so what ``map_files`` returns can be handed straight back to ``read_file``
without either side having to guess which root a bare path belonged to.
Legacy workspace-relative paths (``agents/agent.json``) are still accepted and
are treated as ``workspace/agents/agent.json``.

``source_files`` is declared read-only in ``BROWSE_ROOTS``, so write, create
and delete go through ``require_writable`` and are refused there rather than
silently succeeding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bridge.client import _normalize


class DirectProjectIO:
    """
    Filesystem provider backed directly by the Project Manager's
    parameters.filesystem authority.

    Requires the Project Manager package to be importable
    (``from parameters import filesystem``).
    """

    def __init__(self) -> None:
        from parameters import filesystem

        self._filesystem = filesystem
        self._root = Path(filesystem.PROJECT_ROOT)
        self.scope = None

    # --------------------------------------------------------
    # BROWSER ROOTS
    # --------------------------------------------------------

    def roots(self) -> list[dict[str, Any]]:
        """The browser roots, in the Project Manager's own declaration order."""
        return [
            {
                "name": name,
                "path": str(Path(config["path"])),
                "writable": bool(config.get("writable", False)),
            }
            for name, config in self._filesystem.BROWSE_ROOTS.items()
        ]

    def _root_for_path(self, path: Path) -> tuple[str, Path] | None:
        """The (name, directory) browse root that contains ``path``, if any."""
        for name, config in self._filesystem.BROWSE_ROOTS.items():
            root = Path(config["path"]).resolve()
            if path == root:
                return name, root
            try:
                path.relative_to(root)
                return name, root
            except ValueError:
                continue
        return None

    # --------------------------------------------------------
    # PROVIDER SURFACE
    # --------------------------------------------------------

    @property
    def workspace_root(self) -> str:
        return str(self._root)

    def relpath(self, path: str) -> str:
        """Translate a path into a root-qualified relative path.

        Accepts an absolute path under any browse root, a path that is
        already root-qualified, or a legacy workspace-relative path. The
        repository root itself (an ancestor of every browse root) maps to "",
        which means "every root".
        """
        raw = str(path).strip()
        if not raw or raw in (".", "/", "\\"):
            return ""

        browse_roots = self._filesystem.BROWSE_ROOTS

        candidate = Path(raw)
        if candidate.is_absolute():
            resolved = candidate.resolve()
            located = self._root_for_path(resolved)
            if located is None:
                raise ValueError(
                    f"Path '{raw}' is outside every Project Manager browse "
                    f"root (workspace: {self._root}). Use a path inside "
                    "workspace/, test_environment/ or source_files/."
                )
            name, root = located
            remainder = resolved.relative_to(root).as_posix()
            if remainder == ".":
                return name
            return f"{name}/{remainder}"

        normalized = _normalize(raw)
        if not normalized:
            return ""

        # Already root-qualified: validate it names a real root.
        head = normalized.split("/", 1)[0]
        if head in browse_roots:
            if normalized == head:
                return head
            self._filesystem.resolve_browse_path(normalized)
            return normalized

        # Legacy workspace-relative path.
        self._filesystem.resolve_project_path(normalized, self._root)
        return f"workspace/{normalized}"

    def abspath(self, rel: str) -> str:
        """Absolute path for a root-qualified relative path."""
        resolved, _ = self._filesystem.resolve_browse_path(rel)
        return str(resolved)

    def list_tree(self) -> list:
        return self._filesystem.read_browse_filesystem()

    def _target(self, rel: str) -> tuple[str, Path, str | None]:
        """Split a relative path into the arguments the filesystem wants."""
        return self._filesystem.resolve_browse_target(rel)

    def read(self, rel: str) -> str:
        stripped, root, _ = self._target(rel)
        return self._filesystem.read_file(stripped, root)

    def write(self, rel: str, content: str) -> dict[str, Any]:
        self._filesystem.require_writable(rel)
        stripped, root, root_name = self._target(rel)
        self._filesystem.write_file(stripped, content, root)
        return {"status": "saved", "path": rel, "scope": root_name}

    def create(self, rel: str, content: str) -> dict[str, Any]:
        self._filesystem.require_writable(rel)
        stripped, root, root_name = self._target(rel)
        self._filesystem.create_file(stripped, content, root)
        return {"status": "created", "path": rel, "scope": root_name}

    def delete(self, rel: str) -> dict[str, Any]:
        self._filesystem.require_writable(rel)
        stripped, root, root_name = self._target(rel)
        self._filesystem.delete_path(stripped, root)
        return {"status": "deleted", "path": rel, "scope": root_name}

    def exists(self, rel: str) -> bool:
        try:
            resolved, _ = self._filesystem.resolve_browse_path(rel)
        except ValueError:
            return False
        return resolved.exists()

    # --------------------------------------------------------
    # PROJECT MANAGER CONVENIENCES
    # --------------------------------------------------------

    def health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "project": self._filesystem.read_project_info(),
            "root": str(self._root),
            "roots": self.roots(),
        }

    def tree(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "project": self._filesystem.read_project_info(),
            "root": str(self._root),
            "roots": self.roots(),
            "filesystem": self._filesystem.read_browse_filesystem(),
        }

    def project(self) -> dict[str, Any]:
        return self.tree()

    def sessions(self) -> list:
        return []

    def expose(self) -> dict[str, Any]:
        return {
            "mode": "direct",
            "workspace_root": self.workspace_root,
            "scope": self.scope,
            "roots": self.roots(),
        }


__all__ = ["DirectProjectIO"]