import logging
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd

from groster.http_client import BlizzardAPIClient
from groster.ranks import create_rank_mapping
from groster.repository import CsvRosterRepository, RosterRepository
from groster.services import (
    build_profile_links,
    fetch_playable_classes,
    fetch_playable_races,
    fetch_roster_details,
    identify_alts,
)
from groster.utils import data_path

logger = logging.getLogger(__name__)


def generate_dashboard(base_path: Path, region: str, realm: str, guild: str):
    """
    Generates a consolidated dashboard.csv by merging all other data files.
    """
    logger.info("Generating consolidated dashboard...")

    try:
        # Define paths to all source CSV files
        roster_file = base_path / f"{region}-{realm}-{guild}-roster.csv"
        profiles_file = base_path / f"{region}-{realm}-{guild}-profiles.csv"
        alts_file = base_path / f"{region}-{realm}-{guild}-alts.csv"
        achievements_file = base_path / f"{region}-{realm}-{guild}-achievements.csv"

        # Paths to static mapping files
        classes_file = base_path / "classes.csv"
        races_file = base_path / "races.csv"
        ranks_file = base_path / f"{region}-{realm}-{guild}-ranks.csv"

        # Read all necessary files into pandas DataFrames
        df_roster = pd.read_csv(roster_file)
        df_profiles = pd.read_csv(profiles_file)
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

        # Merge the main data files
        dashboard_df = pd.merge(df_roster, df_profiles, on=["id", "name"])
        dashboard_df = pd.merge(dashboard_df, df_alts, on=["id", "name"])
        dashboard_df = pd.merge(
            dashboard_df, df_achievements, on=["id", "name"], how="left"
        )

        # Map IDs to names
        dashboard_df = pd.merge(dashboard_df, df_classes, on="class_id", how="left")
        dashboard_df = pd.merge(dashboard_df, df_races, on="race_id", how="left")
        dashboard_df = pd.merge(dashboard_df, df_ranks, on="rank", how="left")

        # Rename columns to match the desired output
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

        # Select and order the final columns
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

        # Save the final dashboard file
        dashboard_file = base_path / f"{region}-{realm}-{guild}-dashboard.csv"
        dashboard_df.to_csv(dashboard_file, index=False, encoding="utf-8")
        logger.info("Successfully created dashboard CSV: %s", dashboard_file.resolve())
    except FileNotFoundError as e:
        raise RuntimeError(
            "Failed to generate dashboard: a source CSV file is missing"
        ) from e
    except Exception as e:
        raise RuntimeError(
            "An unexpected error occurred during dashboard generation"
        ) from e


def summary_report(
    base_path: Path, region: str, realm: str, guild: str, time_diff: float
):
    alts_file = data_path(base_path, region, realm, guild, "alts")

    try:
        alts_df = pd.read_csv(alts_file)
        total_alts = alts_df["alt"].sum()
        total_mains = len(alts_df["main"].unique())

        print("\n" + "=" * 50)
        print(f"Processing completed in {time_diff:.2f} seconds")
        print(f"Alts found: {total_alts}")
        print(f"Main characters: {total_mains}")
        print("=" * 50)
    except (
        FileNotFoundError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        KeyError,
    ):
        logger.exception("Failed to generate summary report")
        print(f"\nProcessing completed in {time_diff:.2f} seconds")


async def _get_guild_ranks(
    repo: RosterRepository, region: str, realm: str, guild: str
) -> dict[int, str]:
    """Get guild ranks from the repository or API."""
    ranks_map = await repo.get_guild_ranks(region, realm, guild)
    if ranks_map:
        return ranks_map

    logger.info("No guild ranks found, fetching from API and saving to repository")
    default_ranks_mapping = create_rank_mapping()
    ranks_data_list = [rank._asdict() for rank in default_ranks_mapping.values()]
    if not ranks_data_list:
        raise RuntimeError("Failed to get guild ranks from default mapping")

    await repo.save_guild_ranks(ranks_data_list, region, realm, guild)
    return {rank.id: rank.name for rank in default_ranks_mapping.values()}


