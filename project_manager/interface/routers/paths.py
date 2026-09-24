"""Project path resource router (rename / move)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from . import normalize_scope
from .errors import project_manager_error


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# REQUEST MODELS
# ============================================================

class RenameRequest(BaseModel):

    old_path: str

    new_path: str

    scope: str = "workspace"


# ============================================================
# RENAME
# ============================================================

@router.put("/api/path/rename")
def rename_path(
    request: Request,
    payload: RenameRequest,
):
    """
    Rename or move a project file/directory.
    """

    try:

        return request.app.state.editor.rename(
            payload.old_path,
            payload.new_path,
            scope=normalize_scope(payload.scope),
        )

    except Exception as error:

        raise project_manager_error(
            error
        )
