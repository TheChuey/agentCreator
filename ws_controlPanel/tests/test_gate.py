"""
ws_controlPanel/tests/test_gate.py
==================================

Tests for the two questions the gate answers, and for the seam where they meet
the agent factory.

The gate answers different questions at different times, and the tests are
organised around that split:

* ``allowed_tools`` runs once per agent build and answers *which tools* this
  agent holds.
* ``check_path`` runs on every call and answers *which paths* it may use.

Both are exercised against a real ``build_agent`` in
``TestFactoryIntegration``, because the factory is where the two meet and
that seam is where a permission change actually takes effect. A gate that is
correct in isolation but never called by the factory would pass every unit
test here and grant everything at runtime.
"""

from __future__ import annotations

import sys

import pytest

from ws_controlPanel import gate
from ws_controlPanel import paths
from ws_controlPanel.policy import parse_policy


@pytest.fixture
def registered_workspace():
    """
    Make ``workspace/agents`` a known agent root for the duration of a test.

    The agent roots are process-wide, so this undoes itself on teardown rather
    than leaving a root registered that changes which agents later tests can
    build.
    """

    from engine.agents import roots as roots_module

    roots_module.register_agent_root(
        "workspace",
        paths.PROJECT_ROOT / "agents",
        source="workspace",
    )

    yield

    registered = getattr(
        roots_module,
        "_REGISTERED_ROOTS",
        None,
    )

    if isinstance(registered, dict):

        registered.pop(
            "workspace",
            None,
        )


def _policy(**agents):
    return parse_policy({
        "version": 1,
        "default": "deny",
        "agents": agents,
    })


class TestAllowedTools:
    """
    Build-time filtering: which tools an agent ends up holding.
    """

    def test_granted_tools_survive(self, panel_policy):
        panel_policy(
            _policy(
                helper={
                    "read_file": "allow",
                    "map_files": "allow",
                },
            )
        )

        allowed, refused = gate.allowed_tools(
            "helper",
            ["read_file", "map_files", "write_text_file"],
        )

        assert allowed == ["read_file", "map_files"]

        # A tool-level refusal has no pattern behind it, so ``rule`` is empty
        # and the tool name lives in the reason. Asserting on the name is
        # what tells us the right tool was dropped.
        assert len(refused) == 1
        assert "write_text_file" in refused[0].reason

    def test_order_is_preserved(self, panel_policy):
        panel_policy(
            _policy(
                helper={
                    "map_files": "allow",
                    "read_file": "allow",
                },
            )
        )

        allowed, _ = gate.allowed_tools(
            "helper",
            ["read_file", "map_files"],
        )

        assert allowed == ["read_file", "map_files"]

    def test_an_unknown_agent_gets_nothing(self, panel_policy):
        panel_policy(
            _policy(
                helper={"read_file": "allow"},
            )
        )

        allowed, refused = gate.allowed_tools(
            "stranger",
            ["read_file"],
        )

        assert allowed == []
        assert len(refused) == 1

    def test_a_refusal_explains_itself(self, panel_policy):
        panel_policy(_policy())

        _, refused = gate.allowed_tools(
            "helper",
            ["delete_files"],
        )

        assert "delete_files" in refused[0].reason
        assert "helper" in refused[0].reason

    def test_no_request_means_no_tools(self, panel_policy):
        panel_policy(
            _policy(
                helper={"read_file": "allow"},
            )
        )

        allowed, refused = gate.allowed_tools("helper", [])

        assert allowed == []
        assert refused == []

    def test_log_refusals_accepts_a_sink(self, panel_policy):
        panel_policy(_policy())

        events = []

        gate.log_refusals(
            "helper",
            gate.allowed_tools("helper", ["delete_files"])[1],
            sink=events.append,
        )

        assert len(events) == 1
        assert events[0]["agent_id"] == "helper"


