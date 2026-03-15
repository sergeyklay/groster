import logging

import pytest

from groster.commands.roster import summary_report
from groster.repository import InMemoryRosterRepository

REGION = "eu"
REALM = "terokkar"
GUILD = "test-guild"

DASHBOARD_COLUMNS = [
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
    "iLvl",
    "Last Login",
    "Raider.io",
    "Armory",
    "Logs",
]


@pytest.fixture()
async def seeded_repo(
    in_memory_repo: InMemoryRosterRepository,
) -> InMemoryRosterRepository:
    await in_memory_repo.save_playable_classes(
        [{"id": 1, "name": "Warrior"}, {"id": 2, "name": "Mage"}]
    )
    await in_memory_repo.save_playable_races(
        [{"id": 1, "name": "Human"}, {"id": 7, "name": "Gnome"}]
    )
    await in_memory_repo.save_guild_ranks(
        [{"id": 0, "name": "GM"}, {"id": 1, "name": "Officer"}],
        REGION,
        REALM,
        GUILD,
    )
    await in_memory_repo.save_roster_details(
        [
            {
                "id": 1,
                "name": "Alice",
                "realm": "terokkar",
                "level": 80,
                "class_id": 1,
                "race_id": 1,
                "rank": 0,
                "ilvl": 600,
                "last_login": "2026-01-01",
            },
            {
                "id": 2,
                "name": "Bob",
                "realm": "terokkar",
                "level": 80,
                "class_id": 2,
                "race_id": 7,
                "rank": 1,
                "ilvl": 590,
                "last_login": "2026-01-02",
            },
        ],
        REGION,
        REALM,
        GUILD,
    )
    await in_memory_repo.save_profile_links(
        [
            {
                "id": 1,
                "name": "Alice",
                "rio_link": "https://rio/a",
                "armory_link": "https://arm/a",
                "warcraft_logs_link": "https://logs/a",
            },
            {
                "id": 2,
                "name": "Bob",
                "rio_link": "https://rio/b",
                "armory_link": "https://arm/b",
                "warcraft_logs_link": "https://logs/b",
            },
        ],
        REGION,
        REALM,
        GUILD,
    )
    await in_memory_repo.save_alts_data(
        [
            {"id": 1, "name": "Alice", "alt": False, "main": "Alice"},
            {"id": 2, "name": "Bob", "alt": True, "main": "Alice"},
        ],
        REGION,
        REALM,
        GUILD,
    )
    await in_memory_repo.save_achievements_summary(
        [
            {
                "id": 1,
                "name": "Alice",
                "total_quantity": 100,
                "total_points": 500,
            },
            {
                "id": 2,
                "name": "Bob",
                "total_quantity": 50,
                "total_points": 250,
            },
        ],
        REGION,
        REALM,
        GUILD,
    )
    return in_memory_repo


# ── build_dashboard ──────────────────────────────────────────────────────────


async def test_build_dashboard_all_data_present_creates_dashboard(
    seeded_repo: InMemoryRosterRepository,
):
    await seeded_repo.build_dashboard(REGION, REALM, GUILD)

    key = seeded_repo._guild_key(REGION, REALM, GUILD)
    dashboard = seeded_repo._dashboard[key]
    assert len(dashboard) == 2
    assert dashboard[0]["Name"] == "Alice"
    assert dashboard[0]["Class"] == "Warrior"
    assert dashboard[0]["Race"] == "Human"
    assert dashboard[0]["Rank"] == "GM"
    assert dashboard[0]["AQ"] == 100
    assert dashboard[0]["AP"] == 500
    assert dashboard[0]["Alt?"] is False
    assert dashboard[0]["Main"] == "Alice"
    assert dashboard[1]["Name"] == "Bob"
    assert dashboard[1]["Class"] == "Mage"
    assert dashboard[1]["Race"] == "Gnome"
    assert dashboard[1]["Rank"] == "Officer"
    assert dashboard[1]["Alt?"] is True
    assert dashboard[1]["Main"] == "Alice"


async def test_build_dashboard_missing_source_data_raises_runtime_error(
    in_memory_repo: InMemoryRosterRepository,
):
    with pytest.raises(RuntimeError, match="source CSV file is missing"):
        await in_memory_repo.build_dashboard(REGION, REALM, GUILD)


async def test_build_dashboard_column_order_matches_expected(
    seeded_repo: InMemoryRosterRepository,
):
    await seeded_repo.build_dashboard(REGION, REALM, GUILD)

    key = seeded_repo._guild_key(REGION, REALM, GUILD)
    row = seeded_repo._dashboard[key][0]

    assert list(row.keys()) == DASHBOARD_COLUMNS


