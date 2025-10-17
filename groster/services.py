import asyncio
import json
import logging
from typing import Any

import pandas as pd

from groster.constants import (
    ALT_SIMILARITY_THRESHOLD,
    DATA_PATH,
    FINGERPRINT_ACHIEVEMENT_IDS,
    LEVEL_10_ACHIEVEMENT_ID,
)
from groster.http_client import BlizzardAPIClient
from groster.ranks import create_rank_mapping
from groster.utils import data_path, format_timestamp

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
) -> list[dict[str, Any]]:
    """Fetch detailed profiles for all roster members.

    Args:
        client: Blizzard API client for making requests.
        roster_data: Raw roster data containing member list.

    Returns:
        List of processed member detail dicts with id, name, realm, level,
        class_id, race_id, rank, ilvl, and last_login.
    """
    members = roster_data.get("members", [])
    if not members:
        return []

    logger.info("Fetching profiles for %d members...", len(members))

    # Blizzard caps API requests at 100 per second
    tasks_limit = 90
    semaphore = asyncio.Semaphore(tasks_limit)

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

        char_path = DATA_PATH / client.region / realm / name.lower()
        try:
            char_path.mkdir(parents=True, exist_ok=True)
            with open(char_path / "profile.json", "w", encoding="utf-8") as f:
                json.dump(response, f, ensure_ascii=False, indent=4)
        except OSError:
            logger.warning("Failed to write intermediate profile data for %s", name)
            # we still can continue with the rest of the processing

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

    return processed_data


def create_profile_links(region: str, realm: str, guild: str, data: dict):
    """Create CSV with external profile links for each guild member.

    Generates links to Raider.IO, Armory, and Warcraft Logs for all members
    and writes them to a CSV file.

    Args:
        region: Region code (e.g., 'us', 'eu').
        realm: Realm slug.
        guild: Guild slug.
        data: Raw roster data dict containing members list.
    """
    links_file = data_path(region, realm, guild, "links")
    links_file.parent.mkdir(parents=True, exist_ok=True)

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
            logger.warning("No name or realm found for member: %s", member)
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
        df.to_csv(links_file, index=False, encoding="utf-8")
        logger.info("Successfully created profile links file: %s", links_file.resolve())
    except OSError:
        logger.warning("Failed to write profile links file")


async def get_guild_ranks(region: str, realm: str, guild: str) -> dict:
    """Get guild rank mappings from CSV or create default ranks.

    Creates a ranks CSV file with default WoW guild ranks if it doesn't exist,
    otherwise reads the existing file.

    Args:
        region: Region code for path construction.
        realm: Realm slug for path construction.
        guild: Guild slug for path construction.

    Returns:
        Dict mapping rank IDs (int) to rank names (str).
    """
    ranks_file = data_path(region, realm, guild, "ranks")
    ranks_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        if not ranks_file.exists():
            logger.info("Creating ranks file: %s", ranks_file)
            ranks_mapping = create_rank_mapping()
            ranks_data = [rank._asdict() for rank in ranks_mapping.values()]
            df = pd.DataFrame(ranks_data)
            df.to_csv(ranks_file, index=False, encoding="utf-8")
            logger.info("Successfully created ranks file: %s", ranks_file.resolve())
        else:
            logger.info("Ranks file already exists: %s", ranks_file)
            df = pd.read_csv(ranks_file)
    except OSError as e:
        logger.exception("Failed to process ranks data file for %s guild", guild)
        raise RuntimeError("Failed to process ranks data file") from e

    return pd.Series(df["name"].values, index=df["id"].astype(int)).to_dict()


async def get_playable_classes(client: BlizzardAPIClient) -> dict:
    """Get playable classes from the API."""
    classes_file = data_path("classes")
    classes_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        if not classes_file.exists():
            logger.info("Creating classes file: %s", classes_file)
            classes_list = await client.get_playable_classes()
            classes = [{"id": c["id"], "name": c["name"]} for c in classes_list]
            df = pd.DataFrame(classes)
            df.to_csv(classes_file, index=False, encoding="utf-8")
            logger.info("Successfully created classes file: %s", classes_file.resolve())
        else:
            logger.info("Classes file already exists: %s", classes_file)
            df = pd.read_csv(classes_file)
    except OSError as e:
        logger.exception("Failed to process classes datafile")
        raise RuntimeError("Failed to process classes data file") from e

    return pd.Series(df["name"].values, index=df["id"].astype(int)).to_dict()


