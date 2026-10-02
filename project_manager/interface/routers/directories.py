"""Project directory resource router (create / delete)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from . import normalize_scope
from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# CREATE DIRECTORY
# ============================================================

@router.post("/api/directory/create")
def create_directory(
    request: Request,
    path: str,
    scope: str | None = None,
):
    """
    Create a project directory.

    Query params:
        path:
            Browser-root-qualified or root-relative directory path.
        scope:
            Omit for the browser view; ``"workspace"`` or
            ``"app"`` for a legacy single-root view.
    """

    try:

        return request.app.state.editor.create_directory(
            path,
            scope=normalize_scope(scope),
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# DELETE DIRECTORY
# ============================================================

@router.delete("/api/directory/delete")
def delete_directory(
    request: Request,
    path: str,
    scope: str | None = None,
):
    """
    Delete a project directory.

    Query params:
        path:
            Browser-root-qualified or root-relative directory path.
        scope:
            Omit for the browser view; ``"workspace"`` or
            ``"app"`` for a legacy single-root view.
    """

    try:

        result = request.app.state.editor.delete(
            path,
            scope=normalize_scope(scope),
        )

        # Removing an agent folder also removes its diagnostics. Fail-safe:
        # the delete already succeeded, so a log problem must not turn it
        # into an error response.
        try:
            from .toollog import clear_agent_tool_events_for_path

            clear_agent_tool_events_for_path(path)
        except Exception:
            pass

        return result

    except Exception as error:

        raise project_manager_error(
            error
        )
