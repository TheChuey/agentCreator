"""
Workspace Policy
================

Per-agent, per-tool, per-path permission rules for the tools an AI agent may
call, stored in ``policy.json`` beside this module.

Why a file and not code
-----------------------

The rules were previously implicit in three places that could not see each
other: the ``writable`` flag on each browse root, the ``tools`` array in each
``agent.json``, and a delete-approval step buried in the agent factory. A
person could not answer "what may this agent do?" without reading three
files and mentally intersecting them. Now they can read one JSON file, and
the panel can show it.

The stance is **default-deny**. A tool that no rule mentions is refused. That
is the opposite of the old behaviour, where an unrecognised tool id was
silently dropped and an unmentioned path was allowed -- silence read as
permission, which is how a permission system rots.

Glob semantics
--------------

Patterns are written against root-qualified paths (``workspace/documentation/**``)
and matched **segment by segment**:

``*``
    matches within one segment. It never crosses a ``/``, so
    ``workspace/agents/*`` matches ``workspace/agents/helper/agent.json``'s
    folder but not a file nested deeper. This is deliberately stricter than
    :func:`fnmatch.fnmatch`, whose ``*`` does cross separators -- under
    fnmatch a rule written for one folder would quietly grant a whole tree.

``**``
    matches zero or more whole segments. ``workspace/**`` matches
    ``workspace`` itself as well as everything under it; ``workspace/**/x.md``
    matches the file at any depth.

``?``
    matches exactly one character within a segment.

Matching is case-insensitive on Windows and case-sensitive elsewhere, which is
how the operating system being addressed resolves its own paths. A rule
written for Windows therefore behaves the way its author expected, and a rule
on Linux does not accidentally merge two files that differ only in case.

Precedence
----------

An explicit ``deny`` anywhere beats an ``allow`` anywhere, at every level. An
agent-specific rule beats the shared rule for that tool. Within one rule, the
longest matching path pattern wins, so a narrow carve-out can sit beside a
broad grant:

.. code-block:: json

    "write_text_file": {
      "effect": "allow",
      "paths": ["workspace/**", "!workspace/agents/**"]
    }

The root writability floor in :mod:`ws_controlPanel.paths` is *not* expressed
here and cannot be overridden here. ``source_files`` is generated output; no
rule in this file can make it writable. ``gate.require_path`` checks the floor
and this policy, and the floor is not optional.
"""

from __future__ import annotations

import fnmatch
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ws_controlPanel import paths


# ============================================================
# CONFIGURATION
# ============================================================

PANEL_DIR = Path(__file__).resolve().parent

POLICY_FILE = PANEL_DIR / "policy.json"

#: Tools that change the filesystem. Their seeded grants are limited to the
#: writable roots, because that is what the old root-level floor did and the
#: seed has to reproduce current behaviour exactly rather than quietly tighten
#: it.
MUTATING_TOOLS = frozenset({
    "write_text_file",
    "delete_files",
})


# ============================================================
# GLOB MATCHING
# ============================================================

def _match_segments(
    pattern: list[str],
    path: list[str],
    fold: bool,
) -> bool:
    """Match path segments against pattern segments, left to right.

    Args:
        pattern:
            The pattern split on ``/``, already case-folded when
            ``fold`` is set.
        path:
            The candidate path split on ``/``.
        fold:
            Whether to case-fold both sides before comparing.

    Returns:
        True when the whole path is consumed by the whole pattern.
    """

    if not pattern:

        return not path

    head = pattern[0]
    rest = pattern[1:]

    if head == "**":

        # ``**`` absorbs zero or more whole segments. Trying every skip is
        # linear in the remaining depth, which is a handful of segments for
        # a real path -- cheap enough that clarity wins over a compiled regex.
        for skip in range(
            len(path) + 1
        ):

            if _match_segments(
                rest,
                path[skip:],
                fold,
            ):

                return True

        return False

    if not path:

        return False

    if not _match_segment(
        head,
        path[0],
        fold,
    ):

        return False

    return _match_segments(
        rest,
        path[1:],
        fold,
    )


