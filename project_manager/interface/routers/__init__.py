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

def normalize_scope(scope: str | None) -> str:
    """
    Validate and normalize a scope query parameter.

    Raises:
        HTTPException (422):
            If the scope is not a known scope.
    """

    scope = scope or "workspace"

    if scope not in VALID_SCOPES:

        raise HTTPException(
            status_code=422,
            detail=f"Unknown scope: {scope}",
        )

    return scope
