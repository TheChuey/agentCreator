"""Project Manager operation/interface layer.

This package sits between the HTTP API and the filesystem.
It is not a replacement for the Project Manager; it provides a
clean set of operations that multiple interfaces (browser, AI
agents, scripts) can use.

Every filesystem mutation eventually goes through
parameters.filesystem.
"""

from .session import EditorManager, EditorSession
from .events import EventBus
from .operations import EditorInterface

__all__ = [
    "EditorManager",
    "EditorSession",
    "EventBus",
    "EditorInterface",
]