def _match_segment(
    pattern: str,
    segment: str,
    fold: bool,
) -> bool:
    """Match one path segment against one pattern segment.

    Args:
        pattern:
            The pattern segment, with no ``/`` in it.
        segment:
            The candidate segment, with no ``/`` in it.
        fold:
            Whether to case-fold before comparing.

    Returns:
        True when the segment matches. Because neither side contains a
        separator, ``fnmatch``'s ``*`` cannot escape the segment.
    """

    if fold:

        pattern = pattern.casefold()
        segment = segment.casefold()

    return fnmatch.fnmatchcase(
        segment,
        pattern,
    )


def path_matches(
    pattern: str,
    candidate: str,
) -> bool:
    """
    Whether a root-qualified path matches a glob pattern.

    Args:
        pattern:
            A glob such as ``workspace/documentation/**``. A pattern whose
            first segment is not a root name is treated as root-agnostic: it
            is also matched against the candidate with its root stripped, so
            ``documentation/**`` matches
            ``workspace/documentation/x.md``. Without that, the natural way
            to write a grant silently matches nothing -- a rule that looks
            right in the editor and grants no access at all.
        candidate:
            A root-qualified path such as
            ``workspace/documentation/APP_CODE_SNAPSHOT.md``.

    Returns:
        True when the candidate matches.

        A candidate containing a ``..`` segment never matches, whatever the
        pattern. Callers are meant to resolve and contain paths before asking,
        so a ``..`` reaching here means a check was skipped upstream.
        Refusing it here too makes the primitive safe to call directly -- from
        the API, an editor preview or a test -- without every caller having to
        re-derive the rule.
    """

    fold = (
        os.name == "nt"
    )

    pattern_parts = [
        part
        for part in pattern.strip().replace(
            "\\",
            "/",
        ).split("/")
        if part
    ]

    candidate_parts = [
        part
        for part in candidate.strip().replace(
            "\\",
            "/",
        ).split("/")
        if part
    ]

    if not pattern_parts or not candidate_parts:

        return False

    if ".." in candidate_parts:

        return False

    if _match_segments(
        pattern_parts,
        candidate_parts,
        fold,
    ):

        return True

    # Root-agnostic pattern: retry against the path inside its root.
    if pattern_parts[0] not in paths.ROOTS:

        head, separator, tail = candidate.strip().partition("/")

        if separator and head in paths.ROOTS:

            return _match_segments(
                pattern_parts,
                [part for part in tail.split("/") if part],
                fold,
            )

    return False


def _rule_specificity(
    pattern: str,
) -> int:
    """How specific a path pattern is, so the narrowest match can win.

    Args:
        pattern:
            The glob to score.

    Returns:
        A sort key. More literal segments and fewer ``**`` wildcards score
        higher; a bare ``**`` scores lowest.
    """

    segments = [
        part
        for part in pattern.split("/")
        if part
    ]

    wildcards = sum(
        1
        for part in segments
        if "**" in part
    )

    literals = sum(
        1
        for part in segments
        if "*" not in part and "?" not in part
    )

    return (
        literals * 100
        - wildcards * 50
        + len(segments)
    )


# ============================================================
# RULES
# ============================================================