class TestCheckPath:
    """
    Call-time enforcement: which paths a held tool may touch.
    """

    def test_within_the_grant_is_allowed(self, panel_policy):
        panel_policy(
            _policy(
                helper={
                    "read_file": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                },
            )
        )

        assert gate.check_path(
            "helper",
            "read_file",
            "workspace/documentation/APP_CODE_SNAPSHOT.md",
        ).allowed

    def test_outside_the_grant_is_refused(self, panel_policy):
        panel_policy(
            _policy(
                helper={
                    "read_file": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                },
            )
        )

        assert not gate.check_path(
            "helper",
            "read_file",
            "workspace/agents/helper/agent.json",
        ).allowed

    def test_a_refusal_names_the_path(self, panel_policy):
        panel_policy(
            _policy(
                helper={
                    "read_file": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                },
            )
        )

        decision = gate.check_path(
            "helper",
            "read_file",
            "workspace/agents/helper/agent.json",
        )

        assert "workspace/agents/helper/agent.json" in decision.reason

    def test_several_paths_must_all_be_allowed(self, panel_policy):
        # A list, not a best-effort. One bad path in a delete batch must
        # refuse the whole call rather than silently deleting the rest.
        panel_policy(
            _policy(
                helper={
                    "read_file": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                },
            )
        )

        assert not gate.check_path(
            "helper",
            "read_file",
            [
                "workspace/documentation/a.md",
                "workspace/agents/helper/agent.json",
            ],
        ).allowed

    def test_traversal_is_refused(self, panel_policy):
        panel_policy(
            _policy(
                helper={"read_file": "allow"},
            )
        )

        assert not gate.check_path(
            "helper",
            "read_file",
            "../../Windows/win.ini",
        ).allowed

    def test_an_absolute_path_outside_every_root_is_refused(
        self,
        panel_policy,
    ):
        panel_policy(
            _policy(
                helper={"read_file": "allow"},
            )
        )

        assert not gate.check_path(
            "helper",
            "read_file",
            r"C:\Windows\win.ini",
        ).allowed

    def test_no_target_skips_the_path_question(self, panel_policy):
        # Tools with no path argument should not be refused for lacking one.
        panel_policy(
            _policy(
                helper={"get_current_date": "allow"},
            )
        )

        assert gate.check_path(
            "helper",
            "get_current_date",
        ).allowed


class TestReadOnlyFloor:
    """
    Writability belongs to the root, not to the policy.
    """

    def test_a_policy_cannot_make_a_read_only_root_writable(self):
        # Even a maximally permissive policy does not get to grant a write to
        # source_files. The floor is in paths.py and the gate honours it, so a
        # hand-edited policy cannot talk its way past it.
        policy = parse_policy({
            "tools": {
                "write_text_file": {
                    "effect": "allow",
                    "paths": ["**"],
                },
            },
        })

        decision = gate.check_path(
            "anyone",
            "write_text_file",
            "source_files/engine.py",
            policy=policy,
        )

        assert not decision.allowed
        assert paths.is_writable_root(
            "source_files"
        ) is False

    def test_a_read_inside_a_read_only_root_is_fine(self, panel_policy):
        panel_policy(
            _policy(
                helper={"read_file": "allow"},
            )
        )

        assert gate.check_path(
            "helper",
            "read_file",
            "source_files/APP_CODE_SNAPSHOT.md",
        ).allowed


class TestRequirePath:
    """
    The raising form, for callers that treat a refusal as an error.
    """

    def test_an_allowed_path_does_not_raise(self, panel_policy):
        panel_policy(
            _policy(
                helper={"read_file": "allow"},
            )
        )

        gate.require_path(
            "helper",
            "read_file",
            "workspace/notes.md",
        )

    def test_a_refused_path_raises(self, panel_policy):
        panel_policy(
            _policy(
                helper={
                    "read_file": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                },
            )
        )

        with pytest.raises(
            gate.PermissionDenied,
        ):
            gate.require_path(
                "helper",
                "read_file",
                "workspace/agents/helper/agent.json",
            )

    def test_the_exception_carries_the_decision(self, panel_policy):
        panel_policy(
            _policy(helper={"read_file": "allow"})
        )

        with pytest.raises(
            gate.PermissionDenied,
        ) as caught:

            gate.require_path(
                "helper",
                "delete_files",
                "workspace/x.txt",
            )

        assert caught.value.decision.allowed is False


