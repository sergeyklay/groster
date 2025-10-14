import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from groster.constants import (
    ALT_SIMILARITY_THRESHOLD,
    DATA_PATH,
    FINGERPRINT_ACHIEVEMENT_IDS,
    LEVEL_10_ACHIEVEMENT_ID,
)

logger = logging.getLogger(__name__)


def _fetch_pets_summary(
    character_info: tuple[str, str, str, str, str, str],
) -> dict | None:
    """Fetches pet collection summary and saves the raw JSON."""
    api_token, region, realm, name, char_id, locale = character_info
    url = f"https://{region}.api.blizzard.com/profile/wow/character/{realm}/{name.lower()}/collections/pets"
    headers = {"Authorization": f"Bearer {api_token}"}
    params = {"namespace": f"profile-{region}", "locale": locale}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        char_path = DATA_PATH / region / realm / name.lower()
        char_path.mkdir(parents=True, exist_ok=True)
        with open(char_path / "pets.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return {
            "id": char_id,
            "name": name,
            "realm": realm,
            "pets": len(data.get("pets", [])),
        }
    except requests.exceptions.RequestException as e:
        logger.warning(
            "Could not fetch pet summary for %s: %s",
            name,
            e.response.text if e.response else str(e),
        )
        return {"id": char_id, "name": name, "pets": 0}


def _fetch_mounts_summary(
    character_info: tuple[str, str, str, str, str, str],
) -> dict | None:
    """Fetches mount collection summary and saves the raw JSON."""
    api_token, region, realm, name, char_id, locale = character_info
    url = f"https://{region}.api.blizzard.com/profile/wow/character/{realm}/{name.lower()}/collections/mounts"
    headers = {"Authorization": f"Bearer {api_token}"}
    params = {"namespace": f"profile-{region}", "locale": locale}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        char_path = DATA_PATH / region / realm / name.lower()
        char_path.mkdir(parents=True, exist_ok=True)
        with open(char_path / "mounts.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return {
            "id": char_id,
            "name": name,
            "realm": realm,
            "mounts": len(data.get("mounts", [])),
        }
    except requests.exceptions.RequestException as e:
        logger.warning(
            "Could not fetch mounts summary for %s: %s",
            name,
            e.response.text if e.response else str(e),
        )
        return {"id": char_id, "name": name, "mounts": 0}


def _fetch_achievement_fingerprint(
    character_info: tuple[str, str, str, str, str],
) -> dict | None:
    """Creates a unique fingerprint from key achievement timestamps."""
    api_token, region, realm, name, locale = character_info
    url = f"https://{region}.api.blizzard.com/profile/wow/character/{realm}/{name.lower()}/achievements"
    headers = {"Authorization": f"Bearer {api_token}"}
    params = {"namespace": f"profile-{region}", "locale": locale}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        char_path = DATA_PATH / region / realm / name.lower()
        char_path.mkdir(parents=True, exist_ok=True)
        with open(char_path / "achievements.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        timestamps = {
            ach["id"]: ach.get("completed_timestamp")
            for ach in data.get("achievements", [])
            if ach.get("id") in FINGERPRINT_ACHIEVEMENT_IDS
        }
        # Explicitly add Level 10 achievement for main detection
        level_10_ts = next(
            (
                ach.get("completed_timestamp")
                for ach in data.get("achievements", [])
                if ach.get("id") == LEVEL_10_ACHIEVEMENT_ID
            ),
            None,
        )
        if level_10_ts:
            timestamps[LEVEL_10_ACHIEVEMENT_ID] = level_10_ts

        fingerprint = tuple(
            sorted(
                (k, v)
                for k, v in timestamps.items()
                if v and k != LEVEL_10_ACHIEVEMENT_ID
            )
        )
        return {"name": name, "fingerprint": fingerprint, "timestamps": timestamps}
    except requests.exceptions.RequestException as e:
        logger.warning(
            "Could not fetch full achievements for %s: %s",
            name,
            e.response.text if e.response else str(e),
        )
        return None


