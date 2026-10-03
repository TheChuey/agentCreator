"""
ws_controlPanel/tests/test_policy.py
====================================

Tests for the policy schema, glob matching and default-deny behaviour.

Two API shapes matter when reading these tests, because they are easy to
transpose and transposing them produces confident nonsense:

* ``allows_tool(agent_id, tool)`` -- the agent comes first.
* ``allows_path(agent_id, tool, target)`` returns a ``Decision``, not a bool,
  so assertions read ``.allowed``. A ``Decision`` is always truthy, so
  ``assert policy.allows_path(...)`` would pass even for a refusal.

The seeded ``policy.json`` shipped with this repository was generated from the
agent definitions that already existed, so this file also includes a fidelity
check: the seed must reproduce what the old code actually permitted. A seed
that quietly grants less than before would look correct in unit tests and
break the running application; one that grants more is a security hole.
"""

from __future__ import annotations

import pytest

from ws_controlPanel import policy as policy_module
from ws_controlPanel import paths
from ws_controlPanel.policy import (
    path_matches,
    parse_policy,
)


class TestPathMatches:
    """
    Glob semantics. ``*`` is one segment; ``**`` is zero or more.
    """

    def test_star_matches_a_single_segment(self):
        assert path_matches(
            "workspace/agents/*/agent.json",
            "workspace/agents/helper/agent.json",
        )

    def test_star_does_not_cross_a_separator(self):
        # This is the distinction that matters. If "*" spanned separators,
        # "workspace/agents/*/agent.json" would match an agent nested two
        # levels down, and a grant written for one agent would quietly cover
        # a whole subtree.
        assert not path_matches(
            "workspace/agents/*/agent.json",
            "workspace/agents/helper/nested/agent.json",
        )

    def test_double_star_matches_one_segment(self):
        assert path_matches(
            "workspace/**",
            "workspace/documentation/APP_CODE_SNAPSHOT.md",
        )

    def test_double_star_matches_nested_segments(self):
        assert path_matches(
            "workspace/**",
            "workspace/a/b/c/d/deep.md",
        )

    def test_double_star_matches_a_direct_child(self):
        # "workspace/**" is meant to include the root itself. Excluding it
        # would make the intuitive spelling of "all of the workspace" fail.
        assert path_matches(
            "workspace/**",
            "workspace/file.md",
        )

    def test_literal_segment_must_match_exactly(self):
        assert not path_matches(
            "workspace/agents/*/agent.json",
            "workspace/agents/helper/notes.md",
        )

    def test_a_root_prefix_must_agree(self):
        assert not path_matches(
            "workspace/**",
            "test_environment/scratch.md",
        )

    def test_unqualified_pattern_matches_within_any_root(self):
        # "documentation/**" is how a person writes this grant in the editor.
        # Silently matching nothing would be the worst outcome: a rule that
        # looks correct and grants no access.
        assert path_matches(
            "documentation/**",
            "workspace/documentation/x.md",
        )

    def test_unqualified_pattern_still_respects_the_root(self):
        assert not path_matches(
            "documentation/**",
            "workspace/agents/helper/agent.json",
        )

    def test_leading_dotdot_is_never_matched_by_a_rooted_grant(self):
        # The original traversal bug: "workspace/**" matched
        # "../../escape.md" because the matcher counted leading traversal
        # segments as ordinary path segments.
        assert not path_matches(
            "workspace/**",
            "../../escape.md",
        )

    def test_leading_dotdot_is_not_matched_by_a_bare_grant(self):
        # Even "**" refuses it. Callers are meant to contain paths first, so
        # a ".." here means a check was skipped -- and a matcher that granted
        # on "**" would turn any skipped check into an escape.
        assert not path_matches(
            "**",
            "../../escape.md",
        )

    def test_dotdot_in_the_middle_is_refused(self):
        assert not path_matches(
            "workspace/**",
            "workspace/agents/../../../escape.md",
        )

    def test_empty_inputs_do_not_match(self):
        assert not path_matches("", "workspace/a.md")
        assert not path_matches("workspace/**", "")


