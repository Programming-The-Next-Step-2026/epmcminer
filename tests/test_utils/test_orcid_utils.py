"""Tests for epmcminer.utils.orcid_utils."""

import pytest

from epmcminer.utils.orcid_utils import normalise_orcid, validate_orcid_format

# ---------------------------------------------------------------------------
# TestValidateOrcidFormat
# ---------------------------------------------------------------------------


class TestValidateOrcidFormat:
    """Tests for validate_orcid_format."""

    @pytest.mark.parametrize(
        "orcid",
        [
            "0000-0001-5109-3700",
            "0000-0002-1825-0097",
            "0000-0003-1419-2405",
        ],
    )
    def test_known_valid_orcids_accepted(self, orcid: str) -> None:
        """Known valid ORCIDs with correct checksums are accepted."""
        assert validate_orcid_format(orcid) is True

    def test_valid_orcid_with_https_prefix_accepted(self) -> None:
        """A valid ORCID with https://orcid.org/ prefix is accepted after stripping."""
        assert validate_orcid_format("https://orcid.org/0000-0001-5109-3700") is True

    def test_valid_orcid_with_http_prefix_accepted(self) -> None:
        """A valid ORCID with http://orcid.org/ prefix is accepted after stripping."""
        assert validate_orcid_format("http://orcid.org/0000-0001-5109-3700") is True

    def test_wrong_checksum_digit_rejected(self) -> None:
        """A correctly formatted ORCID with a wrong checksum digit is rejected."""
        # 0000-0001-5109-3700 is valid; change last digit to 1
        assert validate_orcid_format("0000-0001-5109-3701") is False

    def test_too_short_rejected(self) -> None:
        """An ORCID with fewer than four groups is rejected."""
        assert validate_orcid_format("0000-0001-5109") is False

    def test_too_many_groups_rejected(self) -> None:
        """An ORCID with more than four groups is rejected."""
        assert validate_orcid_format("0000-0001-5109-3700-0000") is False

    def test_letters_in_body_rejected(self) -> None:
        """Non-digit characters in the first 15 positions are rejected."""
        assert validate_orcid_format("000A-0001-5109-3700") is False

    def test_no_dashes_rejected(self) -> None:
        """Missing dashes (no separators) are rejected."""
        assert validate_orcid_format("0000000151093700") is False

    def test_empty_string_rejected(self) -> None:
        """An empty string is rejected."""
        assert validate_orcid_format("") is False

    def test_random_string_rejected(self) -> None:
        """A random non-ORCID string is rejected."""
        assert validate_orcid_format("not-an-orcid") is False

    def test_url_prefix_with_invalid_orcid_rejected(self) -> None:
        """A URL-prefixed ORCID with a wrong checksum is still rejected."""
        assert validate_orcid_format("https://orcid.org/0000-0001-5109-3701") is False

    def test_whitespace_around_orcid_accepted(self) -> None:
        """Leading and trailing whitespace is stripped before validation."""
        assert validate_orcid_format("  0000-0001-5109-3700  ") is True

    def test_extra_dash_in_group_rejected(self) -> None:
        """An extra dash splitting a group is rejected."""
        assert validate_orcid_format("0000-000-1-5109-3700") is False


# ---------------------------------------------------------------------------
# TestNormaliseOrcid
# ---------------------------------------------------------------------------


class TestNormaliseOrcid:
    """Tests for normalise_orcid."""

    def test_strips_https_prefix(self) -> None:
        """https://orcid.org/ prefix is stripped."""
        assert normalise_orcid("https://orcid.org/0000-0001-5109-3700") == "0000-0001-5109-3700"

    def test_strips_http_prefix(self) -> None:
        """http://orcid.org/ prefix is stripped."""
        assert normalise_orcid("http://orcid.org/0000-0001-5109-3700") == "0000-0001-5109-3700"

    def test_plain_id_unchanged(self) -> None:
        """An ORCID without a URL prefix is returned unchanged."""
        assert normalise_orcid("0000-0001-5109-3700") == "0000-0001-5109-3700"

    def test_leading_whitespace_stripped(self) -> None:
        """Leading whitespace is stripped."""
        assert normalise_orcid("  0000-0001-5109-3700") == "0000-0001-5109-3700"

    def test_trailing_whitespace_stripped(self) -> None:
        """Trailing whitespace is stripped."""
        assert normalise_orcid("0000-0001-5109-3700  ") == "0000-0001-5109-3700"

    def test_whitespace_around_url_stripped(self) -> None:
        """Whitespace is stripped even when a URL prefix is present."""
        assert (
            normalise_orcid("  https://orcid.org/0000-0001-5109-3700  ")
            == "0000-0001-5109-3700"
        )
