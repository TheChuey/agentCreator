"""
interface_runner.py
===================

The single execution seam of the GenV1 engine.

Every caller - the headless CLI (run.py) and the Project Manager routers -
goes through this module, so build/think/log behaviour cannot drift
between frontends.

    AgentInterface.run_chat(message, agent_id, history=...)
        - one agent resolved by id from any registered root, chat reply.

    AgentInterface.run_single_agent(json_path, md_path, user_input)
        - one ad-hoc agent built from explicit agent.json + agent.md paths.
          When json_path/md_path are omitted the agent is resolved by id.

    AgentInterface.run_pipeline(agent_configs, user_input)
        - an ordered agent chain (feed-forward). Each step receives the
          original message plus every earlier step's reply, labelled; the
          final step's reply is the pipeline result.

    AgentInterface.list_agents() / .get_agent(id)
        - discovery over every registered root.

Every run persists the user turn + agent reply to the plain-text chat log
(data/chatlog/chat.log) *tagged with the agent id*, so per-agent history
survives, is replayed into the next turn, and the agent's own
search_chat_logs tool can recall it. Tool events are recorded to
data/toollog/tool_usage.jsonl.

An optional Project Manager bridge makes the Project Manager server (or its
direct filesystem authority) the filesystem owner for the file tools. The
bridge is bound per agent, so concurrent agents never share file-tool
state.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from engine.agents.factory import (
    build_agent,
    build_agent_from_definition,
    replay_history,
)
from engine.agents.registry import get_agent_meta, list_agents
from engine.pipeline import run_pipeline as _run_pipeline
from tools.chatlog import append_chat, read_history

#: Turns of prior conversation handed to the model, per agent.
DEFAULT_HISTORY_LIMIT = 20


def _as_history(
    agent_id: str | None,
    limit: int | None = DEFAULT_HISTORY_LIMIT,
) -> list[dict] | None:
    """Read one agent's recent turns from the chat log as model messages.

    Scoped by agent id so agents never see each other's conversations.
    Returns None (meaning "no history") when logging is unavailable or
    limit is falsy, so a broken log never blocks a conversation.
    """
    if not limit or limit <= 0:
        return None
    try:
        entries = read_history(limit=limit, agent=agent_id)
    except Exception as exc:  # pragma: no cover - logging must not break runs
        print(f"[INTERFACE] history unavailable: {exc}")
        return None

    history: list[dict] = []
    for entry in entries:
        sender = str(entry.get("sender", ""))
        content = str(entry.get("message", "") or "")
        if not content:
            continue
        history.append({
            "role": "assistant" if sender in ("agent", "ai") else "user",
            "content": content,
        })
    return history or None


class AgentInterface:
    """Thin, stable API over the build/think loop and pipeline chain."""

    def __init__(
        self,
        bridge: Any = None,
        model: str | None = None,
        log_sink: Callable[[dict], None] | None = None,
    ) -> None:
        """Create a runner.

        Args:
            bridge:   optional Project Manager provider (ProjectManagerBridge
                      or DirectProjectIO). When present, the file tools route
                      through the Project Manager filesystem.
            model:    optional default model override for every run.
            log_sink: optional callback receiving every chat log entry as it
                      is written, so a host can mirror the log elsewhere.
        """
        self.bridge = bridge
        self.model = model
        self.log_sink = log_sink

    # ============================================================
    # INTERNAL
    # ============================================================

    def _log(self, sender: str, message: str, agent_id: str) -> dict:
        """Write one chat log entry and hand it to the sink."""
        entry = append_chat(sender, message, agent=agent_id)
        if self.log_sink is not None:
            try:
                self.log_sink(entry)
            except Exception as exc:  # pragma: no cover - sink must not break runs
                print(f"[INTERFACE] log sink failed: {exc}")
        return entry

    def _think(
        self,
        agent: Any,
        message: str,
        agent_id: str,
        history: list[dict] | None,
    ) -> tuple[str, list[dict]]:
        """Replay history, run one turn, and log both sides.

        One place for the build-think-log order, so chat, single-agent
        and pipeline runs behave identically. The current turn is not in
        ``history``; the caller reads the log *before* it is written.
        """
        if history:
            replay_history(agent, history)
        reply = agent.think(message)
        entries = [
            self._log("user", message, agent_id),
            self._log("agent", reply, agent_id),
        ]
        return reply, entries

    # ============================================================
    # CHAT (one agent, resolved by id)
    # ============================================================

    def run_chat(
        self,
        message: str,
        agent_id: str | None = None,
        model: str | None = None,
        history: list[dict] | None = None,
        use_logged_history: bool = True,
    ) -> dict[str, Any]:
        """Run one agent and return its reply.

        agent_id is resolved through the agent roots, so an agent created
        in the Project Manager works exactly like a bundled library agent.
        With no agent_id the first discovered agent is used.

        Args:
            history: explicit prior turns ({role, content}). When None and
                ``use_logged_history`` is set, this agent's own log history
                is replayed (the current turn is logged after the model has
                answered).
        Returns {"reply", "agent_id", "name", "model", "tool_events",
        "entries"}.
        """
        resolved_id = agent_id or self._default_agent_id()
        agent = build_agent(resolved_id, model=model or self.model, bridge=self.bridge)

        if history is None and use_logged_history:
            history = _as_history(resolved_id, DEFAULT_HISTORY_LIMIT)

        reply, entries = self._think(agent, message, resolved_id, history)

        return {
            "reply": reply,
            "agent_id": resolved_id,
            "name": agent.profile.name,
            "model": agent.model,
            "tool_events": agent.tool_events,
            "entries": entries,
        }

    # ============================================================
    # SINGLE AGENT (explicit definition, or by id)
    # ============================================================

    def run_single_agent(
        self,
        user_input: str,
        json_path: str | None = None,
        md_path: str | None = None,
        agent_id: str | None = None,
        model: str | None = None,
        history: list[dict] | None = None,
        use_logged_history: bool = False,
    ) -> dict[str, Any]:
        """Run one agent built from explicit agent.json + agent.md paths.

        This is the headless construction path: the definition can live
        anywhere, not only inside a registered root. When json_path/md_path
        are omitted the agent is resolved by ``agent_id`` instead.

        Returns {"reply", "agent_id", "model", "tool_events", "name",
        "description", "entries"}.
        """
        if json_path and md_path:
            agent = build_agent_from_definition(
                json_path,
                md_path,
                model=model or self.model,
                bridge=self.bridge,
            )
            # A definition loaded from an explicit path may be outside any
            # registered root; use its own id so history stays per-agent.
            resolved_id = str(agent.profile.id)
        elif agent_id:
            resolved_id = agent_id
            agent = build_agent(
                agent_id,
                model=model or self.model,
                bridge=self.bridge,
            )
        else:
            raise ValueError(
                "Provide json_path + md_path, or an agent_id, to run."
            )

        if history is None and use_logged_history:
            history = _as_history(resolved_id, DEFAULT_HISTORY_LIMIT)

        reply, entries = self._think(agent, user_input, resolved_id, history)

        return {
            "reply": reply,
            "agent_id": resolved_id,
            "name": agent.profile.name,
            "description": agent.profile.description,
            "model": agent.model,
            "tool_events": agent.tool_events,
            "entries": entries,
        }

    # ============================================================
    # PIPELINE
    # ============================================================

    def run_pipeline(
        self,
        user_input: str,
        agent_configs: list | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run the ordered agent chain (feed-forward).

        Args:
            agent_configs:
                None  -> load steps from config/pipeline.json.
                list  -> each element is either an agent id (str) or a dict with
                         "json_path" + "md_path" (ad-hoc step agents).

        Returns:
            {"reply", "outputs": [...step outputs...], "tool_events",
             "model", "entries"}.
        """
        result = _run_pipeline(
            user_input,
            model=model or self.model,
            steps=agent_configs,
            bridge=self.bridge,
        )
        # A cascade is not one agent, so the exchange is logged untagged
        # rather than attributed to whichever step happened to run first.
        result["entries"] = [
            self._log("user", user_input, None),
            self._log("agent", result["reply"], None),
        ]
        result["model"] = model or self.model
        return result

    # ============================================================
    # UTILITIES
    # ============================================================

    def _default_agent_id(self) -> str:
        agents = self.list_agents()
        if not agents:
            raise RuntimeError(
                "No agents are registered. Register an agent root "
                "(engine/agents/roots.py) and check that <id>/agent.json "
                "exists in it."
            )
        return agents[0]["id"]

    def list_agents(self) -> list[dict]:
        """Every agent across every registered root (see registry)."""
        return list_agents()

    def get_agent(self, agent_id: str) -> dict | None:
        """Metadata for one agent id, or None when it is not registered."""
        return get_agent_meta(agent_id)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        bridge = getattr(self.bridge, "expose", lambda: None)()
        return (
            f"<AgentInterface model={self.model!r} "
            f"bridge={json.dumps(bridge or {}, default=str) or 'local disk'}>"
        )


__all__ = ["AgentInterface", "DEFAULT_HISTORY_LIMIT"]