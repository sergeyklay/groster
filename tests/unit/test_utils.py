from pathlib import Path

import pytest

from groster.utils import data_path, format_timestamp


@pytest.mark.parametrize(
    "timestamp_ms,expected_datetime_str",
    [
        # January 1, 2024 00:00:00 UTC = 1704067200000 ms
        (1704067200000, "2024-01-01 01:00:00"),  # Europe/Paris is UTC+1
        # June 15, 2024 12:00:00 UTC = 1718452800000 ms
        (1718452800000, "2024-06-15 14:00:00"),  # Europe/Paris is UTC+2 (DST)
        # December 31, 2023 23:59:59 UTC = 1704067199000 ms
        (1704067199000, "2024-01-01 00:59:59"),  # Europe/Paris is UTC+1
    ],
)
def test_format_timestamp_valid_input_returns_formatted_string(
    timestamp_ms: int, expected_datetime_str: str
):
    result = format_timestamp(timestamp_ms)

    assert result == expected_datetime_str


@pytest.mark.parametrize(
    "timestamp_ms,timezone,expected_datetime_str",
    [
        # Test different timezones
        (1704067200000, "UTC", "2024-01-01 00:00:00"),
        (1704067200000, "US/Eastern", "2023-12-31 19:00:00"),  # UTC-5
        (1704067200000, "Asia/Tokyo", "2024-01-01 09:00:00"),  # UTC+9
    ],
)
def test_format_timestamp_custom_timezone_returns_correct_format(
    timestamp_ms: int, timezone: str, expected_datetime_str: str
):
    result = format_timestamp(timestamp_ms, to_tz=timezone)

    assert result == expected_datetime_str


@pytest.mark.parametrize(
    "timestamp_string,expected_datetime_str",
    [
        # Test string input conversion
        ("1704067200000", "2024-01-01 01:00:00"),  # Europe/Paris is UTC+1
        ("1718452800000", "2024-06-15 14:00:00"),  # Europe/Paris is UTC+2 (DST)
    ],
)
def test_format_timestamp_string_input_converts_correctly(
    timestamp_string: str, expected_datetime_str: str
):
    result = format_timestamp(timestamp_string)

    assert result == expected_datetime_str


def test_format_timestamp_string_input_custom_timezone_works_correctly():
    # Test string input with custom timezone
    timestamp_string = "1704067200000"

    result = format_timestamp(timestamp_string, to_tz="UTC")

    assert result == "2024-01-01 00:00:00"


@pytest.mark.parametrize("invalid_timestamp", [0, None, "0"])
def test_format_timestamp_invalid_timestamp_returns_na(invalid_timestamp):
    result = format_timestamp(invalid_timestamp)

    assert result == "N/A"


@pytest.mark.parametrize(
    "invalid_string",
    [
        "not_a_number",
        "abc123",
        "12.34.56",
        "",
        "   ",
    ],
)
def test_format_timestamp_invalid_string_raises_value_error(invalid_string: str):
    with pytest.raises(ValueError, match=r"invalid literal for int\(\) with base 10"):
        format_timestamp(invalid_string)


@pytest.mark.parametrize(
    "invalid_type,expected_error_pattern",
    [
        ([], r"Timestamp must be a valid integer or float\. Got: <class 'list'>"),
        ({}, r"Timestamp must be a valid integer or float\. Got: <class 'dict'>"),
        (
            object(),
            r"Timestamp must be a valid integer or float\. Got: <class 'object'>",
        ),
    ],
)
def test_format_timestamp_invalid_type_raises_value_error(
    invalid_type, expected_error_pattern: str
):
    with pytest.raises(ValueError, match=expected_error_pattern):
        format_timestamp(invalid_type)


def test_format_timestamp_float_input_works_correctly():
    # Test with float timestamp
    timestamp_float = 1704067200000.5  # Half a millisecond

    result = format_timestamp(timestamp_float)

    assert result == "2024-01-01 01:00:00"


def test_format_timestamp_format_matches_expected_pattern():
    # Test that output always matches YYYY-MM-DD HH:MM:SS format
    timestamp_ms = 1704067200000

    result = format_timestamp(timestamp_ms)

    # Verify format using regex
    import re

    pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
    assert re.match(pattern, result), f"Format doesn't match expected pattern: {result}"