@dataclass(frozen=True)
class Rule:
    """One permission rule: an effect and the paths it applies to."""

    effect: str
    paths: tuple[str, ...]

    def best_match(
        self,
        candidate: str,
    ) -> tuple[str | None, str | None]:
        """Find how this rule treats one path.

        Args:
            candidate:
                A root-qualified path.

        Returns:
            ``(effect, pattern)`` for the most specific pattern that
            matches, or ``(None, None)`` when none does.
        """

        best: tuple[str | None, str | None] = (
            None,
            None,
        )

        # "No match yet" rather than a numeric sentinel. _rule_specificity()
        # ranks the widest patterns below zero -- a bare "**" scores around
        # -49 -- so any fixed starting value is a guess about that range, and
        # a guess that is too high silently discards every broad rule. That is
        # exactly what happened: the shorthand "allow" expands to ("**",), so
        # every hand-written shorthand grant was granted the tool and then
        # refused on every single path.
        best_score: int | None = None

        for pattern in self.paths:

            if not path_matches(
                pattern,
                candidate,
            ):

                continue

            score = _rule_specificity(
                pattern
            )

            if best_score is not None and score <= best_score:

                continue

            best_score = score
            best = (
                self.effect,
                pattern,
                )

        return best


def _parse_rule(
    raw: Any,
    where: str,
) -> Rule:
    """Validate and build one rule from parsed JSON.

    Args:
        raw:
            The JSON value for the rule.
        where:
            A human-readable location used in error messages.

    Returns:
        The validated Rule.

    Raises:
        ValueError:
            If the rule is not a well-formed allow or deny.
    """

    if isinstance(
        raw,
        str,
    ):

        # Shorthand: a bare string is an allow over every path.
        raw = {
            "effect": raw,
            "paths": ["**"],
        }

    if not isinstance(
        raw,
        dict,
    ):

        raise ValueError(
            f"{where}: a rule must be a string or an object, "
            f"got {type(raw).__name__}."
        )

    effect = str(
        raw.get(
            "effect",
            "allow",
        )
    ).strip().lower()

    if effect not in ("allow", "deny"):

        raise ValueError(
            f"{where}: effect must be 'allow' or 'deny', "
            f"got {effect!r}."
        )

    raw_paths = raw.get(
        "paths",
        ["**"],
    )

    if isinstance(
        raw_paths,
        str,
    ):

        raw_paths = [raw_paths]

    if not isinstance(
        raw_paths,
        list,
    ) or not all(
        isinstance(item, str)
        for item in raw_paths
    ):

        raise ValueError(
            f"{where}: paths must be a string or a list of strings."
        )

    return Rule(
        effect=effect,
        paths=tuple(
            item.strip().replace(
                "\\",
                "/",
            )
            for item in raw_paths
            if item.strip()
        ) or ("**",),
    )


def _parse_section(
    raw: Any,
    where: str,
) -> dict[str, Rule]:
    """Validate and build a ``{tool: Rule}`` mapping.

    Args:
        raw:
            The JSON value for the section.
        where:
            A human-readable location used in error messages.

    Returns:
        Tool name to Rule, in declaration order.

    Raises:
        ValueError:
            If the section is not an object of rules.
    """

    if raw is None:

        return {}

    if not isinstance(
        raw,
        dict,
    ):

        raise ValueError(
            f"{where}: expected an object of tool rules, "
            f"got {type(raw).__name__}."
        )

    section: dict[str, Rule] = {}

    for tool_name, tool_rule in raw.items():

        section[str(tool_name)] = _parse_rule(
            tool_rule,
            f"{where}.{tool_name}",
        )

    return section


# ============================================================
# DECISIONS
# ============================================================

@dataclass(frozen=True)
class Decision:
    """The verdict for one permission question, and why.

    ``reason`` and ``rule`` are not decoration. A permission layer that can
    only say no is indistinguishable from one that is broken, so every
    answer carries the sentence a human needs in order to either grant the
    permission or go fix their rule.
    """

    allowed: bool
    reason: str
    rule: str = ""

    def as_dict(self) -> dict[str, Any]:
        """This decision as JSON, for the API.

        Returns:
            A dict with ``allowed``, ``reason`` and ``rule``.
        """

        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "rule": self.rule,
        }


