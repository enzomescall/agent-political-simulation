from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.agent import Agent


def fmt(agent: Agent) -> str:
    """Format agent for log lines: [id] name."""
    return f"[{agent.id}] {agent.name}"
