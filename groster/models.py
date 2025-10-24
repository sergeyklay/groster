from typing import Any, TypedDict

import pandas as pd


class PlayableClass(TypedDict):
    """A playable class from the game."""

    id: int
    name: str


class PlayableRace(TypedDict):
    """A playable race from the game."""

    id: int
    name: str


def create_character_info(row: pd.Series) -> dict[str, Any]:
    """Create character info dict from pandas row.

    Args:
        row: Pandas Series containing character data from dashboard CSV.

    Returns:
        Dict with character information.
    """
    # Extract scalar values to avoid pandas Series type issues
    name = row["Name"]
    realm = row["Realm"]
    level = row["Level"]
    char_class = row["Class"]
    race = row["Race"]
    rank = row["Rank"]
    ilvl = row["iLvl"]
    last_login = row["Last Login"]
    is_alt = row["Alt?"]
    main = row["Main"]

    return {
        "name": str(name),
        "realm": str(realm),
        "level": int(level) if pd.notna(level) else 0,  # type: ignore
        "class": str(char_class) if pd.notna(char_class) else "Unknown",  # type: ignore
        "race": str(race) if pd.notna(race) else "Unknown",  # type: ignore
        "rank": str(rank) if pd.notna(rank) else "Unknown",  # type: ignore
        "ilvl": int(ilvl) if pd.notna(ilvl) else 0,  # type: ignore
        "last_login": str(last_login) if pd.notna(last_login) else "N/A",  # type: ignore
        "is_alt": bool(is_alt) if pd.notna(is_alt) else False,  # type: ignore
        "main": str(main) if pd.notna(main) else str(name),  # type: ignore
    }
