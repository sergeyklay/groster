from typing import TypedDict


class PlayableClass(TypedDict):
    """A playable class from the game."""

    id: int
    name: str


class PlayableRace(TypedDict):
    """A playable race from the game."""

    id: int
    name: str
