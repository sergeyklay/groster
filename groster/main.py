import argparse
import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from groster.characters import (
    identify_alts,
    process_profiles,
    process_roster_to_csv,
)
from groster.constants import CACHE_PATH, DATA_PATH, FINGERPRINT_ACHIEVEMENT_IDS
from groster.ranks import create_rank_mapping

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging for the application."""
    log_path = Path().cwd() / "groster.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(str(log_path))],
    )


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
        help="The slug of the guild (e.g., 'darq-side-of-the-moon').",
    )

    parser.add_argument(
        "--locale",
        type=str,
        default="en_US",
        help="The locale for the API request (e.g., 'en_US').",
    )

    parser.add_argument(
        "--debug-chars",
        type=str,
        help=(
            "A comma-separated list of character names to debug (e.g., 'Darq,Lucen'). "
            "Skips normal execution."
        ),
    )

    return parser.parse_args()


def get_access_token(region: str, client_id: str, client_secret: str) -> str | None:
    """
    Obtains an OAuth access token using the Client Credentials flow.

    Args:
        region: The Battle.net region (e.g., 'eu').
        client_id: Your Battle.net application client ID.
        client_secret: Your Battle.net application client secret.

    Returns:
        The access token string or None if the request fails.
    """
    url = f"https://{region}.battle.net/oauth/token"
    data = {"grant_type": "client_credentials"}
    auth = (client_id, client_secret)

    logger.info("Requesting access token from Battle.net")
    try:
        response = requests.post(url, data=data, auth=auth)
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get("access_token")
        if access_token:
            logger.info("Access token successfully obtained")
            return access_token
        logger.error("'access_token' not found in the response")
        logger.debug("Token response: %s", token_data)
        return None
    except requests.exceptions.HTTPError as http_err:
        logger.error("HTTP error occurred while getting token: %s", http_err)
        logger.debug("Response content: %s", response.text)
    except requests.exceptions.RequestException as err:
        logger.error("Request for token failed: %s", err)

    return None


def get_static_data_mappings(
    endpoint_url: str,
    region: str,
    token: str,
    data_key: str,
    cache_filename: str,
    locale: str = "en_US",
) -> dict | None:
    """
    Fetches static data (like classes or races) from the API, with local caching.

    Args:
        endpoint_url: The API URL for the static data index.
        region: The Battle.net region (e.g., 'eu').
        token: The OAuth access token.
        data_key: The key in the JSON response that holds the list of items.
        cache_filename: The local file to use for caching the data.
        locale: The locale for the API request.

    Returns:
        A dictionary mapping IDs to names, or None on failure.
    """
    cache_path = DATA_PATH / cache_filename
    if cache_path.exists():
        logger.info("Loading %s from local cache: %s", data_key, cache_path)
        try:
            df = pd.read_csv(cache_path, dtype={"id": int, "name": str})

            # Ensure keys are strings for consistent mapping
            return dict(zip(df["id"].astype(int), df["name"].astype(str), strict=True))
        except (pd.errors.EmptyDataError, KeyError, OSError) as e:
            logger.warning(
                "Failed to read cache file %s: %s. Refetching from API",
                cache_path,
                e,
            )

    logger.info("Fetching %s from API and creating cache", data_key)
    headers = {"Authorization": f"Bearer {token}"}
    params = {"namespace": f"static-{region}", "locale": locale}

    try:
        response = requests.get(endpoint_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        items = data.get(data_key)
        if not items:
            logger.error("'%s' key not found in static API response.", data_key)
            return None

        df = pd.DataFrame(items)
        df = df[["id", "name"]]

        df.to_csv(cache_path, index=False, encoding="utf-8")
        logger.info("Successfully cached %s to %s", data_key, cache_path)

        return dict(zip(df["id"].astype(int), df["name"].astype(str), strict=True))
    except (OSError, requests.exceptions.RequestException, KeyError) as e:
        logger.error("Failed to fetch or process static data for %s: %s", data_key, e)
        return None


def fetch_guild_roster(
    api_token: str,
    region: str,
    realm_slug: str,
    guild_slug: str,
    locale: str = "en_US",
) -> dict | None:
    """
    Fetches the guild roster from the Battle.net API.

    Args:
        api_token: The OAuth 2.0 bearer token.
        region: The Battle.net region (e.g., 'eu').
        realm_slug: The slug of the realm (e.g., 'terokkar').
        guild_slug: The slug of the guild (e.g., 'darq-side-of-the-moon').
        locale: The locale for the API request (e.g., 'en_US')

    Returns:
        A dictionary with the guild roster data or None if the request fails.
    """
    url = f"https://{region}.api.blizzard.com/data/wow/guild/{realm_slug}/{guild_slug}/roster"
    headers = {"Authorization": f"Bearer {api_token}"}

    params = {"namespace": f"profile-{region}", "locale": locale}

    logger.info("Requesting guild roster from Battle.net API")
    logger.debug("API endpoint: %s", url)

    try:
        response = requests.get(url, headers=headers, params=params)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        logger.info("Guild roster fetched successfully")
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        logger.error("HTTP error occurred: %s", http_err)
        logger.debug("Response content: %s", response.text)
    except requests.exceptions.RequestException as err:
        logger.error("Request failed: %s", err)

    return None


def calculate_hash(data: dict) -> str:
    """Calculate a SHA256 hash of a dictionary."""
    encoded_data = json.dumps(data, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded_data).hexdigest()


def has_roster_changed(new_hash: str, hash_file: Path) -> bool:
    """Checks for hash changes and updates the hash file."""
    if not hash_file.exists():
        logger.info("No previous roster hash found. Processing data...")
        hash_file.write_text(new_hash)
        return True

    old_hash = hash_file.read_text()
    if old_hash == new_hash:
        logger.info("Roster data has not changed since last run. Skipping")
        return False

    logger.info("Roster data has changed. Reprocessing and updating hash...")
    hash_file.write_text(new_hash)
    return True


def _data_path(region: str, realm: str, guild: str, file: str) -> Path:
    return DATA_PATH / f"{region}-{realm}-{guild}-{file}.csv"


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
            usecols=[
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


def debug_character_info(region: str, realm: str, names: list[str]):
    """
    Fetches and prints stored debug information for a list of characters.

    This function is purely for debugging and relies on JSON files
    generated by a prior run of the main script.

    Args:
        region: The region of the characters.
        realm: The realm of the characters.
        names: A list of character names to debug.
    """
    logger.info("--- Starting Character Debug ---")

    for name in names:
        char_path = DATA_PATH / region / realm / name.lower()
        print(f"\n--- Debugging Character: {name.capitalize()} ---")

        if not char_path.exists():
            logger.warning(
                "Data directory for '%s' not found. Run the main script first.", name
            )
            print("--------------------------------------")
            continue

        # 1. Get AP, AQ, and Fingerprint Dates from achievements.json
        achievements_file = char_path / "achievements.json"
        if achievements_file.exists():
            with open(achievements_file, encoding="utf-8") as f:
                ach_data = json.load(f)

            print(f"AP (Achievement Points): {ach_data.get('total_points', 'N/A')}")
            print(
                f"AQ (Achievements Quantity): {ach_data.get('total_quantity', 'N/A')}"
            )

            print("\nFINGERPRINT ACHIEVEMENT DATES:")
            found_fingerprints = False
            for ach in ach_data.get("achievements", []):
                if ach.get("id") in FINGERPRINT_ACHIEVEMENT_IDS:
                    ts = ach.get("completed_timestamp")
                    if ts:
                        # Convert from milliseconds to a readable date
                        date_str = datetime.fromtimestamp(ts / 1000).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        print(
                            f"  - {ach['achievement']['name']} (ID: {ach['id']}): {date_str}"
                        )
                        found_fingerprints = True
            if not found_fingerprints:
                print("  - No fingerprint achievements found.")
        else:
            print(" - Achievements file not found.")

        # 2. Get Mounts Count
        mounts_file = char_path / "mounts.json"
        if mounts_file.exists():
            with open(mounts_file, encoding="utf-8") as f:
                mount_data = json.load(f)
            print(f"\n# Mounts: {len(mount_data.get('mounts', []))}")
        else:
            print("\n# Mounts: File not found.")

        # 3. Get Pets Count
        pets_file = char_path / "pets.json"
        if pets_file.exists():
            with open(pets_file, encoding="utf-8") as f:
                pet_data = json.load(f)
            print(f"# Pets: {len(pet_data.get('pets', []))}")
        else:
            print("# Pets: File not found.")

        print("--------------------------------------")

    logger.info("--- Character Debug Finished ---")


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
    except Exception as e:
        logger.error("Failed to generate summary report: %s", e)
        print(f"\nProcessing completed in {time_diff:.2f} seconds")


def main():
    """Main entry point for the application."""
    start_time = time.time()
    args = parse_arguments()

    setup_logging()
    load_dotenv()

    DATA_PATH.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.mkdir(parents=True, exist_ok=True)

    if args.debug_chars:
        char_names = [name.strip() for name in args.debug_chars.split(",")]
        debug_character_info(args.region, args.realm, char_names)
        exit(0)

    if not args.guild:
        logger.error("Guild name must be provided via --guild argument.")
        exit(1)

    client_id = os.getenv("BLIZZARD_CLIENT_ID")
    client_secret = os.getenv("BLIZZARD_CLIENT_SECRET")

    if not all([client_id, client_secret]):
        logger.error(
            "BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET must be set in .env file."
        )
        exit(1)

    access_token = get_access_token(args.region, client_id, client_secret)  # type: ignore
    if not access_token:
        logger.error("Failed to obtain access token. Exiting.")
        exit(1)

    ranks_map = create_rank_mapping()
    ranks_file = _data_path(args.region, args.realm, args.guild, "ranks")
    if not ranks_file.exists():
        logger.info("Creating ranks file: %s", ranks_file)
        try:
            ranks_data = [rank._asdict() for rank in ranks_map.values()]
            df = pd.DataFrame(ranks_data)
            df.to_csv(ranks_file, index=False, encoding="utf-8")
            logger.info("Successfully created ranks file: %s", ranks_file.resolve())
        except OSError as e:
            logger.error("Failed to write ranks file: %s", e)
    else:
        logger.info("Ranks file already exists: %s", ranks_file)

    class_map = get_static_data_mappings(
        f"https://{args.region}.api.blizzard.com/data/wow/playable-class/index",
        args.region,
        access_token,
        "classes",
        "classes.csv",
    )
    race_map = get_static_data_mappings(
        f"https://{args.region}.api.blizzard.com/data/wow/playable-race/index",
        args.region,
        access_token,
        "races",
        "races.csv",
    )

    if not all([class_map, race_map]):
        logger.error("Failed to get necessary class/race data. Exiting.")
        exit(1)

    roster_data = fetch_guild_roster(
        access_token, args.region, args.realm, args.guild, args.locale
    )
    if not roster_data:
        logger.error("No data fetched from the API. Exiting")
        exit(1)

    roster_hash = calculate_hash(roster_data)
    hash_file = CACHE_PATH / f"{args.region}-{args.realm}-{args.guild}.hash"
    if has_roster_changed(roster_hash, hash_file):
        roster_file = _data_path(args.region, args.realm, args.guild, "roster")
        process_roster_to_csv(roster_data, str(roster_file))
    else:
        logger.info("Roster has not changed since last fetch. Skipping")

    profiles_file = _data_path(args.region, args.realm, args.guild, "profiles")
    process_profiles(args.region, roster_data, str(profiles_file))

    alts_file = _data_path(args.region, args.realm, args.guild, "alts")
    identify_alts(
        access_token,
        args.region,
        roster_data,
        str(alts_file),
        args.locale,
    )

    generate_dashboard(args.region, args.realm, args.guild)

    # Generate summary report
    end_time = time.time()
    time_fiff = end_time - start_time
    summary_report(str(alts_file), time_fiff)


if __name__ == "__main__":
    main()
