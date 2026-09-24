"""Project Manager Server - application entry point.

Slim FastAPI host. The Project Manager remains the filesystem
authority (parameters.filesystem); this file only assembles the
three pillars and the static workspace:

    parameters          Project parameters (filesystem owner)
    workspace           The managed project content
    interface           Editor interface (core, routers, clients, static)

The controller is the single shared resource responsible for
turning Project Manager operations into HTTP contracts.

    interface/routers/project.py      Project state, health, sessions
    interface/routers/files.py        File CRUD / REST
    interface/routers/directories.py  Directory CRUD
    interface/routers/paths.py        Rename / move
    interface/routers/ws.py           Real-time WebSocket interface
    interface/routers/chat.py         Chat log (stub) interface
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from parameters import filesystem

from interface.routers.project import router as project_router
from interface.routers.files import router as files_router
from interface.routers.directories import router as directories_router
from interface.routers.paths import router as paths_router
from interface.routers.ws import router as ws_router
from interface.routers.chat import router as chat_router
from interface.routers.agents import router as agents_router

from interface.core.defaults import get_interface, get_events, get_sessions


# ============================================================
# CONFIGURATION
# ============================================================

HOST = os.environ.get(
    "PROJECT_MANAGER_HOST",
    "127.0.0.1",
)

PORT = int(
    os.environ.get(
        "PROJECT_MANAGER_PORT",
        "8000",
    )
)

PROJECT_ROOT = Path(__file__).resolve().parent

STATIC_DIR = PROJECT_ROOT / "interface" / "static"

HOME_HTML = STATIC_DIR / "home.html"

EDITOR_HTML = STATIC_DIR / "editor.html"

CHAT_HTML = STATIC_DIR / "chat.html"


# ============================================================
# APPLICATION FACTORY
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Build the basic project filesystem on startup.
    """

    filesystem.build_project_filesystem()

    yield


def create_app() -> FastAPI:
    """
    Assemble the Project Manager application.
    """

    app = FastAPI(
        title="Project Manager Server",
        description="Lightweight Project Manager workspace server.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # --------------------------------------------------------
    # Shared interface state
    # --------------------------------------------------------

    app.state.editor = get_interface()
    app.state.events = get_events()
    app.state.sessions = get_sessions()

    # --------------------------------------------------------
    # Routers
    # --------------------------------------------------------

    app.include_router(project_router)
    app.include_router(files_router)
    app.include_router(directories_router)
    app.include_router(paths_router)
    app.include_router(ws_router)
    app.include_router(chat_router)
    app.include_router(agents_router)

    # --------------------------------------------------------
    # Static workspace
    # --------------------------------------------------------

    if STATIC_DIR.is_dir():

        app.mount(
            "/static",
            StaticFiles(directory=STATIC_DIR),
            name="static",
        )

    @app.get("/")
    def home():
        return FileResponse(HOME_HTML)

    @app.get("/chat")
    def chat():
        return FileResponse(CHAT_HTML)

    @app.get("/editor")
    def editor():
        return FileResponse(EDITOR_HTML)

    return app


# ============================================================
# APPLICATION INSTANCE
# ============================================================

app = create_app()


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
    )
