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


def _target(
    path: str,
    scope: str | None,
) -> tuple[str, Path, str | None]:
    """
    Resolve a request path into the arguments the filesystem
    operations expect.

    A path prefixed with a browser root (``source_files/AGENTS.md``)
    resolves inside that root. Anything else keeps the legacy
    behaviour and resolves against the scope's root.

    Returns:
        ``(stripped_relative, root, root_name)``.
    """

    return _filesystem.resolve_browse_target(
        path,
        _root_for(scope),
    )


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

    def _browse_roots(self) -> list[dict[str, Any]]:
        """Every configured browser root, with its absolute path.

        Read-only, in declaration order. Clients that speak the
        root-qualified path vocabulary (``workspace/...``) need the
        absolute path behind each root name to turn one back into a
        filesystem path, and the writable flag to decide whether a
        write may be attempted at all.
        """

        return [
            {
                "name": name,
                "path": str(config["path"]),
                "writable": bool(
                    config.get("writable", False)
                ),
            }
            for name, config
            in self.filesystem.BROWSE_ROOTS.items()
        ]

    def health(self) -> dict[str, Any]:
        """
        Project Manager health and project information.
        """

        return {
            "status": "healthy",
            "project": self.filesystem.read_project_info(),
            "root": str(self.filesystem.PROJECT_ROOT),
            "roots": self._browse_roots(),
        }

    def tree(
        self,
        scope: str | None = None,
        roots: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Project state: project info, active root and filesystem tree.

        Args:
            scope:
                None (default) returns the browser tree, whose top
                level is the configured ``BROWSE_ROOTS`` folders.
                ``"workspace"`` or ``"app"`` return the legacy
                single-root tree for that scope.
            roots:
                Browser roots to include, or None for all of them.
                Ignored when ``scope`` is set: the legacy view is
                already a single root, so there is nothing to
                choose between. This filters the listing only --
                the returned roots stay resolvable everywhere.
        """

        try:

            if not scope:

                browse_roots = (
                    self.filesystem.BROWSE_ROOTS
                )

                if roots is not None:

                    wanted = set(roots)

                    browse_roots = {
                        name: config
                        for name, config in browse_roots.items()
                        if name in wanted
                    }

                return {
                    "scope": None,
                    "project": self.filesystem.read_project_info(),
                    "roots": [
                        {
                            "name": name,
                            "path": str(config["path"]),
                            "writable": bool(
                                config.get(
                                    "writable",
                                    False,
                                )
                            ),
                        }
                        for name, config
                        in browse_roots.items()
                    ],
                    "root": str(
                        self.filesystem.PROJECT_ROOT
                    ),
                    "filesystem": (
                        self.filesystem.read_browse_filesystem(
                            roots=roots
                        )
                    ),
                }

            root = _root_for(scope)

            return {
                "scope": scope,
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
        scope: str | None = None,
    ) -> str:
        """
        Open a project file and return its contents.

        Args:
            path:
                Root-qualified or root-relative file path.
            scope:
                ``None`` (default) or ``"workspace"`` or ``"app"``.

        Returns:
            The file contents.
        """

        stripped, root, _ = _target(path, scope)

        return self.filesystem.read_file(
            stripped,
            root=root,
        )

    def save(
        self,
        path: str,
        content: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Write file contents back to the project filesystem.

        Publishes a ``saved`` event on success. Raises ValueError
        if the path targets a read-only browser root.
        """

        self.filesystem.require_writable(
            path,
            _root_for(scope),
        )

        stripped, root, _ = _target(path, scope)

        self.filesystem.write_file(
            stripped,
            content,
            root=root,
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
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new project file.

        Publishes a ``created`` event on success. Raises ValueError
        if the path targets a read-only browser root.
        """

        self.filesystem.require_writable(
            path,
            _root_for(scope),
        )

        stripped, root, _ = _target(path, scope)

        self.filesystem.create_file(
            stripped,
            content,
            root=root,
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
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new project directory.

        Publishes a ``created`` event on success. Raises ValueError
        if the path targets a read-only browser root.
        """

        self.filesystem.require_writable(
            path,
            _root_for(scope),
        )

        stripped, root, _ = _target(path, scope)

        self.filesystem.create_directory(
            stripped,
            root=root,
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
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Rename or move a project file/directory.

        Publishes a ``renamed`` event on success. Raises ValueError
        if either path targets a read-only browser root, or if the
        two paths belong to different browser roots.
        """

        self.filesystem.require_writable(
            old_path,
            _root_for(scope),
        )

        self.filesystem.require_writable(
            new_path,
            _root_for(scope),
        )

        old_stripped, old_root, old_name = _target(
            old_path,
            scope,
        )

        new_stripped, new_root, new_name = _target(
            new_path,
            scope,
        )

        if old_root != new_root:

            raise ValueError(
                "Cannot rename across browser roots "
                f"({old_name or 'scope'} -> "
                f"{new_name or 'scope'})."
            )

        self.filesystem.rename_path(
            old_stripped,
            new_stripped,
            root=old_root,
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
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Delete a project file or directory.

        Publishes a ``deleted`` event on success. Raises ValueError
        if the path targets a read-only browser root.
        """

        self.filesystem.require_writable(
            path,
            _root_for(scope),
        )

        stripped, root, _ = _target(path, scope)

        self.filesystem.delete_path(
            stripped,
            root=root,
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
