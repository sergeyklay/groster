import json
import logging
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


DATA_PATH = Path().cwd() / "data"


def setup_logging():
    """Configure logging for the application."""
    log_path = Path().cwd() / "groster.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(str(log_path))],
    )


def get_access_token(client_id: str, client_secret: str) -> str | None:
    """
    Obtains an OAuth access token using the Client Credentials flow.

    Args:
        client_id: Your Battle.net application client ID.
        client_secret: Your Battle.net application client secret.

    Returns:
        The access token string or None if the request fails.
    """
    url = "https://eu.battle.net/oauth/token"
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
    endpoint_url: str, token: str, data_key: str, cache_filename: str
) -> dict | None:
    """
    Fetches static data (like classes or races) from the API, with local caching.

    Args:
        endpoint_url: The API URL for the static data index.
        token: The OAuth access token.
        data_key: The key in the JSON response that holds the list of items.
        cache_filename: The local file to use for caching the data.

    Returns:
        A dictionary mapping IDs to names, or None on failure.
    """
    cache_path = DATA_PATH / cache_filename
    if cache_path.exists():
        logger.info("Loading %s from local cache: %s", data_key, cache_path)
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)

    logger.info("Fetching %s from API and creating cache.", data_key)
    headers = {"Authorization": f"Bearer {token}"}
    # Note the 'static-eu' namespace for static data
    params = {"namespace": "static-eu", "locale": "en_US"}

    try:
        response = requests.get(endpoint_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        # Transform list of dicts into a {id: name} mapping
        mapping = {str(item["id"]): item["name"] for item in data[data_key]}

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=4)
        logger.info("Successfully cached %s to %s", data_key, cache_path)
        return mapping
    except (OSError, requests.exceptions.RequestException, KeyError) as e:
        logger.error("Failed to fetch or process static data for %s: %s", data_key, e)
        return None


def fetch_guild_roster(api_token: str) -> dict | None:
    """
    Fetches the guild roster from the Battle.net API.

    Args:
        api_token: The OAuth 2.0 bearer token.

    Returns:
        A dictionary with the guild roster data or None if the request fails.
    """
    url = "https://eu.api.blizzard.com/data/wow/guild/terokkar/darq-side-of-the-moon/roster"
    headers = {"Authorization": f"Bearer {api_token}"}

    params = {"namespace": "profile-eu", "locale": "en_US"}

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


def process_roster_to_csv(
    data: dict,
    class_map: dict,
    race_map: dict,
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
        class_id = str(character.get("playable_class", {}).get("id", "N/A"))
        race_id = str(character.get("playable_race", {}).get("id", "N/A"))

        # Note: For class and race, we extract the ID.
        # A future function could resolve these IDs to names via another API call.
        processed_data.append(
            {
                "id": character.get("id"),
                "name": character.get("name"),
                "realm": character.get("realm", {}).get("slug"),
                "level": character.get("level"),
                "playable_class": class_map.get(
                    class_id, f"Unknown Class ({class_id})"
                ),
                "playable_race": race_map.get(race_id, f"Unknown Race ({race_id})"),
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


def main():
    """Main entry point for the application."""
    setup_logging()
    load_dotenv()

    client_id = os.getenv("BLIZZARD_CLIENT_ID")
    client_secret = os.getenv("BLIZZARD_CLIENT_SECRET")

    if not all([client_id, client_secret]):
        logger.error(
            "BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET must be set in .env file."
        )
        exit(1)

    access_token = get_access_token(client_id, client_secret)  # type: ignore
    if not access_token:
        logger.error("Failed to obtain access token. Exiting.")
        exit(1)

    DATA_PATH.mkdir(parents=True, exist_ok=True)

    class_map = get_static_data_mappings(
        "https://eu.api.blizzard.com/data/wow/playable-class/index",
        access_token,
        "classes",
        "classes.json",
    )
    race_map = get_static_data_mappings(
        "https://eu.api.blizzard.com/data/wow/playable-race/index",
        access_token,
        "races",
        "races.json",
    )

    if not all([class_map, race_map]):
        logger.error("Failed to get necessary class/race data. Exiting.")
        exit(1)

    roster_data = fetch_guild_roster(access_token)
    if not roster_data:
        logger.error("No data fetched from the API. Exiting.")
        exit(1)

    # Store intermediate raw data to a JSON file for reference.
    json_file_path = DATA_PATH / "data_raw.json"
    try:
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(roster_data, f, ensure_ascii=False, indent=4)
        logger.info("Successfully saved roster data to data.json")
    except OSError as e:
        logger.error("Failed to write roster data to file: %s", e)

    csv_file = DATA_PATH / "groster.csv"
    process_roster_to_csv(roster_data, class_map, race_map, str(csv_file))


if __name__ == "__main__":
    main()