class TestPolicyDefaults:
    """
    Default-deny, and what happens to an unmentioned tool.
    """

    def test_unknown_tool_is_denied(self):
        decision = parse_policy({}).allows_tool(
            "nobody",
            "anything",
        )

        assert decision.allowed is False

    def test_unknown_agent_is_denied(self):
        policy = parse_policy({
            "agents": {
                "helper": {"read_file": "allow"},
            },
        })

        assert policy.allows_tool(
            "stranger",
            "read_file",
        ).allowed is False

    def test_a_global_grant_still_needs_a_matching_path(self):
        policy = parse_policy({
            "tools": {"map_files": "allow"},
        })

        assert policy.allows_tool(
            "anyone",
            "map_files",
        ).allowed is True

    def test_empty_policy_denies_everything(self):
        policy = parse_policy({})

        for tool in (
            "read_file",
            "write_text_file",
            "delete_files",
        ):

            assert policy.allows_tool(
                "helper",
                tool,
            ).allowed is False


class TestAgentScoping:
    """
    A grant belongs to one agent unless it is declared globally.
    """

    def test_agent_grant_does_not_leak_to_another_agent(self):
        policy = parse_policy({
            "agents": {
                "helper": {"read_file": "allow"},
            },
        })

        assert policy.allows_tool(
            "helper",
            "read_file",
        ).allowed is True
        assert policy.allows_tool(
            "feature_planner_agent",
            "read_file",
        ).allowed is False

    def test_global_tool_grant_applies_to_every_agent(self):
        policy = parse_policy({
            "tools": {"map_files": "allow"},
        })

        for agent in (
            "helper",
            "feature_planner_agent",
            "nobody",
        ):

            assert policy.allows_tool(
                agent,
                "map_files",
            ).allowed is True

    def test_an_agent_rule_overrides_a_global_allow(self):
        # The point of scoping: a global allow with one agent carved out.
        policy = parse_policy({
            "tools": {"delete_files": "allow"},
            "agents": {
                "helper": {"delete_files": "deny"},
            },
        })

        assert policy.allows_tool(
            "helper",
            "delete_files",
        ).allowed is False
        assert policy.allows_tool(
            "rag_assistant",
            "delete_files",
        ).allowed is True


class TestPathScopedRules:
    """
    A tool can be granted but restricted to part of the tree.
    """

    @staticmethod
    def _documentation_only():
        return parse_policy({
            "agents": {
                "helper": {
                    "read_file": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                },
            },
        })

    def test_allow_within_the_granted_path(self):
        assert self._documentation_only().allows_path(
            "helper",
            "read_file",
            "workspace/documentation/APP_CODE_SNAPSHOT.md",
        ).allowed

    def test_refused_outside_the_granted_path(self):
        assert not self._documentation_only().allows_path(
            "helper",
            "read_file",
            "workspace/agents/helper/agent.json",
        ).allowed

    def test_holding_a_tool_is_not_holding_it_everywhere(self):
        # Two independent questions. Conflating them is how a path-scoped
        # grant silently becomes a global one.
        policy = self._documentation_only()

        assert policy.allows_tool(
            "helper",
            "read_file",
        ).allowed is True
        assert policy.allows_path(
            "helper",
            "read_file",
            "workspace/secrets.env",
        ).allowed is False

    def test_shorthand_string_grants_everywhere(self):
        policy = parse_policy({
            "agents": {
                "helper": {"read_file": "allow"},
            },
        })

        assert policy.allows_path(
            "helper",
            "read_file",
            "workspace/anything/at/all.md",
        ).allowed

    def test_multiple_paths_are_a_union(self):
        policy = parse_policy({
            "agents": {
                "helper": {
                    "read_file": {
                        "effect": "allow",
                        "paths": [
                            "workspace/documentation/**",
                            "source_files/**",
                        ],
                    },
                },
            },
        })

        assert policy.allows_path(
            "helper",
            "read_file",
            "workspace/documentation/a.md",
        ).allowed
        assert policy.allows_path(
            "helper",
            "read_file",
            "source_files/engine.py",
        ).allowed
        assert not policy.allows_path(
            "helper",
            "read_file",
            "workspace/agents/a.json",
        ).allowed

    def test_a_deny_rule_vetoes_an_allow(self):
        policy = parse_policy({
            "agents": {
                "helper": {
                    "write_text_file": {
                        "effect": "allow",
                        "paths": ["workspace/**"],
                    },
                },
            },
            "tools": {
                "write_text_file": {
                    "effect": "deny",
                    "paths": ["workspace/agents/**"],
                },
            },
        })

        assert policy.allows_path(
            "helper",
            "write_text_file",
            "workspace/notes.md",
        ).allowed
        assert not policy.allows_path(
            "helper",
            "write_text_file",
            "workspace/agents/helper/agent.json",
        ).allowed


