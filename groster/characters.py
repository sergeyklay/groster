import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)


def _fetch_character_summary(
    character_info: tuple[str, str, str, str, str], locale: str = "en_US"
) -> dict | None:
    """Fetches the achievement summary for a single character."""
    api_token, region, realm, name, char_id = character_info
    url = f"https://{region}.api.blizzard.com/profile/wow/character/{realm}/{name.lower()}/achievements"
    headers = {"Authorization": f"Bearer {api_token}"}
    params = {"namespace": f"profile-{region}", "locale": locale}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return {
            "id": char_id,
            "name": name,
            "realm": realm,
            "total_points": data.get("total_points", 0),
        }
    except requests.exceptions.RequestException:
        logger.warning("Could not fetch achievement summary for %s.", name)
        return None


def _fetch_level_10_timestamp(
    character_info: tuple[str, str, str, str], locale: str = "en_US"
) -> dict | None:
    """Fetches the full achievement list to find the timestamp for 'Level 10'."""
    api_token, region, realm, name = character_info
    url = f"https://{region}.api.blizzard.com/profile/wow/character/{realm}/{name.lower()}/achievements"
    headers = {"Authorization": f"Bearer {api_token}"}
    params = {"namespace": f"profile-{region}", "locale": locale}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        for achievement in data.get("achievements", []):
            if achievement.get("id") == 6:  # ID for "Level 10"
                return {
                    "name": name,
                    "timestamp": achievement.get("completed_timestamp"),
                }
        return {"name": name, "timestamp": float("inf")}  # Not found, sort last
    except requests.exceptions.RequestException:
        return {"name": name, "timestamp": float("inf")}


def generate_alts_file(
    api_token: str,
    region: str,
    roster_data: dict,
    output_filename: str,
    locale: str = "en_US",
):
    """
    Identifies alts based on shared achievement points and generates a CSV file.
    The "main" is determined by the earliest "Level 10" achievement timestamp.
    """
    members = roster_data.get("members", [])
    if not members:
        return

    logger.info(
        "Fetching achievement summaries for %d members to identify alts.", len(members)
    )
    tasks = [
        (
            api_token,
            region,
            member["character"]["realm"]["slug"],
            member["character"]["name"],
            member["character"]["id"],
        )
        for member in members
    ]

    summaries = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(_fetch_character_summary, tasks)
        summaries = [r for r in results if r]

    # Group characters by total achievement points
    alt_groups = pd.DataFrame(summaries).groupby("total_points")
    main_character_map = {}

    for points, group in alt_groups:
        characters = group.to_dict("records")
        if len(characters) == 1:
            # Single character in this group, they are their own main
            main_character_map[characters[0]["name"]] = characters[0]["name"]
        else:
            # Multiple characters, find the main based on the earliest achievement
            logger.info(
                "Found potential alt group with %d members. Determining main...",
                len(characters),
            )
            group_tasks = [
                (api_token, region, char["realm"], char["name"]) for char in characters
            ]
            timestamps = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                ts_results = executor.map(_fetch_level_10_timestamp, group_tasks)
                timestamps = [ts for ts in ts_results if ts and ts["timestamp"]]

            if not timestamps:
                main_name = characters[0]["name"]  # Fallback if no timestamps found
                logger.warning(
                    "Could not determine main for group with %d points, using first character.",
                    points,
                )
            else:
                main_name = min(timestamps, key=lambda x: x["timestamp"])["name"]

            logger.info("Main for group with %d points is: %s", points, main_name)
            for char in characters:
                main_character_map[char["name"]] = main_name

    # Build the final dataset
    alts_data = []
    for summary in summaries:
        char_name = summary["name"]
        main_name = main_character_map.get(char_name, char_name)
        alts_data.append(
            {
                "id": summary["id"],
                "name": char_name,
                "alt": char_name != main_name,
                "main": main_name,
            }
        )

    try:
        df = pd.DataFrame(alts_data)
        df.to_csv(output_filename, index=False, encoding="utf-8")
        logger.info(
            "Successfully created alts CSV: %s", Path(output_filename).resolve()
        )
    except Exception as e:
        logger.exception("An error occurred during alts processing: %s", e)


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