async def test_build_dashboard_sets_dashboard_modified_timestamp(
    seeded_repo: InMemoryRosterRepository,
):
    await seeded_repo.build_dashboard(REGION, REALM, GUILD)

    key = seeded_repo._guild_key(REGION, REALM, GUILD)
    assert key in seeded_repo._dashboard_modified


async def test_build_dashboard_missing_links_skips_roster_row(
    in_memory_repo: InMemoryRosterRepository,
):
    await in_memory_repo.save_playable_classes([{"id": 1, "name": "Warrior"}])
    await in_memory_repo.save_playable_races([{"id": 1, "name": "Human"}])
    await in_memory_repo.save_guild_ranks(
        [{"id": 0, "name": "GM"}], REGION, REALM, GUILD
    )
    await in_memory_repo.save_roster_details(
        [
            {
                "id": 1,
                "name": "Alice",
                "realm": "t",
                "level": 80,
                "class_id": 1,
                "race_id": 1,
                "rank": 0,
                "ilvl": 600,
                "last_login": "2026-01-01",
            }
        ],
        REGION,
        REALM,
        GUILD,
    )
    await in_memory_repo.save_alts_data(
        [{"id": 1, "name": "Alice", "alt": False, "main": "Alice"}],
        REGION,
        REALM,
        GUILD,
    )

    await in_memory_repo.build_dashboard(REGION, REALM, GUILD)

    key = in_memory_repo._guild_key(REGION, REALM, GUILD)
    assert len(in_memory_repo._dashboard[key]) == 0


async def test_build_dashboard_missing_achievements_uses_empty_values(
    seeded_repo: InMemoryRosterRepository,
):
    key = seeded_repo._guild_key(REGION, REALM, GUILD)
    seeded_repo._achievements[key] = []

    await seeded_repo.build_dashboard(REGION, REALM, GUILD)

    dashboard = seeded_repo._dashboard[key]
    assert dashboard[0]["AQ"] is None
    assert dashboard[0]["AP"] is None


# ── get_alt_summary ──────────────────────────────────────────────────────────


async def test_get_alt_summary_with_alts_returns_correct_counts(
    seeded_repo: InMemoryRosterRepository,
):
    result = await seeded_repo.get_alt_summary(REGION, REALM, GUILD)

    assert result == (1, 1)


async def test_get_alt_summary_no_data_returns_none(
    in_memory_repo: InMemoryRosterRepository,
):
    result = await in_memory_repo.get_alt_summary(REGION, REALM, GUILD)

    assert result is None


async def test_get_alt_summary_no_alts_detected_returns_zero_alts(
    in_memory_repo: InMemoryRosterRepository,
):
    await in_memory_repo.save_alts_data(
        [
            {"id": 1, "name": "Alice", "alt": False, "main": "Alice"},
            {"id": 2, "name": "Bob", "alt": False, "main": "Bob"},
            {"id": 3, "name": "Charlie", "alt": False, "main": "Charlie"},
        ],
        REGION,
        REALM,
        GUILD,
    )

    result = await in_memory_repo.get_alt_summary(REGION, REALM, GUILD)

    assert result == (0, 3)


async def test_get_alt_summary_multiple_mains_returns_distinct_count(
    in_memory_repo: InMemoryRosterRepository,
):
    await in_memory_repo.save_alts_data(
        [
            {"id": 1, "name": "Alice", "alt": False, "main": "Alice"},
            {"id": 2, "name": "Bob", "alt": True, "main": "Alice"},
            {"id": 3, "name": "Charlie", "alt": False, "main": "Charlie"},
            {"id": 4, "name": "Dave", "alt": True, "main": "Charlie"},
        ],
        REGION,
        REALM,
        GUILD,
    )

    result = await in_memory_repo.get_alt_summary(REGION, REALM, GUILD)

    assert result == (2, 2)


# ── summary_report ───────────────────────────────────────────────────────────


async def test_summary_report_with_data_logs_alt_and_main_counts(
    seeded_repo: InMemoryRosterRepository, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.INFO):
        await summary_report(seeded_repo, REGION, REALM, GUILD, 1.23)

    assert "Processing completed in 1.23 seconds" in caplog.text
    assert "Alts found: 1" in caplog.text
    assert "Main characters: 1" in caplog.text


async def test_summary_report_no_data_logs_time_only(
    in_memory_repo: InMemoryRosterRepository, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.INFO):
        await summary_report(in_memory_repo, REGION, REALM, GUILD, 5.67)

    assert "Processing completed in 5.67 seconds" in caplog.text
    assert "Alts found" not in caplog.text
    assert "Main characters" not in caplog.text
