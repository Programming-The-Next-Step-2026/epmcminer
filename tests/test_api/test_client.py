"""Tests for epmcminer.api.client."""

import urllib.parse
from unittest.mock import patch

import pytest
import requests
import responses

from epmcminer.api.client import (
    FREE_FULL_TEXT_FILTER,
    FULL_TEXT_LINKS_URL,
    SEARCH_URL,
    SORT_BY_DATE,
    APIError,
    EuropePMCClient,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PMID = "12345678"
SOURCE = "MED"
FULL_TEXT_URL = FULL_TEXT_LINKS_URL.format(source=SOURCE, pmid=PMID)

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

FULL_TEXT_RESPONSE_WITH_PDF = {
    "version": "6.8",
    "hitCount": 1,
    "fullTextUrlList": {
        "fullTextUrl": [
            {
                "availability": "Open access",
                "availabilityCode": "OA",
                "documentStyle": "html",
                "site": "Europe_PMC",
                "url": "https://europepmc.org/articles/PMC1234567",
            },
            {
                "availability": "Open access",
                "availabilityCode": "OA",
                "documentStyle": "pdf",
                "site": "Europe_PMC",
                "url": "https://europepmc.org/articles/PMC1234567?pdf=render",
            },
        ]
    },
}

FULL_TEXT_RESPONSE_NO_PDF = {
    "version": "6.8",
    "hitCount": 1,
    "fullTextUrlList": {
        "fullTextUrl": [
            {
                "availability": "Open access",
                "availabilityCode": "OA",
                "documentStyle": "html",
                "site": "Europe_PMC",
                "url": "https://europepmc.org/articles/PMC1234567",
            }
        ]
    },
}


@pytest.fixture()
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
# EuropePMCClient.get_pdf_url
# ---------------------------------------------------------------------------


class TestGetPdfUrl:
    """Tests for EuropePMCClient.get_pdf_url."""

    @responses.activate
    def test_pdf_url_found(self, client: EuropePMCClient) -> None:
        """Returns the PDF URL when a pdf documentStyle entry exists."""
        responses.add(responses.GET, FULL_TEXT_URL, json=FULL_TEXT_RESPONSE_WITH_PDF, status=200)

        url = client.get_pdf_url(pmid=PMID, source=SOURCE)

        assert url == "https://europepmc.org/articles/PMC1234567?pdf=render"

    @responses.activate
    def test_pdf_url_not_found(self, client: EuropePMCClient) -> None:
        """Returns None when no pdf documentStyle entry exists."""
        responses.add(responses.GET, FULL_TEXT_URL, json=FULL_TEXT_RESPONSE_NO_PDF, status=200)

        url = client.get_pdf_url(pmid=PMID, source=SOURCE)

        assert url is None

    @responses.activate
    def test_get_pdf_url_returns_none_on_404(self, client: EuropePMCClient) -> None:
        """A 404 response returns None (paper has no full-text links registered)."""
        responses.add(responses.GET, FULL_TEXT_URL, body="Not Found", status=404)

        url = client.get_pdf_url(pmid=PMID, source=SOURCE)

        assert url is None

    @responses.activate
    def test_get_pdf_url_api_error_raises_api_error(self, client: EuropePMCClient) -> None:
        """A non-200, non-404 response raises APIError."""
        responses.add(responses.GET, FULL_TEXT_URL, body="Internal Server Error", status=500)

        with pytest.raises(APIError) as exc_info:
            client.get_pdf_url(pmid=PMID, source=SOURCE)

        assert exc_info.value.status_code == 500

    @responses.activate
    def test_get_pdf_url_default_source_is_med(self, client: EuropePMCClient) -> None:
        """The default source parameter is MED."""
        responses.add(responses.GET, FULL_TEXT_URL, json=FULL_TEXT_RESPONSE_WITH_PDF, status=200)

        client.get_pdf_url(pmid=PMID)

        assert f"/{SOURCE}/" in responses.calls[0].request.url


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
    def test_server_error_raises_api_error(self, client: EuropePMCClient) -> None:
        """A 500 response raises APIError."""
        responses.add(responses.GET, self.PDF_URL, body="Server Error", status=500)

        with pytest.raises(APIError) as exc_info:
            client.download_pdf(url=self.PDF_URL)

        assert exc_info.value.status_code == 500

    @responses.activate
    def test_api_error_includes_status_code_in_message(self, client: EuropePMCClient) -> None:
        """The APIError message includes the HTTP status code."""
        responses.add(responses.GET, self.PDF_URL, body="Forbidden", status=403)

        with pytest.raises(APIError) as exc_info:
            client.download_pdf(url=self.PDF_URL)

        assert "403" in str(exc_info.value)

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
    def test_http_error_not_retried(self, client: EuropePMCClient) -> None:
        """A non-200 HTTP response raises APIError immediately without retrying."""
        responses.add(responses.GET, self.PDF_URL, body="Forbidden", status=403)

        with patch("epmcminer.api.client.time.sleep") as mock_sleep:
            with pytest.raises(APIError):
                client.download_pdf(url=self.PDF_URL)

        mock_sleep.assert_not_called()
        assert len(responses.calls) == 1
