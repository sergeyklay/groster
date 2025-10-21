import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class RosterRepository(ABC):
    """Abstract interface for storing and retrieving guild data.

    This class defines the contract that concrete storage implementations
    (e.g., CSV, SQLite) must implement.
    """

    @abstractmethod
    async def get_playable_classes(self) -> dict[int, str] | None:
        """Retrieve saved playable classes mapping.

        Returns:
            Dictionary mapping class IDs to class names, or None if not found.
        """
        pass

    @abstractmethod
    async def save_playable_classes(self, classes: list[dict[str, Any]]) -> None:
        """Saves the list of playable classes.

        Args:
            classes: List of class data dictionaries to save.
        """
        pass

    @abstractmethod
    async def get_playable_races(self) -> dict[int, str] | None:
        """Retrieves saved playable races mapping.

        Returns:
            Dictionary mapping race IDs to race names, or None if not found.
        """
        pass

    @abstractmethod
    async def save_playable_races(self, races: list[dict[str, Any]]) -> None:
        """Save the list of playable races.

        Args:
            races: List of race data dictionaries to save.
        """
        pass

    @abstractmethod
    async def get_guild_ranks(
        self, region: str, realm: str, guild: str
    ) -> dict[int, str] | None:
        """Retrieve saved guild ranks mapping for a specific guild.

        Args:
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.

        Returns:
            Dictionary mapping rank IDs to rank names, or None if not found.
        """
        pass

    @abstractmethod
    async def save_guild_ranks(
        self, ranks: list[dict[str, Any]], region: str, realm: str, guild: str
    ) -> None:
        """Save the list of guild ranks for a specific guild.

        Args:
            ranks: List of rank data dictionaries to save.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.
        """
        pass
