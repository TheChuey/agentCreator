"""
Workspace Gate
==============

The single place a permission question is asked and answered.

Every other module in the repository asks *this* module rather than deciding
for itself. There are exactly three ways in:

``allowed_tools(agent_id, requested)``
    Build-time. ``headless_app/engine/agents/factory.py`` calls it once when
    it assembles an agent, so an agent whose ``tools`` array names something
    it was never granted simply does not hold that tool. The refusal costs
    nothing per call, because it already happened.

``check_path(agent_id, tool, targets)``
    Call-time. The tool list is fixed per agent but the *paths* are not -- the
    same agent may read ``workspace/documentation`` and be refused
    ``workspace/agents``. This is where each path is checked.

``require_path(agent_id, tool, targets)``
    Call-time, enforcing. Raises :class:`PermissionError` instead of
    returning a decision, for callers that want to refuse by exception.

Two rules, one floor
--------------------

A decision is only ever *narrower* than the root writability floor in
:mod:`ws_controlPanel.paths`, never wider. ``require_path`` checks both, in
that order. This matters because the floor is the one rule that applies to
the human editing in the browser: a policy file cannot make ``source_files``
writable, and no agent grant can talk its way past a read-only root.

The other rule is that **agent tool calls and human browser edits are
different paths through the code and must stay that way.** The browser calls
``operations.py`` with no agent identity at all. If the per-agent rules were
applied there, the panel would start refusing the user's own edits in the
editor -- so the per-agent layer is reached only through this module, and
``parameters.filesystem.require_writable`` keeps handling everyone else on
the floor alone.

What a refusal looks like
-------------------------

A refusal is returned to the model as ordinary tool output, in the same
``{"success", "tool", "data", "error"}`` shape every tool already uses, so the
model reads it as a result rather than a crash. The wording names the tool,
the agent and the path, because an agent that is told only "denied" will
retry the same call; one that is told *which* rule refused it will stop.
"""

from __future__ import annotations

from typing import Any, Callable

from ws_controlPanel import paths
from ws_controlPanel.policy import (
    MUTATING_TOOLS,
    Decision,
    Policy,
    current_policy,
)


# ============================================================
# EXCEPTIONS
# ============================================================

class PermissionDenied(PermissionError):
    """A tool call was refused by the policy.

    A distinct type rather than a bare ``PermissionError`` so a caller can
    tell "the policy said no" from "the operating system said no", and
    report the two very differently: the first is a rule to be changed or
    obeyed, the second is a bug or a broken mount.
    """

    def __init__(
        self,
        decision: Decision,
    ) -> None:
        """Record the decision that produced this refusal.

        Args:
            decision:
                The refusing Decision, kept whole so the reason
                survives to the log and the API.
        """

        self.decision = decision

        super().__init__(
            decision.reason
        )


# ============================================================
# BUILD-TIME GATE
# ============================================================

def allowed_tools(
    agent_id: str,
    requested: list[str],
    policy: Policy | None = None,
) -> tuple[list[str], list[Decision]]:
    """Reduce an agent's requested tools to the ones it may actually hold.

    Called once per agent build by the engine's factory. The result is the
    agent's real tool list, so a refused tool does not reach the model at
    all -- it is not offered, called, and refused, it simply is not there.

    Args:
        agent_id:
            The agent being built.
        requested:
            Tool ids from ``agent.json``, in their original order.
        policy:
            Policy to consult. Defaults to the loaded one.

    Returns:
        ``(kept, refused)``. ``kept`` preserves the requested order so the
        agent's advertised tool list stays stable between builds.
    """

    return (
        policy
        or current_policy()
    ).allowed_tools(
        agent_id,
        requested,
    )