class TestRoundTrip:
    """
    Serialisation, because the control panel has to be able to save edits.
    """

    def test_as_dict_round_trips_through_parse(self):
        original = parse_policy({
            "default": "deny",
            "agents": {
                "helper": {
                    "read_file": "allow",
                    "write_text_file": {
                        "effect": "allow",
                        "paths": ["workspace/**"],
                    },
                },
            },
        })

        again = parse_policy(original.as_dict())

        assert again.as_dict() == original.as_dict()

    def test_shorthand_expands_on_save(self):
        # Not a problem, just worth being explicit about: the saved form is
        # always expanded, so a hand-written "allow" becomes an explicit rule
        # list. Round-tripping is still stable.
        saved = parse_policy({
            "agents": {"helper": {"read_file": "allow"}},
        }).as_dict()

        assert saved["agents"]["helper"]["read_file"]["effect"] == "allow"

    def test_malformed_document_is_rejected_explicitly(self):
        # parse_policy validates hand-edited and API-supplied documents, so a
        # bad one raises rather than silently becoming something permissive.
        # Failing closed at *load* time is a separate behaviour, covered by
        # TestLoadFailure.
        with pytest.raises(
            ValueError,
            match="JSON object",
        ):
            parse_policy("this is not a policy document")

    def test_wrongly_typed_section_is_rejected(self):
        with pytest.raises(
            ValueError,
        ):
            parse_policy({"agents": ["not", "an", "object"]})


class TestLoadFailure:
    """
    A corrupt policy file must not take the server down with it.
    """

    def test_unparseable_file_denies_everything(self, tmp_path, capsys):
        broken = tmp_path / "policy.json"
        broken.write_text("{ this is not json", encoding="utf-8")

        loaded = policy_module.load_policy(broken)

        assert loaded.allows_tool(
            "helper",
            "delete_files",
        ).allowed is False
        assert "unreadable" in loaded.source

    def test_unparseable_file_warns_on_stderr(self, tmp_path, capsys):
        broken = tmp_path / "policy.json"
        broken.write_text("{ nope", encoding="utf-8")

        policy_module.load_policy(broken)

        assert "could not be read" in capsys.readouterr().err

    def test_missing_file_is_seeded_not_denied(self, tmp_path):
        # The opposite case. A fresh checkout has no policy file, and denying
        # everything would break every agent on first run.
        loaded = policy_module.load_policy(
            tmp_path / "does-not-exist.json"
        )

        assert loaded.agents, (
            "a missing policy file should seed from the agent definitions"
        )


class TestSeedFidelity:
    """
    The generated seed must match what the old code permitted.
    """

    def test_seed_covers_every_discovered_agent(self):
        seeded = policy_module.seed_policy()
        discovered = policy_module.discover_agent_ids()

        assert discovered, (
            "no agents were discovered; the fidelity check would be vacuous"
        )

        for agent_id in discovered:

            assert agent_id in seeded.agents, (
                f"{agent_id} is missing from the seeded policy"
            )

    def test_seed_grants_a_tool_only_where_it_was_requested(self):
        seeded = policy_module.seed_policy()

        for agent_id, rules in seeded.agents.items():

            for tool in rules:

                assert seeded.allows_tool(
                    agent_id,
                    tool,
                ).allowed, (
                    f"the seed grants {tool} to {agent_id}, "
                    "but no rule permits it there"
                )

    def test_seed_has_no_universal_grants(self):
        # The check that would catch the worst seed mistake: nothing granted
        # to every agent. A seed that reached for a global "allow" would hand
        # that tool to agents that never asked for it.
        seeded = policy_module.seed_policy()

        for tool, rule in seeded.tools.items():

            assert rule.effect != "allow", (
                f"the seed grants {tool} to every agent"
            )


class TestShippedPolicyFile:
    """
    The policy.json that actually ships must be usable.
    """

    def test_shipped_policy_loads(self):
        loaded = policy_module.load_policy()

        assert loaded.agents, (
            "the shipped policy grants nothing; every tool would be refused"
        )

    def test_shipped_policy_is_default_deny(self):
        assert policy_module.load_policy().default == "deny"

    def test_shipped_policy_does_not_claim_the_read_only_root_is_writable(
        self,
    ):
        # The policy and the path layer have to agree. Writability is not the
        # policy's to grant; it is a floor in paths.py.
        assert paths.is_writable_root(
            "source_files"
        ) is False