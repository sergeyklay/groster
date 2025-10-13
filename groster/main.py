import argparse
import hashlib
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from groster.ranks import create_rank_mapping

logger = logging.getLogger(__name__)


DATA_PATH = Path().cwd() / "data"
CACHE_PATH = Path().cwd() / "cache"


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
        required=True,
        help="The slug of the guild (e.g., 'darq-side-of-the-moon').",
    )

    parser.add_argument(
        "--locale",
        type=str,
        default="en_US",
        help="The locale for the API request (e.g., 'en_US').",
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


def fetch_character_achievements(
    character_info: tuple[str, str, str, str, str],
    locale: str = "en_US",
) -> dict | None:
    """
    Fetches the achievement summary for a single character.

    Args:
        character_info: A tuple containing (api_token, region, realm, name, id).
        locale: The locale for the API request (e.g., 'en_US')

    Returns:
        A dictionary with processed achievement data or None on failure.
    """
    api_token, region, realm, name, char_id = character_info
    url = f"https://{region}.api.blizzard.com/profile/wow/character/{realm}/{name.lower()}/achievements"
    headers = {"Authorization": f"Bearer {api_token}"}
    params = {"namespace": f"profile-{region}", "locale": locale}

    logger.info("Fetching achievements for character: %s", name)
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        return {
            "id": char_id,
            "name": name,
            "total_quantity": data.get("total_quantity", 0),
            "total_points": data.get("total_points", 0),
        }
    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code in [403, 404]:
            logger.warning(
                "Could not fetch achievements for %s (profile private or not found).",
                name,
            )
        else:
            logger.error("HTTP error for character %s: %s", name, http_err)

        return {
            "id": char_id,
            "name": name,
            "total_quantity": "N/A",
            "total_points": "N/A",
        }
    except requests.exceptions.RequestException as err:
        logger.error("Request failed for character %s: %s", name, err)
        return


def process_achievements(
    api_token: str, region: str, data: dict, output_filename: str, max_workers: int = 50
):
    """
    Concurrently fetches achievement data for all guild members and saves to CSV.
    """
    members = data.get("members", [])
    if not members:
        return

    logger.info(
        "Processing achievements for %d guild members concurrently", len(members)
    )

    tasks = []
    for member in members:
        character = member.get("character", {})
        name = character.get("name")
        realm = character.get("realm", {}).get("slug")
        char_id = character.get("id")
        if name and realm and char_id:
            tasks.append((api_token, region, realm, name, char_id))

    all_achievements = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(fetch_character_achievements, tasks)
        for result in results:
            if result:
                all_achievements.append(result)

    if not all_achievements:
        logger.warning("No achievement data could be fetched for any member.")
        return

    try:
        df = pd.DataFrame(all_achievements)
        cols = ["id", "name"] + [col for col in df.columns if col not in ["id", "name"]]
        df = df[cols]
        df.to_csv(output_filename, index=False, encoding="utf-8")
        logger.info(
            "Successfully created achievements CSV: %s",
            Path(output_filename).resolve(),
        )
    except Exception as e:
        logger.exception("An error occurred during achievements processing: %s", e)


def process_profiles(region: str, data: dict, output_filename: str):
    """Process profile for each character."""
    members = data.get("members", [])
    if not members:
        return

    logger.info("Processing %d guild members for profile links", len(members))
    links_data = []
    for member in members:
        character = member.get("character", {})
        name = character.get("name")
        realm = character.get("realm", {}).get("slug")
        if not name or not realm:
            continue

        links_data.append(
            {
                "id": character.get("id"),
                "name": name,
                "rio_link": f"https://raider.io/characters/{region}/{realm}/{name.lower()}",
                "armory_link": f"https://worldofwarcraft.blizzard.com/en-gb/character/{region}/{realm}/{name.lower()}",
                "warcraft_logs_link": f"https://www.warcraftlogs.com/character/{region}/{realm}/{name.lower()}",
            }
        )

    try:
        df = pd.DataFrame(links_data)
        df.to_csv(output_filename, index=False, encoding="utf-8")
        logger.info(
            "Successfully created links CSV: %s", Path(output_filename).resolve()
        )
    except Exception as e:
        logger.exception("An error occurred during links processing: %s", e)


def calculate_hash(data: dict) -> str:
    """Calculate a SHA256 hash of a dictionary."""
    encoded_data = json.dumps(data, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded_data).hexdigest()


def has_roster_changed(new_hash: str, hash_file: Path) -> bool:
    """Checks for hash changes and updates the hash file."""
    if not hash_file.exists():
        logger.info("No previous roster hash found. Processing data.")
        hash_file.write_text(new_hash)
        return True

    old_hash = hash_file.read_text()
    if old_hash == new_hash:
        logger.info("Roster data has not changed since last run. Skipping.")
        return False

    logger.info("Roster data has changed. Reprocessing and updating hash")
    hash_file.write_text(new_hash)
    return True


def process_roster_to_csv(
    data: dict,
    output_filename: str,
):
    """
    Processes guild roster data from a dictionary and saves it to a CSV file.

    Args:
        data: The dictionary loaded from the API's JSON response.
        output_filename: The name of the CSV file to create.
    """
    # Extract the list of members from the data.
    members = data.get("members", [])
    if not members:
        logger.warning("No members found in roster data. Exiting.")
        return

    logger.info("Processing %d guild members", len(members))

    processed_data = []
    for member in members:
        character = member.get("character", {})

        # Note: For class and race, we extract the ID.
        # A future function could resolve these IDs to names via another API call.
        processed_data.append(
            {
                "id": character.get("id"),
                "name": character.get("name"),
                "realm": character.get("realm", {}).get("slug"),
                "level": character.get("level"),
                "class_id": character.get("playable_class", {}).get("id"),
                "race_id": character.get("playable_race", {}).get("id"),
                "rank": member.get("rank"),
            }
        )

    try:
        df = pd.DataFrame(processed_data)
        df.to_csv(output_filename, index=False, encoding="utf-8")
        logger.info(
            "Successfully created CSV file: %s", Path(output_filename).resolve()
        )
    except OSError as e:
        logger.error("Failed to write CSV file '%s': %s", output_filename, e)
    except Exception as e:
        logger.exception("An error occurred during data processing: %s", e)


def _data_path(region: str, realm: str, guild: str, file: str) -> Path:
    return DATA_PATH / f"{region}-{realm}-{guild}-{file}.csv"


def main():
    """Main entry point for the application."""
    args = parse_arguments()

    setup_logging()
    load_dotenv()

    DATA_PATH.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.mkdir(parents=True, exist_ok=True)

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

    roster_data = fetch_guild_roster(
        access_token, args.region, args.realm, args.guild, args.locale
    )
    if not roster_data:
        logger.error("No data fetched from the API. Exiting")
        exit(1)

    achievements_file = _data_path(args.region, args.realm, args.guild, "achievements")
    process_achievements(access_token, args.region, roster_data, str(achievements_file))

    roster_hash = calculate_hash(roster_data)
    hash_file = CACHE_PATH / f"{args.region}-{args.realm}-{args.guild}.hash"
    if not has_roster_changed(roster_hash, hash_file):
        logger.info("Roster has not changed since last fetch. Exiting")
        return

    roster_file = _data_path(args.region, args.realm, args.guild, "roster")
    process_roster_to_csv(roster_data, str(roster_file))

    profiles_file = _data_path(args.region, args.realm, args.guild, "profiles")
    process_profiles(args.region, roster_data, str(profiles_file))


if __name__ == "__main__":
    main()
