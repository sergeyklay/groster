import asyncio

import pytest

from groster.constants import LEVEL_10_ACHIEVEMENT_ID
from groster.http_client import BlizzardAPIClient
from groster.services import (
    _armory_locale,
    _find_main_in_group,
    assign_main_characters,
    build_profile_links,
    cluster_characters_by_fingerprint,
    compute_jaccard_similarity,
    fetch_member_fingerprint,
    fetch_member_mounts_summary,
    fetch_member_pets_summary,
    fetch_playable_classes,
    fetch_playable_races,
    fetch_roster_details,
    identify_alts,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_client(mocker):
    return mocker.AsyncMock(spec=BlizzardAPIClient)


def _make_member(name, realm="terokkar", char_id=1):
    return {
        "character": {
            "id": char_id,
            "name": name,
            "realm": {"slug": realm},
            "level": 80,
            "playable_class": {"id": 1},
            "playable_race": {"id": 2},
        },
        "rank": 5,
    }


def _make_achievements(timestamps_map, *, include_level10=True, level10_ts=1000):
    """Build a Blizzard-style achievements response.

    ``timestamps_map`` is ``{achievement_id: completed_timestamp}``.
    """
    achievements = [
        {"id": aid, "completed_timestamp": ts} for aid, ts in timestamps_map.items()
    ]
    if include_level10 and LEVEL_10_ACHIEVEMENT_ID not in timestamps_map:
        achievements.append(
            {"id": LEVEL_10_ACHIEVEMENT_ID, "completed_timestamp": level10_ts}
        )
    return {
        "achievements": achievements,
        "total_quantity": len(achievements),
        "total_points": len(achievements) * 10,
    }


# ---------------------------------------------------------------------------
# _armory_locale
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "region,expected",
    [
        ("us", "en-us"),
        ("eu", "en-gb"),
        ("kr", "ko-kr"),
        ("tw", "zh-tw"),
        ("cn", "zh-cn"),
    ],
)
def test_armory_locale_known_region_returns_correct_locale(region, expected):
    result = _armory_locale(region)

    assert result == expected


def test_armory_locale_unknown_region_returns_default():
    result = _armory_locale("xx")

    assert result == "en-us"


# ---------------------------------------------------------------------------
# _find_main_in_group
# ---------------------------------------------------------------------------


def test_find_main_in_group_single_character_returns_that_character():
    group = [{"name": "Darq", "timestamps": {LEVEL_10_ACHIEVEMENT_ID: 5000}}]

    result = _find_main_in_group(group)

    assert result == "Darq"


def test_find_main_in_group_multiple_characters_returns_earliest_level10():
    group = [
        {"name": "Alt", "timestamps": {LEVEL_10_ACHIEVEMENT_ID: 9000}},
        {"name": "Main", "timestamps": {LEVEL_10_ACHIEVEMENT_ID: 1000}},
        {"name": "Alt2", "timestamps": {LEVEL_10_ACHIEVEMENT_ID: 5000}},
    ]

    result = _find_main_in_group(group)

    assert result == "Main"


def test_find_main_in_group_no_level10_timestamps_returns_first_character():
    group = [
        {"name": "Alpha", "timestamps": {}},
        {"name": "Beta", "timestamps": {}},
    ]

    result = _find_main_in_group(group)

    assert result == "Alpha"


def test_find_main_in_group_mixed_timestamps_returns_earliest():
    group = [
        {"name": "NoTimestamp", "timestamps": {}},
        {"name": "HasTimestamp", "timestamps": {LEVEL_10_ACHIEVEMENT_ID: 2000}},
    ]

    result = _find_main_in_group(group)

    assert result == "HasTimestamp"


def test_find_main_in_group_none_timestamp_skipped():
    group = [
        {"name": "NoneTs", "timestamps": {LEVEL_10_ACHIEVEMENT_ID: None}},
        {"name": "ValidTs", "timestamps": {LEVEL_10_ACHIEVEMENT_ID: 3000}},
    ]

    result = _find_main_in_group(group)

    assert result == "ValidTs"


