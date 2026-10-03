"""
ws_controlPanel/tests/conftest.py
================================

Test bootstrap for the control panel.

The panel is a repository-level package, not an installed distribution, and
its tests live inside it. This puts the repository root on ``sys.path`` so
``import ws_controlPanel`` resolves the same way whether the suite is started
from the repository root or from inside the panel directory.

It also provides the ``panel_policy`` fixture, which swaps in a policy for the
duration of one test and always puts the original back. Policy is process-wide
state by design -- one policy governs the running server -- so a test that
loaded a policy and did not restore it would silently change the rules for
every test that ran after it. Making the swap automatic removes the chance of
that happening.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(
    __file__
).resolve().parents[2]

for _path in (
    REPO_ROOT,
    REPO_ROOT / "headless_app",
):

    if str(
        _path
    ) not in sys.path:

        sys.path.insert(
            0,
            str(_path),
        )


@pytest.fixture
def panel_policy():
    """
    Install a policy for one test, then restore whatever was there.

    Yields:
        A setter taking a parsed policy::

            policy = parse_policy({...})
            panel_policy(policy)

    Example:
        def test_denied_by_default(panel_policy):
            panel_policy(parse_policy({"agents": {}}))
    """

    from ws_controlPanel import policy as policy_module

    original = policy_module.current_policy()

    def install(new_policy):
        policy_module.set_policy(new_policy)
        return new_policy

    yield install

    policy_module.set_policy(original)


@pytest.fixture
def policy_factory():
    """
    Build a policy from a plain dict, independent of any fixture.

    Returns:
        ``parse_policy`` re-exported for convenience.
    """

    from ws_controlPanel.policy import parse_policy

    return parse_policy