class TestAgentMatrix:
    """
    The table the control-panel UI will render.

    The shape is one row per agent, holding the granted/requested/refused
    split, rather than one row per agent-tool pair. An agent row reads
    directly in a table; a per-tool matrix would be several hundred rows to
    answer "what can this agent do".
    """

    def test_every_agent_appears(self, panel_policy):
        panel_policy(
            _policy(
                helper={"read_file": "allow"},
                rag_assistant={"map_files": "allow"},
            )
        )

        listed = gate.agent_matrix()

        assert listed
        for entry in listed:

            assert {"id", "granted", "requested", "refused"} <= set(entry)

    def test_refused_tools_are_visible_alongside_granted_ones(
        self,
        panel_policy,
    ):
        # The UI needs to show a refusal as clearly as a grant, otherwise the
        # reason an agent cannot write is invisible.
        panel_policy(
            _policy(
                helper={
                    "read_file": "allow",
                    "bundle_files": "allow",
                },
            )
        )

        helper_rows = [
            row
            for row in gate.agent_matrix()
            if row["id"] == "helper"
        ]

        assert len(helper_rows) == 1

        row = helper_rows[0]

        # "granted" keeps agent.json's own order, so an operator reading the
        # matrix sees the tools in the order the agent lists them.
        assert row["granted"] == [
            "read_file",
            "bundle_files",
        ]
        assert set(row["requested"]) == {
            "map_files",
            "read_file",
            "bundle_files",
            "write_text_file",
        }

        # "refused" carries the full Decision rather than a bare name, because
        # the reason is what the operator needs in order to tell a typo in
        # agent.json from a deliberate denial in the policy.
        refused_names = {
            decision["reason"].split("'")[1]
            for decision in row["refused"]
        }

        assert refused_names == {
            "map_files",
            "write_text_file",
        }



class TestFactoryIntegration:
    """
    The seam: policy has to reach a real, callable agent tool.
    """

    @staticmethod
    def _build(agent_id="helper"):
        from engine.agents import factory

        return factory

    def test_a_refused_tool_is_never_built(
        self,
        panel_policy,
        registered_workspace,
    ):
        # Not "raises when called" -- never exists. A tool the model cannot
        # see cannot be called, cannot be advertised in the system prompt, and
        # costs nothing on every subsequent round.
        panel_policy(
            _policy(
                helper={
                    "read_file": "allow",
                    "map_files": "allow",
                },
            )
        )

        factory = self._build()
        agent = factory.build_agent("helper")

        assert "read_file" in agent.tools
        assert "write_text_file" not in agent.tools

    def test_the_shipped_policy_leaves_agents_unchanged(
        self,
        registered_workspace,
    ):
        # The regression guard for the whole exercise: with the shipped
        # policy.json, helper still gets exactly the three tools its
        # agent.json asked for.
        from engine.agents import factory
        from ws_controlPanel import policy as policy_module

        policy_module.reset_for_tests()

        agent = factory.build_agent("helper")

        assert sorted(agent.tools) == [
            "bundle_files",
            "map_files",
            "read_file",
            "write_text_file",
        ]

    def test_a_scoped_grant_refuses_an_unscoped_path(
        self,
        panel_policy,
        registered_workspace,
    ):
        panel_policy(
            _policy(
                helper={
                    "read_file": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                },
            )
        )

        factory = self._build()
        agent = factory.build_agent("helper")

        allowed = agent.tools["read_file"](
            "workspace/documentation/APP_CODE_SNAPSHOT.md"
        )
        refused = agent.tools["read_file"](
            "workspace/agents/helper/agent.json"
        )

        assert allowed.get("success")
        assert not refused.get("success")
        assert "refused_paths" in (
            refused.get("data") or {}
        )

    def test_a_refusal_is_a_result_not_an_exception(
        self,
        panel_policy,
        registered_workspace,
    ):
        # The model has to be able to read a refusal and react to it. An
        # exception here would surface as a tool-loop error instead.
        panel_policy(
            _policy(
                helper={"read_file": "allow"},
            )
        )

        factory = self._build()
        agent = factory.build_agent("helper")

        result = agent.tools["read_file"]("../../Windows/win.ini")

        assert isinstance(result, dict)
        assert result.get("success") is False
        assert result.get("error")

    def test_pathless_tools_are_untouched(
        self,
        panel_policy,
        registered_workspace,
    ):
        # A tool with no path argument must not be refused for lacking one.
        # rag_assistant is the agent that requests get_current_date.
        panel_policy(
            _policy(
                rag_assistant={
                    "get_current_date": "allow",
                },
            )
        )

        factory = self._build()
        agent = factory.build_agent("rag_assistant")

        assert "get_current_date" in agent.tools

    def test_a_policy_cannot_grant_an_unrequested_tool(
        self,
        panel_policy,
        registered_workspace,
    ):
        # agent.json names what an agent wants; the policy can only lower that.
        # The effective grant is the intersection of the two, so a policy that
        # hands out delete_files to every agent still does not put it in
        # helper's hands, because helper never asked for it.
        panel_policy(
            _policy(
                helper={"delete_files": "allow"},
            )
        )

        factory = self._build()
        agent = factory.build_agent("helper")

        assert "delete_files" not in agent.tools


