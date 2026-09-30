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
    interface/routers/testing.py      Agent header tests (test_environment)
"""

from __future__ import annotations

import os
import sys
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
from interface.routers.testing import router as testing_router

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

#: Standalone tool page, opened in its own window from the topbar.
PROMPT_BUILDER_HTML = STATIC_DIR / "Agentpromptbuilder.html"

#: Evidence dashboard for the four agent header tests. The evidence
#: log carries its own styles and script; the tree, the Prompt Builder
#: panel, the resizable panels and the saved report are the shared
#: modules beside it.
TEST_HTML = STATIC_DIR / "test.html"

#: Name the engine knows this agent root by. Re-registering the same
#: name replaces it and promotes it, so restarting the server is safe.
WORKSPACE_AGENT_ROOT = "workspace"


# ============================================================
# AGENT ROOT REGISTRATION
# ============================================================

def _ensure_headless_on_path() -> bool:
    """Put headless_app/ on sys.path so the engine can be imported."""
    candidate = (PROJECT_ROOT.parent / "headless_app").resolve()
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
    return candidate.is_dir()


def register_workspace_agent_root() -> bool:
    """Teach the agent engine about ``workspace/agents/``.

    Without this the engine only knows its bundled ``agent_library/``,
    so an agent created in the Project Manager shows up in the UI but
    ``build_agent()`` raises AgentNotFoundError and chat replies 400.
    Registration is idempotent.

    Returns:
        True when the root was registered.
    """
    if not _ensure_headless_on_path():
        return False
    from engine.agents.roots import register_agent_root

    agents_dir = Path(filesystem.PROJECT_ROOT) / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    register_agent_root(
        WORKSPACE_AGENT_ROOT,
        agents_dir,
        source="workspace",
    )
    return True


def unregister_workspace_agent_root() -> None:
    """Drop the workspace root again (used on shutdown)."""
    try:
        from engine.agents.roots import unregister_agent_root
    except ImportError:
        return
    unregister_agent_root(WORKSPACE_AGENT_ROOT)


# ============================================================
# APPLICATION FACTORY
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Build the basic project filesystem on startup and register the
    workspace agent root with the agent engine.
    """

    filesystem.build_project_filesystem()

    if register_workspace_agent_root():
        print("[server] registered agent root: workspace/agents/")
    else:
        print("[server] headless_app/ not found - workspace agents unavailable")

    try:
        yield
    finally:
        unregister_workspace_agent_root()


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
    app.include_router(testing_router)

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

    @app.get("/prompt-builder")
    def prompt_builder():
        return FileResponse(PROMPT_BUILDER_HTML)

    @app.get("/test")
    def test_dashboard():
        return FileResponse(TEST_HTML)

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
