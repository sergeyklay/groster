import pytest

from groster.commands.roster import _get_roster_details
from groster.http_client import BlizzardAPIClient
from groster.repository import InMemoryRosterRepository

REGION = "eu"
REALM = "terokkar"
GUILD = "test-guild"


@pytest.fixture()
def mock_client(mocker):
    return mocker.AsyncMock(spec=BlizzardAPIClient)


@pytest.fixture()
def repo():
    return InMemoryRosterRepository()


def _make_member(name, char_id, *, rank=5, level=80):
    return {
        "character": {
            "id": char_id,
            "name": name,
            "realm": {"slug": REALM},
            "level": level,
            "playable_class": {"id": 1},
            "playable_race": {"id": 2},
        },
        "rank": rank,
    }


def _make_profile(name, char_id, ilvl=200):
    return {
        "name": name,
        "id": char_id,
        "last_login_timestamp": 0,
        "equipped_item_level": ilvl,
    }


def _make_roster_record(char_id, name, *, rank=5, level=80):
    return {
        "id": char_id,
        "name": name,
        "realm": REALM,
        "level": level,
        "class_id": 1,
        "race_id": 2,
        "rank": rank,
        "ilvl": 200,
        "last_login": "2026-01-01 00:00:00",
    }


# ---------------------------------------------------------------------------
# _get_roster_details
# ---------------------------------------------------------------------------


async def test_get_roster_details_force_true_skips_diff(mock_client, repo):
    await repo.save_roster_details(
        [_make_roster_record(1, "Cached")], REGION, REALM, GUILD
    )
    mock_client.get_guild_roster.return_value = {"members": [_make_member("Cached", 1)]}
    mock_client.get_character_profile.return_value = _make_profile("Cached", 1)

    _, cached = await _get_roster_details(
        repo, mock_client, REGION, REALM, GUILD, force=True
    )

    assert cached == {}
    mock_client.get_character_profile.call_count == 1


async def test_get_roster_details_first_run_fetches_all(mock_client, repo):
    mock_client.get_guild_roster.return_value = {"members": [_make_member("New", 1)]}
    mock_client.get_character_profile.return_value = _make_profile("New", 1)

    _, cached = await _get_roster_details(repo, mock_client, REGION, REALM, GUILD)

    assert cached == {}
    assert mock_client.get_character_profile.call_count == 1


async def test_get_roster_details_incremental_caches_unchanged(mock_client, repo):
    await repo.save_roster_details(
        [
            _make_roster_record(1, "Cached"),
            _make_roster_record(2, "Changed", rank=5),
        ],
        REGION,
        REALM,
        GUILD,
    )
    mock_client.get_guild_roster.return_value = {
        "members": [
            _make_member("Cached", 1, rank=5),
            _make_member("Changed", 2, rank=3),
        ]
    }
    mock_client.get_character_profile.side_effect = [
        _make_profile("Cached", 1),
        _make_profile("Changed", 2),
    ]

    _, cached = await _get_roster_details(repo, mock_client, REGION, REALM, GUILD)

    assert "Cached" in cached
    assert "Changed" not in cached
    assert mock_client.get_character_profile.call_count == 2


async def test_get_roster_details_empty_roster_raises_runtime_error(mock_client, repo):
    mock_client.get_guild_roster.return_value = {}

    with pytest.raises(RuntimeError, match="Failed to get guild roster data"):
        await _get_roster_details(repo, mock_client, REGION, REALM, GUILD)


async def test_get_roster_details_saves_roster_to_repo(mock_client, repo):
    mock_client.get_guild_roster.return_value = {"members": [_make_member("A", 1)]}
    mock_client.get_character_profile.return_value = _make_profile("A", 1)

    await _get_roster_details(repo, mock_client, REGION, REALM, GUILD)

    saved = await repo.get_roster_details(REGION, REALM, GUILD)
    assert saved is not None
    assert saved[0]["name"] == "A"


async def test_get_roster_details_saves_raw_profiles_to_repo(mock_client, repo):
    mock_client.get_guild_roster.return_value = {"members": [_make_member("A", 1)]}
    mock_client.get_character_profile.return_value = _make_profile("A", 1, ilvl=500)

    await _get_roster_details(repo, mock_client, REGION, REALM, GUILD)

    key = repo._char_key(REGION, REALM, "A")
    assert key in repo._profiles
    assert repo._profiles[key]["equipped_item_level"] == 500
