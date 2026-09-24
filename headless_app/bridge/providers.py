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

    workspace_root (str)    .relpath(path) -> posix relative (or raises)
    .list_tree() -> nested  .read(rel) -> str    .write(rel, content)
    .create(rel, content)   .delete(rel)         .exists(rel) -> bool
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bridge.client import _relpath


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
        self.scope = "workspace"

    # --------------------------------------------------------
    # PROVIDER SURFACE
    # --------------------------------------------------------

    @property
    def workspace_root(self) -> str:
        return str(self._root)

    def relpath(self, path: str) -> str:
        return _relpath(self._root, path)

    def list_tree(self) -> list:
        return self._filesystem.read_filesystem()

    def read(self, rel: str) -> str:
        return self._filesystem.read_file(rel)

    def write(self, rel: str, content: str) -> dict[str, Any]:
        self._filesystem.write_file(rel, content)
        return {"status": "saved", "path": rel, "scope": self.scope}

    def create(self, rel: str, content: str) -> dict[str, Any]:
        self._filesystem.create_file(rel, content)
        return {"status": "created", "path": rel, "scope": self.scope}

    def delete(self, rel: str) -> dict[str, Any]:
        self._filesystem.delete_path(rel)
        return {"status": "deleted", "path": rel, "scope": self.scope}

    def exists(self, rel: str) -> bool:
        target = (self._root / rel.replace("\\", "/").strip("/")).resolve()
        try:
            target.relative_to(self._root.resolve())
        except ValueError:
            return False
        return target.exists()

    # --------------------------------------------------------
    # PROJECT MANAGER CONVENIENCES
    # --------------------------------------------------------

    def health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "project": self._filesystem.read_project_info(),
            "root": str(self._root),
        }

    def tree(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "project": self._filesystem.read_project_info(),
            "root": str(self._root),
            "filesystem": self._filesystem.read_filesystem(),
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
        }


__all__ = ["DirectProjectIO"]