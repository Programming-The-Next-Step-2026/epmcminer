"""Tests for epmcminer.api.orcid_client."""

import pytest
import requests
import responses

from epmcminer.api.orcid_client import ORCID_API_BASE, OrcidClient

_ORCID = "0000-0001-5109-3700"
_ORCID_URL = f"{ORCID_API_BASE}/{_ORCID}"


@pytest.fixture
def client() -> OrcidClient:
    """Return a fresh OrcidClient instance."""
    return OrcidClient()


class TestCheckExists:
    """Tests for OrcidClient.check_exists."""

    @responses.activate
    def test_200_response_returns_true(self, client: OrcidClient) -> None:
        """A 200 HTTP response means the ORCID exists in the registry."""
        responses.add(responses.GET, _ORCID_URL, json={}, status=200)
        assert client.check_exists(_ORCID) is True

    @responses.activate
    def test_404_response_returns_false(self, client: OrcidClient) -> None:
        """A 404 HTTP response means the ORCID is not in the registry."""
        responses.add(responses.GET, _ORCID_URL, body="Not Found", status=404)
        assert client.check_exists(_ORCID) is False

    @responses.activate
    def test_other_non_200_returns_false(self, client: OrcidClient) -> None:
        """A non-200, non-404 response (e.g. 503) returns False rather than raising."""
        responses.add(responses.GET, _ORCID_URL, body="Service Unavailable", status=503)
        assert client.check_exists(_ORCID) is False

    @responses.activate
    def test_correct_url_is_requested(self, client: OrcidClient) -> None:
        """The request URL is built from ORCID_API_BASE and the orcid argument."""
        responses.add(responses.GET, _ORCID_URL, json={}, status=200)
        client.check_exists(_ORCID)
        assert responses.calls[0].request.url.startswith(_ORCID_URL)

    @responses.activate
    def test_accept_header_sent(self, client: OrcidClient) -> None:
        """The Accept: application/json header is included in the request."""
        responses.add(responses.GET, _ORCID_URL, json={}, status=200)
        client.check_exists(_ORCID)
        assert responses.calls[0].request.headers.get("Accept") == "application/json"

    @responses.activate
    def test_connection_error_raises_connection_error(self, client: OrcidClient) -> None:
        """A network-level connection failure is re-raised as a built-in ConnectionError."""
        responses.add(
            responses.GET,
            _ORCID_URL,
            body=requests.exceptions.ConnectionError("connection refused"),
        )
        with pytest.raises(ConnectionError):
            client.check_exists(_ORCID)