def _find_main_in_group(group: list[dict]) -> str:
    """Determines the main character by the earliest 'Level 10' timestamp."""
    earliest_char = None
    min_timestamp = float("inf")

    for char in group:
        timestamp = char.get("timestamps", {}).get(LEVEL_10_ACHIEVEMENT_ID)
        if timestamp is not None and timestamp < min_timestamp:
            min_timestamp = timestamp
            earliest_char = char["name"]
    return earliest_char or group[0]["name"]


def identify_alts(
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

    logger.info("Fetching summaries for %d members for initial grouping", len(members))

    summary_tasks = [
        (
            api_token,
            region,
            member["character"]["realm"]["slug"],
            member["character"]["name"],
            member["character"]["id"],
            locale,
        )
        for member in members
    ]
    fingerprint_tasks = [
        (
            api_token,
            region,
            member["character"]["realm"]["slug"],
            member["character"]["name"],
            locale,
        )
        for member in members
    ]

    with ThreadPoolExecutor(max_workers=50) as executor:
        pet_summaries = {
            r["name"]: r for r in executor.map(_fetch_pets_summary, summary_tasks) if r
        }
        mount_summaries = {
            r["name"]: r
            for r in executor.map(_fetch_mounts_summary, summary_tasks)
            if r
        }
        fingerprints_data = {
            r["name"]: r
            for r in executor.map(_fetch_achievement_fingerprint, fingerprint_tasks)
            if r
        }

    all_char_data = []
    for member in members:
        char_info = member.get("character", {})
        name = char_info.get("name")
        if not name:
            continue

        all_char_data.append(
            {
                "id": char_info.get("id"),
                "name": name,
                "realm": char_info.get("realm", {}).get("slug"),
                "pets": pet_summaries.get(name, {}).get("pets", 0),
                "mounts": mount_summaries.get(name, {}).get("mounts", 0),
                "fingerprint": fingerprints_data.get(name, {}).get(
                    "fingerprint", tuple()
                ),
                "timestamps": fingerprints_data.get(name, {}).get("timestamps", {}),
            }
        )

    # Group characters by clustering based on fingerprints and stats
    groups = []
    unmatched_chars = list(all_char_data)

    while unmatched_chars:
        base_char = unmatched_chars.pop(0)
        base_fp = set(base_char["fingerprint"])

        current_group = [base_char]
        remaining_chars = []

        for char_to_compare in unmatched_chars:
            compare_fp = set(char_to_compare["fingerprint"])

            # Skip comparison if either fingerprint is too small to be reliable
            if len(base_fp) < 3 or len(compare_fp) < 3:
                remaining_chars.append(char_to_compare)
                continue

            # Calculate Jaccard Similarity
            intersection_size = len(base_fp.intersection(compare_fp))
            union_size = len(base_fp.union(compare_fp))

            # Avoid division by zero, though union_size should be > 0 here
            if union_size == 0:
                similarity = 1.0
            else:
                similarity = intersection_size / union_size

            # If similarity is high, group them
            if similarity >= ALT_SIMILARITY_THRESHOLD:
                current_group.append(char_to_compare)
            else:
                remaining_chars.append(char_to_compare)

        groups.append(current_group)
        unmatched_chars = remaining_chars

    main_character_map = {}
    for group_list in groups:
        if not group_list:
            continue
        main_name = _find_main_in_group(group_list)
        for char in group_list:
            main_character_map[char["name"]] = main_name

    alts_data = [
        {
            "id": char["id"],
            "name": (char_name := char["name"]),
            "alt": char_name != main_character_map.get(char_name, char_name),
            "main": main_character_map.get(char_name, char_name),
        }
        for char in all_char_data
    ]

    try:
        df_alts = pd.DataFrame(alts_data).sort_values(by=["main", "name"])
        df_alts.to_csv(output_filename, index=False, encoding="utf-8")
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
