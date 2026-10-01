import pytest
from test_environment.agent_test import parse_markdown, create_test_prompt, evaluate_response, run_preflight_parser_check


def test_parser_with_custom_headers(tmp_path):
    """Verifies that headers with spaces and multi-word titles parse correctly."""
    md_content = (
        "## role\nPlanner\n\n"
        "## user vicky\nVicky is a team member who prefers concise direct answers.\n"
    )
    test_file = tmp_path / "test_agent.md"
    test_file.write_text(md_content)

    sections = parse_markdown(str(test_file))
    parsed_map = {s["title"]: s["description"] for s in sections}

    assert "role" in parsed_map
    assert parsed_map["role"] == "Planner"
    assert "user vicky" in parsed_map
    assert "concise direct answers" in parsed_map["user vicky"]


def test_create_test_prompt_formatting():
    """Verifies dynamic prompt string construction."""
    title = "user vicky"
    description = "Prefers email communication."
    prompt = create_test_prompt(title, description)

    assert "user vicky" in prompt
    assert "Prefers email communication." in prompt
    assert "In your own words" in prompt


def test_evaluate_response_pass_and_fail():
    """Verifies lexical evaluation logic for matching responses vs off-topic responses."""
    desc = "Vicky is a team member who prefers concise, direct answers and communicates primarily via email."

    # Matching response -> PASS
    good_resp = "I will communicate with Vicky using direct and concise answers via email."
    passed, reason = evaluate_response(good_resp, desc)
    assert passed is True
    assert "Matched" in reason

    # Unrelated response -> FAIL
    bad_resp = "I help manage databases and cloud backend infrastructure."
    passed, reason = evaluate_response(bad_resp, desc)
    assert passed is False
    assert "Only matched" in reason


def test_preflight_check_passes():
    """Ensures parser pre-flight check executes cleanly."""
    assert run_preflight_parser_check() is True