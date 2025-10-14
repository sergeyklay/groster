import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from groster.constants import (
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

    logger.info(
        "Layer 1: Fetching summaries for %d members for initial grouping",
        len(members),
    )
    tasks = [
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

    with ThreadPoolExecutor(max_workers=50) as executor:
        pet_summaries = {
            r["name"]: r for r in executor.map(_fetch_pets_summary, tasks) if r
        }
        mount_summaries = {
            r["name"]: r for r in executor.map(_fetch_mounts_summary, tasks) if r
        }

    summaries = []
    for member in members:
        char_info = member.get("character", {})
        name = char_info.get("name")
        if not name:
            logger.warning("Skipping member with missing name: %s", char_info)
            continue

        pet_data = pet_summaries.get(name, {})
        mount_data = mount_summaries.get(name, {})

        char_id = char_info.get("id")
        realm = char_info.get("realm", {}).get("slug")
        if not (char_id and realm):
            logger.warning("Skipping member with incomplete data: %s", name)
            continue

        summaries.append(
            {
                "id": char_id,
                "name": name,
                "realm": realm,
                "pets": pet_data.get("pets", 0),
                "mounts": mount_data.get("mounts", 0),
            }
        )

    df_summaries = pd.DataFrame(summaries)
    grouped_by_stats = df_summaries.groupby(["mounts", "pets"])

    final_alt_groups = []
    unidentified_chars = []

    for _, group in grouped_by_stats:
        group_list = group.to_dict("records")
        if len(group_list) > 1:
            final_alt_groups.append(group_list)
        else:
            unidentified_chars.append(group_list[0])

    if unidentified_chars:
        logger.info(
            "Layer 2: Fetching fingerprints for %d unidentified characters",
            len(unidentified_chars),
        )

        fingerprint_tasks = [
            (api_token, region, char["realm"], char["name"], locale)
            for char in unidentified_chars
        ]
        with ThreadPoolExecutor(max_workers=20) as executor:
            fingerprints_data = [
                r
                for r in executor.map(_fetch_achievement_fingerprint, fingerprint_tasks)
                if r
            ]

        # Combine summaries with fingerprint data
        for fp_data in fingerprints_data:
            summary_data = next(
                (c for c in unidentified_chars if c["name"] == fp_data["name"]), None
            )
            if summary_data:
                fp_data.update(summary_data)

        if fingerprints_data:
            df_fingerprints = pd.DataFrame(fingerprints_data)
            df_fingerprints["fingerprint_str"] = df_fingerprints["fingerprint"].astype(
                str
            )

            for fp_str, group in df_fingerprints[
                df_fingerprints["fingerprint_str"] != "()"
            ].groupby("fingerprint_str"):
                if len(group) > 1 and len(group.iloc[0]["fingerprint"]) >= 3:
                    final_alt_groups.append(group.to_dict("records"))
                else:  # Add singles back to be processed individually
                    for char_dict in group.to_dict("records"):
                        final_alt_groups.append([char_dict])

    main_character_map = {}
    processed_chars = set()

    for group in final_alt_groups:
        main_name = _find_main_in_group(group)
        for char in group:
            main_character_map[char["name"]] = main_name
            processed_chars.add(char["name"])

    for summary in summaries:
        if summary["name"] not in processed_chars:
            main_character_map[summary["name"]] = summary["name"]

    alts_data = [
        {
            "id": summary["id"],
            "name": (char_name := summary["name"]),
            "alt": char_name != main_character_map.get(char_name, char_name),
            "main": main_character_map.get(char_name, char_name),
        }
        for summary in summaries
    ]

    try:
        df = pd.DataFrame(alts_data).sort_values(by=["main", "name"])
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