class TestBundleFilesGating:
    """
    ``bundle_files`` reads several paths in one call, so it has to clear every
    one of them before it reads the first.

    The argument is named ``paths`` precisely so the existing path-argument
    handling picks it up. If the name drifted -- say to ``files`` -- the gate
    would find no path to check, the tool would build, and a whole bundle of
    ungoverned repository source would come back in one call. These tests fail
    if that happens.
    """

    @staticmethod
    def _build(agent_id="helper"):
        from engine.agents import factory

        return factory

    def test_the_argument_name_is_still_gated(
        self,
        panel_policy,
        registered_workspace,
    ):
        from engine.agents import factory

        assert "paths" in factory.PATH_ARGUMENT_NAMES

    def test_the_repo_root_is_refused_by_default(
        self,
        panel_policy,
        registered_workspace,
    ):
        panel_policy(
            _policy(
                helper={
                    "read_file": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                    "bundle_files": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                },
            )
        )

        agent = self._build().build_agent("helper")

        assert "bundle_files" in agent.tools

        result = agent.tools["bundle_files"]([
            "repo/headless_app/tools/project_tools.py",
        ])

        assert result.get("success") is False
        assert "repo" in str(result.get("error"))

    def test_one_unreadable_path_refuses_the_whole_bundle(
        self,
        panel_policy,
        registered_workspace,
    ):
        # All-or-nothing, not best-effort. A bundle that quietly drops the
        # one file the agent was not allowed to see is worse than a refusal:
        # the model reasons about an incomplete set of files believing it has
        # the whole picture.
        panel_policy(
            _policy(
                helper={
                    "read_file": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                    "bundle_files": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                },
            )
        )

        agent = self._build().build_agent("helper")

        result = agent.tools["bundle_files"]([
            "workspace/documentation/registry.py",
            "repo/headless_app/tools/project_tools.py",
        ])

        assert result.get("success") is False
        assert result.get("data", {}).get("extracted_content") is None

    def test_granted_paths_still_bundle(
        self,
        panel_policy,
        registered_workspace,
    ):
        panel_policy(
            _policy(
                helper={
                    "read_file": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                    "bundle_files": {
                        "effect": "allow",
                        "paths": ["workspace/documentation/**"],
                    },
                },
            )
        )

        agent = self._build().build_agent("helper")

        result = agent.tools["bundle_files"]([
            "workspace/documentation/registry.py",
        ])

        assert result.get("success") is True
        assert "registry.py" in result["data"]["extracted_content"]

    def test_a_policy_cannot_widen_the_repo_root_to_write(
        self,
        panel_policy,
        registered_workspace,
    ):
        panel_policy(
            _policy(
                helper={
                    "read_file": "allow",
                    "bundle_files": "allow",
                    "write_text_file": {
                        "effect": "allow",
                        "paths": ["repo/**"],
                    },
                },
            )
        )

        agent = self._build().build_agent("helper")

        result = agent.tools["write_text_file"](
            "_gate_probe.py",
            "x = 1\n",
            "repo/headless_app/tools/_gate_probe.py",
        )

        assert result.get("success") is False