async def get_playable_races(client: BlizzardAPIClient) -> dict:
    """Fetch playable race mappings from API or cached CSV.

    Retrieves all playable races from the Blizzard API on first call and
    caches to CSV. Subsequent calls read from the cached file.

    Args:
        client: Blizzard API client for fetching race data.

    Returns:
        Dict mapping race IDs (int) to race names (str).
    """
    races_file = data_path("races")
    races_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        if not races_file.exists():
            logger.info("Creating races file: %s", races_file)
            races_list = await client.get_playable_races()
            races = [{"id": r["id"], "name": r["name"]} for r in races_list]
            df = pd.DataFrame(races)
            df.to_csv(races_file, index=False, encoding="utf-8")
            logger.info("Successfully created races file: %s", races_file.resolve())
        else:
            logger.info("Races file already exists: %s", races_file)
            df = pd.read_csv(races_file)
    except OSError as e:
        logger.exception("Failed to process races data file")
        raise RuntimeError("Failed to process races data file") from e

    return pd.Series(df["name"].values, index=df["id"].astype(int)).to_dict()


async def fetch_member_pets_summary(
    client: BlizzardAPIClient, member: dict
) -> dict | None:
    """Fetch pet collection summary for one member.

    Retrieves pet collection summary for one member from the Blizzard API
    and caches to JSON file. Subsequent calls read from the cached file.

    Args:
        client: Blizzard API client for fetching pet data.
        member: Raw member dict from roster data containing character info.

    Returns:
        Dict with 'id', 'name', 'realm', and 'pets' (int), or None if member data
        is invalid.
    """
    char_info = member.get("character", {})
    name = char_info.get("name")
    realm = char_info.get("realm", {}).get("slug")
    char_id = char_info.get("id")
    if not all([name, realm, char_id]):
        return None

    data = await client.get_character_pets(realm, name)

    char_path = DATA_PATH / client.region / realm / name.lower()
    try:
        char_path.mkdir(parents=True, exist_ok=True)
        with open(char_path / "pets.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except OSError:
        logger.warning("Failed to process pet data file for %s", name)
        # we still can continue with the rest of the processing

    return {
        "id": char_id,
        "name": name,
        "realm": realm,
        "pets": len(data.get("pets", [])),
    }


async def fetch_member_mounts_summary(
    client: BlizzardAPIClient, member: dict
) -> dict | None:
    """Fetch mount collection summary for one member.

    Retrieves mount collection summary for one member from the Blizzard API
    and caches to JSON file. Subsequent calls read from the cached file.

    Args:
        client: Blizzard API client for fetching mount data.
        member: Raw member dict from roster data containing character info.

    Returns:
        Dict with 'id', 'name', 'realm', and 'mounts' (int), or None if member data
        is invalid.
    """
    char_info = member.get("character", {})
    name = char_info.get("name")
    realm = char_info.get("realm", {}).get("slug")
    char_id = char_info.get("id")
    if not all([name, realm, char_id]):
        return None

    data = await client.get_character_mounts(realm, name)

    char_path = DATA_PATH / client.region / realm / name.lower()
    try:
        char_path.mkdir(parents=True, exist_ok=True)
        with open(char_path / "mounts.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except OSError:
        logger.warning("Failed to write mount data file for %s", name)
        # we still can continue with the rest of the processing

    return {
        "id": char_id,
        "name": name,
        "realm": realm,
        "mounts": len(data.get("mounts", [])),
    }


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


async def identify_alts(
    client: BlizzardAPIClient,
    region: str,
    realm: str,
    guild: str,
    roster_data: dict[str, Any],
):
    """Identify alt characters by fingerprinting achievements and collections.

    Fetches achievements, pets, and mounts for all members, then clusters
    characters by Jaccard similarity of achievement fingerprints. Groups
    are assigned a main based on earliest Level 10 achievement.

    Args:
        client: Blizzard API client.
        region: Region code.
        realm: Realm slug.
        guild: Guild slug.
        roster_data: Raw roster data with members list.

    Returns:
        Tuple of (alts_data list, alts_file path) or (empty list, None) if no members.
    """
    members = roster_data.get("members", [])
    if not members:
        return [], None

    logger.info("Fetching fingerprints for %d members to identify alts", len(members))

    tasks_limit = 90
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

    for res in all_results:
        if res is None:
            continue

        name = res["name"]
        if "pets" in res:
            pet_summaries[name] = res
        elif "mounts" in res:
            mount_summaries[name] = res
        elif "fingerprint" in res:
            fingerprints_data[name] = res

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

    alts_file = data_path(region, realm, guild, "alts")
    try:
        df_alts = pd.DataFrame(alts_data).sort_values(by=["main", "name"])
        df_alts.to_csv(alts_file, index=False, encoding="utf-8")
        logger.info("Successfully created alts CSV: %s", alts_file.resolve())
        return alts_data, alts_file
    except OSError as e:
        logger.exception("Failed to write alts file")
        raise RuntimeError("Failed to write alts file") from e
