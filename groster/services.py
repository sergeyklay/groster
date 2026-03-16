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
    char_id = char_info.get("id")

    if not name or not realm:
        return None

    ach_data = await client.get_character_achievements(realm, name)

    total_quantity = ach_data.get("total_quantity", 0)
    total_points = ach_data.get("total_points", 0)

    if not ach_data.get("achievements"):
        logger.info("No achievements found for %s", name)
        return {
            "id": char_id,
            "name": name,
            "fingerprint": (),
            "timestamps": {},
            "total_quantity": total_quantity,
            "total_points": total_points,
        }

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

    return {
        "id": char_id,
        "name": name,
        "fingerprint": fingerprint,
        "timestamps": timestamps,
        "total_quantity": total_quantity,
        "total_points": total_points,
    }


def _build_member_records(
    members: list[dict[str, Any]],
    profile_data: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build processed roster records from raw member and profile data."""
    processed: list[dict[str, Any]] = []
    for member in members:
        character = member.get("character", {})
        name = character.get("name")
        profile = profile_data.get(name, {})

        if not profile:
            continue

        processed.append(
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
    return processed


async def fetch_roster_details(
    client: BlizzardAPIClient,
    roster_data: dict[str, Any],
    *,
    cached_records: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Fetch detailed profiles for roster members.

    Args:
        client: Blizzard API client for making requests.
        roster_data: Raw roster data containing member list.
        cached_records: Previously saved roster records for unchanged members.
            When provided, only members not in this dict are fetched from the
            API. Their cached records are merged into the result.

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

    if cached_records is not None:
        members_to_fetch = [
            m
            for m in members
            if m.get("character", {}).get("name") not in cached_records
        ]
        logger.info(
            "Incremental roster update: %d members to fetch, "
            "%d cached (skipping API calls)",
            len(members_to_fetch),
            len(cached_records),
        )
    else:
        members_to_fetch = members

    logger.info("Fetching profiles for %d members", len(members_to_fetch))

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
    tasks = [fetch_profile(member) for member in members_to_fetch]
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
    processed_data = _build_member_records(members, profile_data)

    logger.info(
        "Successfully processed details for %d out of %d members.",
        len(processed_data),
        len(members),
    )

    if cached_records:
        processed_data.extend(cached_records.values())

    return processed_data, raw_profiles


_REGION_LOCALE: dict[str, str] = {
    "us": "en-us",
    "eu": "en-gb",
    "kr": "ko-kr",
    "tw": "zh-tw",
    "cn": "zh-cn",
}


def _armory_locale(region: str) -> str:
    """Return the Blizzard Armory locale segment for a region."""
    return _REGION_LOCALE.get(region, "en-us")


def build_profile_links(
    region: str,
    data: dict,
) -> list[dict[str, Any]]:
    """Build external profile links for each guild member.

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
    locale = _armory_locale(region)

    armory_base = "https://worldofwarcraft.blizzard.com"

    for member in members:
        character = member.get("character", {})
        name = character.get("name")
        realm = character.get("realm", {}).get("slug")
        if not name or not realm:
            logger.warning(
                "No name or realm found for member: %s",
                member,
            )
            continue

        fq_name = f"{region}/{realm}/{name.lower()}"
        rio = f"https://raider.io/characters/{fq_name}"
        armory = f"{armory_base}/{locale}/character/{fq_name}"
        logs = f"https://www.warcraftlogs.com/character/{fq_name}"
        links_data.append(
            {
                "id": character.get("id"),
                "name": name,
                "rio_link": rio,
                "armory_link": armory,
                "warcraft_logs_link": logs,
            },
        )

    return links_data


def diff_roster_members(
    current_members: list[dict[str, Any]],
    previous_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Diff current Blizzard roster members against previously saved records.

    A member is considered unchanged if it exists in previous_records with
    the same character id, rank, AND level. Changed or new members require
    fresh API calls; unchanged members can reuse cached data.

    Args:
        current_members: Raw Blizzard API member dicts from get_guild_roster.
        previous_records: Saved roster records from get_roster_details.

    Returns:
        Tuple of:
        - members_to_fetch: list of raw Blizzard member dicts needing
          fresh API calls (new or changed since last run).
        - cached_records: dict mapping character name to the previous
          record for members whose rank and level are unchanged.
    """
    prev_by_id: dict[int, dict[str, Any]] = {rec["id"]: rec for rec in previous_records}
    members_to_fetch: list[dict[str, Any]] = []
    cached_records: dict[str, dict[str, Any]] = {}

    for member in current_members:
        character = member.get("character", {})
        char_id = character.get("id")
        name = character.get("name")
        if not char_id or not name:
            members_to_fetch.append(member)
            continue

        prev = prev_by_id.get(char_id)
        if prev is None:
            members_to_fetch.append(member)
        elif prev["rank"] != member.get("rank") or prev["level"] != character.get(
            "level"
        ):
            members_to_fetch.append(member)
        else:
            cached_records[name] = prev

    return members_to_fetch, cached_records


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


def compute_jaccard_similarity(
    fingerprint_a: set[tuple[int, int]],
    fingerprint_b: set[tuple[int, int]],
) -> float:
    """Compute Jaccard similarity between two achievement fingerprints.

    Returns 0.0 when both sets are empty.
    """
    union_size = len(fingerprint_a | fingerprint_b)
    if union_size == 0:
        return 0.0
    return len(fingerprint_a & fingerprint_b) / union_size


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


def cluster_characters_by_fingerprint(
    characters: list[dict],
    threshold: float = ALT_SIMILARITY_THRESHOLD,
) -> list[list[dict]]:
    """Group characters by fingerprint similarity using greedy clustering.

    Characters with fewer than 3 fingerprint entries are not compared and
    are placed in their own singleton group. Ordering of the input list
    affects grouping results (greedy algorithm).
    """
    groups: list[list[dict]] = []
    unmatched_chars = list(characters)

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

            similarity = compute_jaccard_similarity(base_fp, compare_fp)

            if similarity >= threshold:
                current_group.append(char_to_compare)
            else:
                remaining_chars.append(char_to_compare)

        groups.append(current_group)
        unmatched_chars = remaining_chars

    return groups


def assign_main_characters(
    groups: list[list[dict]],
) -> dict[str, str]:
    """Select the main character in each group and return a name-to-main mapping.

    Delegates per-group main detection to _find_main_in_group().
    """
    main_character_map: dict[str, str] = {}
    for group_list in groups:
        if not group_list:
            continue
        main_name = _find_main_in_group(group_list)
        for char in group_list:
            main_character_map[char["name"]] = main_name
    return main_character_map


def _classify_fetch_results(
    all_results: list,
) -> tuple[
    dict[str, dict],
    dict[str, dict],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
]:
    """Classify raw fetch results into fingerprints, pets, and mounts."""
    pet_summaries: dict[str, dict] = {}
    mount_summaries: dict[str, dict] = {}
    fingerprints_data: dict[str, dict[str, Any]] = {}
    achievements_summaries: list[dict[str, Any]] = []
    all_raw_pets: dict[str, dict[str, Any]] = {}
    all_raw_mounts: dict[str, dict[str, Any]] = {}

    for res in all_results:
        if res is None:
            continue

        if isinstance(res, dict) and "fingerprint" in res:
            fingerprints_data[res["name"]] = res
            achievements_summaries.append(
                {
                    "id": res["id"],
                    "name": res["name"],
                    "total_quantity": res.get("total_quantity", 0),
                    "total_points": res.get("total_points", 0),
                }
            )
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

    return (
        fingerprints_data,
        pet_summaries,
        mount_summaries,
        all_raw_pets,
        all_raw_mounts,
        achievements_summaries,
    )


async def identify_alts(
    client: BlizzardAPIClient,
    roster_data: dict[str, Any],
    *,
    cached_fingerprints: dict[str, dict[str, Any]] | None = None,
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    """Identify alt characters by fingerprinting achievements and collections."""
    members = roster_data.get("members", [])
    if not members:
        return [], {}, {}, [], {}

    if cached_fingerprints is not None:
        members_to_fetch = [
            m
            for m in members
            if m.get("character", {}).get("name") not in cached_fingerprints
        ]
        logger.info(
            "Incremental alt detection: %d members to fingerprint, "
            "%d cached (skipping API calls)",
            len(members_to_fetch),
            len(cached_fingerprints),
        )
    else:
        members_to_fetch = members

    logger.info(
        "Fetching fingerprints for %d members to identify alts",
        len(members_to_fetch),
    )

    # Blizzard caps API requests at 100 per second
    tasks_limit = 50
    all_tasks = []
    for member in members_to_fetch:
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

    (
        fingerprints_data,
        pet_summaries,
        mount_summaries,
        all_raw_pets,
        all_raw_mounts,
        achievements_summaries,
    ) = _classify_fetch_results(all_results)

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

    # Build fingerprint_cache from freshly-fetched entries only
    if cached_fingerprints is not None:
        freshly_fetched_names = {
            m.get("character", {}).get("name") for m in members_to_fetch
        }
        fingerprint_cache = {
            name: data
            for name, data in fingerprints_data.items()
            if name in freshly_fetched_names
        }
        # Merge cached fingerprints into the working data
        for name, cached in cached_fingerprints.items():
            fingerprints_data[name] = cached
            achievements_summaries.append(
                {
                    "id": cached.get("id"),
                    "name": name,
                    "total_quantity": cached.get("total_quantity", 0),
                    "total_points": cached.get("total_points", 0),
                }
            )
    else:
        fingerprint_cache = dict(fingerprints_data)

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
    groups = cluster_characters_by_fingerprint(all_char_data)

    logger.info("Finding main characters in %d groups...", len(groups))
    main_character_map = assign_main_characters(groups)

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

    return (
        alts_data,
        all_raw_pets,
        all_raw_mounts,
        achievements_summaries,
        fingerprint_cache,
    )
