"""
Project Manager HTTP API helpers.
==================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import HTTPException

from parameters import filesystem
from interface.core.defaults import get_interface
from interface.core.operations import VALID_SCOPES


# ============================================================
# SHARED CONTROLLER
# ============================================================

def controller() -> Any:
    """
    The single shared Project Manager interface instance.
    """

    return get_interface()


# ============================================================
# SCOPE HANDLING
# ============================================================

def normalize_scope(scope: str | None) -> str | None:
    """
    Validate and normalize a scope query parameter.

    Returns None when the parameter is absent, which selects the
    browser view (paths may carry a browser-root prefix). An
    explicit scope keeps the legacy single-root behaviour.

    Raises:
        HTTPException (422):
            If the scope is not a known scope.
    """

    if scope is None:

        return None

    if scope not in VALID_SCOPES:

        raise HTTPException(
            status_code=422,
            detail=f"Unknown scope: {scope}",
        )

    return scope


def normalize_roots(
    roots: str | None,
) -> list[str] | None:
    """
    Validate and normalize the ``roots`` query parameter.

    A comma-separated list of browser-root names. Empty entries are
    dropped and order is preserved; None means "no filter", which is
    the whole browser tree.

    Raises:
        HTTPException (422):
            If a name is not a configured browser root. An unknown
            root is refused rather than dropped, because a typo
            that returned a smaller tree would read as a page that
            legitimately has less in it.
    """

    if roots is None:

        return None

    names = [
        name.strip()
        for name in roots.split(",")
        if name.strip()
    ]

    if not names:

        return None

    for name in names:

        if name not in filesystem.BROWSE_ROOTS:

            raise HTTPException(
                status_code=422,
                detail=f"Unknown browser root: {name}",
            )

    return names
