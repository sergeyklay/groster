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
    async def get_roster_details(
        self, region: str, realm: str, guild: str
    ) -> list[dict[str, Any]] | None:
        """Retrieve previously saved roster details for a specific guild.

        Used to snapshot the last-known member state for incremental diffing.

        Args:
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.

        Returns:
            List of roster record dicts (keys: id, name, realm, level,
            class_id, race_id, rank, ilvl, last_login), or None if the
            roster file does not yet exist (first run).
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
    async def save_character_achievements(
        self,
        achievements_data: dict[str, Any],
        region: str,
        realm: str,
        char_name: str,
    ) -> None:
        """Save per-character achievement fingerprint data.

        Persists the fingerprint, timestamps, and summary totals needed to
        reconstruct alt-detection data for incremental runs without API calls.

        Args:
            achievements_data: Dict with keys: id, name, fingerprint
                (list of [id, ts] pairs), timestamps (dict), total_quantity,
                total_points.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            char_name: The character's name.
        """

    @abstractmethod
    async def get_member_fingerprints(
        self,
        region: str,
        realm: str,
        member_names: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Bulk-load cached achievement fingerprints for listed members.

        Reads per-character achievement data for each name in member_names.
        Missing entries are silently skipped.

        Args:
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            member_names: List of character names to load.

        Returns:
            Dict mapping character name to achievement data dict. The
            ``fingerprint`` field is returned as tuple[tuple[int, int], ...]
            (deserialised from the JSON list-of-lists representation).
            Characters with no cached data are absent from the result.
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

    @abstractmethod
    async def build_dashboard(self, region: str, realm: str, guild: str) -> None:
        """Build and persist a consolidated dashboard from source data files.

        Reads roster, links, alts, achievements, classes, races, and ranks
        data, merges them into a single dashboard, and persists the result.

        Args:
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.

        Raises:
            RuntimeError: If a required source data file is missing or
                an error occurs during dashboard generation.
        """

    @abstractmethod
    async def get_alt_summary(
        self, region: str, realm: str, guild: str
    ) -> tuple[int, int] | None:
        """Retrieve a summary of alt detection results.

        Args:
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.

        Returns:
            A tuple of (total_alts, total_mains), or None if the alts
            data is not available or cannot be read.
        """

    @abstractmethod
    async def get_alts_per_main(
        self, region: str, realm: str, guild: str
    ) -> list[tuple[str, str, int]] | None:
        """Return per-main alt counts from the dashboard.

        Args:
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.

        Returns:
            Sorted list of (main_name, class_name, alt_count) tuples,
            ordered by alt_count descending then main_name ascending.
            None if dashboard data is unavailable.
        """

    @abstractmethod
    async def search_character_names(
        self,
        prefix: str,
        region: str,
        realm: str,
        guild: str,
        *,
        limit: int = 25,
    ) -> list[str]:
        """Search character names in the dashboard by case-insensitive prefix.

        Args:
            prefix: Case-insensitive prefix to match against character names.
                Empty string matches all names.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.
            limit: Maximum number of results to return (default 25, Discord max).

        Returns:
            List of matching character names sorted alphabetically,
            up to ``limit`` entries. Empty list if dashboard is unavailable.
        """
