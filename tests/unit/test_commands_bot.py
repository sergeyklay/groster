import json
import os
from datetime import datetime

import pytest

os.environ.setdefault(
    "DISCORD_PUBLIC_KEY",
    "0" * 64,
)

from groster.commands.bot import (
    _format_no_character_message,
    _handle_alts,
    _handle_autocomplete,
    _handle_whois,
    format_alts_embed,
)
from groster.repository import InMemoryRosterRepository

REGION = "eu"
REALM = "terokkar"
GUILD = "test-guild"


def _make_dashboard_row(name: str, *, is_alt: bool = False, main: str = "") -> dict:
    return {
        "Name": name,
        "Realm": "terokkar",
        "Level": 80,
        "Class": "Warrior",
        "Race": "Human",
        "Rank": "GM",
        "AQ": 100,
        "AP": 500,
        "Alt?": is_alt,
        "Main": main or name,
        "iLvl": 600,
        "Last Login": "2026-01-01",
        "Raider.io": "",
        "Armory": "",
        "Logs": "",
    }


@pytest.fixture()
def repo() -> InMemoryRosterRepository:
    return InMemoryRosterRepository()


@pytest.fixture()
def seeded_repo(repo: InMemoryRosterRepository) -> InMemoryRosterRepository:
    repo.seed_dashboard(
        [
            _make_dashboard_row("Alicestorm"),
            _make_dashboard_row("Alicendra", is_alt=True, main="Alicestorm"),
            _make_dashboard_row("Bobhunter"),
        ],
        REGION,
        REALM,
        GUILD,
        modified_at=datetime.now(),
    )
    return repo


# ── _format_no_character_message ─────────────────────────────────────────────


def test_format_no_character_message_with_suggestions_appends_names():
    result = _format_no_character_message(
        "Alicestrom", None, None, suggestions=["Alicestorm", "Alicendra"]
    )

    assert "Did you mean: **Alicestorm**, **Alicendra**?" in result


def test_format_no_character_message_without_suggestions_unchanged():
    result = _format_no_character_message("Zzzzz", None, None)

    assert "Did you mean" not in result


def test_format_no_character_message_none_suggestions_unchanged():
    result = _format_no_character_message("Zzzzz", None, None, suggestions=None)

    assert "Did you mean" not in result


def test_format_no_character_message_empty_suggestions_unchanged():
    result = _format_no_character_message("Zzzzz", None, None, suggestions=[])

    assert "Did you mean" not in result


# ── _handle_autocomplete ─────────────────────────────────────────────────────


async def test_handle_autocomplete_prefix_match_returns_matching_choices(
    seeded_repo: InMemoryRosterRepository,
):
    data = {"data": {"options": [{"name": "player", "value": "ali", "focused": True}]}}

    response = await _handle_autocomplete(data, seeded_repo, REGION, REALM, GUILD)
    body = response.body

    payload = json.loads(body)

    assert payload["type"] == 8
    names = [c["name"] for c in payload["data"]["choices"]]
    assert names == ["Alicendra", "Alicestorm"]


async def test_handle_autocomplete_empty_input_returns_all_names(
    seeded_repo: InMemoryRosterRepository,
):
    data = {"data": {"options": [{"name": "player", "value": "", "focused": True}]}}

    response = await _handle_autocomplete(data, seeded_repo, REGION, REALM, GUILD)

    payload = json.loads(response.body)

    assert len(payload["data"]["choices"]) == 3


async def test_handle_autocomplete_no_dashboard_returns_empty_choices(
    repo: InMemoryRosterRepository,
):
    data = {"data": {"options": [{"name": "player", "value": "ali", "focused": True}]}}

    response = await _handle_autocomplete(data, repo, REGION, REALM, GUILD)

    payload = json.loads(response.body)

    assert payload == {"type": 8, "data": {"choices": []}}


async def test_handle_autocomplete_no_focused_option_returns_all_names(
    seeded_repo: InMemoryRosterRepository,
):
    data = {"data": {"options": [{"name": "player", "value": "ali"}]}}

    response = await _handle_autocomplete(data, seeded_repo, REGION, REALM, GUILD)

    payload = json.loads(response.body)

    assert len(payload["data"]["choices"]) == 3


# ── _handle_whois with fuzzy fallback ────────────────────────────────────────


async def test_handle_whois_not_found_with_fuzzy_suggestions_includes_did_you_mean(
    seeded_repo: InMemoryRosterRepository,
):
    data = {
        "data": {
            "name": "whois",
            "options": [{"name": "player", "value": "Alicestrom"}],
        }
    }

    response = await _handle_whois(
        data, seeded_repo, REGION, REALM, GUILD, user_id=None
    )

    payload = json.loads(response.body)

    assert payload["type"] == 4
    assert "Did you mean: **Alicestorm**" in payload["data"]["content"]


async def test_handle_whois_not_found_no_fuzzy_matches_returns_standard_message(
    seeded_repo: InMemoryRosterRepository,
):
    data = {
        "data": {
            "name": "whois",
            "options": [{"name": "player", "value": "Zzzzzzzzz"}],
        }
    }

    response = await _handle_whois(
        data, seeded_repo, REGION, REALM, GUILD, user_id=None
    )

    payload = json.loads(response.body)

    assert payload["type"] == 4
    assert "Did you mean" not in payload["data"]["content"]
    assert "not found in guild roster" in payload["data"]["content"]