# ---------------------------------------------------------------------------
# build_profile_links
# ---------------------------------------------------------------------------


def test_build_profile_links_valid_members_returns_correct_links():
    data = {"members": [_make_member("Darq", "terokkar")]}

    result = build_profile_links("eu", data)

    assert len(result) == 1
    link = result[0]
    assert link["name"] == "Darq"
    assert "raider.io/characters/eu/terokkar/darq" in link["rio_link"]
    armory = link["armory_link"]
    assert "worldofwarcraft.blizzard.com/en-gb/character/eu/terokkar/darq" in armory
    assert "warcraftlogs.com/character/eu/terokkar/darq" in link["warcraft_logs_link"]


def test_build_profile_links_empty_members_returns_empty_list():
    result = build_profile_links("eu", {"members": []})

    assert result == []


def test_build_profile_links_no_members_key_returns_empty_list():
    result = build_profile_links("eu", {})

    assert result == []


def test_build_profile_links_member_missing_name_skipped():
    member = {"character": {"id": 1, "realm": {"slug": "terokkar"}}}
    data = {"members": [member]}

    result = build_profile_links("eu", data)

    assert result == []


def test_build_profile_links_member_missing_realm_skipped():
    member = {"character": {"id": 1, "name": "Darq"}}
    data = {"members": [member]}

    result = build_profile_links("eu", data)

    assert result == []


def test_build_profile_links_us_region_uses_en_us_locale():
    data = {"members": [_make_member("Darq", "thrall")]}

    result = build_profile_links("us", data)

    assert "en-us" in result[0]["armory_link"]


def test_build_profile_links_multiple_members_returns_all():
    data = {
        "members": [
            _make_member("Darq", "terokkar", 1),
            _make_member("Alt", "terokkar", 2),
        ]
    }

    result = build_profile_links("eu", data)

    assert len(result) == 2
    names = {r["name"] for r in result}
    assert names == {"Darq", "Alt"}


# ---------------------------------------------------------------------------
# fetch_member_fingerprint
# ---------------------------------------------------------------------------


def test_fetch_member_fingerprint_valid_member_returns_fingerprint(mock_client):
    member = _make_member("Darq")
    ach_data = _make_achievements({9670: 100, 10693: 200})
    mock_client.get_character_achievements.return_value = ach_data

    result = asyncio.run(fetch_member_fingerprint(mock_client, member))

    assert result is not None
    assert result["name"] == "Darq"
    assert result["id"] == 1
    assert isinstance(result["fingerprint"], tuple)
    assert len(result["fingerprint"]) == 2
    assert result["timestamps"][LEVEL_10_ACHIEVEMENT_ID] == 1000


def test_fetch_member_fingerprint_no_name_returns_none(mock_client):
    member = {"character": {"realm": {"slug": "terokkar"}}}

    result = asyncio.run(fetch_member_fingerprint(mock_client, member))

    assert result is None


def test_fetch_member_fingerprint_no_realm_returns_none(mock_client):
    member = {"character": {"name": "Darq"}}

    result = asyncio.run(fetch_member_fingerprint(mock_client, member))

    assert result is None


def test_fetch_member_fingerprint_empty_achievements_returns_empty_fingerprint(
    mock_client,
):
    member = _make_member("Darq")
    mock_client.get_character_achievements.return_value = {
        "achievements": [],
        "total_quantity": 0,
        "total_points": 0,
    }

    result = asyncio.run(fetch_member_fingerprint(mock_client, member))

    assert result is not None
    assert result["fingerprint"] == ()
    assert result["timestamps"] == {}


