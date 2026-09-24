"""
Project Manager — Python interface client.
============================================

Talk to the Project Manager over HTTP from any Python program or
AI agent.

The client is the *interface*. It never touches the filesystem; it
always goes through the running Project Manager server.

Sync client:
    >>> from interface.clients import EditorClient
    >>> client = EditorClient()
    >>> client.health()

Async client (for agents / async code):
    >>> from interface.clients import AsyncEditorClient
    >>> client = AsyncEditorClient()
    >>> await client.health()

WebSocket subscriptions (real-time events):
    >>> async for event in client.subscribe():
    ...     print(event)

File operations accept a ``scope`` argument:
    * ``"workspace"`` (default) — the managed workspace
    * ``"app"``               — the application repository (dev files)
"""

from __future__ import annotations

import asyncio
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


# ============================================================
# SYNC CLIENT
# ============================================================

class EditorClient:
    """
    Synchronous HTTP client for the Project Manager interface.

    All calls hit the running Project Manager server. Nothing is
    done directly against the filesystem.
    """

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

        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
        )

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
            params=params,
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
            params=params,
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
            params=params,
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
            params=params,
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
        return self._get("/api/project")

    def tree(self) -> dict[str, Any]:
        return self.project()

    def sessions(self) -> dict[str, Any]:
        return self._get("/api/sessions")

    # ========================================================
    # FILE OPERATIONS
    # ========================================================

    def read(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._get(
            "/api/file/read",
            path=_apply_project_root(path),
            scope=scope,
        )

    def open(
        self,
        path: str,
        scope: str = "workspace",
    ):
        """
        Open a project file and return its contents.

        Alias for read().
        """

        return self.read(path, scope=scope)

    def write(
        self,
        path: str,
        content: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._put(
            "/api/file/write",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope,
            },
        )

    def save(
        self,
        path: str,
        content: str,
        scope: str = "workspace",
    ):
        """
        Save file content. Alias for write().
        """

        return self.write(path, content, scope=scope)

    def create_file(
        self,
        path: str,
        content: str = "",
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._post(
            "/api/file/create",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope,
            },
        )

    def delete_file(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._delete(
            "/api/file/delete",
            path=_apply_project_root(path),
            scope=scope,
        )

    # ========================================================
    # DIRECTORY OPERATIONS
    # ========================================================

    def create_directory(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._post(
            "/api/directory/create",
            params={
                "path": _apply_project_root(path),
                "scope": scope,
            },
        )

    def delete_directory(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._delete(
            "/api/directory/delete",
            path=_apply_project_root(path),
            scope=scope,
        )

    # ========================================================
    # RENAME / MOVE OPERATIONS
    # ========================================================

    def rename(
        self,
        old_path: str,
        new_path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return self._put(
            "/api/path/rename",
            payload={
                "old_path": _apply_project_root(old_path),
                "new_path": _apply_project_root(new_path),
                "scope": scope,
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
        Open a WebSocket and yield events as they arrive.

        Returns:
            Synchronous iterator over Project Manager event dicts.
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

    def close(self) -> None:
        self._http.close()

    # context-manager support
    def __enter__(self) -> "EditorClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _decode_message(message: Any) -> dict[str, Any]:
    """
    Turn a raw WebSocket message into an event dict.

    Handles bytes and str payloads.
    """

    if isinstance(message, bytes):

        import json

        return json.loads(
            message.decode(
                "utf-8"
            )
        )

    import json

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
# ASYNC CLIENT
# ============================================================

class AsyncEditorClient:
    """
    Asynchronous HTTP + WebSocket client for AI agents.

    Provides the same operations as EditorClient but with
    async/await, plus ``subscribe()`` for real-time events.
    """

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

        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
        )

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
            params=params,
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
            params=params,
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
            params=params,
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
            params=params,
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
        return await self._get("/api/project")

    async def tree(self) -> dict[str, Any]:
        return await self.project()

    async def sessions(self) -> dict[str, Any]:
        return await self._get("/api/sessions")

    async def read(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._get(
            "/api/file/read",
            path=_apply_project_root(path),
            scope=scope,
        )

    async def open(
        self,
        path: str,
        scope: str = "workspace",
    ):
        return await self.read(path, scope=scope)

    async def write(
        self,
        path: str,
        content: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._put(
            "/api/file/write",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope,
            },
        )

    async def save(
        self,
        path: str,
        content: str,
        scope: str = "workspace",
    ):
        return await self.write(path, content, scope=scope)

    async def create_file(
        self,
        path: str,
        content: str = "",
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._post(
            "/api/file/create",
            payload={
                "path": _apply_project_root(path),
                "content": content,
                "scope": scope,
            },
        )

    async def delete_file(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._delete(
            "/api/file/delete",
            path=_apply_project_root(path),
            scope=scope,
        )

    async def create_directory(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._post(
            "/api/directory/create",
            params={
                "path": _apply_project_root(path),
                "scope": scope,
            },
        )

    async def delete_directory(
        self,
        path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._delete(
            "/api/directory/delete",
            path=_apply_project_root(path),
            scope=scope,
        )

    async def rename(
        self,
        old_path: str,
        new_path: str,
        scope: str = "workspace",
    ) -> dict[str, Any]:
        return await self._put(
            "/api/path/rename",
            payload={
                "old_path": _apply_project_root(old_path),
                "new_path": _apply_project_root(new_path),
                "scope": scope,
            },
        )

    # ========================================================
    # REAL-TIME SUBSCRIPTION
    # ========================================================

    async def subscribe(
        self,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Open a WebSocket and yield Project Manager events.

        Example:
            >>> async for event in client.subscribe():
            ...     if event["type"] == "saved":
            ...         print("Saved", event["path"])
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