def log_refusals(
    agent_id: str,
    refused: list[Decision],
    sink: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    """Record the tools an agent asked for and was not given.

    A silently dropped tool is the failure mode this module exists to
    replace: the old registry printed a warning to stdout and moved on, so a
    mistyped tool id in an ``agent.json`` produced an agent that quietly could
    not do its job. Refusals are therefore reported, one line each, and
    optionally handed to a sink for the panel's event log.

    Args:
        agent_id:
            The agent being built.
        refused:
            The refusing decisions from ``allowed_tools``.
        sink:
            Optional callable receiving one dict per refusal.

    Returns:
        None.
    """

    for decision in refused:

        event = {
            "kind": "permission",
            "stage": "build",
            "agent_id": agent_id,
            "allowed": False,
            "reason": decision.reason,
            "rule": decision.rule,
        }

        print(
            f"[gate] {agent_id}: {decision.reason}"
        )

        if sink is not None:

            try:

                sink(event)

            except Exception:

                # A failing log sink must not stop an agent from being
                # built. Every other log write in this repository is
                # fail-safe for the same reason.
                pass


# ============================================================
# CALL-TIME GATE
# ============================================================

def check_path(
    agent_id: str,
    tool: str,
    targets: list[str] | str | None = None,
    policy: Policy | None = None,
) -> Decision:
    """Whether an agent may use a tool on a set of paths.

    A tool with no path argument -- ``get_current_date`` -- is checked with
    ``targets`` empty, which asks only whether the tool is held at all.

    Every path must clear the gate; the first refusal wins and is returned.
    Checking them one at a time and stopping is deliberate: a model that
    proposed four paths deserves to be told about the one that is forbidden,
    not handed a partial allow it will then act on.

    Mutating tools additionally clear the read-only floor before any pattern
    is consulted. ``source_files`` is read-only for everyone, so a policy
    that grants ``write_text_file`` on ``**`` -- a plausible thing to type
    into the editor -- must not be able to talk its way past that. The floor
    lives in ``paths``, not in the policy, precisely so that it cannot be
    widened by editing a permission file.

    Args:
        agent_id:
            The agent asking.
        tool:
            The tool name.
        targets:
            The paths involved, in any form the tools use: absolute,
            root-qualified, or bare relative. Each is canonicalised before
            matching, so the answer does not depend on which form arrived.
        policy:
            Policy to consult. Defaults to the loaded one.

    Returns:
        The Decision for the whole call. An empty ``targets`` yields a
        tool-level decision.
    """

    active = policy or current_policy()

    held = active.allows_tool(
        agent_id,
        tool,
    )

    if not held.allowed:

        return held

    paths_to_check = _as_list(
        targets
    )

    if not paths_to_check:

        return Decision(
            allowed=True,
            reason=held.reason,
            rule=held.rule,
        )

    mutating = tool in MUTATING_TOOLS

    for target in paths_to_check:

        # Canonicalise first. This both produces the form the policy patterns
        # are written against and performs the containment check, so a path
        # that escapes every root is reported as the containment failure it is
        # rather than being folded into the read-only refusal below -- the two
        # need different wording, and the UI groups by ``rule``.
        try:

            qualified = paths.to_root_qualified(
                target
            )

        except ValueError as error:

            return Decision(
                allowed=False,
                reason=(
                    f"'{tool}' refused for agent '{agent_id}': "
                    f"{error}"
                ),
                rule="outside-roots",
            )

        if mutating:

            # The same primitive require_path() uses, so the two forms of the
            # gate cannot disagree about what is read-only. Consulted only
            # after containment, so it can never be the reason a path outside
            # the roots was refused.
            try:

                paths.require_writable(
                    target
                )

            except ValueError as error:

                return Decision(
                    allowed=False,
                    reason=(
                        f"'{tool}' refused for agent '{agent_id}': "
                        f"{error}"
                    ),
                    rule="read-only-root",
                )

        try:

            decision = active.allows_path(
                agent_id,
                tool,
                target,
            )

        except ValueError as error:

            # The path is outside every declared root, so no rule can
            # describe it. That is a containment failure, and it is
            # reported as a refusal rather than as an unmatched pattern.
            return Decision(
                allowed=False,
                reason=(
                    f"'{tool}' refused for agent '{agent_id}': "
                    f"{error}"
                ),
                rule="",
            )

        if not decision.allowed:

            return decision

    return Decision(
        allowed=True,
        reason=(
            f"'{tool}' is allowed for agent '{agent_id}' on all "
            f"{len(paths_to_check)} requested path(s)."
        ),
        rule=held.rule,
    )


def require_path(
    agent_id: str,
    tool: str,
    targets: list[str] | str | None = None,
    policy: Policy | None = None,
    check_floor: bool = True,
) -> None:
    """Refuse a tool call by exception unless every layer permits it.

    Args:
        agent_id:
            The agent asking.
        tool:
            The tool name.
        targets:
            The paths involved.
        policy:
            Policy to consult. Defaults to the loaded one.
        check_floor:
            Also require the root writability floor. Leave this True for
            anything that changes the filesystem. It exists as a
            parameter only so the read-only test suite can assert the
            floor directly; production callers never pass False.

    Returns:
        None.

    Raises:
        PermissionDenied:
            If the policy refuses, or the root is read-only.
        ValueError:
            If a path escapes its root. The containment failure keeps its
            own type because it is a different kind of problem from a
            refused permission and reads as one in the log.
    """

    active = policy or current_policy()

    if check_floor:

        for target in _as_list(
            targets
        ):

            paths.require_writable(
                target
            )

    decision = check_path(
        agent_id,
        tool,
        targets,
        policy=active,
    )

    if not decision.allowed:

        raise PermissionDenied(
            decision
        )


def _as_list(
    targets: list[str] | str | None,
) -> list[str]:
    """Coerce the many shapes a caller may pass paths in.

    Args:
        targets:
            A single path, a list of paths, or None.

    Returns:
            A list of non-empty strings, possibly empty.
    """

    if targets is None:

        return []

    if isinstance(
        targets,
        str,
    ):

        candidates = [targets]

    elif isinstance(
        targets,
        (list, tuple, set),
    ):

        candidates = list(targets)

    else:

        candidates = [targets]

    return [
        str(item).strip()
        for item in candidates
        if str(item).strip()
    ]


# ============================================================
# PANEL HELPERS
# ============================================================

def agent_matrix(
    policy: Policy | None = None,
) -> list[dict[str, Any]]:
    """Every known agent with the tools it may hold, for the panel.

    Reads the agents from disk and asks the policy about each, so the
    matrix shows what is *actually* in force rather than what the
    ``agent.json`` requests. An agent whose request was trimmed shows up
    with the difference visible.

    Args:
        policy:
            Policy to consult. Defaults to the loaded one.

    Returns:
        One dict per agent with ``id``, ``granted`` and ``refused``.
    """

    from ws_controlPanel.policy import discover_agent_ids

    active = policy or current_policy()

    rows: list[dict[str, Any]] = []

    for agent_id in discover_agent_ids():

        requested = _requested_tools(
            agent_id
        )

        kept, refused = active.allowed_tools(
            agent_id,
            requested,
        )

        rows.append(
            {
                "id": agent_id,
                "granted": kept,
                "requested": requested,
                "refused": [
                    decision.as_dict()
                    for decision in refused
                ],
            }
        )

    return rows


def _requested_tools(
    agent_id: str,
) -> list[str]:
    """The tools an agent's own definition asks for.

    Args:
        agent_id:
            The agent id, which is not always its folder name.

    Returns:
        The requested tool ids, or an empty list when the agent is not on
        disk.
    """

    from ws_controlPanel.policy import (
        _iter_agent_pairs,
    )

    for agent_dir, declared in _iter_agent_pairs():

        if declared == agent_id:

            from ws_controlPanel.policy import (
                _read_agent_tool_ids,
            )

            return _read_agent_tool_ids(
                agent_dir
            )

    return []