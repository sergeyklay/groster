import json

import pytest

from groster.repository.csv import CsvRosterRepository

REGION = "eu"
REALM = "terokkar"
GUILD = "test-guild"


@pytest.fixture()
def csv_repo(tmp_path):
    return CsvRosterRepository(base_path=tmp_path)


# ---------------------------------------------------------------------------
# get_roster_details
# ---------------------------------------------------------------------------


async def test_get_roster_details_no_file_returns_none(csv_repo):
    result = await csv_repo.get_roster_details(REGION, REALM, GUILD)

    assert result is None


async def test_get_roster_details_save_then_get_round_trips_records(csv_repo):
    roster = [
        {
            "id": 1,
            "name": "Thrall",
            "realm": "terokkar",
            "level": 80,
            "class_id": 1,
            "race_id": 2,
            "rank": 0,
            "ilvl": 600,
            "last_login": "2026-01-01",
        },
        {
            "id": 2,
            "name": "Jaina",
            "realm": "terokkar",
            "level": 80,
            "class_id": 2,
            "race_id": 1,
            "rank": 1,
            "ilvl": 590,
            "last_login": "2026-01-02",
        },
    ]
    await csv_repo.save_roster_details(roster, REGION, REALM, GUILD)

    result = await csv_repo.get_roster_details(REGION, REALM, GUILD)

    assert result is not None
    assert len(result) == 2
    assert result[0]["name"] == "Thrall"
    assert result[1]["name"] == "Jaina"


async def test_get_roster_details_empty_csv_returns_none(csv_repo, tmp_path):
    from groster.utils import data_path

    roster_file = data_path(tmp_path, REGION, REALM, GUILD, "roster")
    roster_file.write_text("")

    result = await csv_repo.get_roster_details(REGION, REALM, GUILD)

    assert result is None


# ---------------------------------------------------------------------------
# save_character_achievements / get_member_fingerprints
# ---------------------------------------------------------------------------


async def test_save_and_get_member_fingerprints_round_trips_tuple(csv_repo):
    fp_data = {
        "id": 1,
        "name": "Thrall",
        "fingerprint": [[9670, 100], [10693, 200]],
        "timestamps": {"9670": 100, "10693": 200},
        "total_quantity": 50,
        "total_points": 500,
    }
    await csv_repo.save_character_achievements(fp_data, REGION, REALM, "Thrall")

    result = await csv_repo.get_member_fingerprints(REGION, REALM, ["Thrall"])

    assert "Thrall" in result
    fp = result["Thrall"]["fingerprint"]
    assert isinstance(fp, tuple)
    assert all(isinstance(pair, tuple) for pair in fp)
    assert fp == ((9670, 100), (10693, 200))


async def test_get_member_fingerprints_missing_name_returns_empty_dict(csv_repo):
    result = await csv_repo.get_member_fingerprints(REGION, REALM, ["Ghost"])

    assert result == {}


async def test_get_member_fingerprints_corrupted_json_skips_entry(csv_repo, tmp_path):
    char_path = tmp_path / REGION / REALM / "badchar"
    char_path.mkdir(parents=True)
    (char_path / "achievements.json").write_text("not valid json")

    result = await csv_repo.get_member_fingerprints(REGION, REALM, ["Badchar"])

    assert result == {}


async def test_save_character_achievements_creates_json_file(csv_repo, tmp_path):
    fp_data = {
        "id": 1,
        "name": "Varian",
        "fingerprint": [[9670, 100]],
        "timestamps": {"9670": 100},
        "total_quantity": 10,
        "total_points": 100,
    }

    await csv_repo.save_character_achievements(fp_data, REGION, REALM, "Varian")

    ach_file = tmp_path / REGION / REALM / "varian" / "achievements.json"
    assert ach_file.exists()
    with open(ach_file, encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["name"] == "Varian"
    assert saved["fingerprint"] == [[9670, 100]]


async def test_get_member_fingerprints_multiple_names_returns_found_only(csv_repo):
    for name, char_id in [("Alpha", 1), ("Beta", 2)]:
        await csv_repo.save_character_achievements(
            {
                "id": char_id,
                "name": name,
                "fingerprint": [[9670, char_id * 100]],
                "timestamps": {},
                "total_quantity": 1,
                "total_points": 10,
            },
            REGION,
            REALM,
            name,
        )

    result = await csv_repo.get_member_fingerprints(
        REGION, REALM, ["Alpha", "Beta", "Missing"]
    )

    assert set(result) == {"Alpha", "Beta"}
    assert "Missing" not in result
