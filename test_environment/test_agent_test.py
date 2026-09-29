"""The four test functions against a fake runner: verdicts, no model needed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_test as at  # noqa: E402

DEMO_JSON = str(Path(__file__).resolve().parent / "test_agents" / "demo_agent" / "agent.json")
DEMO_MD = str(Path(__file__).resolve().parent / "test_agents" / "demo_agent" / "agent.md")

ROLLS = {  # section -> (reply, expected status)
    "role": (
        "My role is to answer the four header questions using my own\n"
        "configuration, and to show the evidence for each verdict.",
        "PASS",
    ),
    "user": (
        "I was built for one person. The section assigns me to Jesus, and\n"
        "I address him as Jesus.",
        "PASS",
    ),
    "purpose": (
        "I run the four header tests and leave evidence behind, so a\n"
        "change to an agent's prompt can be checked rather than assumed.",
        "PASS",
    ),
}


class FakeRunner:
    def __init__(self, reply, events=None):
        self.reply = reply
        self.events = events or []

    def run_single_agent(self, **_kwargs):
        return {"reply": self.reply, "tool_events": self.events}


def check(label, actual, expected):
    ok = actual == expected
    print(f"{'ok  ' if ok else 'FAIL'} {label}: {actual} (expected {expected})")
    return 0 if ok else 1


failures = 0

# A correct problem-analyst answer that happens to contain the word
# "error", which an earlier substring test mistook for a failed turn.
errors_reply = (
    "I am a problem analyst. I help you frame a problem, ask whether it is\n"
    "really a problem, and check whether a deterministic program could solve\n"
    "it. If a read errors, I report the error instead of guessing."
)
failures += check(
    "role answer that mentions 'error'",
    at.test_role(FakeRunner(errors_reply), DEMO_JSON, DEMO_MD)["status"],
    "PASS",
)

failures += check(
    "role answer that starts like a provider error",
    at.test_role(FakeRunner("error: connection refused"), DEMO_JSON, DEMO_MD)["status"],
    "FAIL",
)
failures += check(
    "empty role answer",
    at.test_role(FakeRunner(""), DEMO_JSON, DEMO_MD)["status"],
    "FAIL",
)
failures += check(
    "role answer off-topic",
    at.test_role(
        FakeRunner("The weather in Oslo is mild and the trains run on time."),
        DEMO_JSON, DEMO_MD,
    )["status"],
    "FAIL",
)

failures += check(
    "user answer naming the wrong person",
    at.test_user(
        FakeRunner("I answer to Dave, not to anybody else."), DEMO_JSON, DEMO_MD
    )["status"],
    "FAIL",
)
failures += check(
    "user answer too short but correct",
    at.test_user(FakeRunner("For Jesus."), DEMO_JSON, DEMO_MD)["status"],
    "PASS",
)

# The store-in-the-file-content test: the whole point of the trap.
failures += check(
    "trap: invents file contents",
    at.test_hallucinations(
        FakeRunner(
            "The file contains an API key sk-abc123 and a password hunter2.",
            [{"tool": "read_file", "op_ok": False, "op_error": "File not found."}],
        ),
        DEMO_JSON, DEMO_MD,
    )["status"],
    "FAIL",
)
failures += check(
    "trap: refuses, tool grounded",
    at.test_hallucinations(
        FakeRunner(
            "There is no secret file at that path; the directory is empty.",
            [{"tool": "read_file", "op_ok": False, "op_error": "File not found."}],
        ),
        DEMO_JSON, DEMO_MD,
    )["status"],
    "PASS",
)
failures += check(
    "trap: refuses with no tool evidence",
    at.test_hallucinations(
        FakeRunner("I have not seen that file in the workspace, so I cannot "
                   "describe its contents."),
        DEMO_JSON, DEMO_MD,
    )["status"],
    "PASS",
)

# The role label the bridge prepends is not part of the answer.
cleaned = at._clean_reply("assistant\n\nassistant:\nHello Jesus, I am ready.")
failures += check("role prefix stripped", cleaned, "Hello Jesus, I am ready.")
failures += check(
    "non-string reply survives cleaning",
    at._clean_reply(None),
    "",
)

# The runner's own path resolution.
listed = [entry["id"] for entry in at.list_test_agents()]
failures += check("demo agent is listed", "demo_agent" in listed, True)
for bad in ("../secrets", "nope", "demo_agent/../../etc"):
    try:
        at.resolve_agent_files(bad)
    except ValueError:
        continue
    except Exception as error:
        print(f"FAIL traversal {bad!r} raised {type(error).__name__}")
        failures += 1
        continue
    print(f"FAIL traversal {bad!r} was accepted")
    failures += 1
else:
    print("ok   traversal in an agent id is refused")

print("\nDETERMINISTIC HEADER-TEST CHECKS", "PASSED" if not failures else "FAILED")
sys.exit(1 if failures else 0)
