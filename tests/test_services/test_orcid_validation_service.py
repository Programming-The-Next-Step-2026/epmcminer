"""Tests for epmcminer.services.orcid_validation_service."""

import pytest

from epmcminer.api.orcid_client import OrcidClient
from epmcminer.services.orcid_validation_service import OrcidValidationService

_VALID_ORCID = "0000-0001-5109-3700"
_INVALID_ORCID = "0000-0001-5109-3701"  # wrong checksum


@pytest.fixture
def mock_client(mocker) -> OrcidClient:
    """Return a mock OrcidClient."""
    return mocker.MagicMock(spec=OrcidClient)


@pytest.fixture
def service(mock_client: OrcidClient) -> OrcidValidationService:
    """Return an OrcidValidationService backed by a mock client."""
    return OrcidValidationService(client=mock_client)


class TestValidateFormat:
    """Tests for OrcidValidationService.validate_format."""

    def test_valid_orcid_returns_true(self, service: OrcidValidationService) -> None:
        """A correctly formatted ORCID with a valid checksum returns True."""
        assert service.validate_format(_VALID_ORCID) is True

    def test_invalid_checksum_returns_false(self, service: OrcidValidationService) -> None:
        """A correctly formatted ORCID with a wrong checksum returns False."""
        assert service.validate_format(_INVALID_ORCID) is False

    def test_empty_string_returns_false(self, service: OrcidValidationService) -> None:
        """An empty string returns False."""
        assert service.validate_format("") is False

    def test_url_prefixed_valid_orcid_returns_true(self, service: OrcidValidationService) -> None:
        """An ORCID with https://orcid.org/ prefix is accepted after normalisation."""
        assert service.validate_format(f"https://orcid.org/{_VALID_ORCID}") is True

    def test_does_not_call_client(
        self, service: OrcidValidationService, mock_client: OrcidClient
    ) -> None:
        """validate_format is purely local — it never calls the HTTP client."""
        service.validate_format(_VALID_ORCID)
        mock_client.check_exists.assert_not_called()


class TestCheckExists:
    """Tests for OrcidValidationService.check_exists."""

    def test_delegates_to_client(
        self, service: OrcidValidationService, mock_client: OrcidClient
    ) -> None:
        """check_exists delegates the call to OrcidClient.check_exists."""
        mock_client.check_exists.return_value = True
        result = service.check_exists(_VALID_ORCID)
        mock_client.check_exists.assert_called_once_with(_VALID_ORCID)
        assert result is True

    def test_returns_false_when_client_returns_false(
        self, service: OrcidValidationService, mock_client: OrcidClient
    ) -> None:
        """Returns False when the client reports the ORCID does not exist."""
        mock_client.check_exists.return_value = False
        assert service.check_exists(_VALID_ORCID) is False

    def test_propagates_connection_error(
        self, service: OrcidValidationService, mock_client: OrcidClient
    ) -> None:
        """A ConnectionError raised by the client is propagated to the caller."""
        mock_client.check_exists.side_effect = ConnectionError("network failure")
        with pytest.raises(ConnectionError):
            service.check_exists(_VALID_ORCID)


class TestNormalise:
    """Tests for OrcidValidationService.normalise."""

    def test_strips_https_prefix(self, service: OrcidValidationService) -> None:
        """https://orcid.org/ prefix is stripped."""
        assert service.normalise(f"https://orcid.org/{_VALID_ORCID}") == _VALID_ORCID

    def test_strips_http_prefix(self, service: OrcidValidationService) -> None:
        """http://orcid.org/ prefix is stripped."""
        assert service.normalise(f"http://orcid.org/{_VALID_ORCID}") == _VALID_ORCID

    def test_plain_id_unchanged(self, service: OrcidValidationService) -> None:
        """A bare ORCID without a URL prefix is returned unchanged."""
        assert service.normalise(_VALID_ORCID) == _VALID_ORCID

    def test_whitespace_stripped(self, service: OrcidValidationService) -> None:
        """Leading and trailing whitespace is stripped."""
        assert service.normalise(f"  {_VALID_ORCID}  ") == _VALID_ORCID

    def test_does_not_call_client(
        self, service: OrcidValidationService, mock_client: OrcidClient
    ) -> None:
        """normalise is purely local — it never calls the HTTP client."""
        service.normalise(_VALID_ORCID)
        mock_client.check_exists.assert_not_called()
