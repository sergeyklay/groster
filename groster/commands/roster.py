import logging
import os
import time
from typing import Any

from groster.constants import resolve_data_path
from groster.http_client import BlizzardAPIClient, BlizzardAPIError
from groster.ranks import create_rank_mapping
from groster.repository import CsvRosterRepository, RosterRepository
from groster.services import (
    build_profile_links,
    diff_roster_members,
    fetch_playable_classes,
    fetch_playable_races,
    fetch_roster_details,
    identify_alts,
)

logger = logging.getLogger(__name__)


async def summary_report(
    repo: RosterRepository,
    region: str,
    realm: str,
    guild: str,
    time_diff: float,
) -> None:
    """Log a summary of the roster processing run."""
    result = await repo.get_alt_summary(region, realm, guild)

    logger.info("Processing completed in %.2f seconds", time_diff)
    if result is not None:
        total_alts, total_mains = result
        logger.info("Alts found: %s", total_alts)
        logger.info("Main characters: %s", total_mains)


async def _get_guild_ranks(
    repo: RosterRepository, region: str, realm: str, guild: str
) -> dict[int, str]:
    """Get guild ranks from the repository or API."""
    ranks_map = await repo.get_guild_ranks(region, realm, guild)
    if ranks_map:
        return ranks_map

    logger.info("No guild ranks found, fetching from API and saving to repository")
    default_ranks_mapping = create_rank_mapping()
    ranks_data_list = [rank._asdict() for rank in default_ranks_mapping.values()]
    if not ranks_data_list:
        raise RuntimeError("Failed to get guild ranks from default mapping")

    await repo.save_guild_ranks(ranks_data_list, region, realm, guild)
    return {rank.id: rank.name for rank in default_ranks_mapping.values()}


async def _get_playable_classes(
    repo: RosterRepository, client: BlizzardAPIClient
) -> dict[int, str]:
    """Get playable classes from the repository or API."""
    class_map = await repo.get_playable_classes()
    if class_map:
        return class_map

    logger.info("No playable classes found, fetching from API and saving to repository")
    classes_data = await fetch_playable_classes(client)
    if not classes_data:
        raise RuntimeError("Failed to fetch playable classes from API")

    await repo.save_playable_classes(classes_data)
    return {c["id"]: c["name"] for c in classes_data}


async def _get_playable_races(
    repo: RosterRepository, client: BlizzardAPIClient
) -> dict[int, str]:
    """Get playable races from the repository or API."""
    race_map = await repo.get_playable_races()
    if race_map:
        return race_map

    logger.info("No playable races found, fetching from API and saving to repository")
    races_data = await fetch_playable_races(client)
    if not races_data:
        raise RuntimeError("Failed to fetch playable races from API")

    await repo.save_playable_races(races_data)
    return {r["id"]: r["name"] for r in races_data}


async def _get_roster_details(
    repo: RosterRepository,
    client: BlizzardAPIClient,
    region: str,
    realm: str,
    guild: str,
    *,
    force: bool = False,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Get roster details, returning (roster_data, cached_profile_records).

    cached_profile_records is empty when force=True or on first run.
    """
    try:
        roster_data: dict[str, Any] = await client.get_guild_roster(realm, guild)
    except BlizzardAPIError as exc:
        raise RuntimeError("Failed to get guild roster data.") from exc

    cached_profile_records: dict[str, dict[str, Any]] = {}
    if not force:
        prev = await repo.get_roster_details(region, realm, guild)
        if prev is not None:
            _, cached_profile_records = diff_roster_members(
                roster_data.get("members", []), prev
            )

    logger.info("Processing roster details for all members")

    details_data, raw_profiles = await fetch_roster_details(
        client,
        roster_data,
    )
    if details_data:
        await repo.save_roster_details(details_data, region, realm, guild)
    else:
        logger.warning("No roster details data found. Skipping roster file creation")

    if raw_profiles:
        logger.info("Saving raw profile data for %d characters", len(raw_profiles))
        for name, profile_json in raw_profiles.items():
            await repo.save_character_profile(profile_json, region, realm, name)

    return roster_data, cached_profile_records


async def update_roster(
    region: str,
    realm: str,
    guild: str,
    locale: str,
    *,
    force: bool = False,
) -> None:
    """Main entry point for the application."""
    start_time = time.time()
    base_path = resolve_data_path()

    client_id = os.getenv("BLIZZARD_CLIENT_ID")
    client_secret = os.getenv("BLIZZARD_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing BLIZZARD_CLIENT_ID/BLIZZARD_CLIENT_SECRET in environment"
        )

    client = BlizzardAPIClient(
        region=region,
        client_id=client_id,
        client_secret=client_secret,
        locale=locale,
    )

    repo = CsvRosterRepository(base_path=base_path)

    try:
        await _get_guild_ranks(repo, region, realm, guild)
        await _get_playable_classes(repo, client)
        await _get_playable_races(repo, client)

        roster_data, cached_profile_records = await _get_roster_details(
            repo, client, region, realm, guild, force=force
        )

        logger.info("Building profile links")
        links_data = build_profile_links(region, roster_data)
        await repo.save_profile_links(links_data, region, realm, guild)

        unchanged_names = list(cached_profile_records)
        if unchanged_names and not force:
            cached_fingerprints = await repo.get_member_fingerprints(
                region, realm, unchanged_names
            )
        else:
            cached_fingerprints = {}

        # Load cached fingerprints for ALL members (fallback for hidden profiles)
        all_member_names = [
            m.get("character", {}).get("name")
            for m in roster_data.get("members", [])
            if m.get("character", {}).get("name")
        ]
        all_cached_fingerprints = await repo.get_member_fingerprints(
            region, realm, all_member_names
        )
        logger.info(
            "Loaded cached fingerprints for %d members",
            len(all_cached_fingerprints),
        )

        (
            alts_data,
            all_raw_pets,
            all_raw_mounts,
            achievements_summaries,
            new_fp_cache,
        ) = await identify_alts(
            client,
            roster_data,
            cached_fingerprints=cached_fingerprints or None,
            all_cached_fingerprints=all_cached_fingerprints or None,
        )

        if not alts_data:
            raise RuntimeError("Failed to identify alts")

        await repo.save_alts_data(alts_data, region, realm, guild)

        if achievements_summaries:
            logger.info(
                "Saving achievement summaries for %d characters",
                len(achievements_summaries),
            )
            await repo.save_achievements_summary(
                achievements_summaries, region, realm, guild
            )
        else:
            logger.warning(
                "No achievement summaries found. "
                "Skipping achievement summary file creation"
            )

        if new_fp_cache:
            logger.info("Caching fingerprint data for %d characters", len(new_fp_cache))
            for name, fp_data in new_fp_cache.items():
                await repo.save_character_achievements(fp_data, region, realm, name)

        logger.info("Saving raw pets data for %d characters", len(all_raw_pets))
        for name, pets_json in all_raw_pets.items():
            await repo.save_character_pets(pets_json, region, realm, name)

        logger.info("Saving raw mounts data for %d characters", len(all_raw_mounts))
        for name, mounts_json in all_raw_mounts.items():
            await repo.save_character_mounts(mounts_json, region, realm, name)

        await repo.build_dashboard(region, realm, guild)

        end_time = time.time()
        time_diff = end_time - start_time

        await summary_report(repo, region, realm, guild, time_diff)
    finally:
        await client.close()