def test_format_timestamp_boundary_values_work_correctly():
    # Test edge cases with very small and large timestamps
    # Epoch start: January 1, 1970 00:00:00 UTC
    epoch_start = 0
    result_epoch = format_timestamp(epoch_start)
    assert result_epoch == "N/A"  # Should handle 0 as special case

    # Small positive timestamp: January 1, 1970 00:00:01 UTC = 1000 ms
    small_timestamp = 1000
    result_small = format_timestamp(small_timestamp)
    assert result_small == "1970-01-01 01:00:01"  # Europe/Paris UTC+1


def test_format_timestamp_large_timestamp_works_correctly():
    # Test with a large timestamp (year 2050)
    # January 1, 2050 00:00:00 UTC = 2524608000000 ms
    large_timestamp = 2524608000000

    result = format_timestamp(large_timestamp)

    assert result == "2050-01-01 01:00:00"


@pytest.mark.parametrize(
    "components,expected_filename",
    [
        # Single component
        (("guild",), "guild.csv"),
        (("roster",), "roster.csv"),
        # Multiple components
        (("guild", "roster"), "guild-roster.csv"),
        (("eu", "terokkar", "guild"), "eu-terokkar-guild.csv"),
        (("data", "export", "members", "active"), "data-export-members-active.csv"),
    ],
)
def test_data_path_valid_components_returns_correct_path(
    components: tuple[str, ...], expected_filename: str, mocker
):
    # Mock DATA_PATH to have predictable test results
    mock_data_path = Path("/test/data")
    result = data_path(mock_data_path, *components)

    expected_path = mock_data_path / expected_filename
    assert result == expected_path
    assert result.suffix == ".csv"


def test_data_path_single_component_works_correctly(mocker):
    mock_data_path = Path("/mock/data")
    result = data_path(mock_data_path, "members")

    assert result == mock_data_path / "members.csv"


def test_data_path_multiple_components_joined_with_hyphens(mocker):
    mock_data_path = Path("/mock/data")
    result = data_path(mock_data_path, "guild", "roster", "export")

    assert result == mock_data_path / "guild-roster-export.csv"


@pytest.mark.parametrize(
    "components,expected_filename",
    [
        # Components with special characters
        (("guild_name", "data"), "guild_name-data.csv"),
        (("user.profile", "export"), "user.profile-export.csv"),
        (("data123", "test456"), "data123-test456.csv"),
        # Components with numbers
        (("guild1", "roster2"), "guild1-roster2.csv"),
    ],
)
def test_data_path_special_characters_handled_correctly(
    components: tuple[str, ...], expected_filename: str, mocker
):
    mock_data_path = Path("/test")
    result = data_path(mock_data_path, *components)

    assert result == mock_data_path / expected_filename


def test_data_path_leading_slash_stripped_correctly(mocker):
    mock_data_path = Path("/data")
    result = data_path(mock_data_path, "/guild", "roster")

    assert result == mock_data_path / "guild-roster.csv"


def test_data_path_no_arguments_raises_value_error():
    with pytest.raises(ValueError, match="At least one path component is required"):
        data_path(Path("/data"))


def test_data_path_returns_pathlib_path_object(mocker):
    mock_data_path = Path("/test")
    result = data_path(mock_data_path, "test")

    assert isinstance(result, Path)


def test_data_path_always_adds_csv_extension(mocker):
    mock_data_path = Path("/data")

    result1 = data_path(mock_data_path, "file")
    result2 = data_path(mock_data_path, "guild", "members")
    result3 = data_path(mock_data_path, "a", "b", "c", "d")

    assert result1.suffix == ".csv"
    assert result2.suffix == ".csv"
    assert result3.suffix == ".csv"


@pytest.mark.parametrize(
    "components",
    [
        ("",),  # Empty string component
        ("guild", ""),  # Mixed with empty string
        ("   ", "roster"),  # Whitespace component
    ],
)
def test_data_path_empty_components_handled_correctly(
    components: tuple[str, ...], mocker
):
    mock_data_path = Path("/data")
    result = data_path(mock_data_path, *components)

    expected_filename = "-".join(components) + ".csv"
    assert result == mock_data_path / expected_filename
