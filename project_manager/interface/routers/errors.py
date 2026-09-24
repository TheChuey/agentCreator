"""Shared FastAPI error mapping for the Project Manager API."""

from __future__ import annotations

from fastapi import HTTPException


def project_manager_error(
    error: Exception,
) -> HTTPException:
    """
    Convert a Project Manager operation error into an HTTP error.

    This is the single translator for the HTTP API. Routers do
    not implement their own status-code logic.
    """

    if isinstance(
        error,
        HTTPException,
    ):

        return error

    if isinstance(
        error,
        FileNotFoundError,
    ):

        return HTTPException(
            status_code=404,
            detail=str(error),
        )

    if isinstance(
        error,
        FileExistsError,
    ):

        return HTTPException(
            status_code=409,
            detail=str(error),
        )

    if isinstance(
        error,
        ValueError,
    ):

        return HTTPException(
            status_code=400,
            detail=str(error),
        )

    # --------------------------------------------------------
    # WebSocket-disconnect / client errors
    # --------------------------------------------------------

    if isinstance(
        error,
        KeyError,
    ):

        return HTTPException(
            status_code=404,
            detail=str(error),
        )

    return HTTPException(
        status_code=500,
        detail=str(error),
    )
