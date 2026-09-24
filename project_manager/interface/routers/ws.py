"""
Project Manager WebSocket router.
=================================

Real-time interface sync for the Project Manager. Every client
connection gets:

  * a dedicated EditorSession inside the shared EditorManager;
  * a subscription to the shared EventBus, so every publish is
    forwarded to the browser over the same socket.

Not every publish reaches the browser -- only the projected
types the dashboard cares about (saved / created / renamed /
deleted / session events). Everything goes through the shared
EventBus; there is no direct filesystem access here.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter()


@router.websocket("/api/ws")
async def project_manager_socket(
    websocket: WebSocket,
) -> None:
    """
    Real-time Project Manager socket.

    Client -> Server (JSON messages):

        {"type": "open",        "path": "src/app.py"}
        {"type": "dirty",       "dirty": true}
        {"type": "subscribe",   "events": ["saved", "created"]}

    Server -> Client (JSON messages):

        {"type": "hello",        "client_id": "..."}
        {"type": "event",        "event": {publish payload}}
        {"type": "sessions",     "sessions": [...]}
    """

    await websocket.accept()

    controller = websocket.app.state.editor

    loop = asyncio.get_running_loop()

    session = controller.session_manager.register()

    try:

        await websocket.send_json(
            {
                "type": "hello",
                "client_id": session.client_id,
            }
        )

        def forward(
            event: dict[str, Any],
        ) -> None:
            """
            Forward a published event to this socket.

            ``EventBus.publish`` is called synchronously, and it can run on a
            worker thread (sync ``def`` endpoints run in the threadpool where
            there is no running event loop). We therefore capture the socket's
            loop up front and use ``loop.call_soon_threadsafe`` to hop back
            onto that loop before creating the send task -- a plain
            ``asyncio.create_task`` / ``get_running_loop`` here would raise
            ``RuntimeError`` on a worker thread and silently drop the event.
            """

            async def _send() -> None:

                try:

                    await websocket.send_json(
                        {
                            "type": "event",
                            "event": event,
                        }
                    )

                except Exception:

                    pass

            def _schedule() -> None:

                try:

                    loop.create_task(
                        _send()
                    )

                except Exception:

                    pass

            try:

                loop.call_soon_threadsafe(
                    _schedule
                )

            except Exception:

                pass

        subscription_id = controller.events.subscribe(
            forward,
        )

        async def _send_sessions() -> None:

            await websocket.send_json(
                {
                    "type": "sessions",
                    "sessions": controller.session_manager.snapshot(),
                }
            )

        await _send_sessions()

        while True:

            raw = await websocket.receive_text()

            try:

                message = json.loads(raw)

            except json.JSONDecodeError:

                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": "Message was not valid JSON.",
                    }
                )

                continue

            message_type = message.get(
                "type"
            )

            if message_type == "open":

                controller.session_manager.update(
                    session.client_id,
                    open_file=message.get(
                        "path"
                    ),
                )

                await websocket.send_json(
                    {
                        "type": "hello",
                        "client_id": session.client_id,
                        "open_file": message.get(
                            "path"
                        ),
                    }
                )

            elif message_type == "dirty":

                controller.session_manager.update(
                    session.client_id,
                    dirty=bool(
                        message.get(
                            "dirty",
                            False,
                        )
                    ),
                )

            elif message_type == "sessions":

                await _send_sessions()

            else:

                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": "Unknown message type: "
                        + str(message_type),
                    }
                )

    except WebSocketDisconnect:

        pass

    except Exception:

        pass

    finally:

        try:

            controller.events.unsubscribe(
                subscription_id  # type: ignore[possibly-undefined]
            )

        except Exception:

            pass

        controller.session_manager.unregister(
            session.client_id
        )
