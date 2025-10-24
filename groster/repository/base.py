from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


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

    @abstractmethod
    async def save_playable_classes(self, classes: list[dict[str, Any]]) -> None:
        """Saves the list of playable classes.

        Args:
            classes: List of class data dictionaries to save.
        """

    @abstractmethod
    async def get_playable_races(self) -> dict[int, str] | None:
        """Retrieves saved playable races mapping.

        Returns:
            Dictionary mapping race IDs to race names, or None if not found.
        """

    @abstractmethod
    async def save_playable_races(self, races: list[dict[str, Any]]) -> None:
        """Save the list of playable races.

        Args:
            races: List of race data dictionaries to save.
        """

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

    @abstractmethod
    async def save_profile_links(
        self, links_data: list[dict[str, Any]], region: str, realm: str, guild: str
    ) -> None:
        """Save generated profile links for guild members.

        Args:
            links_data: List of profile link data dictionaries to save.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.
        """

    @abstractmethod
    async def save_roster_details(
        self, roster_data: list[dict[str, Any]], region: str, realm: str, guild: str
    ) -> None:
        """Save processed roster details for a specific guild.

        Args:
            roster_data: List of processed member detail dictionaries to save.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.
        """

    @abstractmethod
    async def save_character_profile(
        self,
        profile_data: dict[str, Any],
        region: str,
        realm: str,
        char_name: str,
    ) -> None:
        """Save raw JSON profile data for a single character.

        Args:
            profile_data: Raw character profile data dictionary to save.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            char_name: The character's name.
        """

    @abstractmethod
    async def save_character_pets(
        self,
        pets_data: dict[str, Any],
        region: str,
        realm: str,
        character_name: str,
    ) -> None:
        """Save pet collection data for a single character.

        Args:
            pets_data: Raw character pet collection data dictionary to save.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            character_name: The character's name.
        """

    @abstractmethod
    async def save_character_mounts(
        self,
        mounts_data: dict[str, Any],
        region: str,
        realm: str,
        character_name: str,
    ) -> None:
        """Save mount collection data for a single character.

        Args:
            mounts_data: Raw character mount collection data dictionary to save.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            character_name: The character's name.
        """

    @abstractmethod
    async def save_alts_data(
        self, alts_data: list[dict[str, Any]], region: str, realm: str, guild: str
    ) -> None:
        """Save processed alts data for a specific guild.

        Args:
            alts_data: List of processed alt data dictionaries to save.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.
        """

    @abstractmethod
    async def get_character_info_by_name(
        self, name: str, region: str, realm: str, guild: str
    ) -> tuple[dict[str, Any] | None, datetime | None]:
        """Retrieve character information by name from the dashboard data.

        Searches for a character in the dashboard and returns their complete
        information including main and alt character details.

        Args:
            name: The character's name to search for (case-insensitive).
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.

        Returns:
            A tuple containing
            - the character information dictionary
            - the last modified datetime of the dashboard data
        """

    @abstractmethod
    async def save_achievements_summary(
        self, summary_data: list[dict[str, Any]], region: str, realm: str, guild: str
    ) -> None:
        """Saves the summary of achievements (count, points) for all members.

        Args:
            summary_data: List of dicts, each with 'id', 'name',
                          'total_quantity', 'total_points'.
            region: The region identifier.
            realm: The realm slug.
            guild: The guild slug.
        """
