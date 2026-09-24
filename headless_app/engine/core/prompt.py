"""
app/core/prompt.py
==================

PromptManager: converts an agent definition (agent.json + parsed agent.md
sections) plus the agent's resolved tools into an AgentProfile with a
composed system prompt.

    agent.md + agent.json + tools
        ↓
    PromptManager.build()
        ↓
    AgentProfile (system_prompt ready)
"""

from dataclasses import field
from typing import Callable, List

from engine.core.agent import AgentProfile

# Markdown '## sections' that map to named profile fields.
# Any other section passes through verbatim into the prompt as an
# UPPERCASE-titled block, so new sections need no code changes.
KNOWN_SECTIONS = (
    "role",
    "purpose",
    "personality",
    "boundaries",
    "communication",
    "principles",
    "decision_style",
    "priorities",
)

# Sections actually composed INTO the system prompt.
# 'priorities' is documentation-only and is deliberately excluded,
# matching the original PromptManager behavior.
PROMPT_SECTIONS = tuple(name for name in KNOWN_SECTIONS if name != "priorities")


class PromptManager:
    """Builds an AgentProfile from an agent definition and composes the system prompt."""

    @staticmethod
    def build(definition: dict, tools: List[Callable] | None = None) -> AgentProfile:
        """Build an AgentProfile.

        Args:
            definition: {"meta": {...agent.json...}, "sections": {...parsed agent.md...}}
            tools:      resolved tool functions; their docstrings become the
                        AVAILABLE TOOLS section of the prompt.

        Steps:
            1. Map metadata and markdown sections onto the profile fields
            2. Collect unknown sections as extras
            3. Compose the system prompt
        """
        meta = definition.get("meta", {})
        sections = {k.lower().strip(): v for k, v in definition.get("sections", {}).items()}

        known = {name: sections.get(name, "") for name in KNOWN_SECTIONS}
        extras = {
            name: content for name, content in sections.items()
            if name not in KNOWN_SECTIONS and name not in ("skills", "identity")
        }

        profile = AgentProfile(
            id=meta.get("id", ""),
            name=meta.get("name", ""),
            description=meta.get("description", ""),
            mode=meta.get("mode", "chat"),
            **known,
            extras=extras,
        )
        profile.system_prompt = PromptManager.compose_system_prompt(profile, tools)
        return profile

    @staticmethod
    def compose_system_prompt(profile: AgentProfile, tools: List[Callable] | None = None) -> str:
        """Build the final system prompt from profile sections."""
        parts = []

        if profile.role:
            parts.append(f"ROLE\n{profile.role}")

        if profile.purpose:
            parts.append(f"PURPOSE\n{profile.purpose}")

        if profile.personality:
            parts.append(f"PERSONALITY\n{profile.personality}")

        if profile.boundaries:
            parts.append(f"BOUNDARIES\n{profile.boundaries}")

        if profile.communication:
            parts.append(f"COMMUNICATION STYLE\n{profile.communication}")

        if profile.principles:
            parts.append(f"PRINCIPLES\n{profile.principles}")

        if profile.decision_style:
            parts.append(f"DECISION STYLE\n{profile.decision_style}")

        tool_lines = PromptManager._tool_lines(tools)
        if tool_lines:
            parts.append("AVAILABLE TOOLS\n" + "\n".join(tool_lines))

        # Generic extra sections (user, greeting, project_notes, ...) become
        # UPPERCASE-titled blocks, sorted for deterministic prompts.
        for title, content in sorted(profile.extras.items()):
            if content:
                parts.append(f"{title.upper()}\n{content}")

        return "\n\n".join(parts)

    @staticmethod
    def _tool_lines(tools: List[Callable] | None) -> List[str]:
        """Format tool callables as '- id: first docstring line' lines."""
        lines = []
        for fn in tools or []:
            doc = (fn.__doc__ or "").strip()
            summary = doc.splitlines()[0] if doc else ""
            lines.append(f"- {fn.__name__}: {summary}")
        return lines