def test_fetch_member_fingerprint_no_achievements_key_returns_empty_fingerprint(
    mock_client,
):
    member = _make_member("Darq")
    mock_client.get_character_achievements.return_value = {
        "total_quantity": 5,
        "total_points": 50,
    }

    result = asyncio.run(fetch_member_fingerprint(mock_client, member))

    assert result is not None
    assert result["fingerprint"] == ()
    assert result["timestamps"] == {}
    assert result["total_quantity"] == 5
    assert result["total_points"] == 50


def test_fetch_member_fingerprint_level10_excluded_from_fingerprint_tuple(mock_client):
    member = _make_member("Darq")
    ach_data = _make_achievements(
        {LEVEL_10_ACHIEVEMENT_ID: 500, 9670: 100}, include_level10=False
    )
    mock_client.get_character_achievements.return_value = ach_data

    result = asyncio.run(fetch_member_fingerprint(mock_client, member))

    fp_ids = {aid for aid, _ in result["fingerprint"]}
    assert LEVEL_10_ACHIEVEMENT_ID not in fp_ids
    assert result["timestamps"][LEVEL_10_ACHIEVEMENT_ID] == 500


def test_fetch_member_fingerprint_non_fingerprint_achievements_ignored(mock_client):
    member = _make_member("Darq")
    ach_data = {
        "achievements": [
            {"id": 99999, "completed_timestamp": 100},
            {"id": 9670, "completed_timestamp": 200},
            {"id": LEVEL_10_ACHIEVEMENT_ID, "completed_timestamp": 300},
        ],
        "total_quantity": 3,
        "total_points": 30,
    }
    mock_client.get_character_achievements.return_value = ach_data

    result = asyncio.run(fetch_member_fingerprint(mock_client, member))

    fp_ids = {aid for aid, _ in result["fingerprint"]}
    assert 99999 not in fp_ids
    assert 9670 in fp_ids


# ---------------------------------------------------------------------------
# fetch_playable_classes / fetch_playable_races
# ---------------------------------------------------------------------------


def test_fetch_playable_classes_returns_id_name_dicts(mock_client):
    mock_client.get_playable_classes.return_value = [
        {"id": 1, "name": "Warrior", "extra": "ignored"},
        {"id": 2, "name": "Paladin", "extra": "ignored"},
    ]

    result = asyncio.run(fetch_playable_classes(mock_client))

    assert result == [{"id": 1, "name": "Warrior"}, {"id": 2, "name": "Paladin"}]


def test_fetch_playable_races_returns_id_name_dicts(mock_client):
    mock_client.get_playable_races.return_value = [
        {"id": 1, "name": "Human", "extra": "ignored"},
        {"id": 2, "name": "Orc", "extra": "ignored"},
    ]

    result = asyncio.run(fetch_playable_races(mock_client))

    assert result == [{"id": 1, "name": "Human"}, {"id": 2, "name": "Orc"}]


# ---------------------------------------------------------------------------
# fetch_member_pets_summary
# ---------------------------------------------------------------------------


def test_fetch_member_pets_summary_valid_member_returns_summary(mock_client):
    member = _make_member("Darq")
    mock_client.get_character_pets.return_value = {
        "pets": [{"id": 1}, {"id": 2}, {"id": 3}]
    }

    summary, raw = asyncio.run(fetch_member_pets_summary(mock_client, member))

    assert summary["name"] == "Darq"
    assert summary["pets"] == 3
    assert raw["pets"] == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_fetch_member_pets_summary_missing_info_returns_none(mock_client):
    member = {"character": {"name": "Darq", "realm": {"slug": "terokkar"}}}

    summary, raw = asyncio.run(fetch_member_pets_summary(mock_client, member))

    assert summary is None
    assert raw is None


def test_fetch_member_pets_summary_empty_pets_returns_zero(mock_client):
    member = _make_member("Darq")
    mock_client.get_character_pets.return_value = {}

    summary, _ = asyncio.run(fetch_member_pets_summary(mock_client, member))

    assert summary["pets"] == 0


