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

    async def get_roster_details(
        self, region: str, realm: str, guild: str
    ) -> list[dict[str, Any]] | None:
        """Retrieve previously saved roster details for a specific guild.

        Args:
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            guild: The guild slug.

        Returns:
            List of roster record dicts, or None if file does not exist.
        """
        roster_file = data_path(self.base_path, region, realm, guild, "roster")

        if not roster_file.exists():
            logger.info("Roster file does not exist yet: %s", roster_file)
            return None

        try:
            logger.info("Loading roster from file: %s", roster_file)
            df = pd.read_csv(roster_file)
            if df.empty:
                logger.warning("Roster file is empty: %s", roster_file)
                return None
            return df.to_dict(orient="records")  # type: ignore[return-value]
        except (pd.errors.EmptyDataError, FileNotFoundError, OSError) as e:
            logger.warning(
                "Failed to read roster file, will perform full refresh: %s", e
            )
            return None

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

    async def save_character_achievements(
        self,
        achievements_data: dict[str, Any],
        region: str,
        realm: str,
        char_name: str,
    ) -> None:
        """Save per-character achievement fingerprint data.

        Args:
            achievements_data: Dict with fingerprint, timestamps, and totals.
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            char_name: The character's name.
        """
        char_path = self.base_path / region / realm / char_name.lower()
        char_path.mkdir(parents=True, exist_ok=True)
        achievements_file = char_path / "achievements.json"

        try:
            logger.debug(
                "Creating achievements file for %s: %s",
                char_name,
                achievements_file,
            )
            with open(achievements_file, "w", encoding="utf-8") as f:
                json.dump(achievements_data, f, ensure_ascii=False, indent=4)
            logger.debug(
                "Achievements file successfully created: %s",
                achievements_file.resolve(),
            )
        except OSError as exc:
            logger.warning(
                "Failed to process achievements file for %s: %s", char_name, exc
            )

    async def get_member_fingerprints(
        self,
        region: str,
        realm: str,
        member_names: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Bulk-load cached achievement fingerprints for listed members.

        Args:
            region: The region identifier (e.g., 'eu', 'us').
            realm: The realm slug.
            member_names: List of character names to load.

        Returns:
            Dict mapping character name to achievement data dict.
        """
        result: dict[str, dict[str, Any]] = {}
        for name in member_names:
            ach_file = (
                self.base_path / region / realm / name.lower() / "achievements.json"
            )
            if not ach_file.exists():
                continue
            try:
                with open(ach_file, encoding="utf-8") as f:
                    data = json.load(f)
                raw_fp = data.get("fingerprint", ())
                if isinstance(raw_fp, list):
                    data["fingerprint"] = tuple(tuple(pair) for pair in raw_fp)
                result[name] = data
            except (json.JSONDecodeError, OSError, KeyError) as exc:
                logger.warning(
                    "Failed to load achievements cache for %s: %s", name, exc
                )
        return result

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

    async def save_achievements_summary(
        self, summary_data: list[dict[str, Any]], region: str, realm: str, guild: str
    ) -> None:
        """Save the summary of achievements (count, points) for all members.

        Args:
            summary_data: List of dicts, each with 'id', 'name',
                          'total_quantity', 'total_points'.
            region: The region identifier.
            realm: The realm slug.
            guild: The guild slug.
        """
        achievements_file = data_path(
            self.base_path, region, realm, guild, "achievements"
        )

        try:
            logger.info("Creating achievements summary file: %s", achievements_file)
            df = pd.DataFrame(summary_data)
            df = df[["id", "name", "total_quantity", "total_points"]]
            df.to_csv(achievements_file, index=False, encoding="utf-8")
            logger.info(
                "Achievements summary file successfully created: %s",
                achievements_file.resolve(),
            )
        except OSError as e:
            raise RuntimeError("Failed to write achievements summary file") from e
        except KeyError as e:
            raise RuntimeError("Invalid achievement summary data structure") from e

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
        logger.info("Generating consolidated dashboard...")

        try:
            roster_file = data_path(self.base_path, region, realm, guild, "roster")
            links_file = data_path(self.base_path, region, realm, guild, "links")
            alts_file = data_path(self.base_path, region, realm, guild, "alts")
            achievements_file = data_path(
                self.base_path, region, realm, guild, "achievements"
            )
            classes_file = data_path(self.base_path, "classes")
            races_file = data_path(self.base_path, "races")
            ranks_file = data_path(self.base_path, region, realm, guild, "ranks")

            df_roster = pd.read_csv(roster_file)
            df_links = pd.read_csv(links_file)
            df_alts = pd.read_csv(alts_file)
            df_achievements = pd.read_csv(
                achievements_file,
                usecols=[  # type: ignore
                    "id",
                    "name",
                    "total_quantity",
                    "total_points",
                ],
            )

            df_classes = pd.read_csv(classes_file).rename(
                columns={"id": "class_id", "name": "Class"}
            )
            df_races = pd.read_csv(races_file).rename(
                columns={"id": "race_id", "name": "Race"}
            )
            df_ranks = pd.read_csv(ranks_file).rename(
                columns={"id": "rank", "name": "Rank"}
            )

            dashboard_df = pd.merge(df_roster, df_links, on=["id", "name"])
            dashboard_df = pd.merge(dashboard_df, df_alts, on=["id", "name"])
            dashboard_df = pd.merge(
                dashboard_df, df_achievements, on=["id", "name"], how="left"
            )

            dashboard_df = pd.merge(dashboard_df, df_classes, on="class_id", how="left")
            dashboard_df = pd.merge(dashboard_df, df_races, on="race_id", how="left")
            dashboard_df = pd.merge(dashboard_df, df_ranks, on="rank", how="left")

            dashboard_df = dashboard_df.rename(
                columns={
                    "name": "Name",
                    "realm": "Realm",
                    "level": "Level",
                    "total_quantity": "AQ",
                    "total_points": "AP",
                    "alt": "Alt?",
                    "main": "Main",
                    "ilvl": "iLvl",
                    "last_login": "Last Login",
                    "rio_link": "Raider.io",
                    "armory_link": "Armory",
                    "warcraft_logs_link": "Logs",
                }
            )

            final_columns = [
                "Name",
                "Realm",
                "Level",
                "Class",
                "Race",
                "Rank",
                "AQ",
                "AP",
                "Alt?",
                "Main",
                "iLvl",
                "Last Login",
                "Raider.io",
                "Armory",
                "Logs",
            ]
            dashboard_df = dashboard_df[final_columns]

            dashboard_file = data_path(
                self.base_path, region, realm, guild, "dashboard"
            )
            dashboard_df.to_csv(dashboard_file, index=False, encoding="utf-8")
            logger.info(
                "Successfully created dashboard CSV: %s", dashboard_file.resolve()
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                "Failed to generate dashboard: a source CSV file is missing"
            ) from e
        except Exception as e:
            raise RuntimeError(
                "An unexpected error occurred during dashboard generation"
            ) from e

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
        alts_file = data_path(self.base_path, region, realm, guild, "alts")

        try:
            alts_df = pd.read_csv(alts_file)
            total_alts = int(alts_df["alt"].sum())
            total_mains = len(alts_df["main"].unique())
            return (total_alts, total_mains)
        except (
            FileNotFoundError,
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
            KeyError,
        ):
            logger.exception("Failed to read alts data for summary")
            return None

    async def get_alts_per_main(
        self, region: str, realm: str, guild: str
    ) -> list[tuple[str, str, int]] | None:
        """Return per-main alt counts from the dashboard."""
        dashboard_file = data_path(self.base_path, region, realm, guild, "dashboard")
        if not dashboard_file.exists():
            logger.debug("Dashboard file does not exist: %s", dashboard_file)
            return None

        try:
            df = pd.read_csv(dashboard_file)
            mains_df = df[df["Alt?"] == False][["Name", "Class"]]  # noqa: E712
            mains_df = mains_df.rename(columns={"Name": "Main"})

            alts_df = df[df["Alt?"] == True]  # noqa: E712
            grouped = alts_df.groupby("Main").size().reset_index(name="alt_count")

            result = mains_df.merge(grouped, on="Main", how="left").fillna(0)
            result["alt_count"] = result["alt_count"].astype(int)
            result = result.sort_values(["alt_count", "Main"], ascending=[False, True])
            return [
                (r["Main"], r["Class"], r["alt_count"]) for _, r in result.iterrows()
            ]
        except (
            FileNotFoundError,
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
            KeyError,
        ):
            logger.exception("Failed to read dashboard data for alts per main")
            return None

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
        dashboard_file = data_path(self.base_path, region, realm, guild, "dashboard")
        if not dashboard_file.exists():
            logger.debug("Dashboard file does not exist: %s", dashboard_file)
            return []

        df = pd.read_csv(dashboard_file, usecols=["Name"])
        lower_prefix = prefix.lower()
        matches = df[df["Name"].str.lower().str.startswith(lower_prefix)]
        return matches["Name"].sort_values().head(limit).tolist()
