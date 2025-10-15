import pytest

from groster.utils import format_timestamp


class TestFormatTimestamp:
    """Test suite for format_timestamp function."""

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
        self, timestamp_ms: int, expected_datetime_str: str
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
        self, timestamp_ms: int, timezone: str, expected_datetime_str: str
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
        self, timestamp_string: str, expected_datetime_str: str
    ):
        result = format_timestamp(timestamp_string)

        assert result == expected_datetime_str

    def test_format_timestamp_string_input_custom_timezone_works_correctly(self):
        # Test string input with custom timezone
        timestamp_string = "1704067200000"

        result = format_timestamp(timestamp_string, to_tz="UTC")

        assert result == "2024-01-01 00:00:00"

    @pytest.mark.parametrize("invalid_timestamp", [0, None, "0"])
    def test_format_timestamp_invalid_timestamp_returns_na(self, invalid_timestamp):
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
    def test_format_timestamp_invalid_string_raises_value_error(
        self, invalid_string: str
    ):
        with pytest.raises(
            ValueError, match=r"invalid literal for int\(\) with base 10"
        ):
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
        self, invalid_type, expected_error_pattern: str
    ):
        with pytest.raises(ValueError, match=expected_error_pattern):
            format_timestamp(invalid_type)

    def test_format_timestamp_float_input_works_correctly(self):
        # Test with float timestamp
        timestamp_float = 1704067200000.5  # Half a millisecond

        result = format_timestamp(timestamp_float)

        assert result == "2024-01-01 01:00:00"

    def test_format_timestamp_format_matches_expected_pattern(self):
        # Test that output always matches YYYY-MM-DD HH:MM:SS format
        timestamp_ms = 1704067200000

        result = format_timestamp(timestamp_ms)

        # Verify format using regex
        import re

        pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
        assert re.match(pattern, result), (
            f"Format doesn't match expected pattern: {result}"
        )

    def test_format_timestamp_boundary_values_work_correctly(self):
        # Test edge cases with very small and large timestamps
        # Epoch start: January 1, 1970 00:00:00 UTC
        epoch_start = 0
        result_epoch = format_timestamp(epoch_start)
        assert result_epoch == "N/A"  # Should handle 0 as special case

        # Small positive timestamp: January 1, 1970 00:00:01 UTC = 1000 ms
        small_timestamp = 1000
        result_small = format_timestamp(small_timestamp)
        assert result_small == "1970-01-01 01:00:01"  # Europe/Paris UTC+1

    def test_format_timestamp_large_timestamp_works_correctly(self):
        # Test with a large timestamp (year 2050)
        # January 1, 2050 00:00:00 UTC = 2524608000000 ms
        large_timestamp = 2524608000000

        result = format_timestamp(large_timestamp)

        assert result == "2050-01-01 01:00:00"