#: The answer when no rule anywhere mentions the tool.
def _default_deny(
    tool: str,
    agent_id: str,
) -> Decision:
    """Build the default-deny decision for an unmentioned tool.

    Args:
        tool:
            The tool name.
        agent_id:
            The agent that asked.

    Returns:
        A refusing Decision naming the missing rule.
    """

    return Decision(
        allowed=False,
        reason=(
            f"No rule grants '{tool}' to agent '{agent_id}'. "
            "This workspace is default-deny, so an unmentioned tool "
            "is refused rather than assumed harmless."
        ),
        rule="",
    )


# ============================================================
# POLICY
# ============================================================

@dataclass
class Policy:
    """A loaded set of permission rules.

    Attributes:
        version:
            The schema version of the file this came from.
        default:
            ``"deny"`` or ``"allow"``. Only ``"deny"`` is honoured; an
            ``"allow"`` default is refused at load time, because a
            permissive default is the failure mode this whole module
            exists to prevent.
        tools:
            Rules that apply to every agent.
        agents:
            Per-agent rules. An agent's rules are consulted before the
            shared ones.
        source:
            Where the rules were read from, for display.
    """

    version: int = 1
    default: str = "deny"
    tools: dict[str, Rule] = field(default_factory=dict)
    agents: dict[str, dict[str, Rule]] = field(
        default_factory=dict
    )
    source: str = ""

    # -- lookup ------------------------------------------------

    def agent_rule(
        self,
        agent_id: str,
        tool: str,
    ) -> Rule | None:
        """The rule this agent carries for this tool, if any.

        Args:
            agent_id:
                The agent asking.
            tool:
                The tool name.

        Returns:
            The agent's own Rule, falling back to the shared rule, or None
            when neither mentions the tool.
        """

        for scope in (agent_id, "*"):

            section = self.agents.get(
                scope
            )

            if not section:

                continue

            if tool in section:

                return section[tool]

        return self.tools.get(tool)

    def _scopes_for(
        self,
        agent_id: str,
        tool: str,
    ) -> list[tuple[str, Rule]]:
        """Every rule that could apply, most authoritative first.

        Deny has to be visible across all of them before any allow is
        honoured, so this returns the whole ordered candidate set rather
        than collapsing to a single winner up front.

        Args:
            agent_id:
                The agent asking.
            tool:
                The tool name.

        Returns:
            ``(scope, rule)`` pairs, agent-specific before shared.
        """

        candidates: list[tuple[str, Rule]] = []

        for scope in (agent_id, "*"):

            section = self.agents.get(
                scope
            ) or {}

            if tool in section:

                candidates.append(
                    (scope, section[tool])
                )

        if tool in self.tools:

            candidates.append(
                ("*", self.tools[tool])
            )

        return candidates

    # -- decisions --------------------------------------------

    def allows_tool(
        self,
        agent_id: str,
        tool: str,
    ) -> Decision:
        """Whether this agent may hold this tool at all.

        Consulted once, when the agent is built, so a tool-level refusal
        costs nothing per call. A tool granted over some paths but not all
        still counts as held here; the path check is what narrows it.

        Args:
            agent_id:
                The agent asking.
            tool:
                The tool name.

        Returns:
            The Decision. When allowed, the reason records that a path
            check still applies.
        """

        rule = self.agent_rule(
            agent_id,
            tool,
        )

        if rule is None:

            return _default_deny(
                tool,
                agent_id,
            )

        if rule.effect == "deny":

            return Decision(
                allowed=False,
                reason=(
                    f"'{tool}' is explicitly denied to agent "
                    f"'{agent_id}'."
                ),
                rule="deny",
            )

        return Decision(
            allowed=True,
            reason=(
                f"'{tool}' is granted to agent '{agent_id}' over "
                f"{len(rule.paths)} path pattern(s); each call is "
                "still checked against them."
            ),
            rule="allow",
        )

    def allows_path(
        self,
        agent_id: str,
        tool: str,
        target: str,
    ) -> Decision:
        """Whether this agent may use this tool on this path.

        Args:
            agent_id:
                The agent asking.
            tool:
                The tool name.
            target:
                The path, in any form. It is canonicalised to a
                root-qualified path first, so the same answer comes back
                whether the caller sent an absolute Windows path or a
                relative one.

        Returns:
            The Decision, with the winning pattern in ``rule``.

        Raises:
            ValueError:
                If the path cannot be canonicalised, which means it lies
                outside every declared root. The caller turns this into a
                refusal; it is raised rather than swallowed so a
                containment failure can never be mistaken for an
                unmatched path.
        """

        qualified = paths.to_root_qualified(
            target
        )

        # An explicit deny at any scope wins over any allow, so collect
        # first and only then decide.
        denied: Decision | None = None
        allowed: Decision | None = None

        for scope, rule in self._scopes_for(
            agent_id,
            tool,
        ):

            effect, pattern = rule.best_match(
                qualified
            )

            if effect is None:

                continue

            if effect == "deny":

                denied = Decision(
                    allowed=False,
                    reason=(
                        f"'{tool}' is denied on '{qualified}' by the "
                        f"rule for '{scope}' (pattern '{pattern}')."
                    ),
                    rule=str(pattern),
                )

                break

            if allowed is None:

                allowed = Decision(
                    allowed=True,
                    reason=(
                        f"'{tool}' is allowed on '{qualified}' by the "
                        f"rule for '{scope}' (pattern '{pattern}')."
                    ),
                    rule=str(pattern),
                )

        if denied is not None:

            return denied

        if allowed is not None:

            return allowed

        return Decision(
            allowed=False,
            reason=(
                f"'{tool}' is granted to agent '{agent_id}' but not on "
                f"'{qualified}'. No pattern in the applicable rules "
                "covers this path."
            ),
            rule="",
        )

    def allowed_tools(
        self,
        agent_id: str,
        requested: list[str],
    ) -> tuple[list[str], list[Decision]]:
        """Filter a requested tool list down to what this agent may hold.

        This is the build-time gate. An agent's ``tools`` array is a
        *request*; this is where it becomes a grant, and it runs once per
        agent build so a refusal costs nothing on every subsequent tool
        call.

        Args:
            agent_id:
                The agent being built.
            requested:
                The tool ids from ``agent.json``, in their original order.

        Returns:
            ``(kept, refused)`` where ``kept`` preserves the requested
            order and ``refused`` carries one Decision per dropped tool,
            so the caller can log exactly what was taken away and why.
        """

        kept: list[str] = []
        refused: list[Decision] = []

        for tool in requested:

            decision = self.allows_tool(
                agent_id,
                tool,
            )

            if decision.allowed:

                kept.append(tool)

            else:

                refused.append(decision)

        return kept, refused

    # -- serialisation ----------------------------------------

    def as_dict(self) -> dict[str, Any]:
        """These rules as the JSON that would reproduce them.

        Returns:
            A dict matching the ``policy.json`` schema.
        """

        def render(
            rule: Rule,
        ) -> dict[str, Any]:

            return {
                "effect": rule.effect,
                "paths": list(rule.paths),
            }

        return {
            "version": self.version,
            "default": self.default,
            "tools": {
                name: render(rule)
                for name, rule in self.tools.items()
            },
            "agents": {
                agent: {
                    name: render(rule)
                    for name, rule in section.items()
                }
                for agent, section in self.agents.items()
            },
        }


