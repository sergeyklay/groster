import asyncio
import logging
from typing import Any

from groster.constants import (
    ALT_SIMILARITY_THRESHOLD,
    FINGERPRINT_ACHIEVEMENT_IDS,
    LEVEL_10_ACHIEVEMENT_ID,
)
from groster.http_client import BlizzardAPIClient
from groster.utils import format_timestamp

logger = logging.getLogger(__name__)


async def fetch_member_fingerprint(
    client: BlizzardAPIClient, member: dict
) -> dict | None:
    """Fetch achievement data and compute a fingerprint for one member.

    A fingerprint is a tuple of (achievement_id, timestamp) pairs used to
    identify alt characters by comparing achievement completion patterns.

    Args:
        client: Blizzard API client for making requests.
        member: Raw member dict from roster data containing character info.

    Returns:
       Dict with 'name', 'fingerprint' (tuple), and 'timestamps' (dict),
       or None if member data is invalid.
    """
    char_info = member.get("character", {})
    name = char_info.get("name")
    realm = char_info.get("realm", {}).get("slug")
    if not name or not realm:
        return None

    ach_data = await client.get_character_achievements(realm, name)
    if not ach_data.get("achievements"):
        logger.warning("No achievements found for %s", name)
        return {"name": name, "fingerprint": (), "timestamps": {}}

    timestamps = {
        ach["id"]: ach.get("completed_timestamp")
        for ach in ach_data["achievements"]
        if ach.get("id") in FINGERPRINT_ACHIEVEMENT_IDS
    }

    # Explicitly add Level 10 achievement for main detection
    level_10_ts = next(
        (
            ach.get("completed_timestamp")
            for ach in ach_data["achievements"]
            if ach.get("id") == LEVEL_10_ACHIEVEMENT_ID
        ),
        None,
    )

    if level_10_ts:
        timestamps[LEVEL_10_ACHIEVEMENT_ID] = level_10_ts

    fingerprint = tuple(
        sorted(
            (k, v) for k, v in timestamps.items() if v and k != LEVEL_10_ACHIEVEMENT_ID
        )
    )

    return {"name": name, "fingerprint": fingerprint, "timestamps": timestamps}


