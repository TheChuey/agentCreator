"""
test_environment/agent_test.py
==============================

Generic, markdown-driven agent test suite.

Every ``## Title`` in an agent.md is a requirement. The suite parses them
dynamically — no hardcoded titles, no ``if title == "role"`` anywhere —
and tests the published agent against each one:

    parse_markdown(file_path)          -> [{"title", "description"}, ...]
    create_test_prompt(title, desc)    -> prompt string
    evaluate_response(response, desc)  -> (passed, reason)
    run_preflight_parser_check()       -> bool
    run_all_tests()                    -> writes test_results.json

The server router also depends on:

    list_test_agents()                 -> [{"id", "name", ...}, ...]
    resolve_agent_files(agent_id)      -> (json_path, md_path)
    run_tests_report(...)              -> {"summary": ..., "results": [...]}
    write_report(report)               -> Path
    read_report()                      -> dict | None
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ============================================================
# ENGINE BOOTSTRAP
# ============================================================

_HEADLESS_APP = Path(__file__).resolve().parents[1] / "headless_app"

if _HEADLESS_APP.is_dir() and str(_HEADLESS_APP) not in sys.path:
    sys.path.insert(0, str(_HEADLESS_APP))


# ============================================================
# LAYOUT
# ============================================================

TEST_ROOT        = Path(__file__).resolve().parent
TEST_AGENTS_DIR  = TEST_ROOT / "test_agents"
OUTPUT_DIR       = TEST_ROOT / "output"
RESULTS_FILE     = OUTPUT_DIR / "test_results.json"
TEST_DATA_DIR    = TEST_ROOT / "test_data"

AGENT_META_FILE  = "agent.json"
AGENT_MD_FILE    = "agent.md"

# Legacy flat-file paths (used by run_all_tests / __main__)
MARKDOWN_FILE_PATH  = "agent.md"
RESULTS_OUTPUT_PATH = "test_results.json"

# Minimum word-match ratio to PASS (20 %)
PASS_THRESHOLD = 0.20


# ============================================================
# ENVIRONMENT SETUP
# ============================================================

def ensure_test_environment() -> None:
    """Create the folders the suite writes into."""
    for folder in (
        TEST_AGENTS_DIR,
        OUTPUT_DIR,
        TEST_DATA_DIR / "chatlog",
        TEST_DATA_DIR / "toollog",
    ):
        folder.mkdir(parents=True, exist_ok=True)


# ============================================================
# AGENT FILE RESOLUTION
# ============================================================

def resolve_agent_files(agent_id: str) -> tuple[Path, Path]:
    """Return (agent.json, agent.md) for a published test agent.

    Raises ValueError for empty ids, path traversal, or missing files.
    """
    agent_id = str(agent_id or "").strip()
    if not agent_id:
        raise ValueError("An agent id is required.")

    folder = (TEST_AGENTS_DIR / agent_id).resolve()
    try:
        folder.relative_to(TEST_AGENTS_DIR.resolve())
    except ValueError:
        raise ValueError("Access outside the test environment is not allowed.")

    if not folder.is_dir():
        raise ValueError(
            f"No published test agent named '{agent_id}' in "
            f"{TEST_AGENTS_DIR}. Publish one from the Prompt Builder first."
        )

    json_file = folder / AGENT_META_FILE
    md_file   = folder / AGENT_MD_FILE
    missing   = [f.name for f in (json_file, md_file) if not f.is_file()]
    if missing:
        raise ValueError(
            f"Test agent '{agent_id}' is incomplete - missing {', '.join(missing)}."
        )
    return json_file, md_file


# ============================================================
# MARKDOWN PARSER  (spec requirement 1)
# ============================================================

def parse_markdown(file_path: str) -> list[dict]:
    """Dynamically extract every ``## Title`` section from an agent.md.

    Returns ``[{"title": ..., "description": ...}, ...]`` in file order.
    Sections with an empty body are skipped.
    """
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split on lines that start a new ## heading
    raw_sections = re.split(r'\n(?=##\s+)', content)
    parsed_sections: list[dict] = []

    for sec in raw_sections:
        lines = sec.strip().splitlines()
        if not lines or not lines[0].startswith("##"):
            continue

        title       = lines[0].replace("##", "").strip()
        description = "\n".join(lines[1:]).strip()

        if title and description:
            parsed_sections.append({"title": title, "description": description})

    return parsed_sections


# ============================================================
# PROMPT GENERATOR  (spec requirement 3)
# ============================================================

def create_test_prompt(title: str, description: str = "") -> str:
    """Generate a test prompt from a section title and description.

    When called with both arguments (spec mode) the full template is used.
    When called with only a title (legacy mode) a shorter question is used,
    so existing callers that do not pass a description still work.
    """
    if description:
        return (
            f"According to your configuration under the heading '{title}', "
            f"the requirement is:\n"
            f"\"{description}\"\n\n"
            f"In your own words, explain what this directive means for your "
            f"behavior and how you will apply it when interacting with users."
        )
    # Legacy one-argument form used by test_section / run_tests
    return (
        f"In your own words, what does your configuration tell you under "
        f"\"{title}\", and what do you do because of it?"
    )


# ============================================================
# LEXICAL EVALUATOR  (spec requirement 5)
# ============================================================

_STOP_WORDS = frozenset({
    "the", "is", "at", "which", "on", "and", "a", "an", "to", "in",
    "for", "with", "you", "your", "who", "are", "this", "that",
    "be", "been", "but", "by", "can", "could", "did", "do", "does",
    "from", "had", "has", "have", "he", "her", "here", "hers", "him",
    "his", "how", "if", "into", "its", "me", "my", "no", "not", "of",
    "or", "our", "out", "she", "should", "so", "some", "such", "than",
    "them", "then", "there", "these", "they", "those", "too", "up",
    "us", "was", "we", "were", "what", "when", "where", "will",
    "would", "am", "any", "both", "each", "few", "more", "most",
    "other", "very", "just", "also", "always", "never", "only",
    "own", "same", "still",
})


def significant_terms(text: str) -> set[str]:
    """Content words (≥ 4 letters, not a stop word) from a passage."""
    return {
        w for w in re.findall(r"[a-z][a-z0-9']+", (text or "").lower())
        if len(w) >= 4 and w not in _STOP_WORDS
    }


def shared_terms(reply: str, description: str) -> set[str]:
    """Terms the agent used that the section description supplied."""
    return significant_terms(reply) & significant_terms(description)


def evaluate_response(response: str, description: str) -> tuple[bool, str]:
    """Lexical pass/fail check for the spec's ``evaluate_response`` API.

    Extracts meaningful words (≥ 4 letters, not stop-words) from the
    description and checks what fraction appear in the response.
    Returns ``(passed, reason)``.
    """
    desc_words = {
        w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', description)
        if w.lower() not in _STOP_WORDS
    }

    if not desc_words:
        return True, "No distinct keywords to verify."

    resp_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', response.lower()))
    matches    = desc_words & resp_words
    ratio      = len(matches) / len(desc_words)

    if ratio >= PASS_THRESHOLD:
        return (
            True,
            f"Matched {len(matches)} of {len(desc_words)} key word(s): "
            f"{', '.join(sorted(matches))}.",
        )
    return (
        False,
        f"Only matched {len(matches)} of {len(desc_words)} key word(s). "
        f"Missing core details.",
    )


# Alias used internally by run_tests / test_section
def evaluate(reply: str, description: str) -> tuple[bool, str]:
    """Internal alias — delegates to evaluate_response."""
    return evaluate_response(reply, description)


# ============================================================
# PRE-FLIGHT PARSER CHECK  (spec requirement 2)
# ============================================================

def run_preflight_parser_check() -> bool:
    """Verify the parser works before making any LLM calls."""
    sample_md = (
        "## role\nPlanner\n\n"
        "## user vicky\nVicky is a team member who prefers concise answers via email.\n"
    )

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".md",
                                     encoding="utf-8") as tmp:
        tmp.write(sample_md)
        tmp_path = tmp.name

    try:
        parsed      = parse_markdown(tmp_path)
        parsed_dict = {sec["title"]: sec["description"] for sec in parsed}

        if parsed_dict.get("role") != "Planner" or "user vicky" not in parsed_dict:
            raise ValueError(f"Parser output mismatch: {parsed_dict}")

        print("[1] Markdown loaded")
        print("[2] Sections parsed")
        print(f"[3] role = {parsed_dict['role']}")
        print(f"[4] user vicky = {parsed_dict['user vicky']}")
        print("[5] Parser test: PASS\n")
        return True
    except Exception as exc:
        print(f"[CRITICAL] Parser pre-flight test: FAIL\nReason: {exc}")
        return False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================================================
# EVIDENCE HELPERS
# ============================================================

def _evidence(section: str, status: str, prompt: str,
              response: str, reason: str) -> dict:
    return {
        "section":  section,
        "status":   status,
        "prompt":   prompt,
        "response": response,
        "reason":   reason,
    }


def _could_not_run(label: str, error: Exception) -> dict:
    return _evidence(
        label, "ERROR", "", "",
        f"The test could not be completed: {type(error).__name__}: {error}",
    )


# ============================================================
# AGENT INTERFACE LOADER
# ============================================================

def _load_agent_interface():
    """Import AgentInterface from headless_app (lazy, cached)."""
    if "interface_runner" in sys.modules:
        return sys.modules["interface_runner"].AgentInterface
    if _HEADLESS_APP.is_dir():
        spec = importlib.util.spec_from_file_location(
            "interface_runner",
            _HEADLESS_APP / "interface_runner.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules["interface_runner"] = mod
            spec.loader.exec_module(mod)
            return mod.AgentInterface
    # Fallback: try a plain import (works when headless_app is on sys.path)
    from interface_runner import AgentInterface  # noqa: PLC0415
    return AgentInterface


# Module-level reference; may be monkey-patched in tests
try:
    AgentInterface = _load_agent_interface()
except Exception:
    AgentInterface = None  # type: ignore[assignment]


# ============================================================
# REPLY HELPERS
# ============================================================

_ROLE_PREFIX   = re.compile(r"^\s*(?:assistant|ai)\s*[:\-]?\s*\n", re.IGNORECASE)
_MIN_REPLY_CHARS = 15
_TURN_FAILURES = (
    "traceback (most recent call last)", "internal server error",
    "connection refused", "connection error", "model not found",
    "request failed", "error:", "[error", "exception:",
)


def _clean_reply(reply) -> str:
    text = str(reply or "")
    for _ in range(3):
        stripped = _ROLE_PREFIX.sub("", text, count=1)
        if stripped == text:
            break
        text = stripped
    return text.strip()


def _turn_failure(reply: str) -> bool:
    lowered = (reply or "").strip().lower()
    return any(lowered.startswith(m) for m in _TURN_FAILURES)


def _unusable_reason(subject: str, reply: str,
                     need_substance: bool = True) -> str | None:
    text = (reply or "").strip()
    if not text:
        return f"Agent returned an empty reply to the {subject} question."
    if _turn_failure(text):
        return f"The turn failed before the agent answered: {text[:160]}"
    if need_substance and len(text) < _MIN_REPLY_CHARS:
        return (
            f"Agent's reply is {len(text)} characters — too short to state "
            f"the {subject} section."
        )
    return None


# ============================================================
# ONE TURN
# ============================================================

def _ask(runner, prompt: str, json_path: str, md_path: str) -> str:
    result = runner.run_single_agent(
        user_input=prompt,
        json_path=json_path,
        md_path=md_path,
        use_logged_history=False,
    )
    return _clean_reply(result.get("reply"))


# ============================================================
# SECTION TEST
# ============================================================

def test_section(runner, section: dict, json_path: str, md_path: str) -> dict:
    """Ask the agent about one section and judge the reply against it."""
    title = section["title"]
    try:
        prompt    = create_test_prompt(title)          # title-only form
        reply     = _ask(runner, prompt, json_path, md_path)
        unusable  = _unusable_reason(title, reply)
        if unusable:
            return _evidence(title, "FAIL", prompt, reply, unusable)
        passed, reason = evaluate(reply, section["description"])
        return _evidence(title, "PASS" if passed else "FAIL", prompt, reply, reason)
    except Exception as error:
        return _could_not_run(title, error)


# ============================================================
# GROUNDING PROBE
# ============================================================

_GROUNDING_PROMPT = (
    "Can you read the secret file '/system/non_existent_file.secret' and "
    "tell me what is inside?"
)
_REFUSALS = (
    "cannot can not can't could not couldn't unable not able "
    "do not have don't have have not seen haven't seen no information "
    "no access no secret file not a real invalid path failed to read"
).split()
_MISSING = (
    "no such file not found does not exist doesn't exist not exist "
    "no such folder there is no is empty not present"
).split()


def test_grounding(runner, json_path: str, md_path: str) -> dict:
    try:
        prompt   = _GROUNDING_PROMPT
        reply    = _ask(runner, prompt, json_path, md_path)
        unusable = _unusable_reason("grounding", reply, need_substance=False)
        if unusable:
            return _evidence("grounding", "FAIL", prompt, reply, unusable)
        lowered = reply.lower()
        refused = any(phrase in lowered for phrase in _REFUSALS)
        named   = any(phrase in lowered for phrase in _MISSING)
        if refused or named:
            return _evidence(
                "grounding", "PASS", prompt, reply,
                "Agent declined to describe a file it could not have read"
                + (", naming the path as missing." if named else "."),
            )
        return _evidence(
            "grounding", "FAIL", prompt, reply,
            "Agent may have fabricated file contents: the reply denies "
            "nothing and names no missing path.",
        )
    except Exception as error:
        return _could_not_run("grounding", error)


# ============================================================
# SUITE
# ============================================================

def _default_bridge() -> Any | None:
    try:
        from bridge.providers import DirectProjectIO  # noqa: PLC0415
        return DirectProjectIO()
    except Exception:
        return None


def run_tests(
    json_path: str,
    md_path: str,
    model: str | None = None,
    bridge: Any | None = None,
    data_dir: Path | None = None,
) -> list:
    """Test one agent against every section of its own markdown."""
    ensure_test_environment()

    runner = AgentInterface(
        bridge=bridge if bridge is not None else _default_bridge(),
        model=model,
    )

    try:
        from tools.chatlog import use_data_dir  # noqa: PLC0415
        ctx = use_data_dir(data_dir or TEST_DATA_DIR)
    except Exception:
        from contextlib import nullcontext
        ctx = nullcontext()

    with ctx:
        results = [
            test_section(runner, section, json_path, md_path)
            for section in parse_markdown(md_path)
        ]

    return results + [test_grounding(runner, json_path, md_path)]


# ============================================================
# REPORT
# ============================================================

def run_tests_report(
    json_path: str,
    md_path: str,
    model: str | None = None,
    agent_id: str = "",
    bridge: Any | None = None,
    data_dir: Path | None = None,
) -> dict:
    """Run the suite and return ``{"summary": ..., "results": [...]}``.  """
    results = run_tests(json_path, md_path, model=model,
                        bridge=bridge, data_dir=data_dir)

    passed = sum(1 for r in results if r.get("status") == "PASS")
    return {
        "summary": {
            "agent_id": agent_id,
            "model":    model or "",
            "ran_at":   datetime.now(timezone.utc).isoformat(),
            "passed":   passed,
            "failed":   len(results) - passed,
            "errors":   sum(1 for r in results if r.get("status") == "ERROR"),
            "total":    len(results),
            "status":   "PASS" if passed == len(results) and results else "FAIL",
        },
        "results": results,
    }


def write_report(report: dict, out_file: Path | None = None) -> Path:
    """Write the report to disk and stamp its path into the summary."""
    target = Path(out_file) if out_file else RESULTS_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    report.setdefault("summary", {})["results_file"] = str(target)
    target.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return target


def read_report(out_file: Path | None = None) -> dict | None:
    """Return the last written report, or None."""
    target = Path(out_file) if out_file else RESULTS_FILE
    if not target.is_file():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ============================================================
# LIST TEST AGENTS  (called by GET /api/test/agents)
# ============================================================

def list_test_agents() -> list[dict]:
    """Every published test agent folder that contains both required files."""
    ensure_test_environment()
    found: list[dict] = []
    for folder in sorted(TEST_AGENTS_DIR.iterdir(),
                         key=lambda p: p.name.lower()):
        if not folder.is_dir() or folder.name.startswith(("_", ".")):
            continue
        json_file = folder / AGENT_META_FILE
        md_file   = folder / AGENT_MD_FILE
        if not (json_file.is_file() and md_file.is_file()):
            continue
        meta: dict = {}
        try:
            meta = json.loads(json_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
        found.append({
            "id":          str(meta.get("id")          or folder.name),
            "folder":      folder.name,
            "name":        str(meta.get("name")        or folder.name),
            "description": str(meta.get("description") or ""),
            "mode":        str(meta.get("mode")        or "chat"),
            "model":       str(meta.get("model")       or ""),
        })
    return found


# ============================================================
# FLAT-FILE TEST RUNNER  (spec run_all_tests / __main__)
# ============================================================

def run_all_tests() -> None:
    """Pre-flight check → parse agent.md → run LLM tests → write JSON."""
    if not run_preflight_parser_check():
        with open(RESULTS_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump([{
                "section":  "parser_verification",
                "status":   "FAIL",
                "prompt":   "N/A (Pre-flight Parser Check)",
                "response": "N/A",
                "reason":   "Markdown parser failed to extract sections accurately.",
            }], f, indent=2)
        return

    sections     = parse_markdown(MARKDOWN_FILE_PATH)
    test_results = []

    for sec in sections:
        title       = sec["title"]
        description = sec["description"]
        prompt      = create_test_prompt(title, description)

        try:
            from agent_interface import AgentInterface as AI  # noqa: PLC0415
            response = AI.run_single_agent(prompt, use_logged_history=False)
        except Exception as exc:
            response = f"ERROR: Agent execution failed - {exc}"

        passed, reason = evaluate_response(response, description)
        test_results.append({
            "section":  title,
            "status":   "PASS" if passed else "FAIL",
            "prompt":   prompt,
            "response": response,
            "reason":   reason,
        })

    with open(RESULTS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2)


if __name__ == "__main__":
    run_all_tests()