# ============================================================
# LOADING
# ============================================================

def parse_policy(
    raw: Any,
    source: str = "",
) -> Policy:
    """Validate parsed JSON and build a Policy.

    Args:
        raw:
            The decoded JSON value.
        source:
            Where it came from, recorded for display.

    Returns:
        The validated Policy.

    Raises:
        ValueError:
            If the document is not a valid policy. Every message names
            the offending location, because a policy file that fails to
            load must not be silently replaced by a permissive default.
    """

    if not isinstance(
        raw,
        dict,
    ):

        raise ValueError(
            "A policy document must be a JSON object."
        )

    version = raw.get(
        "version",
        1,
    )

    if not isinstance(
        version,
        int,
    ):

        raise ValueError(
            f"version must be an integer, got "
            f"{type(version).__name__}."
        )

    default = str(
        raw.get(
            "default",
            "deny",
        )
    ).strip().lower()

    if default != "deny":

        raise ValueError(
            "default must be 'deny'. A permissive default is not "
            "supported: an unmentioned tool has to be refused, or the "
            "policy file stops being the thing that decides."
        )

    shared = _parse_section(
        raw.get("tools"),
        "tools",
    )

    agents_raw = raw.get(
        "agents",
        {},
    ) or {}

    if not isinstance(
        agents_raw,
        dict,
    ):

        raise ValueError(
            "agents must be an object keyed by agent id."
        )

    agents = {
        str(agent_id): _parse_section(
            section,
            f"agents.{agent_id}",
        )
        for agent_id, section in agents_raw.items()
    }

    return Policy(
        version=version,
        default=default,
        tools=shared,
        agents=agents,
        source=source,
    )