async def _get_playable_classes(
    repo: RosterRepository, client: BlizzardAPIClient
) -> dict[int, str]:
    """Get playable classes from the repository or API."""
    class_map = await repo.get_playable_classes()
    if class_map:
        return class_map

    logger.info("No playable classes found, fetching from API and saving to repository")
    classes_data = await fetch_playable_classes(client)
    if not classes_data:
        raise RuntimeError("Failed to fetch playable classes from API")

    await repo.save_playable_classes(classes_data)
    return {c["id"]: c["name"] for c in classes_data}


async def _get_playable_races(
    repo: RosterRepository, client: BlizzardAPIClient
) -> dict[int, str]:
    """Get playable races from the repository or API."""
    race_map = await repo.get_playable_races()
    if race_map:
        return race_map

    logger.info("No playable races found, fetching from API and saving to repository")
    races_data = await fetch_playable_races(client)
    if not races_data:
        raise RuntimeError("Failed to fetch playable races from API")

    await repo.save_playable_races(races_data)
    return {r["id"]: r["name"] for r in races_data}


async def _get_roster_details(
    repo: RosterRepository,
    client: BlizzardAPIClient,
    region: str,
    realm: str,
    guild: str,
) -> dict[str, Any]:
    """Get roster details from the repository or API."""
    roster_data: dict[str, Any] = await client.get_guild_roster(realm, guild)
    if not roster_data:
        raise RuntimeError("Failed to get guild roster data.")

    logger.info("Processing roster details for all members")

    details_data, raw_profiles = await fetch_roster_details(client, roster_data)
    if details_data:
        await repo.save_roster_details(details_data, region, realm, guild)
    else:
        logger.warning("No roster details data found. Skipping roster file creation")

    if raw_profiles:
        logger.info("Saving raw profile data for %d characters", len(raw_profiles))
        for name, profile_json in raw_profiles.items():
            await repo.save_character_profile(profile_json, region, realm, name)

    return roster_data


async def update_roster(region: str, realm: str, guild: str, locale: str):
    """Main entry point for the application."""
    start_time = time.time()
    base_path = Path(os.getenv("GROSTER_DATA_PATH", Path.cwd() / "data"))

    client_id = os.getenv("BLIZZARD_CLIENT_ID")
    client_secret = os.getenv("BLIZZARD_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing BLIZZARD_CLIENT_ID/BLIZZARD_CLIENT_SECRET in environment"
        )

    client = BlizzardAPIClient(
        region=region,
        client_id=client_id,
        client_secret=client_secret,
        locale=locale,
    )

    repo = CsvRosterRepository(base_path=base_path)

    try:
        await _get_guild_ranks(repo, region, realm, guild)
        await _get_playable_classes(repo, client)
        await _get_playable_races(repo, client)

        roster_data = await _get_roster_details(repo, client, region, realm, guild)

        logger.info("Building profile links")
        links_data = build_profile_links(region, roster_data)
        await repo.save_profile_links(links_data, region, realm, guild)

        alts_data, all_raw_pets, all_raw_mounts = await identify_alts(
            client, roster_data
        )
        if not alts_data:
            raise RuntimeError("Failed to identify alts")

        await repo.save_alts_data(alts_data, region, realm, guild)

        logger.info("Saving raw pets data for %d characters", len(all_raw_pets))
        for name, pets_json in all_raw_pets.items():
            await repo.save_character_pets(pets_json, region, realm, name)

        logger.info("Saving raw mounts data for %d characters", len(all_raw_mounts))
        for name, mounts_json in all_raw_mounts.items():
            await repo.save_character_mounts(mounts_json, region, realm, name)

        generate_dashboard(base_path, region, realm, guild)

        end_time = time.time()
        time_diff = end_time - start_time

        summary_report(base_path, region, realm, guild, time_diff)
    finally:
        await client.close()