async def fetch_roster_details(
    client: BlizzardAPIClient, roster_data: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Fetch detailed profiles for all roster members.

    Args:
        client: Blizzard API client for making requests.
        roster_data: Raw roster data containing member list.

    Returns:
        Tuple of
        - List of processed member detail dicts with id, name, realm, level,
        class_id, race_id, rank, ilvl, and last_login.
        - Dictionary of profile data by character name.
    """
    members = roster_data.get("members", [])
    if not members:
        logger.warning("No members found in roster data")
        return [], {}

    logger.info("Fetching profiles for %d members", len(members))

    # Blizzard caps API requests at 100 per second
    tasks_limit = 50
    semaphore = asyncio.Semaphore(tasks_limit)
    raw_profiles: dict[str, dict[str, Any]] = {}

    async def fetch_profile(member: dict) -> dict | None:
        """Coroutine to fetch a single character's profile."""
        char_info = member.get("character", {})
        realm = char_info.get("realm", {}).get("slug")
        name = char_info.get("name")

        if not realm or not name:
            logger.warning("No realm or name found for member: %s", member)
            return None

        async with semaphore:
            response = await client.get_character_profile(realm, name)
            await asyncio.sleep(0.01)

        if not response:
            return None

        raw_profiles[name] = response

        return {
            "name": response.get("name"),
            "id": response.get("id"),
            "last_login": response.get("last_login_timestamp"),
            "ilvl": response.get("equipped_item_level"),
        }

    # Split tasks into batches to respect rate limits
    tasks = [fetch_profile(member) for member in members]
    profile_results = []

    for i in range(0, len(tasks), tasks_limit):
        batch = tasks[i : i + tasks_limit]
        batch_results = await asyncio.gather(*batch)
        profile_results.extend(batch_results)

        # Sleep for 1 second between batches to respect rate limits
        if i + tasks_limit < len(tasks):
            await asyncio.sleep(1)

    profile_data = {p["name"]: p for p in profile_results if p}

    logger.info("Processing %d guild members", len(members))
    processed_data = []

    for member in members:
        character = member.get("character", {})
        name = character.get("name")
        profile = profile_data.get(name, {})

        if not profile:
            continue

        processed_data.append(
            {
                "id": character.get("id"),
                "name": name,
                "realm": character.get("realm", {}).get("slug"),
                "level": character.get("level"),
                "class_id": character.get("playable_class", {}).get("id"),
                "race_id": character.get("playable_race", {}).get("id"),
                "rank": member.get("rank"),
                "ilvl": profile.get("ilvl", 0),
                "last_login": format_timestamp(profile.get("last_login")),
            }
        )

    logger.info(
        "Successfully processed details for %d out of %d members.",
        len(processed_data),
        len(members),
    )

    return processed_data, raw_profiles


def build_profile_links(region: str, data: dict) -> list[dict[str, Any]]:
    """Builds external profile links for each guild member.

    Args:
        region: Guild region identifier (e.g., 'eu').
        data: Raw roster data containing the 'members' list.

    Returns:
        List of dictionaries containing profile links for each member.
    """
    members = data.get("members", [])
    if not members:
        return []

    logger.info("Building profile links for %d members", len(members))
    links_data = []

    for member in members:
        character = member.get("character", {})
        name = character.get("name")
        realm = character.get("realm", {}).get("slug")
        if not name or not realm:
            logger.warning("No name or realm found for member: %s", member)
            continue

        fq_name = f"{region}/{realm}/{name.lower()}"
        links_data.append(
            {
                "id": character.get("id"),
                "name": name,
                "rio_link": f"https://raider.io/characters/{fq_name}",
                "armory_link": f"https://worldofwarcraft.blizzard.com/en-gb/character/{fq_name}",
                "warcraft_logs_link": f"https://www.warcraftlogs.com/character/{fq_name}",
            }
        )

    return links_data


async def fetch_playable_classes(client: BlizzardAPIClient) -> list[dict[str, Any]]:
    """Fetch playable classes from the Blizzard API.

    Args:
        client: Blizzard API client for making requests.

    Returns:
        List of dictionaries containing class data, e.g.,
            [{"id": 1, "name": "Warrior"}, ...]
    """
    logger.debug("Requesting playable classes from API")
    classes_list = await client.get_playable_classes()
    return [{"id": c["id"], "name": c["name"]} for c in classes_list]


async def fetch_playable_races(client: BlizzardAPIClient) -> list[dict[str, Any]]:
    """Fetch playable races from the Blizzard API.

    Args:
        client: Blizzard API client for making requests.

    Returns:
        List of dictionaries containing race data, e.g.,
            [{"id": 1, "name": "Human"}, ...]
    """
    logger.debug("Requesting playable races from API")
    races_list = await client.get_playable_races()
    return [{"id": r["id"], "name": r["name"]} for r in races_list]


async def fetch_member_pets_summary(
    client: BlizzardAPIClient, member: dict
) -> tuple[dict | None, dict | None]:
    """Fetch pet collection summary for one member.

    Args:
        client: Blizzard API client for fetching pet data.
        member: Raw member dict from roster data containing character info.

    Returns:
        Tuple of
        - pet summary dict
        - raw pet data dict
        or (None, None) if member data is invalid.
    """
    char_info = member.get("character", {})
    name = char_info.get("name")
    realm = char_info.get("realm", {}).get("slug")
    char_id = char_info.get("id")
    if not all([name, realm, char_id]):
        return None, None

    data = await client.get_character_pets(realm, name)
    summary = {
        "id": char_id,
        "name": name,
        "realm": realm,
        "pets": len(data.get("pets", [])),
    }

    return summary, data


async def fetch_member_mounts_summary(
    client: BlizzardAPIClient, member: dict
) -> tuple[dict | None, dict | None]:
    """Fetch mount collection summary for one member.

    Args:
        client: Blizzard API client for fetching mount data.
        member: Raw member dict from roster data containing character info.

    Returns:
        Tuple of
        - mount summary dict
        - raw mount data dict
        or (None, None) if member data is invalid.
    """
    char_info = member.get("character", {})
    name = char_info.get("name")
    realm = char_info.get("realm", {}).get("slug")
    char_id = char_info.get("id")
    if not all([name, realm, char_id]):
        return None, None

    data = await client.get_character_mounts(realm, name)

    summary = {
        "id": char_id,
        "name": name,
        "realm": realm,
        "mounts": len(data.get("mounts", [])),
    }

    return summary, data


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


async def identify_alts(  # noqa: C901
    client: BlizzardAPIClient,
    roster_data: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    """Identify alt characters by fingerprinting achievements and collections."""
    members = roster_data.get("members", [])
    if not members:
        return [], {}, {}

    logger.info("Fetching fingerprints for %d members to identify alts", len(members))

    # Blizzard caps API requests at 100 per second
    tasks_limit = 50
    all_tasks = []
    for member in members:
        all_tasks.append(fetch_member_fingerprint(client, member))
        all_tasks.append(fetch_member_pets_summary(client, member))
        all_tasks.append(fetch_member_mounts_summary(client, member))

    all_results = []
    for i in range(0, len(all_tasks), tasks_limit):
        batch = all_tasks[i : i + tasks_limit]
        batch_results = await asyncio.gather(*batch)
        all_results.extend(batch_results)

        if i + tasks_limit < len(all_tasks):
            await asyncio.sleep(1)

    pet_summaries = {}
    mount_summaries = {}
    fingerprints_data = {}

    all_raw_pets: dict[str, dict[str, Any]] = {}
    all_raw_mounts: dict[str, dict[str, Any]] = {}

    for res in all_results:
        if res is None:
            continue

        if isinstance(res, dict) and "fingerprint" in res:
            fingerprints_data[res["name"]] = res
            continue

        if isinstance(res, tuple) and len(res) == 2:
            summary, raw_data = res
            if summary is None or raw_data is None:
                continue

            name = summary["name"]
            if "pets" in summary:
                pet_summaries[name] = summary
                all_raw_pets[name] = raw_data
            elif "mounts" in summary:
                mount_summaries[name] = summary
                all_raw_mounts[name] = raw_data

    logger.info(
        "Found %d pet summaries for %d characters", len(pet_summaries), len(members)
    )
    logger.info(
        "Found %d mount summaries for %d characters", len(mount_summaries), len(members)
    )
    logger.info(
        "Found %d fingerprints data for %d characters",
        len(fingerprints_data),
        len(members),
    )

    logger.info("Building character data for grouping")

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
                "fingerprint": fingerprints_data.get(name, {}).get("fingerprint", ()),
                "timestamps": fingerprints_data.get(name, {}).get("timestamps", {}),
            }
        )

    # Group characters by clustering based on fingerprints and stats
    logger.info("Grouping %d characters...", len(all_char_data))
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

    logger.info("Finding main characters in %d groups...", len(groups))

    main_character_map = {}
    for group_list in groups:
        if not group_list:
            continue
        main_name = _find_main_in_group(group_list)
        for char in group_list:
            main_character_map[char["name"]] = main_name

    logger.info("Creating alts data for %d characters...", len(all_char_data))

    alts_data = [
        {
            "id": char["id"],
            "name": (char_name := char["name"]),
            "alt": char_name != main_character_map.get(char_name, char_name),
            "main": main_character_map.get(char_name, char_name),
        }
        for char in all_char_data
    ]

    return alts_data, all_raw_pets, all_raw_mounts
