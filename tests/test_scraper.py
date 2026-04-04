"""Tests for scraper helper functions (parsing, date handling, amounts).

These tests cover the pure functions in the scraper modules without
needing a browser or network access.
"""

from sunpass.scraper.transactions import (
    _combine_date_time,
    _parse_amount,
    _parse_date,
    _parse_details,
)


class TestParseDate:
    def test_mm_dd_yyyy(self):
        assert _parse_date("01/15/2024") == "2024-01-15"

    def test_mm_dd_yy(self):
        assert _parse_date("03/05/25") == "2025-03-05"

    def test_empty_string(self):
        assert _parse_date("") is None

    def test_whitespace(self):
        assert _parse_date("  ") is None

    def test_invalid_format(self):
        assert _parse_date("not-a-date") is None

    def test_end_of_month(self):
        assert _parse_date("02/28/2024") == "2024-02-28"

    def test_leading_zeros(self):
        assert _parse_date("01/01/2024") == "2024-01-01"


class TestCombineDateTime:
    def test_12h_pm(self):
        result = _combine_date_time("2024-01-15", "05:59:57 PM")
        assert result == "2024-01-15 17:59:57"

    def test_12h_am(self):
        result = _combine_date_time("2024-01-15", "08:30:00 AM")
        assert result == "2024-01-15 08:30:00"

    def test_24h_format(self):
        result = _combine_date_time("2024-01-15", "14:30:00")
        assert result == "2024-01-15 14:30:00"

    def test_invalid_time_passthrough(self):
        result = _combine_date_time("2024-01-15", "bad-time")
        assert result == "2024-01-15 bad-time"

    def test_midnight_12h(self):
        result = _combine_date_time("2024-01-15", "12:00:00 AM")
        assert result == "2024-01-15 00:00:00"

    def test_noon_12h(self):
        result = _combine_date_time("2024-01-15", "12:00:00 PM")
        assert result == "2024-01-15 12:00:00"


class TestParseAmount:
    def test_dollar_sign(self):
        assert _parse_amount("$3.50") == 3.50

    def test_no_dollar_sign(self):
        assert _parse_amount("3.50") == 3.50

    def test_with_comma(self):
        assert _parse_amount("$1,234.56") == 1234.56

    def test_empty_string(self):
        assert _parse_amount("") is None

    def test_whitespace(self):
        assert _parse_amount("  ") is None

    def test_invalid(self):
        assert _parse_amount("abc") is None

    def test_zero(self):
        assert _parse_amount("$0.00") == 0.0


class TestParseDetails:
    def test_full_details(self):
        html = """
        <b>Transaction Number:</b> TXN12345
        <b>Agency Name:</b> Florida Turnpike
        <b>Location:</b> I-95 Main Plaza
        <b>Lane:</b> 4
        <b>Axle:</b> 2
        <b>Transaction Type:</b> Toll
        """
        result = _parse_details(html)
        assert result["transaction_number"] == "TXN12345"
        assert result["agency"] == "Florida Turnpike"
        assert result["location"] == "I-95 Main Plaza"
        assert result["lane"] == "4"
        assert result["axle"] == "2"
        assert result["transaction_type"] == "Toll"

    def test_empty_html(self):
        assert _parse_details("") == {}

    def test_partial_details(self):
        html = '<b>Agency Name:</b> SunPass<br>'
        result = _parse_details(html)
        assert result["agency"] == "SunPass"
        assert "transaction_number" not in result