def load_policy(
    policy_file: Path | str | None = None,
) -> Policy:
    """Read and validate the policy file.

    Args:
        policy_file:
            Override for the default location. Used by the tests to
            load a fixture without touching the real file.

    Returns:
        The loaded Policy. A missing file is seeded rather than treated
        as an error, so a fresh checkout comes up with rules that
        reproduce current behaviour instead of refusing everything.

        A file that exists but cannot be parsed also does not raise. It
        yields a policy that denies everything, with the reason recorded in
        ``source``. This is a deliberate trade: raising here would mean a
        single typo in ``policy.json`` prevents the server from starting,
        which leaves nobody able to reach the control panel and repair the
        file that is stopping them. Denying everything is safe, visible and
        recoverable -- every agent loses its tools until the policy parses,
        and ``source`` says why. The warning below exists so the failure is
        still noticed during development.
    """

    target = Path(
        policy_file
    ) if policy_file else POLICY_FILE

    if not target.is_file():

        return seed_policy()

    try:

        raw = json.loads(
            target.read_text(
                encoding="utf-8"
            )
        )

    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        OSError,
    ) as error:

        _warn_unreadable(
            target,
            error,
        )

        return Policy(
            source=f"unreadable ({error})",
        )

    return parse_policy(
        raw,
        source=str(target),
    )


def _warn_unreadable(
    target: Path,
    error: Exception,
) -> None:
    """Announce that the policy file could not be read, then carry on denying.

    The policy in use is deny-all at this point, so this is not a cosmetic
    warning -- every agent has just lost its tools. It goes to stderr because
    it is a startup fault rather than a request-scoped one, and it names the
    file so the fix is obvious.
    """

    import sys

    print(
        f"[ws_controlPanel] policy file {target} could not be read "
        f"({error}). Denying every tool until it is repaired.",
        file=sys.stderr,
    )


def save_policy(
    policy: Policy,
    policy_file: Path | str | None = None,
) -> Path:
    """Write a policy back to disk atomically.

    The write goes to a temporary file in the same directory and is then
    renamed over the target, so a crash mid-write cannot leave a
    truncated policy behind -- which would be a permission file that fails
    to parse, i.e. a server that will not start.

    Args:
        policy:
            The Policy to persist.
        policy_file:
            Override for the default location.

    Returns:
            The path written.
    """

    target = Path(
        policy_file
    ) if policy_file else POLICY_FILE

    payload = json.dumps(
        policy.as_dict(),
        indent=2,
    ) + "\n"

    temporary = target.with_name(
        target.name + ".tmp"
    )

    temporary.write_text(
        payload,
        encoding="utf-8",
    )

    temporary.replace(target)

    return target


