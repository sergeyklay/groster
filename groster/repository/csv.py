import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from groster.models import create_character_info
from groster.repository import RosterRepository
from groster.utils import data_path

logger = logging.getLogger(__name__)


class CsvRosterRepository(RosterRepository):
    """CSV-based implementation of RosterRepository.

    Stores all roster data in CSV files within the data directory.
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def get_playable_classes(self) -> dict[int, str] | None:
        """Loads playable classes from 'data/classes.csv'.

        Returns:
            Dictionary mapping class IDs to class names, or None if file doesn't exist.
        """
        classes_file = data_path(self.base_path, "classes")

        if not classes_file.exists():
            logger.info("Classes file does not exist yet: %s", classes_file)
            return None

        try:
            logger.info("Loading classes from file: %s", classes_file)
            df = pd.read_csv(classes_file)
            if df.empty:
                logger.warning("Classes file is empty: %s", classes_file)
                return None

            return pd.Series(df["name"].values, index=df["id"].astype(int)).to_dict()
        except (pd.errors.EmptyDataError, FileNotFoundError, OSError) as e:
            logger.warning(
                "Failed to read classes file, a new one will be created: %s", e
            )
            return None

    async def save_playable_classes(self, classes: list[dict[str, Any]]) -> None:
        """Saves playable classes to 'data/classes.csv'.

        Args:
            classes: List of class data dictionaries to save.

        Raises:
            RuntimeError: If the classes file cannot be written.
        """
        classes_file = data_path(self.base_path, "classes")

        try:
            logger.info("Creating classes file: %s", classes_file)
            df = pd.DataFrame(classes)
            df.to_csv(classes_file, index=False, encoding="utf-8")
            logger.info("Classes file successfully created: %s", classes_file.resolve())
        except OSError as e:
            raise RuntimeError("Failed to write classes file") from e

    async def get_playable_races(self) -> dict[int, str] | None:
        """Loads playable races from 'data/races.csv'.

        Returns:
            Dictionary mapping race IDs to race names, or None if file doesn't exist.
        """
        races_file = data_path(self.base_path, "races")

        if not races_file.exists():
            logger.info("Races file does not exist yet: %s", races_file)
            return None

        try:
            logger.info("Loading races from file: %s", races_file)
            df = pd.read_csv(races_file)
            if df.empty:
                logger.warning("Races file is empty: %s", races_file)
                return None

            return pd.Series(df["name"].values, index=df["id"].astype(int)).to_dict()
        except (pd.errors.EmptyDataError, FileNotFoundError, OSError) as e:
            logger.warning(
                "Failed to read races file, a new one will be created: %s", e
            )
            return None

    async def save_playable_races(self, races: list[dict[str, Any]]) -> None:
        """Saves playable races to 'data/races.csv'.

        Args:
            races: List of race data dictionaries to save.
        """
        races_file = data_path(self.base_path, "races")

        try:
            logger.info("Creating races file: %s", races_file)
            df = pd.DataFrame(races)
            df.to_csv(races_file, index=False, encoding="utf-8")
            logger.info("Races file successfully created: %s", races_file.resolve())
        except OSError as e:
            raise RuntimeError("Failed to write races file") from e

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
        ranks_file = data_path(self.base_path, region, realm, guild, "ranks")

        if not ranks_file.exists():
            logger.info("Ranks file does not exist yet: %s", ranks_file)
            return None

        try:
            logger.info("Loading ranks from file: %s", ranks_file)
            df = pd.read_csv(ranks_file)
            if df.empty:
                logger.warning("Ranks file is empty: %s", ranks_file)
                return None

            return pd.Series(df["name"].values, index=df["id"].astype(int)).to_dict()
        except (pd.errors.EmptyDataError, FileNotFoundError, OSError) as e:
            logger.warning(
                "Failed to read ranks file, a new one will be created: %s", e
            )
            return None

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
        ranks_file = data_path(self.base_path, region, realm, guild, "ranks")

        try:
            logger.info("Creating ranks file: %s", ranks_file)
            df = pd.DataFrame(ranks)
            df.to_csv(ranks_file, index=False, encoding="utf-8")
            logger.info("Ranks file successfully created: %s", ranks_file.resolve())
        except OSError as e:
            raise RuntimeError("Failed to write ranks file") from e

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
        links_file = data_path(self.base_path, region, realm, guild, "links")

        try:
            logger.info("Creating links file: %s", links_file)
            df = pd.DataFrame(links_data)
            df.to_csv(links_file, index=False, encoding="utf-8")
            logger.info("Links file successfully created: %s", links_file.resolve())
        except OSError as e:
            logger.warning("Failed to process links file: %s", e)

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
        roster_file = data_path(self.base_path, region, realm, guild, "roster")

        try:
            logger.info("Creating roster file: %s", roster_file)
            df = pd.DataFrame(roster_data)
            df.to_csv(roster_file, index=False, encoding="utf-8")
            logger.info("Roster file successfully created: %s", roster_file.resolve())
        except OSError as e:
            raise RuntimeError("Failed to write roster file") from e

    async def save_character_profile(
        self, profile_data: dict[str, Any], region: str, realm: str, char_name: str
    ) -> None:
        """Save raw JSON profile data for a single character.

        Args:
            profile_data: Raw character profile data dictionary to save.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            char_name: The character's name.
        """
        char_path = self.base_path / region / realm / char_name.lower()
        char_path.mkdir(parents=True, exist_ok=True)
        profile_file = char_path / "profile.json"

        try:
            logger.debug("Creating profile file for %s: %s", char_name, profile_file)
            with open(profile_file, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, ensure_ascii=False, indent=4)
            logger.debug(
                "Profile file successfully created: %s", profile_file.resolve()
            )
        except OSError as exc:
            logger.warning("Failed to process profile file for %s: %s", char_name, exc)

    async def save_character_pets(
        self,
        pets_data: dict[str, Any],
        region: str,
        realm: str,
        character_name: str,
    ) -> None:
        """Save raw JSON pet collection data for a single character.

        Args:
            pets_data: Raw character pet collection data dictionary to save.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            character_name: The character's name.
        """
        char_path = self.base_path / region / realm / character_name.lower()
        char_path.mkdir(parents=True, exist_ok=True)
        pets_file = char_path / "pets.json"

        try:
            logger.debug("Creating pets file for %s: %s", character_name, pets_file)
            with open(pets_file, "w", encoding="utf-8") as f:
                json.dump(pets_data, f, ensure_ascii=False, indent=4)
            logger.debug("Pets file successfully created: %s", pets_file.resolve())
        except OSError as exc:
            logger.warning(
                "Failed to process pets file for %s: %s", character_name, exc
            )

    async def save_character_mounts(
        self,
        mounts_data: dict[str, Any],
        region: str,
        realm: str,
        character_name: str,
    ) -> None:
        """Save raw JSON mount collection data for a single character.

        Args:
            mounts_data: Raw character mount collection data dictionary to save.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            character_name: The character's name.
        """
        char_path = self.base_path / region / realm / character_name.lower()
        char_path.mkdir(parents=True, exist_ok=True)
        mounts_file = char_path / "mounts.json"

        try:
            logger.debug("Creating mounts file for %s: %s", character_name, mounts_file)
            with open(mounts_file, "w", encoding="utf-8") as f:
                json.dump(mounts_data, f, ensure_ascii=False, indent=4)
            logger.debug("Mounts file successfully created: %s", mounts_file.resolve())
        except OSError as exc:
            logger.warning(
                "Failed to process mounts file for %s: %s", character_name, exc
            )

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
        alts_file = data_path(self.base_path, region, realm, guild, "alts")

        try:
            logger.info("Creating alts file: %s", alts_file)
            df = pd.DataFrame(alts_data)
            df.to_csv(alts_file, index=False, encoding="utf-8")
            logger.info("Alts file successfully created: %s", alts_file.resolve())
        except OSError as e:
            raise RuntimeError("Failed to write alts file") from e

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

            If the character is not found, first element of the tuple is None.
            If dashboard file does not exist, second element of the tuple is None.
        """
        dashboard_file = data_path(self.base_path, region, realm, guild, "dashboard")
        if not dashboard_file.exists():
            logger.warning("Dashboard file does not exist: %s", dashboard_file)
            return None, None

        modified_at = datetime.fromtimestamp(dashboard_file.stat().st_mtime)
        df = pd.read_csv(dashboard_file)

        # Search for character (case-insensitive)
        character_row = df[df["Name"].str.lower() == name.lower()]
        if character_row.empty:
            logger.debug(
                "Character '%s' not found in guild roster: %s", name, dashboard_file
            )
            return None, modified_at

        # Determine main character name
        char_data = character_row.iloc[0]
        main_name = char_data["Main"] if char_data["Alt?"] else char_data["Name"]

        # Get main character data
        main_row = df[df["Name"].str.lower() == main_name.lower()]
        if main_row.empty:
            logger.warning("Main character '%s' not found for '%s'", main_name, name)
            # Use alt data as a fallback
            main_info = create_character_info(char_data)
        else:
            main_info = create_character_info(main_row.iloc[0])

        # Find all alts for this main character
        alts_df = df[(df["Main"].str.lower() == main_name.lower()) & df["Alt?"]]

        alts = []
        for _, alt_row in alts_df.iterrows():
            alts.append(create_character_info(alt_row))

        # Add alts list to main character info
        main_info["alts"] = alts
        logger.debug(
            "Found character '%s' (main: %s) with %d alts", name, main_name, len(alts)
        )

        return main_info, modified_at
