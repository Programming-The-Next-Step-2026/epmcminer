"""Tests for epmcminer.api.client."""

import urllib.parse
from unittest.mock import patch

import pytest
import requests
import responses

from epmcminer.api.client import (
    FREE_FULL_TEXT_FILTER,
    SEARCH_URL,
    SORT_BY_DATE,
    APIError,
    EuropePMCClient,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEARCH_RESPONSE = {
    "version": "6.8",
    "hitCount": 2,
    "nextCursorMark": "AoE=",
    "resultList": {
        "result": [
            {
                "id": "12345678",
                "pmid": "12345678",
                "title": "A study on depression",
                "authorString": "Smith J, Jones A",
                "journalTitle": "Journal of Psychiatry",
                "pubYear": "2022",
            }
        ]
    },
}

EMPTY_SEARCH_RESPONSE = {
    "version": "6.8",
    "hitCount": 0,
    "nextCursorMark": "*",
    "resultList": {"result": []},
}


@pytest.fixture
def client() -> EuropePMCClient:
    """Return a fresh EuropePMCClient instance."""
    return EuropePMCClient()


# ---------------------------------------------------------------------------
# EuropePMCClient.search
# ---------------------------------------------------------------------------


class TestSearch:
    """Tests for EuropePMCClient.search."""

    @responses.activate
    def test_successful_search_returns_dict(self, client: EuropePMCClient) -> None:
        """A 200 response is returned as a parsed dict."""
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_RESPONSE, status=200)

        result = client.search(query="depression", page_size=10)

        assert result["hitCount"] == 2
        assert result["resultList"]["result"][0]["pmid"] == "12345678"

    @responses.activate
    def test_search_appends_free_full_text_filter(self, client: EuropePMCClient) -> None:
        """The free-full-text filter is always appended to the query."""
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_RESPONSE, status=200)

        client.search(query="depression", page_size=10)

        sent_query = urllib.parse.parse_qs(
            urllib.parse.urlparse(responses.calls[0].request.url).query
        )["query"][0]
        assert FREE_FULL_TEXT_FILTER in sent_query

    @responses.activate
    def test_search_omits_sort_when_none(self, client: EuropePMCClient) -> None:
        """No sort parameter is sent when sort=None (defaults to relevance)."""
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_RESPONSE, status=200)

        client.search(query="depression", page_size=10)

        sent_params = urllib.parse.parse_qs(
            urllib.parse.urlparse(responses.calls[0].request.url).query
        )
        assert "sort" not in sent_params

    @responses.activate
    def test_search_includes_sort_when_provided(self, client: EuropePMCClient) -> None:
        """The sort parameter is forwarded to the API when provided."""
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_RESPONSE, status=200)

        client.search(query="depression", page_size=10, sort=SORT_BY_DATE)

        sent_params = urllib.parse.parse_qs(
            urllib.parse.urlparse(responses.calls[0].request.url).query
        )
        assert sent_params["sort"][0] == SORT_BY_DATE

    @responses.activate
    def test_search_api_error_raises_api_error(self, client: EuropePMCClient) -> None:
        """A non-200 response raises APIError with status code and body."""
        responses.add(responses.GET, SEARCH_URL, body="Internal Server Error", status=500)

        with pytest.raises(APIError) as exc_info:
            client.search(query="depression", page_size=10)

        assert exc_info.value.status_code == 500
        assert "500" in str(exc_info.value)

    @responses.activate
    def test_search_empty_results(self, client: EuropePMCClient) -> None:
        """A 200 response with no results returns an empty result list."""
        responses.add(responses.GET, SEARCH_URL, json=EMPTY_SEARCH_RESPONSE, status=200)

        result = client.search(query="xyzzy_no_match", page_size=10)

        assert result["hitCount"] == 0
        assert result["resultList"]["result"] == []

    @responses.activate
    def test_search_passes_cursor_mark(self, client: EuropePMCClient) -> None:
        """The cursorMark parameter is forwarded to the API."""
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_RESPONSE, status=200)

        client.search(query="depression", page_size=10, cursor_mark="AoE=")

        sent_params = urllib.parse.parse_qs(
            urllib.parse.urlparse(responses.calls[0].request.url).query
        )
        assert sent_params["cursorMark"][0] == "AoE="


# ---------------------------------------------------------------------------
# EuropePMCClient.download_pdf
# ---------------------------------------------------------------------------


