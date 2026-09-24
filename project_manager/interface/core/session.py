"""
Project Manager interface sessions.
====================================

Tracks connected interface clients (browser tabs, agents).

This is intentionally an in-memory system. No database.
"""

from __future__ import annotations

import time
import uuid
from typing import Any


# ============================================================
# EDITOR SESSION
# ============================================================

class EditorSession:
    """
    State for a single connected interface client.
    """

    def __init__(
        self,
        client_id: str | None = None,
    ) -> None:
        self.client_id = client_id or uuid.uuid4().hex
        self.open_file: str | None = None
        self.dirty: bool = False
        self.last_modified: float | None = None

    def snapshot(self) -> dict[str, Any]:
        """
        JSON-friendly copy of this session.
        """

        return {
            "client_id": self.client_id,
            "open_file": self.open_file,
            "dirty": self.dirty,
            "last_modified": self.last_modified,
        }

    def touch(self) -> None:
        """
        Update the last-modified timestamp.
        """

        self.last_modified = time.time()


# ============================================================
# EDITOR MANAGER
# ============================================================

class EditorManager:
    """
    Maintains the active in-memory interface sessions.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, EditorSession] = {}

    def register(self, client_id: str | None = None) -> EditorSession:
        """
        Register a new connected client.
        """

        session = EditorSession(client_id=client_id)
        session.touch()

        self._sessions[session.client_id] = session

        return session

    def unregister(self, client_id: str) -> None:
        """
        Remove a client session.
        """

        self._sessions.pop(client_id, None)

    def get(self, client_id: str) -> EditorSession | None:
        """
        Fetch a session by client id.
        """

        return self._sessions.get(client_id)

    def update(
        self,
        client_id: str,
        *,
        open_file: str | None = None,
        dirty: bool | None = None,
    ) -> EditorSession | None:
        """
        Update one field of a client session.

        Returns the session, or None if the client is unknown.
        """

        session = self._sessions.get(client_id)

        if session is None:
            return None

        session.touch()

        if open_file is not None:
            session.open_file = open_file

        if dirty is not None:
            session.dirty = dirty

        return session

    def snapshot(self) -> list[dict[str, Any]]:
        """
        JSON-friendly list of all active sessions.
        """

        return [
            session.snapshot()
            for session in self._sessions.values()
        ]
