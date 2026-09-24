"""Project file resource router (read / write / create / delete)."""

from __future__ import annotations

from typing import Any

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

class FileWriteRequest(BaseModel):

    path: str

    content: str

    scope: str = "workspace"


class FileCreateRequest(BaseModel):

    path: str

    content: str = ""

    scope: str = "workspace"


# ============================================================
# READ FILE
# ============================================================

@router.get("/api/file/read")
def read_file(
    request: Request,
    path: str,
    scope: str = "workspace",
):
    """
    Read a project text file.

    Query params:
        path:
            Root-relative file path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
    """

    try:

        content = request.app.state.editor.open(
            path,
            scope=normalize_scope(scope),
        )
        return {
            "path": path,
            "content": content,
            "scope": scope,
        }

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# WRITE FILE
# ============================================================

@router.put("/api/file/write")
def write_file(
    request: Request,
    payload: FileWriteRequest,
):
    """
    Create or overwrite a project text file.
    """

    try:

        return request.app.state.editor.save(
            payload.path,
            payload.content,
            scope=normalize_scope(payload.scope),
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# CREATE FILE
# ============================================================

@router.post("/api/file/create")
def create_file(
    request: Request,
    payload: FileCreateRequest,
):
    """
    Create a new project file.
    """

    try:

        return request.app.state.editor.create_file(
            payload.path,
            payload.content,
            scope=normalize_scope(payload.scope),
        )

    except Exception as error:

        raise project_manager_error(
            error
        )


# ============================================================
# DELETE FILE
# ============================================================

@router.delete("/api/file/delete")
def delete_file(
    request: Request,
    path: str,
    scope: str = "workspace",
):
    """
    Delete a project file.

    Query params:
        path:
            Root-relative file path.
        scope:
            ``"workspace"`` (default) or ``"app"``.
    """

    try:

        return request.app.state.editor.delete(
            path,
            scope=normalize_scope(scope),
        )

    except Exception as error:

        raise project_manager_error(
            error
        )
