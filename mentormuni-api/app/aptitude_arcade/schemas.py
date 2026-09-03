"""Schemas for Aptitude Arcade question generation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

GAME_IDS = (
    "seating_shuffle",
    "family_tree_rush",
    "rail_rush",
    "factory_floor",
    "pattern_pulse",
)

GameId = Literal[
    "seating_shuffle",
    "family_tree_rush",
    "rail_rush",
    "factory_floor",
    "pattern_pulse",
]


class ArcadeGenerateIn(BaseModel):
    game_id: GameId
    count: int = Field(default=30, ge=10, le=30)


class ArcadeGenerateOut(BaseModel):
    game_id: GameId
    count: int
    questions: list[dict[str, Any]]
    source: str = "openai"
    model: str | None = None
