"""
ws_controlPanel/tests/test_paths.py
===================================

Tests for the path authority: root resolution, containment and writability.

These are the tests that matter most, because every other component trusts
these functions. ``policy`` decides *whether* an operation is allowed; these
decide *where* it lands. A bug here is not a wrong answer, it is an escape
from the sandbox, so the cases below are mostly adversarial.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ws_controlPanel import paths


class TestSplitRoot:
    """
    Splitting a root-qualified path into its root name and remainder.
    """

    def test_recognises_a_known_root(self):
        assert paths.split_root(
            "workspace/agents/helper/agent.json"
        ) == (
            "workspace",
            "agents/helper/agent.json",
        )

    def test_recognises_the_read_only_root(self):
        assert paths.split_root(
            "source_files/engine.py"
        ) == (
            "source_files",
            "engine.py",
        )

    def test_unknown_head_is_a_legacy_path(self):
        # No known root, so the caller resolves it against the workspace,
        # which is what every pre-existing API caller sends.
        assert paths.split_root(
            "agents/helper/agent.json"
        ) == (
            None,
            "agents/helper/agent.json",
        )

    def test_backslashes_are_normalised(self):
        assert paths.split_root(
            "workspace\\agents\\helper\\agent.json"
        ) == (
            "workspace",
            "agents/helper/agent.json",
        )

    def test_bare_name_has_no_root(self):
        assert paths.split_root("workspace") == (
            None,
            "workspace",
        )


class TestResolveProjectPath:
    """
    Legacy (root-less) resolution against the managed workspace.
    """

    def test_relative_path_resolves_into_the_workspace(self):
        resolved = paths.resolve_project_path(
            "agents/helper/agent.json"
        )

        assert resolved.is_absolute()
        assert paths.is_within(
            resolved,
            paths.PROJECT_ROOT,
        )

    def test_traversal_is_refused(self):
        # The regression that started this module: "workspace/**" matched
        # "../../escape.md" because "**" was treated as "anything, including
        # separators and leading dots".
        with pytest.raises(
            ValueError,
            match="outside",
        ):
            paths.resolve_project_path("../../escape.md")

    def test_traversal_inside_a_root_qualified_path_is_refused(self):
        with pytest.raises(
            ValueError,
            match="outside",
        ):
            paths.resolve_project_path("workspace/../../escape.md")

    def test_absolute_path_inside_the_workspace_is_accepted(self):
        target = paths.PROJECT_ROOT / "project.json"

        assert paths.resolve_project_path(
            str(target)
        ) == target.resolve()

    def test_absolute_path_outside_the_workspace_is_refused(self):
        with pytest.raises(
            ValueError,
            match="outside",
        ):
            paths.resolve_project_path(
                str(
                    paths.PROJECT_ROOT.parent.parent / "elsewhere.md"
                )
            )


class TestResolveAgentPath:
    """
    Agent-file resolution, which is workspace-relative and rejects escapes.
    """

    def test_bare_relative_path(self):
        resolved = paths.resolve_agent_path(
            "agents/helper/agent.json"
        )

        assert resolved == (
            paths.PROJECT_ROOT / "agents" / "helper" / "agent.json"
        ).resolve()

    def test_root_qualified_path_resolves_to_the_same_file(self):
        # The double-prefix bug: "workspace/agents/..." used to become
        # "workspace/workspace/agents/..." and be reported as an escape.
        assert paths.resolve_agent_path(
            "workspace/agents/helper/agent.json"
        ) == paths.resolve_agent_path(
            "agents/helper/agent.json"
        )

    def test_empty_path_is_refused(self):
        with pytest.raises(
            ValueError,
            match="required",
        ):
            paths.resolve_agent_path("")

    def test_traversal_is_refused(self):
        with pytest.raises(
            ValueError,
            match="outside",
        ):
            paths.resolve_agent_path("../../../Windows/win.ini")

    def test_absolute_path_outside_is_refused(self):
        with pytest.raises(
            ValueError,
            match="outside",
        ):
            paths.resolve_agent_path(r"C:\Windows\win.ini")

    def test_explicit_boundary_is_honoured(self, tmp_path):
        inside = tmp_path / "agents" / "demo" / "agent.json"
        inside.parent.mkdir(parents=True)
        inside.write_text("{}", encoding="utf-8")

        resolved = paths.resolve_agent_path(
            "agents/demo/agent.json",
            workspace_root=tmp_path,
        )

        assert resolved == inside.resolve()

    def test_a_rootless_relative_path_lands_inside_an_empty_boundary(
        self,
        tmp_path,
    ):
        # Resolving a path under a root that does not exist yet is legitimate
        # -- that is how a new agent directory gets created. The containment
        # rule is about escapes, not about existence.
        resolved = paths.resolve_agent_path(
            "agents/demo/agent.json",
            workspace_root=tmp_path / "not-created-yet",
        )

        assert resolved == (
            tmp_path / "not-created-yet" / "agents" / "demo" / "agent.json"
        )

    def test_traversal_out_of_an_explicit_boundary_is_refused(
        self,
        tmp_path,
    ):
        with pytest.raises(
            ValueError,
            match="outside",
        ):
            paths.resolve_agent_path(
                "agents/../../escape.md",
                workspace_root=tmp_path,
            )

    def test_absolute_path_outside_an_explicit_boundary_is_refused(
        self,
        tmp_path,
    ):
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        target = elsewhere / "agent.json"
        target.write_text("{}", encoding="utf-8")

        with pytest.raises(
            ValueError,
            match="outside",
        ):
            paths.resolve_agent_path(
                str(target),
                workspace_root=tmp_path / "boundary",
            )

    def test_symlinked_root_is_not_mistaken_for_an_escape(
        self,
        tmp_path,
    ):
        # Both sides of the containment comparison are resolved, so a root
        # reached through a symlink still matches. Comparing a resolved
        # candidate against an unresolved root would refuse this as an
        # escape and make the boundary unusable.
        real = tmp_path / "real-workspace"
        inside = real / "agents" / "demo" / "agent.json"
        inside.parent.mkdir(parents=True)
        inside.write_text("{}", encoding="utf-8")

        link = tmp_path / "linked-workspace"

        try:
            link.symlink_to(
                real,
                target_is_directory=True,
            )
        except (OSError, NotImplementedError):
            pytest.skip(
                "symlink creation not permitted on this filesystem"
            )

        resolved = paths.resolve_agent_path(
            "agents/demo/agent.json",
            workspace_root=link,
        )

        assert resolved == inside.resolve()


class TestWritability:
    """
    The read-only floor that applies to everyone, human or agent.
    """

    def test_source_files_is_never_writable(self):
        assert paths.is_writable_root(
            "source_files"
        ) is False

    def test_workspace_is_writable(self):
        assert paths.is_writable_root("workspace") is True

    def test_test_environment_is_writable(self):
        assert paths.is_writable_root("test_environment") is True

    def test_legacy_paths_resolve_to_the_writable_workspace(self):
        # Every existing API caller sends a root-less path. Refusing those
        # would break the editor, so the default has to be writable.
        assert paths.is_writable_root(None) is True

    def test_unknown_root_is_not_writable(self):
        # Fail closed on a typo'd root rather than guessing it is the
        # workspace.
        assert paths.is_writable_root(
            "workspce"
        ) is False


class TestToRootQualified:
    """
    Producing the canonical ``root/relative`` form used by policy globs.
    """

    def test_bare_path_is_qualified_with_the_workspace(self):
        qualified = paths.to_root_qualified(
            "agents/helper/agent.json"
        )

        assert qualified == (
            "workspace/agents/helper/agent.json"
        )

    def test_already_qualified_path_is_unchanged(self):
        # Idempotent: qualifying twice must not double the prefix.
        once = paths.to_root_qualified(
            "workspace/agents/helper/agent.json"
        )

        assert paths.to_root_qualified(once) == once

    def test_source_files_path_keeps_its_root(self):
        assert paths.to_root_qualified(
            "source_files/engine.py"
        ) == "source_files/engine.py"

    def test_result_is_normalised_to_forward_slashes(self):
        qualified = paths.to_root_qualified(
            "agents\\helper\\agent.json"
        )

        assert "\\" not in qualified
        assert qualified.startswith("workspace/")


class TestIsInside:
    """
    Containment, including the sibling-prefix trap.
    """

    def test_direct_child_is_inside(self):
        assert paths.is_within(
            paths.PROJECT_ROOT / "a" / "b.txt",
            paths.PROJECT_ROOT,
        )

    def test_the_boundary_itself_is_inside(self):
        assert paths.is_within(
            paths.PROJECT_ROOT,
            paths.PROJECT_ROOT,
        )

    def test_sibling_with_a_shared_prefix_is_outside(self):
        # "E:\repo_backup" starts with "E:\repo" as a string but is not
        # inside it. A string prefix test gets this wrong; path comparison
        # does not.
        assert not paths.is_within(
            paths.PROJECT_ROOT.parent / "repo_backup" / "secrets.env",
            paths.PROJECT_ROOT,
        )

    def test_parent_is_outside(self):
        assert not paths.is_within(
            paths.PROJECT_ROOT.parent,
            paths.PROJECT_ROOT,
        )


class TestRepoRoot:
    """
    The application repository as a read-only root.

    Added so an agent can read the code it is running. The two properties that
    matter are that it is read-only, and that adding an outermost root did not
    disturb the three roots nested inside it.
    """

    def test_repo_is_a_declared_root(self):
        assert "repo" in paths.ROOTS
        assert paths.root_path(
            "repo"
        ) == paths.AGENTCREATOR_ROOT

    def test_repo_is_not_writable(self):
        assert paths.is_writable_root("repo") is False

    def test_repo_paths_resolve_to_the_repo_root(self):
        qualified = paths.to_root_qualified(
            "repo/headless_app/tools/project_tools.py"
        )

        assert qualified == "repo/headless_app/tools/project_tools.py"

    def test_nested_roots_still_win(self):
        # repo contains the other three. Longest-match has to keep resolving
        # workspace/notes.md to workspace, or every existing policy glob would
        # silently stop matching.
        for expected, candidate in (
            ("workspace/notes.md", "workspace/notes.md"),
            ("test_environment/a.py", "test_environment/a.py"),
            ("source_files/a.md", "source_files/a.md"),
        ):

            assert paths.to_root_qualified(candidate) == expected

    def test_a_bare_path_still_resolves_against_the_workspace(self):
        # Unqualified paths are workspace-relative. That is what every
        # pre-existing caller sends, and routing them to repo instead would
        # be a silent change of meaning.
        assert paths.to_root_qualified(
            "agents/helper/agent.json"
        ) == "workspace/agents/helper/agent.json"

    def test_repo_does_not_become_writable_through_a_policy(self):
        from ws_controlPanel import gate
        from ws_controlPanel.policy import parse_policy

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
            "repo/headless_app/tools/project_tools.py",
            policy=policy,
        )

        assert not decision.allowed
        assert decision.rule == "read-only-root"

    def test_repo_is_not_granted_to_any_agent_by_default(self):
        from ws_controlPanel import gate

        for agent_id in (
            "helper",
            "rag_assistant",
            "execute_engineer_agent",
            "module_builder_agent",
        ):

            assert not gate.check_path(
                agent_id,
                "read_file",
                "repo/headless_app/tools/project_tools.py",
            ).allowed, (
                f"{agent_id} can read repo/** without an explicit grant"
            )


class TestShouldIgnore:
    """
    The two-tier ignore rule.

    Tier one is "this name is tool output wherever it appears". Tier two is
    "this name is noise under this root". They are separate because a flat
    list takes a user's own directory away along with the application's.
    """

    def test_tool_output_is_ignored_at_any_depth(self):
        for candidate in (
            ".git/config",
            "repo/.git/config",
            "headless_app/.venv/x.py",
            "headless_app/__pycache__/a.pyc",
            "workspace/__pycache__/a.pyc",
        ):

            assert paths.should_ignore(
                Path(candidate)
            ), candidate

    def test_repo_data_is_ignored(self):
        for candidate in (
            "repo/data",
            "repo/data/chatlog/chat.log",
            paths.AGENTCREATOR_ROOT / "data" / "chatlog" / "chat.log",
        ):

            assert paths.should_ignore(
                Path(candidate)
            ), candidate

    def test_a_bare_data_path_is_workspace_data_and_is_kept(self):
        # ``data/chat.log`` is read as ``workspace/data/chat.log``, because a
        # bare relative path has always meant the workspace. So it is kept.
        # The application's own logs are addressed as ``repo/data/...`` or by
        # absolute path, and those are the forms that get excluded.
        assert not paths.should_ignore(
            Path("data/chatlog/chat.log")
        )

    def test_workspace_data_is_kept(self):
        # The regression this tiering exists to prevent.
        for candidate in (
            "workspace/data",
            "workspace/data/notes.md",
            paths.PROJECT_ROOT / "data" / "notes.md",
        ):

            assert not paths.should_ignore(
                Path(candidate)
            ), candidate

    def test_a_data_directory_deeper_in_a_root_is_kept(self):
        assert not paths.should_ignore(
            Path("workspace/documentation/data/x.md")
        )
        assert not paths.should_ignore(
            Path("test_environment/src/data/loader.py")
        )

    def test_ordinary_content_is_never_ignored(self):
        for candidate in (
            "workspace/project.json",
            "workspace/src/dataset.py",
            "workspace/metadata.yaml",
            "repo/headless_app/tools/project_tools.py",
        ):

            assert not paths.should_ignore(
                Path(candidate)
            ), candidate