# ============================================================
# SEEDING
# ============================================================

def _read_agent_tool_ids(
    agent_dir: Path,
) -> list[str]:
    """Read the ``tools`` array out of one agent.json.

    Args:
        agent_dir:
            A folder holding ``agent.json``.

    Returns:
        The requested tool ids, or an empty list when the folder has no
        readable agent.json. A malformed file yields an empty list rather
        than an exception, because seeding must not be blocked by one bad
        agent.
    """

    meta_file = agent_dir / "agent.json"

    if not meta_file.is_file():

        return []

    try:

        meta = json.loads(
            meta_file.read_text(
                encoding="utf-8"
            )
        )

    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        OSError,
    ):

        return []

    tools = meta.get(
        "tools",
        [],
    )

    if not isinstance(
        tools,
        list,
    ):

        return []

    return [
        str(tool)
        for tool in tools
        if isinstance(tool, str)
    ]


def _has_agent_meta(
    agent_dir: Path,
) -> bool:
    """Whether a folder holds a readable ``agent.json``.

    Args:
        agent_dir:
            The folder to check.

    Returns:
        True when the folder declares itself an agent. Used to keep a
        stray folder out of the policy as a key that matches nothing.
    """

    meta_file = agent_dir / "agent.json"

    if not meta_file.is_file():

        return False

    try:

        json.loads(
            meta_file.read_text(
                encoding="utf-8"
            )
        )

    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        OSError,
    ):

        return False

    return True


def discover_agent_ids(
    agent_dirs: list[Path] | None = None,
) -> list[str]:
    """Every agent id the workspace knows about.

    Reads the same folders the engine registers: the workspace's own
    ``agents/`` folder and the engine's bundled ``agent_library/``. The
    policy panel needs the full list so it can show a matrix, including
    agents that currently hold no grants at all.

    Args:
        agent_dirs:
            Folders to scan. Defaults to the workspace agents folder and
            the engine's bundled library.

    Returns:
        Agent ids, deduplicated, workspace agents first because they
        shadow library agents of the same id.
    """

    if agent_dirs is None:

        agent_dirs = [
            paths.PROJECT_ROOT / "agents",
            paths.AGENTCREATOR_ROOT
            / "headless_app"
            / "engine"
            / "agent_library",
        ]

    found: list[str] = []

    for agent_dir in agent_dirs:

        if not agent_dir.is_dir():

            continue

        for child in sorted(
            agent_dir.iterdir(),
            key=lambda item: item.name.lower(),
        ):

            if not child.is_dir():

                continue

            if child.name.startswith(
                ("_", ".")
            ):

                continue

            # An agent is a folder with an agent.json. A folder without a
            # readable one is not an agent and must not become a policy
            # key that silently matches nothing.
            if not _has_agent_meta(
                child
            ):

                continue

            agent_id = _agent_id_of(
                child
            )

            if agent_id and agent_id not in found:

                found.append(agent_id)

    return found


def _agent_id_of(
    agent_dir: Path,
) -> str:
    """The id declared inside an agent folder.

    Prefers ``agent.json``'s own ``id`` field over the folder name, because
    the two disagree in practice -- the shipped workspace contains a folder
    ``problem_clarfier`` whose id is ``problem_clarifer``. Keying a policy
    on the folder name would silently never match.

    Args:
        agent_dir:
            The agent folder.

    Returns:
        The declared id, or the folder name when there is none.
    """

    meta_file = agent_dir / "agent.json"

    if meta_file.is_file():

        try:

            meta = json.loads(
                meta_file.read_text(
                    encoding="utf-8"
                )
            )

            declared = meta.get(
                "id",
                "",
            )

            if isinstance(
                declared,
                str,
            ) and declared.strip():

                return declared.strip()

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            OSError,
        ):

            pass

    return agent_dir.name


