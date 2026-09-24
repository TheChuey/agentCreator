"""
Project Manager event system.
=============================

A small publish/subscribe event bus. Changes inside the Project
Manager publish events so that the browser and future agents can
receive information without monitoring the filesystem directly.

Example event:
    {
        "type": "saved",
        "path": "app.py"
    }
"""

from __future__ import annotations

import uuid
from typing import Any, Callable


# ============================================================
# EVENT TYPES
# ============================================================

EVENT_TYPES = {
    "saved",
    "created",
    "renamed",
    "deleted",
    "tree_changed",
}


# ============================================================
# EVENT BUS
# ============================================================

class EventBus:
    """
    Simple in-memory publish/subscribe event bus.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, Callable[[dict[str, Any]], None]] = {}

    def subscribe(
        self,
        callback: Callable[[dict[str, Any]], None],
    ) -> str:
        """
        Subscribe a callback to every project event.

        Args:
            callback:
                Function called with each published event dict.

        Returns:
            Subscription id (use with unsubscribe()).
        """

        subscription_id = uuid.uuid4().hex

        self._subscribers[subscription_id] = callback

        return subscription_id

    def unsubscribe(self, subscription_id: str) -> None:
        """
        Remove a subscription.
        """

        self._subscribers.pop(subscription_id, None)

    def publish(
        self,
        event_type: str,
        path: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event_type:
                One of EVENT_TYPES.
            path:
                Optional project-relative path the event refers to.
            kwargs:
                Extra fields merged into the event payload.
        """

        event: dict[str, Any] = {
            "type": event_type,
        }

        if path is not None:
            event["path"] = path

        event.update(kwargs)

        for callback in list(self._subscribers.values()):
            callback(event)
