"""
interface_runner.py
===================

Headless agent runners for the GenV1 engine.

This is the programmatic entry point of the headless runtime:

    AgentInterface.run_chat(message, agent_id)
        - one registered agent from engine/agent_library/, chat reply.

    AgentInterface.run_single_agent(json_path, md_path, user_input)
        - one ad-hoc agent built from explicit agent.json + agent.md paths.

    AgentInterface.run_pipeline(agent_configs, user_input)
        - an ordered agent chain (feed-forward). Each step receives the
          original message plus every earlier step's reply, labelled; the
          final step's reply is the pipeline result.

Every run persists the user turn + agent reply to the plain-text chat log
(data/chatlog/chat.log), so history survives and the agent's own
search_chat_logs tool can recall it. Tool events are recorded to
data/toollog/tool_usage.jsonl.

An optional Project Manager bridge makes the Project Manager server (or its
direct filesystem authority) the filesystem owner for the file tools.
"""

from __future__ import annotations

import json
from typing import Any

from engine.agents.factory import build_agent, build_agent_from_definition
from engine.agents.registry import list_agents
from engine.pipeline import run_pipeline as _run_pipeline
from tools.chatlog import append_chat


class AgentInterface:
    """Thin, stable API over the build/think loop and pipeline chain."""

    def __init__(self, bridge: Any = None, model: str | None = None) -> None:
        """Create a runner.

        Args:
            bridge: optional Project Manager provider (ProjectManagerBridge
                or DirectProjectIO). When present, the file tools route through
                the Project Manager filesystem.
            model:  optional default model override for every run.
        """
        self.bridge = bridge
        self.model = model

    # ============================================================
    # CHAT (one registered agent)
    # ============================================================

    def run_chat(
        self,
        message: str,
        agent_id: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run one registered agent and return its reply.

        agent_id defaults to the first agent found in engine/agent_library/.
        Returns {"reply", "agent_id", "model", "tool_events"}.
        """
        resolved_id = agent_id or self._default_agent_id()
        agent = build_agent(resolved_id, model=model or self.model, bridge=self.bridge)
        reply = agent.think(message)
        append_chat("user", message)
        append_chat("agent", reply)
        return {
            "reply": reply,
            "agent_id": resolved_id,
            "model": agent.model,
            "tool_events": agent.tool_events,
        }

    # ============================================================
    # SINGLE AD-HOC AGENT
    # ============================================================

    def run_single_agent(
        self,
        json_path: str,
        md_path: str,
        user_input: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run one agent built from explicit agent.json + agent.md paths.

        This is the headless construction path: the definition can live
        anywhere, not only inside engine/agent_library/.

        Returns {"reply", "agent_id", "model", "tool_events", "name",
        "description"}.
        """
        agent = build_agent_from_definition(
            json_path,
            md_path,
            model=model or self.model,
            bridge=self.bridge,
        )
        reply = agent.think(user_input)
        append_chat("user", user_input)
        append_chat("agent", reply)
        return {
            "reply": reply,
            "agent_id": agent.profile.id,
            "name": agent.profile.name,
            "description": agent.profile.description,
            "model": agent.model,
            "tool_events": agent.tool_events,
        }

    # ============================================================
    # PIPELINE
    # ============================================================

    def run_pipeline(
        self,
        agent_configs: list | None,
        user_input: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run the ordered agent chain (feed-forward).

        agent_configs:
            None  -> load steps from config/pipeline.json.
            list  -> each element is either an agent id (str) or a dict with
                     "json_path" + "md_path" (ad-hoc step agents).

        Returns:
            {"reply", "outputs": [...step outputs...], "tool_events",
             "model"}.
        """
        result = _run_pipeline(
            user_input,
            model=model or self.model,
            steps=agent_configs,
            bridge=self.bridge,
        )
        reply = result["reply"]
        append_chat("user", user_input)
        append_chat("agent", reply)
        result["model"] = model or self.model
        return result

    # ============================================================
    # UTILITIES
    # ============================================================

    def _default_agent_id(self) -> str:
        agents = list_agents()
        if not agents:
            raise RuntimeError(
                "No agents are registered in engine/agent_library/. "
                "Check that <id>/agent.json and <id>/agent.md exist."
            )
        return agents[0]["id"]

    def available_agents(self) -> list[dict]:
        return list_agents()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        bridge = getattr(self.bridge, "expose", lambda: None)()
        return (
            f"<AgentInterface model={self.model!r} "
            f"bridge={json.dumps(bridge or {}, default=str) or 'local disk'}>"
        )


__all__ = ["AgentInterface"]