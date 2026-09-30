"""Project resource router.

Dashboard, health and interface-state endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from . import normalize_roots, normalize_scope
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
    scope: str | None = None,
    roots: str | None = None,
):
    """
    Project information and filesystem tree.

    Query params:
        scope:
            Omit for the browser tree, whose top level is the
            configured browser roots. ``"workspace"`` or ``"app"``
            return the legacy single-root tree.
        roots:
            Comma-separated browser roots to include in the browser
            tree, e.g. ``?roots=test_environment``. Omit for all of
            them. This decides what a page is shown, not what it may
            read or write: an omitted root still resolves for file
            operations.
    """

    try:

        return request.app.state.editor.tree(
            scope=normalize_scope(scope),
            roots=normalize_roots(roots),
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
