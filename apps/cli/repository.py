import logging
from pathlib import Path
from typing import Any

import pandas as pd

from apps.cli.utils import data_path
from groster.repository import RosterRepository

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
            logger.exception("Failed to process classes file: %s", e)
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
            logger.exception("Failed to process races file: %s", e)
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
            logger.exception("Failed to process ranks file: %s", e)
            raise RuntimeError("Failed to write ranks file") from e