# ---------------------------------------------------------------------------
# fetch_member_mounts_summary
# ---------------------------------------------------------------------------


def test_fetch_member_mounts_summary_valid_member_returns_summary(mock_client):
    member = _make_member("Darq")
    mock_client.get_character_mounts.return_value = {"mounts": [{"id": 10}, {"id": 20}]}

    summary, raw = asyncio.run(fetch_member_mounts_summary(mock_client, member))

    assert summary["name"] == "Darq"
    assert summary["mounts"] == 2
    assert raw["mounts"] == [{"id": 10}, {"id": 20}]


def test_fetch_member_mounts_summary_missing_info_returns_none(mock_client):
    member = {"character": {"name": "Darq", "realm": {"slug": "terokkar"}}}

    summary, raw = asyncio.run(fetch_member_mounts_summary(mock_client, member))

    assert summary is None
    assert raw is None


# ---------------------------------------------------------------------------
# fetch_roster_details
# ---------------------------------------------------------------------------


def test_fetch_roster_details_valid_roster_returns_processed_data(mock_client):
    roster = {"members": [_make_member("Darq")]}
    mock_client.get_character_profile.return_value = {
        "name": "Darq",
        "id": 1,
        "last_login_timestamp": 1704067200000,
        "equipped_item_level": 480,
    }

    processed, raw_profiles = asyncio.run(fetch_roster_details(mock_client, roster))

    assert len(processed) == 1
    assert processed[0]["name"] == "Darq"
    assert processed[0]["ilvl"] == 480
    assert "Darq" in raw_profiles


def test_fetch_roster_details_empty_members_returns_empty(mock_client):
    processed, raw_profiles = asyncio.run(
        fetch_roster_details(mock_client, {"members": []})
    )

    assert processed == []
    assert raw_profiles == {}


def test_fetch_roster_details_no_members_key_returns_empty(mock_client):
    processed, raw_profiles = asyncio.run(fetch_roster_details(mock_client, {}))

    assert processed == []
    assert raw_profiles == {}


def test_fetch_roster_details_profile_returns_none_skipped(mock_client):
    roster = {"members": [_make_member("Darq")]}
    mock_client.get_character_profile.return_value = None

    processed, _ = asyncio.run(fetch_roster_details(mock_client, roster))

    assert processed == []


def test_fetch_roster_details_member_missing_realm_skipped(mock_client):
    member = {"character": {"name": "Darq"}, "rank": 5}
    roster = {"members": [member]}

    processed, _ = asyncio.run(fetch_roster_details(mock_client, roster))

    assert processed == []


# ---------------------------------------------------------------------------
# compute_jaccard_similarity
# ---------------------------------------------------------------------------


def test_compute_jaccard_similarity_identical_sets_returns_one():
    fp = {(9670, 100), (10693, 200), (10691, 300)}

    result = compute_jaccard_similarity(fp, fp.copy())

    assert result == 1.0


def test_compute_jaccard_similarity_disjoint_sets_returns_zero():
    fp_a = {(9670, 100), (10693, 200), (10691, 300)}
    fp_b = {(10689, 400), (10687, 500), (10685, 600)}

    result = compute_jaccard_similarity(fp_a, fp_b)

    assert result == 0.0


def test_compute_jaccard_similarity_partial_overlap_returns_expected():
    fp_a = {(9670, 100), (10693, 200), (10691, 300)}
    fp_b = {(9670, 100), (10693, 200), (10689, 400)}

    result = compute_jaccard_similarity(fp_a, fp_b)

    # 2 shared out of 4 unique → 0.5
    assert result == pytest.approx(0.5)


def test_compute_jaccard_similarity_both_empty_returns_zero():
    result = compute_jaccard_similarity(set(), set())

    assert result == 0.0


# ---------------------------------------------------------------------------
# cluster_characters_by_fingerprint
# ---------------------------------------------------------------------------


