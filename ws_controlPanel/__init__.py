"""
Workspace Control Panel
======================

The one place that answers three questions about the managed workspace:

    * Where is it?          -> ``paths``    the browse roots and the only
                                          containment check
    * Who may do what?      -> ``policy``   per-agent, per-tool, per-path rules
    * What changed?         -> ``watcher``  a change journal fed by the
                                          filesystem watcher

and one question about its documentation:

    * What does it say?     -> ``rag``      a SQLite FTS5 index over the
                                          prose under ``workspace/documentation``

Every other module in the repository asks this package instead of deciding
for itself. ``project_manager.parameters.filesystem`` re-exports ``paths`` so
its own callers keep working; ``headless_app``'s agent factory asks ``gate``
which tools an agent may hold. Consolidation here means the rules are *stated
once*, not that the old spellings stop existing.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: The repository root. This package is a sibling of ``project_manager`` and
#: ``headless_app``, so its own location identifies the whole repository.
PANEL_ROOT = Path(__file__).resolve().parent

#: The git repository root, which is the parent of this package.
AGENTCREATOR_ROOT = PANEL_ROOT.parent


def ensure_importable() -> str:
    """Put the repository root on ``sys.path`` so ``import ws_controlPanel`` works.

    The repository already does this for ``headless_app`` in five separate
    places. This helper is the panel's own copy, used by the entry points that
    need the panel before they can reach the rest of the app.

    Args:
        None.

    Returns:
        The repository root as a string, whether it was added or was
        already present.
    """

    root = str(
        AGENTCREATOR_ROOT
    )

    if root not in sys.path:

        sys.path.insert(
            0,
            root,
        )

    return root


__all__ = [
    "AGENTCREATOR_ROOT",
    "PANEL_ROOT",
    "ensure_importable",
]