def seed_policy(
    agent_dirs: list[Path] | None = None,
) -> Policy:
    """Build rules that reproduce the permissions in force right now.

    This exists so that adopting the policy engine changes *where* the rules
    live without changing *what they say*. Every tool every agent already
    holds is granted, over exactly the roots it could already reach:

    * a mutating tool is granted the writable roots only, which is what the
      old ``writable`` flag enforced;
    * a non-mutating tool is granted every root, because reads were never
      restricted.

    Tightening is then a deliberate edit to ``policy.json``, visible in a diff,
    rather than a side effect of installing a permission system.

    Args:
        agent_dirs:
            Folders to scan for agents.

    Returns:
        A Policy seeded from the current filesystem and agent definitions.
    """

    writable_globs = [
        f"{name}/**"
        for name in paths.root_names()
        if paths.is_writable_root(name)
    ]

    all_globs = [
        f"{name}/**"
        for name in paths.root_names()
    ]

    def globs_for(
        tool: str,
    ) -> list[str]:

        if tool in MUTATING_TOOLS:

            return list(writable_globs)

        return list(all_globs)

    agents: dict[str, dict[str, Rule]] = {}

    for agent_id in discover_agent_ids(
        agent_dirs
    ):

        agents[agent_id] = {}

    for agent_dir, agent_id in _iter_agent_pairs(
        agent_dirs
    ):

        rules = agents.setdefault(
            agent_id,
            {},
        )

        for tool in _read_agent_tool_ids(
            agent_dir
        ):

            if tool in rules:

                continue

            rules[tool] = Rule(
                effect="allow",
                paths=tuple(
                    globs_for(tool)
                ),
            )

    return Policy(
        version=1,
        default="deny",
        tools={},
        agents=agents,
        source="<seeded>",
    )


def _iter_agent_pairs(
    agent_dirs: list[Path] | None = None,
) -> list[tuple[Path, str]]:
    """Every agent folder paired with the id it declares.

    Args:
        agent_dirs:
            Folders to scan.

    Returns:
        ``(folder, agent_id)`` pairs in discovery order.
    """

    if agent_dirs is None:

        agent_dirs = [
            paths.PROJECT_ROOT / "agents",
            paths.AGENTCREATOR_ROOT
            / "headless_app"
            / "engine"
            / "agent_library",
        ]

    pairs: list[tuple[Path, str]] = []

    for agent_dir in agent_dirs:

        if not agent_dir.is_dir():

            continue

        for child in sorted(
            agent_dir.iterdir(),
            key=lambda item: item.name.lower(),
        ):

            if not child.is_dir():

                continue

            if child.name.startswith(
                ("_", ".")
            ):

                continue

            if not _has_agent_meta(
                child
            ):

                continue

            pairs.append(
                (child, _agent_id_of(
                    child,
                ))
            )

    return pairs


# ============================================================
# MODULE STATE
# ============================================================

#: The process-wide policy. Loaded on first use rather than at import, so a
#: test that writes a fixture policy does not have to fight an import-time
#: side effect.
_policy: Policy | None = None


def current_policy(
    reload: bool = False,
) -> Policy:
    """The loaded policy, loading it on first use.

    Args:
        reload:
            Re-read the file even if a policy is already loaded. The
            panel calls this after saving so an edit takes effect without
            a restart.

    Returns:
        The active Policy.
    """

    global _policy

    if _policy is None or reload:

        _policy = load_policy()

    return _policy


def set_policy(
    policy: Policy | None,
) -> None:
    """Replace the active policy, or clear it.

    Args:
        policy:
            The Policy to install, or None to force a reload from disk
            on next use.

    Returns:
        None.
    """

    global _policy

    _policy = policy


def reset_for_tests() -> None:
    """Forget the loaded policy so the next use re-reads from disk.

    Mirrors ``project_manager.interface.core.defaults.reset_for_tests``.

    Returns:
        None.
    """

    set_policy(None)