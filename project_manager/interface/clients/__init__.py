"""Project Manager Python interface client package.

Talk to the Project Manager over HTTP from any Python program or
AI agent::

    from interface.clients import EditorClient

    client = EditorClient()
    client.health()

The async agent client::

    from interface.clients import AsyncEditorClient
"""

from .editor_client import EditorClient, AsyncEditorClient

__all__ = [
    "EditorClient",
    "AsyncEditorClient",
]