async def test_handle_whois_fuzzy_search_is_case_insensitive(
    seeded_repo: InMemoryRosterRepository,
):
    data = {
        "data": {
            "name": "whois",
            "options": [{"name": "player", "value": "alicestrom"}],
        }
    }

    response = await _handle_whois(
        data, seeded_repo, REGION, REALM, GUILD, user_id=None
    )

    payload = json.loads(response.body)

    assert payload["type"] == 4
    assert "Did you mean: **Alicestorm**" in payload["data"]["content"]


async def test_handle_whois_exact_match_returns_character_info(
    seeded_repo: InMemoryRosterRepository,
):
    data = {
        "data": {
            "name": "whois",
            "options": [{"name": "player", "value": "Alicestorm"}],
        }
    }

    response = await _handle_whois(
        data, seeded_repo, REGION, REALM, GUILD, user_id=None
    )

    payload = json.loads(response.body)

    assert payload["type"] == 4
    assert "Alicestorm" in payload["data"]["content"]
    assert "not found" not in payload["data"]["content"]


async def test_handle_whois_no_character_name_returns_prompt(
    repo: InMemoryRosterRepository,
):
    data = {"data": {"name": "whois", "options": [{"name": "player"}]}}

    response = await _handle_whois(data, repo, REGION, REALM, GUILD, user_id=None)

    payload = json.loads(response.body)

    assert payload["type"] == 4
    assert "provide a character name" in payload["data"]["content"].lower()


# ── format_alts_embed ────────────────────────────────────────────────────────


def test_format_alts_embed_normal_returns_sorted_lines():
    data = [
        ("Alicestorm", "Warrior", 5),
        ("Bobhunter", "Hunter", 2),
        ("Charlie", "Mage", 0),
    ]

    embed = format_alts_embed(data)

    assert embed["title"] == "Guild Alt Summary"
    assert embed["color"] == 0x00AAFF
    assert "**Alicestorm**" in embed["description"]
    assert "**Bobhunter**" in embed["description"]
    assert "**Charlie**" in embed["description"]
    assert embed["description"].index("Alicestorm") < embed["description"].index(
        "Bobhunter"
    )


def test_format_alts_embed_singular_alt_uses_correct_label():
    data = [("Alicestorm", "Warrior", 1)]

    embed = format_alts_embed(data)

    assert "1 alt\n" in embed["description"]
    assert "1 alts" not in embed["description"]


def test_format_alts_embed_zero_alts_included():
    data = [("Alicestorm", "Warrior", 0)]

    embed = format_alts_embed(data)

    assert "0 alts" in embed["description"]


def test_format_alts_embed_truncation_appends_remaining_count():
    data = [(f"MainCharacter{i:04d}", "Warrior", 5) for i in range(500)]

    embed = format_alts_embed(data)

    assert len(embed["description"]) <= 4096
    assert "more mains" in embed["description"]


def test_format_alts_embed_empty_list_returns_empty_description():
    embed = format_alts_embed([])

    assert embed["description"] == ""
    assert "0 mains" in embed["footer"]["text"]
    assert "0 alts" in embed["footer"]["text"]


def test_format_alts_embed_footer_shows_correct_totals():
    data = [
        ("Alice", "Warrior", 2),
        ("Bob", "Hunter", 1),
        ("Charlie", "Mage", 0),
    ]

    embed = format_alts_embed(data)

    assert "3 mains" in embed["footer"]["text"]
    assert "3 alts" in embed["footer"]["text"]
    assert "6 total characters" in embed["footer"]["text"]


def test_format_alts_embed_class_emoji_appears_in_description():
    data = [("Darq", "Death Knight", 3)]

    embed = format_alts_embed(data)

    assert "\U0001f480" in embed["description"]
    assert "**Darq**" in embed["description"]


# ── _handle_alts ─────────────────────────────────────────────────────────────


async def test_handle_alts_seeded_repo_returns_embed_response(
    seeded_repo: InMemoryRosterRepository,
):
    response = await _handle_alts(seeded_repo, REGION, REALM, GUILD)

    payload = json.loads(response.body)

    assert payload["type"] == 4
    assert payload["data"]["flags"] == 64
    assert len(payload["data"]["embeds"]) == 1
    assert "Alicestorm" in payload["data"]["embeds"][0]["description"]


async def test_handle_alts_seeded_repo_footer_shows_correct_totals(
    seeded_repo: InMemoryRosterRepository,
):
    response = await _handle_alts(seeded_repo, REGION, REALM, GUILD)

    payload = json.loads(response.body)
    footer = payload["data"]["embeds"][0]["footer"]["text"]

    assert "2 mains" in footer
    assert "1 alts" in footer
    assert "3 total characters" in footer


async def test_handle_alts_no_dashboard_returns_error_message(
    repo: InMemoryRosterRepository,
):
    response = await _handle_alts(repo, REGION, REALM, GUILD)

    payload = json.loads(response.body)

    assert payload["type"] == 4
    assert payload["data"]["flags"] == 64
    assert "not available yet" in payload["data"]["content"]


async def test_handle_alts_repo_exception_returns_error_message():
    class BrokenRepo(InMemoryRosterRepository):
        async def get_alts_per_main(self, region, realm, guild):
            raise RuntimeError("test error")

    repo = BrokenRepo()

    response = await _handle_alts(repo, REGION, REALM, GUILD)

    payload = json.loads(response.body)

    assert payload["type"] == 4
    assert payload["data"]["flags"] == 64
    assert "error occurred" in payload["data"]["content"]