class TestDownloadPdf:
    """Tests for EuropePMCClient.download_pdf."""

    PDF_URL = "https://europepmc.org/articles/PMC1234567?pdf=render"
    PDF_BYTES = b"%PDF-1.4 test content"

    @responses.activate
    def test_successful_download_returns_bytes(self, client: EuropePMCClient) -> None:
        """A 200 response returns the PDF content as bytes."""
        responses.add(responses.GET, self.PDF_URL, body=self.PDF_BYTES, status=200)

        result = client.download_pdf(url=self.PDF_URL)

        assert result == self.PDF_BYTES

    @responses.activate
    def test_non_200_raises_api_error(self, client: EuropePMCClient) -> None:
        """A non-200 response raises APIError with the correct status code."""
        responses.add(responses.GET, self.PDF_URL, body="Not Found", status=404)

        with pytest.raises(APIError) as exc_info:
            client.download_pdf(url=self.PDF_URL)

        assert exc_info.value.status_code == 404

    @responses.activate
    def test_server_error_raises_api_error_after_retries(self, client: EuropePMCClient) -> None:
        """A persistent 500 response raises APIError after exhausting all retries."""
        for _ in range(3):
            responses.add(responses.GET, self.PDF_URL, body="Server Error", status=500)

        with patch("epmcminer.api.client.time.sleep"):
            with pytest.raises(APIError) as exc_info:
                client.download_pdf(url=self.PDF_URL)

        assert exc_info.value.status_code == 500
        assert len(responses.calls) == 3

    @responses.activate
    def test_api_error_includes_status_code_in_message(self, client: EuropePMCClient) -> None:
        """The APIError message includes the HTTP status code."""
        responses.add(responses.GET, self.PDF_URL, body="Forbidden", status=403)

        with pytest.raises(APIError) as exc_info:
            client.download_pdf(url=self.PDF_URL)

        assert "403" in str(exc_info.value)

    @responses.activate
    def test_5xx_is_retried_and_succeeds(self, client: EuropePMCClient) -> None:
        """A transient 5xx error is retried and succeeds on a later attempt."""
        responses.add(responses.GET, self.PDF_URL, body="Service Unavailable", status=503)
        responses.add(responses.GET, self.PDF_URL, body=self.PDF_BYTES, status=200)

        with patch("epmcminer.api.client.time.sleep"):
            result = client.download_pdf(url=self.PDF_URL)

        assert result == self.PDF_BYTES
        assert len(responses.calls) == 2

    @responses.activate
    def test_5xx_retry_uses_exponential_backoff(self, client: EuropePMCClient) -> None:
        """5xx retry delays follow 1 s, 2 s exponential backoff."""
        for _ in range(3):
            responses.add(responses.GET, self.PDF_URL, body="Server Error", status=500)

        with patch("epmcminer.api.client.time.sleep") as mock_sleep:
            with pytest.raises(APIError):
                client.download_pdf(url=self.PDF_URL)

        assert mock_sleep.call_count == 2
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1, 2]

    @responses.activate
    def test_connection_error_is_retried_and_succeeds(self, client: EuropePMCClient) -> None:
        """A transient ConnectionError is retried and succeeds on a later attempt."""
        responses.add(
            responses.GET, self.PDF_URL, body=requests.exceptions.ConnectionError("dropped")
        )
        responses.add(responses.GET, self.PDF_URL, body=self.PDF_BYTES, status=200)

        with patch("epmcminer.api.client.time.sleep"):
            result = client.download_pdf(url=self.PDF_URL)

        assert result == self.PDF_BYTES
        assert len(responses.calls) == 2

    @responses.activate
    def test_connection_error_exhausted_raises_connection_error(
        self, client: EuropePMCClient
    ) -> None:
        """ConnectionError is raised (as built-in) after all retry attempts fail."""
        for _ in range(3):
            responses.add(
                responses.GET,
                self.PDF_URL,
                body=requests.exceptions.ConnectionError("dropped"),
            )

        with patch("epmcminer.api.client.time.sleep"):
            with pytest.raises(ConnectionError):
                client.download_pdf(url=self.PDF_URL)

        assert len(responses.calls) == 3

    @responses.activate
    def test_connection_error_retry_uses_exponential_backoff(
        self, client: EuropePMCClient
    ) -> None:
        """Retry delays follow 1 s, 2 s exponential backoff."""
        for _ in range(3):
            responses.add(
                responses.GET,
                self.PDF_URL,
                body=requests.exceptions.ConnectionError("dropped"),
            )

        with patch("epmcminer.api.client.time.sleep") as mock_sleep:
            with pytest.raises(ConnectionError):
                client.download_pdf(url=self.PDF_URL)

        assert mock_sleep.call_count == 2
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1, 2]

    @responses.activate
    def test_4xx_error_not_retried(self, client: EuropePMCClient) -> None:
        """A 4xx HTTP response raises APIError immediately without retrying."""
        responses.add(responses.GET, self.PDF_URL, body="Forbidden", status=403)

        with patch("epmcminer.api.client.time.sleep") as mock_sleep:
            with pytest.raises(APIError):
                client.download_pdf(url=self.PDF_URL)

        mock_sleep.assert_not_called()
        assert len(responses.calls) == 1
