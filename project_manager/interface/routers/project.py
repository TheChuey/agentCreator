"""Project resource router.

Dashboard, health and interface-state endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from . import normalize_scope
from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# HEALTH
# ============================================================

@router.get("/api/health")
def health(
    request: Request,
):
    """
    Project Manager health and project information.
    """

    try:

        return request.app.state.editor.health()

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# PROJECT STATE
# ============================================================

@router.get("/api/project")
def get_project(
    request: Request,
    scope: str = "workspace",
):
    """
    Project information and filesystem tree.

    Query params:
        scope:
            ``"workspace"`` (default) or ``"app"``.
    """

    try:

        return request.app.state.editor.tree(
            scope=normalize_scope(scope)
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# SESSIONS
# ============================================================

@router.get("/api/sessions")
def get_sessions(
    request: Request,
):
    """
    Active interface sessions.
    """

    try:

        return request.app.state.editor.sessions()

    except Exception as error:

        raise project_manager_error(
            error
        )