def _make_char_data(name, fingerprint_tuples, timestamps=None):
    """Build a character dict matching the shape used in identify_alts."""
    return {
        "id": hash(name),
        "name": name,
        "realm": "terokkar",
        "pets": 0,
        "mounts": 0,
        "fingerprint": tuple(sorted(fingerprint_tuples)),
        "timestamps": timestamps or {},
    }


def test_cluster_characters_identical_fingerprints_single_group():
    shared_fp = {(9670, 100), (10693, 200), (10691, 300)}
    char_a = _make_char_data("CharA", shared_fp)
    char_b = _make_char_data("CharB", shared_fp)

    groups = cluster_characters_by_fingerprint([char_a, char_b])

    assert len(groups) == 1
    assert len(groups[0]) == 2


def test_cluster_characters_disjoint_fingerprints_separate_groups():
    char_a = _make_char_data("CharA", {(9670, 100), (10693, 200), (10691, 300)})
    char_b = _make_char_data("CharB", {(10689, 400), (10687, 500), (10685, 600)})

    groups = cluster_characters_by_fingerprint([char_a, char_b])

    assert len(groups) == 2
    assert len(groups[0]) == 1
    assert len(groups[1]) == 1


def test_cluster_characters_small_fingerprint_isolated():
    small = _make_char_data("Small", {(9670, 100), (10693, 200)})
    normal = _make_char_data("Normal", {(9670, 100), (10693, 200), (10691, 300)})

    groups = cluster_characters_by_fingerprint([small, normal])

    assert len(groups) == 2


def test_cluster_characters_empty_list_returns_empty():
    groups = cluster_characters_by_fingerprint([])

    assert groups == []


# ---------------------------------------------------------------------------
# assign_main_characters
# ---------------------------------------------------------------------------


def test_assign_main_characters_single_group_returns_earliest_level10():
    group = [
        _make_char_data("New", {(9670, 100)}, {LEVEL_10_ACHIEVEMENT_ID: 9000}),
        _make_char_data("Old", {(9670, 100)}, {LEVEL_10_ACHIEVEMENT_ID: 1000}),
    ]

    result = assign_main_characters([group])

    assert result["New"] == "Old"
    assert result["Old"] == "Old"


def test_assign_main_characters_multiple_groups_independent():
    group_a = [
        _make_char_data("A1", {(9670, 100)}, {LEVEL_10_ACHIEVEMENT_ID: 2000}),
        _make_char_data("A2", {(9670, 100)}, {LEVEL_10_ACHIEVEMENT_ID: 5000}),
    ]
    group_b = [
        _make_char_data("B1", {(9670, 100)}, {LEVEL_10_ACHIEVEMENT_ID: 3000}),
        _make_char_data("B2", {(9670, 100)}, {LEVEL_10_ACHIEVEMENT_ID: 1000}),
    ]

    result = assign_main_characters([group_a, group_b])

    assert len(result) == 4
    assert result["A1"] == "A1"
    assert result["A2"] == "A1"
    assert result["B1"] == "B2"
    assert result["B2"] == "B2"


def test_assign_main_characters_empty_groups_returns_empty():
    result = assign_main_characters([])

    assert result == {}


# ---------------------------------------------------------------------------
# identify_alts — Jaccard similarity & grouping
# ---------------------------------------------------------------------------


def _fp_achievements(ids):
    """Create a fingerprint-compatible achievements map from a set of IDs."""
    return {aid: aid * 100 for aid in ids}


def test_identify_alts_empty_roster_returns_empty(mock_client):
    result = asyncio.run(identify_alts(mock_client, {"members": []}))

    alts, pets, mounts, ach_summaries = result
    assert alts == []
    assert pets == {}
    assert mounts == {}
    assert ach_summaries == []


