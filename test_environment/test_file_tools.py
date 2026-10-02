"""
test_environment/test_file_tools.py
===================================

Tests for the headless file tools as they run against a Project Manager
provider: the three browse roots, the path translation between them, the
text-extension rules, and the tool log.

These live in ``test_environment/`` rather than beside the code because
they are about the provider contract - what an agent may reach, and how a
path it was handed comes back - not about one function in isolation. The
Project Manager filesystem is the authority under test, so these run
against the real roots and clean up everything they create.

Run:

    .venv/Scripts/python -m pytest test_environment/test_file_tools.py -v

``test_environment`` is on ``sys.path`` (it is imported by the Project
Manager's testing router), so ``conftest.py`` beside this file puts the
engine and the Project Manager package on the path as well.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


# ============================================================
# PATH SETUP
# ============================================================

REPO_ROOT = Path(__file__).resolve().parents[1]

for _on_path in (REPO_ROOT / "headless_app", REPO_ROOT / "project_manager"):
    if _on_path.is_dir() and str(_on_path) not in sys.path:
        sys.path.insert(0, str(_on_path))

from bridge.client import _relpath, _relpath_roots  # noqa: E402
from bridge.providers import DirectProjectIO  # noqa: E402
from tools import project_tools  # noqa: E402
from tools.chatlog import (  # noqa: E402
    clear_tool_events,
    read_tool_events,
    use_data_dir,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(scope="module")
def provider() -> DirectProjectIO:
    return DirectProjectIO()


@pytest.fixture(autouse=True)
def bound_provider(provider):
    """Bind the Project Manager provider for the duration of each test.

    The tools resolve their filesystem through ``current_provider()``, which
    is what the runtime's per-agent binding does, so every test exercises the
    real provider path rather than the local-disk fallback.
    """
    with project_tools.using(provider):
        yield provider


@pytest.fixture(autouse=True)
def isolated_tool_log(tmp_path):
    """Send tool-stage events to a throwaway data dir.

    Every tool now reports its own verdict (stage="tool") when it runs, so
    even a test that merely calls a tool writes the shared log. Redirecting
    keeps the real data/toollog/tool_usage.jsonl out of the test run.
    """
    with use_data_dir(tmp_path / "data"):
        yield


@pytest.fixture
def scratch(provider):
    """A throwaway folder inside the writable test_environment root.

    Yields the absolute path and removes it afterwards, so a failing test
    cannot leave files behind in a root the agent can also write to.
    """
    created = []

    def make(name: str) -> Path:
        target = Path(provider.abspath(f"test_environment/{name}"))
        target.mkdir(parents=True, exist_ok=True)
        created.append(target)
        return target

    yield make
    for target in reversed(created):
        try:
            for child in sorted(target.rglob("*"), reverse=True):
                child.rmdir() if child.is_dir() else child.unlink()
            target.rmdir()
        except OSError:
            pass


# ============================================================
# ROOT QUALIFICATION
# ============================================================

class TestRelpath:
    """A path becomes root-qualified, so the tools and the Project Manager
    never have to guess which root a bare path belonged to."""

    def test_workspace_root_maps_to_workspace(self, provider):
        assert provider.relpath(str(provider._root)) == "workspace"

    def test_dot_maps_to_every_root(self, provider):
        assert provider.relpath(".") == ""
        assert provider.relpath("") == ""

    def test_absolute_path_in_a_root(self, provider):
        target = provider.abspath("source_files/headless_app_MASTER_COPY.md")
        assert provider.relpath(target) == (
            "source_files/headless_app_MASTER_COPY.md"
        )

    def test_root_qualified_path_is_kept(self, provider):
        assert provider.relpath("source_files") == "source_files"

    def test_legacy_workspace_path_gets_qualified(self, provider):
        assert provider.relpath("agents/agent.json") == (
            "workspace/agents/agent.json"
        )

    def test_path_outside_every_root_is_refused(self, provider):
        with pytest.raises(ValueError, match="outside every Project Manager"):
            provider.relpath(str(REPO_ROOT / "docs"))

    def test_shared_helper_normalises_root(self, tmp_path):
        """The absolute branch used to return '.', which map_files then
        turned into a base path that filtered out every entry."""
        assert _relpath(tmp_path, str(tmp_path)) == ""

    def test_shared_helper_handles_root_qualified_input(self):
        roots = {
            "workspace": "C:/repo/workspace",
            "source_files": "C:/repo/source_files",
        }
        assert _relpath_roots(roots, "C:/repo/source_files/x.md") == (
            "source_files/x.md"
        )
        assert _relpath_roots(roots, "C:/repo/workspace") == "workspace"
        assert _relpath_roots(roots, "notes") == "workspace/notes"


# ============================================================
# map_files
# ============================================================

class TestMapFiles:

    def test_workspace_root_lists_its_entries(self, provider):
        result = project_tools.map_files(
            str(provider._root)
        )
        assert result["success"]
        assert result["data"]["files"], "mapping the workspace root returned nothing"

    def test_every_browse_root_is_reachable(self, provider):
        seen = set()
        for root in ("workspace", "test_environment", "source_files"):
            result = project_tools.map_files(root)
            assert result["success"], f"{root} is not mappable"
            for entry in result["data"]["files"]:
                assert entry["path_relative"].startswith(root + "/")
                seen.add(entry["path_relative"])
        assert seen, "no entries across any root"

    def test_root_mapping_reaches_all_roots(self, provider):
        result = project_tools.map_files("")
        roots = {f["path_relative"].split("/")[0] for f in result["data"]["files"]}
        assert {"workspace", "test_environment", "source_files"} <= roots

    def test_subdirectory_is_relative_to_its_base(self, provider):
        result = project_tools.map_files("workspace/agents")
        files = result["data"]["files"]
        assert files
        assert all(f["path_relative"].startswith("workspace/agents/") for f in files)

    def test_ignored_directories_are_filtered(self, provider):
        result = project_tools.map_files("")
        leaked = [
            f["path_relative"] for f in result["data"]["files"]
            if any(part in project_tools.DEFAULT_IGNORE_DIRS
                   for part in f["path_relative"].split("/"))
        ]
        assert not leaked, f"ignored directories leaked into the map: {leaked[:5]}"

    def test_paths_are_absolute_and_reusable(self, provider):
        result = project_tools.map_files("workspace/agents")
        entry = next(f for f in result["data"]["files"] if f["type"] == "file")
        assert Path(entry["path"]).is_absolute()
        # The reported relative path is one read_file accepts unchanged.
        assert provider.relpath(entry["path"]) == entry["path_relative"]
        assert provider.read(entry["path_relative"])

    def test_outside_root_is_reported_as_an_error(self, provider):
        result = project_tools.map_files(
            str(REPO_ROOT / "scripts")
        )
        assert result["success"] is False
        assert result["error"]


# ============================================================
# read_file
# ============================================================

class TestReadFile:

    def test_reads_from_a_non_workspace_root(self, provider):
        result = project_tools.read_file(
            "source_files/headless_app_MASTER_COPY.md"
        )
        assert result["success"], result.get("error")
        assert result["data"]["extracted_content"]
        assert result["data"]["path"].endswith("headless_app_MASTER_COPY.md")

    def test_legacy_path_reads_from_the_workspace(self, provider):
        result = project_tools.read_file(
            "agents/ProjectManager/agent.md"
        )
        assert result["success"], result.get("error")
        assert result["data"]["path_relative"] == (
            "workspace/agents/ProjectManager/agent.md"
        )

    def test_reads_a_text_type_the_editor_also_allows(self, scratch, provider):
        target = scratch("read_fixture")
        path = project_tools.write_text_file(
            "note.log", "a line\n", str(target)
        )
        assert path["success"], path.get("error")
        read = project_tools.read_file(
            path["data"]["path_relative"]
        )
        assert read["success"], read.get("error")
        assert read["data"]["extracted_content"] == "a line\n"

    def test_missing_file_reports_not_found(self, provider):
        result = project_tools.read_file(
            "workspace/definitely/not/here.md"
        )
        assert result["success"] is False
        assert result["error"]


# ============================================================
# write_text_file
# ============================================================

class TestWriteTextFile:

    def test_writes_into_a_non_workspace_root(self, scratch, provider):
        target = scratch("write_fixture")
        result = project_tools.write_text_file(
            "out.md", "hello\n", str(target)
        )
        assert result["success"], result.get("error")
        assert result["data"]["path_relative"] == (
            "test_environment/write_fixture/out.md"
        )
        assert Path(result["data"]["path"]).is_file()

    def test_reports_real_size(self, scratch, provider):
        target = scratch("size_fixture")
        result = project_tools.write_text_file(
            "sized.txt", "0123456789", str(target)
        )
        assert result["success"], result.get("error")
        assert result["data"]["size"] == 10

    def test_root_level_write_reports_a_qualified_path(self, provider):
        result = project_tools.write_text_file(
            "root_probe.txt", "x", "."
        )
        assert result["success"], result.get("error")
        assert result["data"]["path_relative"] == "workspace/root_probe.txt"
        try:
            provider.delete(result["data"]["path_relative"])
        except Exception:
            pass

    @pytest.mark.parametrize(
        "name", ["a.log", "b.markdown", "c.rst", "d.tsv", "e.scss", "f.tex"]
    )
    def test_text_types_the_two_layers_disagreed_on(self, scratch, provider, name):
        target = scratch("ext_fixture")
        result = project_tools.write_text_file(
            name, "content\n", str(target)
        )
        assert result["success"], result.get("error")

    def test_read_only_root_refuses_a_write(self, provider):
        result = project_tools.write_text_file(
            "should_not_exist.md", "x", "source_files"
        )
        assert result["success"] is False
        assert "read-only" in result["error"]

    def test_overwrite_is_respected(self, scratch, provider):
        target = scratch("overwrite_fixture")
        project_tools.write_text_file(
            "o.txt", "first", str(target)
        )
        blocked = project_tools.write_text_file(
            "o.txt", "second", str(target)
        )
        assert blocked["success"] is False
        allowed = project_tools.write_text_file(
            "o.txt", "second", str(target), overwrite=True
        )
        assert allowed["success"], allowed.get("error")


# ============================================================
# TOOL-STAGE REPORTING
# ============================================================

class TestToolStageReporting:
    """Each tool reports its own verdict, tagged stage="tool", independent of
    the agent's dispatch event. The agent context is what makes the event
    filterable per agent."""

    def test_success_is_logged_with_agent_context(self):
        with project_tools.reporting_agent("agent-x", "Agent X", "llama3.1:8b"):
            project_tools.get_current_date()

        events = read_tool_events()
        assert len(events) == 1
        event = events[0]
        assert event["stage"] == "tool"
        assert event["tool"] == "get_current_date"
        assert event["ok"] is True
        assert event["agent_id"] == "agent-x"
        assert event["agentName"] == "Agent X"
        assert event["model"] == "llama3.1:8b"

    def test_failed_operation_is_logged_not_ok(self):
        project_tools.read_file("does/not/exist.txt")

        events = [e for e in read_tool_events() if e.get("stage") == "tool"]
        assert events
        event = events[-1]
        assert event["tool"] == "read_file"
        assert event["ok"] is False
        assert event["error"]


# ============================================================
# TOOL LOG
# ============================================================

class TestToolLog:

    @pytest.fixture
    def data_dir(self, tmp_path):
        with use_data_dir(tmp_path / "data"):
            yield tmp_path / "data"

    def _event(self, **overrides):
        event = {
            "time": "10:00:00",
            "tool": "read_file",
            "args": {"path": "workspace/a.md"},
            "status": "success",
            "op_ok": True,
            "origin": "TEXT reply",
        }
        event.update(overrides)
        return event

    def test_round_trips_through_the_log(self, data_dir):
        from tools.chatlog import append_tool_event

        assert append_tool_event(self._event())
        events = read_tool_events()
        assert len(events) == 1
        assert events[0]["tool"] == "read_file"

    def test_reads_the_newest_events_in_order(self, data_dir):
        from tools.chatlog import append_tool_event

        for index in range(5):
            append_tool_event(self._event(args={"path": f"workspace/{index}.md"}))
        events = read_tool_events(limit=3)
        assert [e["args"]["path"] for e in events] == [
            "workspace/2.md", "workspace/3.md", "workspace/4.md",
        ]

    def test_filters_by_tool(self, data_dir):
        from tools.chatlog import append_tool_event

        append_tool_event(self._event())
        append_tool_event(self._event(tool="map_files"))
        assert [e["tool"] for e in read_tool_events(tool="map_files")] == ["map_files"]

    def test_filters_by_agent(self, data_dir):
        from tools.chatlog import append_tool_event

        append_tool_event(self._event(agent_id="a", agentId="a"))
        append_tool_event(self._event(agent_id="b", agentId="b"))
        assert [e["agent_id"] for e in read_tool_events(agent="b")] == ["b"]

    def test_write_content_is_not_logged_verbatim(self, data_dir):
        from tools.chatlog import append_tool_event

        append_tool_event(self._event(
            tool="write_text_file",
            args={"name": "x.md", "content": "s" * 4096, "output_path": "."},
        ))
        logged = read_tool_events()[0]
        assert logged["args"]["content"] != "s" * 4096
        assert logged["args"]["content_chars"] == 4096

    def test_clear_removes_events(self, data_dir):
        from tools.chatlog import append_tool_event

        append_tool_event(self._event(agent_id="a", agentId="a"))
        append_tool_event(self._event(agent_id="b", agentId="b"))
        assert clear_tool_events("a") == 1
        assert len(read_tool_events()) == 1

    def test_agent_logs_valid_json(self, data_dir):
        """The event an agent writes must parse as JSON, and must carry the
        result as data rather than as a Python repr."""
        from engine.core.agent import _as_payload, _as_text

        raw = {"success": True, "data": {"size": 3}, "error": None}
        assert json.loads(_as_text(raw)) == raw
        assert _as_payload(raw) == raw

    def test_appending_reports_failure_instead_of_raising(self, data_dir):
        from tools.chatlog import append_tool_event

        # A directory where the log file should be: the write cannot succeed.
        blocked = data_dir / "toollog" / "tool_usage.jsonl"
        blocked.parent.mkdir(parents=True, exist_ok=True)
        blocked.mkdir()
        try:
            assert append_tool_event(self._event()) is False
        finally:
            blocked.rmdir()


# ============================================================
# EXTENSION AGREEMENT
# ============================================================

class TestExtensionAgreement:

    def test_the_two_layers_agree_on_plain_text(self):
        """The tools layer routed .log to a text read while the Project
        Manager refused it as uneditable, so the same file read or failed
        depending on which backend answered."""
        from parameters import filesystem

        unsupported = {
            ext for ext in project_tools._PLAIN_TEXT_EXTENSIONS
            if ext not in filesystem.TEXT_EXTENSIONS
        }
        assert not unsupported, f"Project Manager still refuses: {sorted(unsupported)}"

    def test_filesystem_agrees_a_log_file_is_text(self):
        from parameters import filesystem

        assert filesystem.is_text_file(Path("x.log"))
        assert filesystem.is_text_file(Path("x.markdown"))