import argparse
import asyncio
import logging
import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from groster.constants import DATA_PATH
from groster.http_client import BlizzardAPIClient
from groster.services import (
    create_profile_links,
    fetch_roster_details,
    get_guild_ranks,
    get_playable_classes,
    get_playable_races,
    identify_alts,
)
from groster.utils import data_path

logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False):
    """Configure logging for the application.

    Args:
        debug: If True, enable debug logging for httpx/httpcore requests.
    """
    log_path = Path().cwd() / "groster.log"

    # Set base logging level
    log_level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(str(log_path))],
    )

    if not debug:
        # Reduce httpx/httpcore logging noise - only show WARNING and above
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)


def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch and process a WoW guild roster from the Battle.net API."
    )

    parser.add_argument(
        "--region",
        type=str,
        default="eu",
        help="The region for the API request (e.g., 'eu').",
    )

    parser.add_argument(
        "--realm",
        type=str,
        required=True,
        help="The slug of the realm (e.g., 'terokkar').",
    )

    parser.add_argument(
        "--guild",
        type=str,
        required=True,
        help="The slug of the guild (e.g., 'darq-side-of-the-moon').",
    )

    parser.add_argument(
        "--locale",
        type=str,
        default="en_US",
        help="The locale for the API request (e.g., 'en_US').",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging, including HTTP request/response details.",
    )

    return parser.parse_args()


def generate_dashboard(region: str, realm: str, guild: str):
    """
    Generates a consolidated dashboard.csv by merging all other data files.
    """
    logger.info("Generating consolidated dashboard...")

    try:
        # Define paths to all source CSV files
        roster_file = DATA_PATH / f"{region}-{realm}-{guild}-roster.csv"
        profiles_file = DATA_PATH / f"{region}-{realm}-{guild}-profiles.csv"
        alts_file = DATA_PATH / f"{region}-{realm}-{guild}-alts.csv"
        achievements_file = DATA_PATH / f"{region}-{realm}-{guild}-achievements.csv"

        # Paths to static mapping files
        classes_file = DATA_PATH / "classes.csv"
        races_file = DATA_PATH / "races.csv"
        ranks_file = DATA_PATH / f"{region}-{realm}-{guild}-ranks.csv"

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
        dashboard_file = DATA_PATH / f"{region}-{realm}-{guild}-dashboard.csv"
        dashboard_df.to_csv(dashboard_file, index=False, encoding="utf-8")
        logger.info("Successfully created dashboard CSV: %s", dashboard_file.resolve())

    except FileNotFoundError as e:
        logger.error(
            "Failed to generate dashboard: a source CSV file is missing. %s", e
        )
    except Exception as e:
        logger.exception(
            "An unexpected error occurred during dashboard generation: %s", e
        )


def summary_report(alts_file: str, time_diff: float):
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


async def main():
    """Main entry point for the application."""
    start_time = time.time()
    args = parse_arguments()

    load_dotenv()
    setup_logging(debug=args.debug)

    DATA_PATH.mkdir(parents=True, exist_ok=True)

    client_id = os.getenv("BLIZZARD_CLIENT_ID")
    client_secret = os.getenv("BLIZZARD_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing BLIZZARD_CLIENT_ID/BLIZZARD_CLIENT_SECRET in environment"
        )

    api_client = BlizzardAPIClient(
        region=args.region,
        client_id=client_id,
        client_secret=client_secret,
        locale=args.locale,
    )

    try:
        ranks_data = await get_guild_ranks(args.region, args.realm, args.guild)
        if not ranks_data:
            raise RuntimeError("Failed to get guild ranks data")

        class_map = await get_playable_classes(api_client)
        race_map = await get_playable_races(api_client)
        if not all([class_map, race_map]):
            raise RuntimeError("Failed to get necessary playable classes/races data")

        roster_data = await api_client.get_guild_roster(args.realm, args.guild)
        if not roster_data:
            raise RuntimeError("Failed to get guild roster data.")

        logger.info("Processing roster details for all members...")
        details_data = await fetch_roster_details(api_client, roster_data)
        roster_file = data_path(args.region, args.realm, args.guild, "roster")
        if details_data:
            df = pd.DataFrame(details_data)
            df.to_csv(roster_file, index=False, encoding="utf-8")
            logger.info("Successfully created roster file: %s", roster_file.resolve())
        else:
            logger.warning(
                "No roster details data found. Skipping roster file creation"
            )
            roster_file.unlink(missing_ok=True)

        create_profile_links(args.region, args.realm, args.guild, roster_data)

        alts_data, alts_file = await identify_alts(
            api_client, args.region, args.realm, args.guild, roster_data
        )
        if not alts_data:
            raise RuntimeError("Failed to identify alts")

        generate_dashboard(args.region, args.realm, args.guild)

        end_time = time.time()
        time_diff = end_time - start_time
        summary_report(str(alts_file), time_diff)
    finally:
        await api_client.close()


def cli() -> None:
    """Synchronous entry point for the CLI command."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
