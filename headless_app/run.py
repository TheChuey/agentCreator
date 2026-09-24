"""
run.py
======

Command-line entry point for the headless GenV1 engine.

Examples:
    python run.py list-agents
    python run.py refresh-models

    python run.py run-agent rag_assistant --message "what date is it today?"

    python run.py run-agent enginner --base-url http://127.0.0.1:8011 \
        --message "read config/agents.json"

    python run.py run-pipeline --message "idea: add a settings screen" \
        --steps rag_assistant execute_engineer_agent module_builder_agent

Options:
    --base-url    Project Manager URL (default: $PROJECT_MANAGER_BASE_URL or
                  http://127.0.0.1:8000).
    --no-bridge   do not connect to the Project Manager; file tools fall back
                  to the local disk.
    -m/--model    model override (default: per-agent agent.json model).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from interface_runner import AgentInterface
from engine.core.llm import refresh_models
from engine.agents.registry import list_agents


def _build_bridge(args) -> object | None:
    if args.no_bridge:
        print("[run] --no-bridge: file tools use the local disk.")
        return None
    try:
        from bridge.client import ProjectManagerBridge

        bridge = ProjectManagerBridge(base_url=args.base_url)
        health = bridge.health()
        root = (health or {}).get("root", "?")
        print(f"[run] connected to Project Manager at {args.base_url} (root={root})")
        return bridge
    except Exception as exc:
        print(
            f"[run] WARNING: could not connect to Project Manager at "
            f"{args.base_url} ({exc}). Continuing WITHOUT a bridge "
            "(local disk tools)."
        )
        return None


def _read_message(args) -> str:
    if args.message:
        return args.message
    try:
        return input("> ")
    except EOFError:
        return ""


def cmd_list_agents(args) -> int:
    agents = list_agents()
    if not agents:
        print("No agents found in engine/agent_library/.")
        return 1
    for agent in agents:
        tools = "chat" if agent["mode"] == "chat" else agent["model"] or "default model"
        print(
            f"- {agent['id']}  [{agent['name']}]  "
            f"({tools}) - {agent['description']}"
        )
    return 0


def cmd_refresh_models(args) -> int:
    models = refresh_models()
    print(
        f"Installed Ollama models ({len(models)}): "
        + ", ".join(m["id"] for m in models)
    )
    print("Wrote config/models.json")
    return 0


def _print_run(result: dict, args) -> None:
    print("\n" + "=" * 60)
    print("REPLY")
    print("=" * 60)
    print(result.get("reply", ""))
    tool_events = result.get("tool_events") or []
    if tool_events:
        print("\nTOOL EVENTS")
        for event in tool_events:
            print(
                f"- {event.get('time', '')} {event.get('tool')} "
                f"{json.dumps(event.get('args', {}) or {}, default=str)[:160]} "
                f"-> {event.get('status')}"
            )
    if args.json:
        print("\nJSON")
        print(json.dumps(result, indent=2, default=str))


def cmd_run_agent(args) -> int:
    bridge = _build_bridge(args)
    runner = AgentInterface(bridge=bridge, model=args.model)
    message = _read_message(args)
    if not message:
        print("No message provided. Use --message or pipe stdin.")
        return 2
    result = runner.run_chat(message, agent_id=args.agent_id, model=args.model)
    _print_run(result, args)
    return 0


def cmd_run_pipeline(args) -> int:
    bridge = _build_bridge(args)
    runner = AgentInterface(bridge=bridge, model=args.model)
    message = _read_message(args)
    if not message:
        print("No message provided. Use --message or pipe stdin.")
        return 2
    steps = args.steps or None
    result = runner.run_pipeline(steps, message, model=args.model)
    _print_run(result, args)
    if result.get("outputs"):
        print("\nPIPELINE STEPS")
        for step in result["outputs"]:
            print(f"- {step['agent_id']}: {step['output'][:100]!r}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Headless GenV1 agent engine runner.",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Project Manager base URL (default: PROJECT_MANAGER_BASE_URL env "
             "or http://127.0.0.1:8000).",
    )
    parser.add_argument(
        "--no-bridge",
        action="store_true",
        help="Do not connect to a Project Manager; file tools use local disk.",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Model override for all agents.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full JSON result as well.",
    )
    parser.add_argument(
        "--message",
        default=None,
        help="Message to send (read interactively when omitted).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-agents", help="List registered agents.")
    p_list.set_defaults(func=cmd_list_agents)

    p_refresh = sub.add_parser("refresh-models", help="Scan Ollama models.")
    p_refresh.set_defaults(func=cmd_refresh_models)

    p_run = sub.add_parser("run-agent", help="Run one registered agent.")
    p_run.add_argument("agent_id", nargs="?", default=None,
                       help="Agent id (default: first registered).")
    p_run.set_defaults(func=cmd_run_agent)

    p_pipe = sub.add_parser("run-pipeline", help="Run the agent chain.")
    p_pipe.add_argument("steps", nargs="*",
                        help="Step agent ids (default: config/pipeline.json).")
    p_pipe.set_defaults(func=cmd_run_pipeline)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())