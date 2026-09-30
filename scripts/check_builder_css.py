"""
scripts/check_builder_css.py
============================

Guard rails for the extracted Prompt Builder styles and markup.

The builder is embedded in two pages, so its CSS has to be scoped and its
ids have to be unique across every host. Both are easy to break with a
one-line edit and impossible to notice by eye - an unscoped `button` rule
does not look wrong in builder.css, it only shows up as a restyled
control on a page nobody was editing.

Run it directly, or let the test suite pick it up:

    .venv\\Scripts\\python.exe scripts\\check_builder_css.py

Exits non-zero and prints what it found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STATIC = ROOT / "project_manager" / "interface" / "static"

BUILDER_CSS = STATIC / "builder.css"

BUILDER_JS = STATIC / "js" / "builder.js"

#: Every page that hosts the builder. A new host has to be added here or
#: the id check silently stops covering it.
HOSTS = {
    "test.html": STATIC / "test.html",
    "Agentpromptbuilder.html": STATIC / "Agentpromptbuilder.html",
}

#: Selectors that cannot be scoped and are deleted instead. Present only
#: to give the failure a reason rather than just a line number.
UNSCOPABLE = {"body", "html"}


def css_rules(text: str) -> list[tuple[int, str]]:
    """Every selector in the stylesheet, with its line number.

    Comments and at-rule preludes are skipped; an @media block is walked
    into rather than reported as one selector, because the rules inside
    it need checking just as much.
    """

    rules: list[tuple[int, str]] = []
    depth = 0
    buffer = ""

    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()

        if stripped.startswith("/*") or stripped.startswith("*"):
            continue

        # A comment that opens and closes on the same line.
        line = re.sub(r"/\*.*?\*/", "", line).strip()
        if not line:
            continue

        if stripped.startswith("@"):
            depth += line.count("{")
            buffer = ""
            continue

        if "{" in line:
            selector = line.split("{", 1)[0].strip()
            if selector:
                rules.append((number, selector))
            depth += line.count("{")
            buffer = ""

        if "}" in line:
            depth -= line.count("}")
            buffer = ""

    del depth, buffer
    return rules


def check_css() -> list[str]:
    text = BUILDER_CSS.read_text(encoding="utf-8")
    problems: list[str] = []

    for number, selector in css_rules(text):
        for part in selector.split(","):
            part = part.strip()
            if not part:
                continue

            head = part.split(" ")[0].split(">")[0].split(":")[0]
            root = head.lstrip("*.")

            if root in UNSCOPABLE:
                problems.append(
                    f"builder.css:{number}: {part!r} targets {root!r}, "
                    f"which cannot be scoped to the panel. Delete the rule - "
                    f"the host page owns it."
                )
            elif not head.startswith(".pb"):
                problems.append(
                    f"builder.css:{number}: {part!r} is not scoped under "
                    f".pb, so it becomes a global rule on every host page."
                )

    return problems


def markup_ids(text: str) -> set[str]:
    """Ids in a chunk of HTML or in a JS template literal."""

    return set(re.findall(r'id="([^"]+)"', text))


def builder_ids() -> set[str]:
    text = BUILDER_JS.read_text(encoding="utf-8")
    match = re.search(r"const MARKUP = `(.*?)`;", text, re.S)
    if not match:
        return set()
    return markup_ids(match.group(1))


def check_ids() -> list[str]:
    mine = builder_ids()
    problems: list[str] = []

    if not mine:
        return ["builder.js: no ids found in MARKUP - has it been moved?"]

    for name, path in HOSTS.items():
        if not path.is_file():
            problems.append(f"host page missing: {path}")
            continue

        theirs = markup_ids(path.read_text(encoding="utf-8"))

        for shared in sorted(mine & theirs):
            problems.append(
                f"id {shared!r} is in both js/builder.js's MARKUP and {name}. "
                f"The builder looks ids up on the document, so the page would "
                f"steal its element."
            )

    return problems


def main() -> int:
    problems = check_css() + check_ids()

    for problem in problems:
        print(f"[FAIL] {problem}")

    if problems:
        print(f"\n{len(problems)} problem(s).")
        return 1

    print(
        f"[ok] builder.css: every selector scoped under .pb\n"
        f"[ok] ids: js/builder.js's {len(builder_ids())} ids are unique "
        f"across {len(HOSTS)} host page(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())