def test_identify_alts_identical_fingerprints_grouped_together(mock_client):
    shared_achs = {9670: 100, 10693: 200, 10691: 300}
    members = [_make_member("Main", char_id=1), _make_member("Alt", char_id=2)]
    roster = {"members": members}

    mock_client.get_character_achievements.return_value = _make_achievements(
        shared_achs
    )
    mock_client.get_character_pets.return_value = {"pets": []}
    mock_client.get_character_mounts.return_value = {"mounts": []}

    alts, _, _, _ = asyncio.run(identify_alts(mock_client, roster))

    mains = {a["main"] for a in alts}
    assert len(mains) == 1


def test_identify_alts_disjoint_fingerprints_separate_groups(mock_client):
    achs_a = {9670: 100, 10693: 200, 10691: 300}
    achs_b = {10689: 400, 10687: 500, 10685: 600}
    members = [_make_member("CharA", char_id=1), _make_member("CharB", char_id=2)]
    roster = {"members": members}

    mock_client.get_character_achievements.side_effect = [
        _make_achievements(achs_a),
        _make_achievements(achs_b),
    ]
    mock_client.get_character_pets.return_value = {"pets": []}
    mock_client.get_character_mounts.return_value = {"mounts": []}

    alts, _, _, _ = asyncio.run(identify_alts(mock_client, roster))

    mains = {a["main"] for a in alts}
    assert len(mains) == 2


def test_identify_alts_small_fingerprint_not_grouped(mock_client):
    achs_small = {9670: 100, 10693: 200}  # only 2, below threshold of 3
    achs_normal = {9670: 100, 10693: 200, 10691: 300}
    members = [_make_member("Small", char_id=1), _make_member("Normal", char_id=2)]
    roster = {"members": members}

    mock_client.get_character_achievements.side_effect = [
        _make_achievements(achs_small),
        _make_achievements(achs_normal),
    ]
    mock_client.get_character_pets.return_value = {"pets": []}
    mock_client.get_character_mounts.return_value = {"mounts": []}

    alts, _, _, _ = asyncio.run(identify_alts(mock_client, roster))

    mains = {a["main"] for a in alts}
    assert len(mains) == 2


def test_identify_alts_single_member_not_marked_as_alt(mock_client):
    members = [_make_member("Solo", char_id=1)]
    roster = {"members": members}

    mock_client.get_character_achievements.return_value = _make_achievements(
        {9670: 100, 10693: 200, 10691: 300}
    )
    mock_client.get_character_pets.return_value = {"pets": []}
    mock_client.get_character_mounts.return_value = {"mounts": []}

    alts, _, _, _ = asyncio.run(identify_alts(mock_client, roster))

    assert len(alts) == 1
    assert alts[0]["alt"] is False
    assert alts[0]["main"] == "Solo"


def test_identify_alts_main_detection_uses_earliest_level10(mock_client):
    achs_shared = {9670: 100, 10693: 200, 10691: 300}
    members = [_make_member("NewChar", char_id=1), _make_member("OldChar", char_id=2)]
    roster = {"members": members}

    mock_client.get_character_achievements.side_effect = [
        _make_achievements(achs_shared, level10_ts=9000),
        _make_achievements(achs_shared, level10_ts=1000),
    ]
    mock_client.get_character_pets.return_value = {"pets": []}
    mock_client.get_character_mounts.return_value = {"mounts": []}

    alts, _, _, _ = asyncio.run(identify_alts(mock_client, roster))

    for a in alts:
        assert a["main"] == "OldChar"


def test_identify_alts_achievements_summaries_populated(mock_client):
    members = [_make_member("Darq", char_id=1)]
    roster = {"members": members}

    mock_client.get_character_achievements.return_value = _make_achievements(
        {9670: 100}
    )
    mock_client.get_character_pets.return_value = {"pets": []}
    mock_client.get_character_mounts.return_value = {"mounts": []}

    _, _, _, ach_summaries = asyncio.run(identify_alts(mock_client, roster))

    assert len(ach_summaries) == 1
    assert ach_summaries[0]["name"] == "Darq"
    assert ach_summaries[0]["total_quantity"] > 0
