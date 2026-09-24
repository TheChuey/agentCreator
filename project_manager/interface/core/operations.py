"""
Project Manager operation layer.
=================================

This is the single controller that HTTP routers, the browser, and
the Python client all funnel through.

The controller does NOT implement filesystem logic. Every filesystem
operation is delegated to parameters.filesystem, which
remains the sovereign owner of the Project Manager filesystem.

    Router / Client
        ↓
    EditorInterface
        ↓
    parameters.filesystem
        ↓
    Filesystem

Scopes
------
Operations address files relative to an active root chosen by scope:

    * workspace  ->  the managed workspace (default)
    * app        ->  the application repository root (dev files)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from parameters import filesystem as _filesystem
from .events import EventBus
from .session import EditorManager


# ============================================================
# SCOPES
# ============================================================

VALID_SCOPES = ("workspace", "app")


def _root_for(scope: str | None) -> Path:
    """
    Resolve a scope string into a filesystem root.

    ``app`` reaches the application repository root (dev files);
    everything else defaults to the managed workspace.
    """

    if scope == "app":

        return _filesystem.REPO_ROOT

    return _filesystem.PROJECT_ROOT


# ============================================================
# EDITOR INTERFACE
# ============================================================

class EditorInterface:
    """
    The Project Manager operation/interface layer.

    Provides a narrow set of high-level operations agents and the
    web editor can use. All filesystem work goes through
    parameters.filesystem.
    """

    def __init__(
        self,
        filesystem: Any = None,
        events: EventBus | None = None,
        sessions: EditorManager | None = None,
    ) -> None:

        # The Project Manager remains the filesystem authority.
        self.filesystem = (
            filesystem
            if filesystem is not None
            else _filesystem
        )

        self.events = (
            events
            if events is not None
            else EventBus()
        )

        self.session_manager = (
            sessions
            if sessions is not None
            else EditorManager()
        )

    # ========================================================
    # HEALTH / STATE
    # ========================================================

    def health(self) -> dict[str, Any]:
        """
        Project Manager health and project information.
        """

        return {
            "status": "healthy",
            "project": self.filesystem.read_project_info(),
            "root": str(self.filesystem.PROJECT_ROOT),
        }

    def tree(
        self,
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Project state: project info, active root and filesystem tree.

        Args:
            scope:
                ``"workspace"`` (default) or ``"app"``.
        """

        try:

            root = _root_for(scope)

            return {
                "scope": scope or "workspace",
                "project": self.filesystem.read_project_info(),
                "root": str(root),
                "filesystem": self.filesystem.read_filesystem(
                    directory=root
                ),
            }

        except Exception as error:

            raise self._to_error(
                error
            )

    def sessions(self) -> list[dict[str, Any]]:
        """
        Snapshot of all connected interface sessions.
        """

        return self.session_manager.snapshot()

    # ========================================================
    # READ / WRITE
    # ========================================================

    def open(
        self,
        path: str,
        scope: str | None = "workspace",
    ) -> str:
        """
        Open a project file and return its contents.

        Args:
            path:
                Root-relative file path.
            scope:
                ``"workspace"`` (default) or ``"app"``.

        Returns:
            The file contents.
        """

        return self.filesystem.read_file(
            path,
            root=_root_for(scope),
        )

    def save(
        self,
        path: str,
        content: str,
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Write file contents back to the project filesystem.

        Publishes a ``saved`` event on success.
        """

        self.filesystem.write_file(
            path,
            content,
            root=_root_for(scope),
        )

        self.events.publish(
            "saved",
            path=path,
            scope=scope,
        )

        return {
            "status": "saved",
            "path": path,
            "scope": scope,
        }

    # ========================================================
    # CREATE
    # ========================================================

    def create_file(
        self,
        path: str,
        content: str = "",
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Create a new project file.

        Publishes a ``created`` event on success.
        """

        self.filesystem.create_file(
            path,
            content,
            root=_root_for(scope),
        )

        self.events.publish(
            "created",
            path=path,
            scope=scope,
        )

        return {
            "status": "created",
            "path": path,
            "scope": scope,
        }

    def create_directory(
        self,
        path: str,
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Create a new project directory.

        Publishes a ``created`` event on success.
        """

        self.filesystem.create_directory(
            path,
            root=_root_for(scope),
        )

        self.events.publish(
            "created",
            path=path,
            scope=scope,
        )

        return {
            "status": "created",
            "path": path,
            "scope": scope,
        }

    # ========================================================
    # RENAME
    # ========================================================

    def rename(
        self,
        old_path: str,
        new_path: str,
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Rename or move a project file/directory.

        Publishes a ``renamed`` event on success.
        """

        self.filesystem.rename_path(
            old_path,
            new_path,
            root=_root_for(scope),
        )

        self.events.publish(
            "renamed",
            path=new_path,
            old_path=old_path,
            scope=scope,
        )

        return {
            "status": "renamed",
            "old_path": old_path,
            "new_path": new_path,
            "scope": scope,
        }

    # ========================================================
    # DELETE
    # ========================================================

    def delete(
        self,
        path: str,
        scope: str | None = "workspace",
    ) -> dict[str, Any]:
        """
        Delete a project file or directory.

        Publishes a ``deleted`` event on success.
        """

        self.filesystem.delete_path(
            path,
            root=_root_for(scope),
        )

        self.events.publish(
            "deleted",
            path=path,
            scope=scope,
        )

        return {
            "status": "deleted",
            "path": path,
            "scope": scope,
        }

    # ========================================================
    # ERROR MAPPING
    # ========================================================

    # Kept on the controller so every interface shares the same
    # error behaviour. See routers/error.py for the HTTP mapping.
    _to_error = staticmethod(
        lambda error: error
    )
