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
    _handle_autocomplete,
    _handle_whois,
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
