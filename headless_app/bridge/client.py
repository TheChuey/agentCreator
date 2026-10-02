"""
bridge/client.py
================

Project Manager bridge clients for the headless engine.

The bridge is the *interface* the headless agents use to reach the running
Project Manager. Every file operation goes through the Project Manager
server (or its direct in-process filesystem authority) - the bridge never
touches the project filesystem itself unless a direct provider is used.

Two transports:

    ProjectManagerBridge       - synchronous HTTP (+ sync WebSocket subscribe)
    AsyncProjectManagerBridge  - async/await HTTP (+ async WebSocket subscribe)

Both implement the provider surface the file tools expect:

    workspace_root (str)    .relpath(path) -> root-qualified rel (or raises)
    .list_tree() -> nested  .read(rel) -> str    .write(rel, content)
    .create(rel, content)   .delete(rel)         .exists(rel) -> bool
    .abspath(rel) -> str    .roots() -> root info

Relative paths crossing this boundary are *root-qualified*:
``workspace/...``, ``test_environment/...`` or ``source_files/...``, which is
the vocabulary the Project Manager browser tree already speaks. Legacy
workspace-relative paths are still accepted and qualified as ``workspace/...``.
The clients therefore send no ``scope`` parameter, so the server answers with
the browser view (all browse roots) rather than the legacy single-root view.

Plus Project Manager conveniences: health(), project(), sessions(),
rename(), create_directory(), delete_directory(), open(), subscribe().

The server responses follow the Project Manager contract:

    GET  /api/health          -> {"status", "project", "root"}
    GET  /api/project         -> {"scope", "project", "root", "filesystem"}
    GET  /api/file/read       -> {"path", "content", "scope"}
    PUT  /api/file/write      -> {"status": "saved", "path", "scope"}
    POST /api/file/create     -> {"status": "created", "path", "scope"}
    DELETE /api/file/delete   -> {"status": "deleted", "path", "scope"}
    DELETE /api/directory/delete -> {"status": "deleted", ...}
    POST /api/directory/create   -> {"status": "created", ...}
    PUT  /api/path/rename     -> {"status": "renamed", ...}
    WS   /api/ws              -> {"type": "event", "event": {...}} frames
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, AsyncIterator, Callable

import httpx
from websockets.asyncio.client import ClientConnection
from websockets.asyncio.client import connect as ws_connect


# ============================================================
# BASE URL DETECTION
# ============================================================

def _default_base_url() -> str:
    """
    Best-effort default: localhost on the standard Project Manager port.
    """

    import os

    return os.environ.get(
        "PROJECT_MANAGER_BASE_URL",
        "http://127.0.0.1:8000",
    )


def _apply_project_root(
    path: str,
    project_root: str = "",
) -> str:
    """
    Normalize a project-relative path into the API path form.
    """

    path = path.replace("\\", "/").strip("/")

    return path


# ============================================================
# SHARED RESPONSE MACHINERY
# ============================================================

def _raise_for_error(
    response: httpx.Response,
) -> None:
    """
    Turn a non-2xx response into a useful Python error.
    """

    if response.is_success:
        return

    detail = ""

    try:

        detail = response.json().get(
            "detail",
            "",
        )

    except Exception:
        pass

    message = detail or f"Project Manager error (HTTP {response.status_code})."

    raise RuntimeError(
        message
    )


def _decode_message(message: Any) -> dict[str, Any]:
    """
    Turn a raw WebSocket message into a dict (bytes or str payload).
    """

    import json

    if isinstance(message, bytes):
        return json.loads(
            message.decode(
                "utf-8"
            )
        )

    try:

        return json.loads(
            message
        )

    except Exception:

        return {
            "type": "message",
            "data": message,
        }


# ============================================================
# PATH HELPERS (shared by both clients)
# ============================================================

def _normalize(raw: str) -> str:
    return str(raw).replace("\\", "/").strip("/")


def _relpath(root: Path, path: str) -> str:
    """Translate an absolute-or-relative path into a posix relative path that
    stays inside the Project Manager workspace root. The root itself maps to
    "". Raises ValueError when the path would escape the root."""
    raw = str(path).strip()
    if not raw:
        return ""
    if raw in (".", "/", "\\"):
        return ""

    root = root.resolve()

    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        try:
            rel = resolved.relative_to(root)
        except ValueError:
            raise ValueError(
                f"Path '{raw}' is outside the Project Manager workspace root "
                f"({root})."
            )
        as_posix = rel.as_posix()
        return "" if as_posix == "." else as_posix

    joined = (root / _normalize(raw)).resolve()
    try:
        rel = joined.relative_to(root)
    except ValueError:
        raise ValueError(
            f"Path '{raw}' is outside the Project Manager workspace root "
            f"({root})."
        )
    as_posix = rel.as_posix()
    return "" if as_posix == "." else as_posix


def _relpath_roots(roots: dict[str, str], path: str) -> str:
    """Translate a path into a *root-qualified* posix path.

    ``roots`` maps each Project Manager browser-root name to its absolute
    path, which is the vocabulary the browser tree already speaks. The
    longest matching root wins, so a root nested inside another one would
    still resolve to the more specific name.

    Accepts an absolute path under any root, a path that is already
    root-qualified, or a legacy workspace-relative path (which is
    qualified as ``workspace/...``). The result is what
    ``map_files`` hands back and what ``read_file`` accepts.
    """

    raw = str(path).strip()
    if not raw or raw in (".", "/", "\\"):
        return ""

    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        ordered = sorted(
            roots.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        )
        for name, root in ordered:
            root_path = Path(root).resolve()
            if resolved == root_path:
                return name
            try:
                remainder = resolved.relative_to(root_path).as_posix()
            except ValueError:
                continue
            if remainder == ".":
                return name
            return f"{name}/{remainder}"
        raise ValueError(
            f"Path '{raw}' is outside every Project Manager browse root "
            f"({', '.join(sorted(roots))})."
        )

    normalized = _normalize(raw)
    if not normalized:
        return ""

    head = normalized.split("/", 1)[0]
    if head in roots:
        return head if normalized == head else normalized

    return f"workspace/{normalized}"


def _abspath_roots(roots: dict[str, str], rel: str) -> str:
    """Absolute path for a root-qualified relative path."""

    normalized = _normalize(rel)
    head = normalized.split("/", 1)[0] if normalized else ""
    if head in roots:
        remainder = normalized[len(head):].lstrip("/")
        return str(Path(roots[head]) / remainder) if remainder else str(Path(roots[head]))
    workspace = roots.get("workspace", "")
    return str(Path(workspace) / normalized) if workspace else normalized


def _clean_params(params: dict[str, Any] | None) -> dict[str, Any]:
    """Drop query parameters the caller left unset.

    ``httpx`` renders a ``None`` value as an empty string, so sending
    ``scope=None`` arrives as ``scope=``, which the Project Manager reads as
    an unknown scope rather than as "not supplied". It selects its browser
    (multi-root) view by *omitting* the parameter, so an unset value has to
    be omitted here rather than transmitted.
    """
    if not params:
        return {}
    return {key: value for key, value in params.items() if value is not None}


# ============================================================
# SYNC CLIENT
# ============================================================

class ProjectManagerBridge:
    """Synchronous HTTP bridge to the Project Manager server.

    Implements the provider surface used by the headless file tools and the
    Project Manager operations exposed by the original Python client.
    """

    #: how long a project tree snapshot is trusted (list/exists lookups)
    _TREE_TTL = 2.0

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (
            base_url
            if base_url is not None
            else _default_base_url()
        )
        self.timeout = timeout
        self.scope = None

        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
        )

        self._root: str | None = None
        self._roots: dict[str, str] | None = None
        self._tree_cache: tuple[float, list] = (0.0, [])

    # ========================================================
    # PROVIDER SURFACE
    # ========================================================

    @property
    def workspace_root(self) -> str:
        """The Project Manager workspace root (from /api/health)."""
        if self._root is None:
            health = self.health()
            self._root = str((health or {}).get("root", ""))
        if not self._root:
            raise RuntimeError(
                "Project Manager did not report a workspace root."
            )
        return self._root

    def _root_map(self) -> dict[str, str]:
        """Browse-root name -> absolute path, from /api/health."""
        if self._roots is None:
            health = self.health()
            roots: dict[str, str] = {}
            for entry in (health or {}).get("roots") or []:
                name = entry.get("name", "")
                path = entry.get("path", "")
                if name and path:
                    roots[name] = path
            if not roots:
                # An older server that reports no roots: the workspace is
                # still reachable, it just carries the legacy vocabulary.
                root = str((health or {}).get("root", ""))
                if root:
                    roots["workspace"] = root
            self._roots = roots
        return self._roots

    def roots(self) -> list[dict[str, Any]]:
        """The Project Manager browse roots, as the server reports them."""
        health = self.health()
        return list((health or {}).get("roots") or [])

    def relpath(self, path: str) -> str:
        return _relpath_roots(self._root_map(), path)

    def abspath(self, rel: str) -> str:
        return _abspath_roots(self._root_map(), rel)

    def _fresh_tree(self) -> list:
        now = time.monotonic()
        if now - self._tree_cache[0] < self._TREE_TTL:
            return self._tree_cache[1]
        tree: list = (self.tree() or {}).get("filesystem") or []
        self._tree_cache = (now, tree)
        return tree

    def list_tree(self) -> list:
        """Nested project tree ([{name, path, type, children?, size?}...])."""
        return self._fresh_tree()

    def read(self, rel: str) -> str:
        """Read a workspace text file; returns the content."""
        return self.open(rel)["content"]

    def write(self, rel: str, content: str) -> dict[str, Any]:
        return self._mutate(lambda: self.save(rel, content))

    def create(self, rel: str, content: str) -> dict[str, Any]:
        return self._mutate(lambda: self.create_file(rel, content))

    def delete(self, rel: str) -> dict[str, Any]:
        return self._mutate(lambda: self.delete_file(rel))

    def _mutate(self, call) -> dict[str, Any]:
        """Run a mutating call and drop the cached tree.

        ``exists`` answers from that tree, so a cached snapshot taken before
        a write makes this provider report a file it has just created as
        missing. That is not a cosmetic staleness issue: delete_files asks
        exists() before deleting, so a stale cache silently turns a delete
        into "file_not_found".
        """
        try:
            return call()
        finally:
            self._tree_cache = (0.0, [])

    def exists(self, rel: str) -> bool:
        rel = rel.replace("\\", "/").strip("/")
        for entry in self._flatten_paths():
            if entry == rel:
                return True
        return False

    def _flatten_paths(self) -> list[str]:
        paths: list[str] = []

        def walk(entries):
            for entry in entries or []:
                rel = entry.get("path", "")
                if rel:
                    paths.append(rel)
                walk(entry.get("children") or [])

        walk(self._fresh_tree())
        return paths

    # ========================================================
    # GET HELPERS
    # ========================================================

    def _get(
        self,
        endpoint: str,
        **params: Any,
    ) -> dict[str, Any]:
        response = self._http.get(
            endpoint,
            params=_clean_params(params),
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    def _put(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._http.put(
            endpoint,
            params=_clean_params(params),
            json=payload,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    def _post(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._http.post(
            endpoint,
            params=_clean_params(params),
            json=payload,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    def _delete(
        self,
        endpoint: str,
        **params: Any,
    ) -> dict[str, Any]:
        response = self._http.delete(
            endpoint,
            params=_clean_params(params),
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    # ========================================================
    # PROJECT OPERATIONS
    # ========================================================

    def health(self) -> dict[str, Any]:
        return self._get("/api/health")

    def project(self) -> dict[str, Any]:
        return self._get("/api/project", scope=self.scope)

    def tree(self) -> dict[str, Any]:
        return self.project()

    def sessions(self) -> dict[str, Any]:
        return self._get("/api/sessions")

    # ========================================================
    # FILE OPERATIONS
    # ========================================================

    def read_file(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._get(
            "/api/file/read",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    def open(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Open a project file and return its contents.
        """

        return self.read_file(path, scope=scope)

    def write_file(
        self,
        path: str,
        content: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._put(
            "/api/file/write",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope or self.scope,
            },
        )

    def save(
        self,
        path: str,
        content: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Save file content. Alias for write_file().
        """

        return self.write_file(path, content, scope=scope)

    def create_file(
        self,
        path: str,
        content: str = "",
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._post(
            "/api/file/create",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope or self.scope,
            },
        )

    def delete_file(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._delete(
            "/api/file/delete",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    # ========================================================
    # DIRECTORY OPERATIONS
    # ========================================================

    def create_directory(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._post(
            "/api/directory/create",
            params={
                "path": _apply_project_root(path),
                "scope": scope or self.scope,
            },
        )

    def delete_directory(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._delete(
            "/api/directory/delete",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    # ========================================================
    # RENAME / MOVE OPERATIONS
    # ========================================================

    def rename(
        self,
        old_path: str,
        new_path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return self._put(
            "/api/path/rename",
            payload={
                "old_path": _apply_project_root(old_path),
                "new_path": _apply_project_root(new_path),
                "scope": scope or self.scope,
            },
        )

    # ========================================================
    # LIFECYCLE
    # ========================================================

    def subscribe(
        self,
        *,
        timeout: float | None = None,
    ):
        """
        Open a WebSocket and yield Project Manager frames as they arrive.

        Frames keep the server contract: {"type": "event", "event": {...}}
        for project changes, {"type": "hello", ...} and
        {"type": "sessions", ...} for session state.
        """

        ws_url = self.base_url.replace(
            "http",
            "ws",
            count=1
        )

        ws_url = ws_url.rstrip("/") + "/api/ws"

        import websockets.sync.client as ws_sync

        with ws_sync.connect(
            ws_url,
            timeout=timeout,
        ) as socket:

            while True:

                message = socket.recv()

                if message is None:
                    break

                yield _decode_message(message)

    def expose(
        self,
    ) -> dict[str, Any]:
        """Self-description: which Project Manager endpoints the bridge uses."""
        return {
            "base_url": self.base_url,
            "workspace_root": self.workspace_root,
            "scope": self.scope,
        }

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "ProjectManagerBridge":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


# ============================================================
# ASYNC CLIENT
# ============================================================

class AsyncProjectManagerBridge:
    """Asynchronous HTTP + WebSocket bridge to the Project Manager.

    Provides the same operations as ProjectManagerBridge with async/await,
    plus subscribe() for real-time project events.
    """

    _TREE_TTL = 2.0

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (
            base_url
            if base_url is not None
            else _default_base_url()
        )
        self.timeout = timeout
        self.scope = None

        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
        )

        self._root: str | None = None
        self._roots: dict[str, str] | None = None
        self._tree_cache: tuple[float, list] = (0.0, [])

    # ========================================================
    # PROVIDER SURFACE (async)
    # ========================================================

    @property
    async def workspace_root(self) -> str:
        if self._root is None:
            health = await self.health()
            self._root = str((health or {}).get("root", ""))
        if not self._root:
            raise RuntimeError(
                "Project Manager did not report a workspace root."
            )
        return self._root

    async def _root_map(self) -> dict[str, str]:
        """Browse-root name -> absolute path, from /api/health."""
        if self._roots is None:
            health = await self.health()
            roots: dict[str, str] = {}
            for entry in (health or {}).get("roots") or []:
                name = entry.get("name", "")
                path = entry.get("path", "")
                if name and path:
                    roots[name] = path
            if not roots:
                root = str((health or {}).get("root", ""))
                if root:
                    roots["workspace"] = root
            self._roots = roots
        return self._roots

    async def roots(self) -> list[dict[str, Any]]:
        health = await self.health()
        return list((health or {}).get("roots") or [])

    async def relpath(self, path: str) -> str:
        return _relpath_roots(await self._root_map(), path)

    async def abspath(self, rel: str) -> str:
        return _abspath_roots(await self._root_map(), rel)

    async def _fresh_tree(self) -> list:
        now = time.monotonic()
        if now - self._tree_cache[0] < self._TREE_TTL:
            return self._tree_cache[1]
        payload = await self.tree()
        tree: list = (payload or {}).get("filesystem") or []
        self._tree_cache = (now, tree)
        return tree

    async def list_tree(self) -> list:
        return await self._fresh_tree()

    async def read(self, rel: str) -> str:
        return (await self.open(rel))["content"]

    async def write(self, rel: str, content: str) -> dict[str, Any]:
        return await self._mutate(lambda: self.save(rel, content))

    async def create(self, rel: str, content: str) -> dict[str, Any]:
        return await self._mutate(lambda: self.create_file(rel, content))

    async def delete(self, rel: str) -> dict[str, Any]:
        return await self._mutate(lambda: self.delete_file(rel))

    async def _mutate(self, call) -> dict[str, Any]:
        """Run a mutating call and drop the cached tree (see the sync class)."""
        try:
            return await call()
        finally:
            self._tree_cache = (0.0, [])

    async def exists(self, rel: str) -> bool:
        rel = rel.replace("\\", "/").strip("/")
        for path in await self._flatten_paths():
            if path == rel:
                return True
        return False

    async def _flatten_paths(self) -> list[str]:
        paths: list[str] = []

        def walk(entries):
            for entry in entries or []:
                rel = entry.get("path", "")
                if rel:
                    paths.append(rel)
                walk(entry.get("children") or [])

        walk(await self._fresh_tree())
        return paths

    # ========================================================
    # ASYNC HELPERS
    # ========================================================

    async def _get(
        self,
        endpoint: str,
        **params: Any,
    ) -> dict[str, Any]:
        response = await self._http.get(
            endpoint,
            params=_clean_params(params),
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    async def _put(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._http.put(
            endpoint,
            params=_clean_params(params),
            json=payload,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    async def _post(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._http.post(
            endpoint,
            params=_clean_params(params),
            json=payload,
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    async def _delete(
        self,
        endpoint: str,
        **params: Any,
    ) -> dict[str, Any]:
        response = await self._http.delete(
            endpoint,
            params=_clean_params(params),
        )

        _raise_for_error(response)

        if not response.content:
            return {}

        return response.json()

    # ========================================================
    # OPERATIONS (ASYNC)
    # ========================================================

    async def health(self) -> dict[str, Any]:
        return await self._get("/api/health")

    async def project(self) -> dict[str, Any]:
        return await self._get("/api/project", scope=self.scope)

    async def tree(self) -> dict[str, Any]:
        return await self.project()

    async def sessions(self) -> dict[str, Any]:
        return await self._get("/api/sessions")

    async def read_file(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._get(
            "/api/file/read",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    async def open(
        self,
        path: str,
        scope: str | None = None,
    ):
        return await self.read_file(path, scope=scope)

    async def write_file(
        self,
        path: str,
        content: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._put(
            "/api/file/write",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope or self.scope,
            },
        )

    async def save(
        self,
        path: str,
        content: str,
        scope: str | None = None,
    ):
        return await self.write_file(path, content, scope=scope)

    async def create_file(
        self,
        path: str,
        content: str = "",
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            "/api/file/create",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope or self.scope,
            },
        )

    async def delete_file(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._delete(
            "/api/file/delete",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    async def create_directory(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            "/api/directory/create",
            params={
                "path": _apply_project_root(path),
                "scope": scope or self.scope,
            },
        )

    async def delete_directory(
        self,
        path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._delete(
            "/api/directory/delete",
            path=_apply_project_root(path),
            scope=scope or self.scope,
        )

    async def rename(
        self,
        old_path: str,
        new_path: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        return await self._put(
            "/api/path/rename",
            payload={
                "old_path": _apply_project_root(old_path),
                "new_path": _apply_project_root(new_path),
                "scope": scope or self.scope,
            },
        )

    # ========================================================
    # REAL-TIME SUBSCRIPTION
    # ========================================================

    async def subscribe(
        self,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Open a WebSocket and yield Project Manager event frames.

        Example:
            >>> async for frame in client.subscribe():
            ...     if frame.get("type") == "event":
            ...         event = frame["event"]
            ...         if event["type"] == "saved":
            ...             print("Saved", event["path"])
        """

        ws_url = self.base_url.replace(
            "http",
            "ws",
            count=1
        )

        ws_url = ws_url.rstrip("/") + "/api/ws"

        async with ws_connect(
            ws_url
        ) as socket:

            async for message in socket:

                yield _decode_message(
                    message
                )

    async def expose(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "workspace_root": await self.workspace_root,
            "scope": self.scope,
        }

    async def close(self) -> None:
        await self._http.aclose()


__all__ = [
    "ProjectManagerBridge",
    "AsyncProjectManagerBridge",
    "_default_base_url",
]
