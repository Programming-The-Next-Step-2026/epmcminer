"""Tests for epmcminer.api.client."""

import threading
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
    InvalidPdfContentError,
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
        """A non-200, non-429 response raises APIError immediately without retrying."""
        responses.add(responses.GET, SEARCH_URL, body="Internal Server Error", status=500)

        with patch("epmcminer.api.client.time.sleep"), pytest.raises(APIError) as exc_info:
            client.search(query="depression", page_size=10)

        assert exc_info.value.status_code == 500
        assert "500" in str(exc_info.value)
        assert len(responses.calls) == 1

    @responses.activate
    def test_search_429_is_retried_and_succeeds(self, client: EuropePMCClient) -> None:
        """A 429 response is retried and succeeds on the next attempt."""
        responses.add(responses.GET, SEARCH_URL, body="Too Many Requests", status=429)
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_RESPONSE, status=200)

        with patch("epmcminer.api.client.time.sleep") as mock_sleep:
            result = client.search(query="depression", page_size=10)

        assert result["hitCount"] == 2
        assert len(responses.calls) == 2
        mock_sleep.assert_called_once()

    @responses.activate
    def test_search_429_exhausted_raises_api_error(self, client: EuropePMCClient) -> None:
        """A persistent 429 raises APIError after exhausting all retries."""
        for _ in range(3):
            responses.add(responses.GET, SEARCH_URL, body="Too Many Requests", status=429)

        with patch("epmcminer.api.client.time.sleep"), pytest.raises(APIError) as exc_info:
            client.search(query="depression", page_size=10)

        assert exc_info.value.status_code == 429
        assert len(responses.calls) == 3

    @responses.activate
    def test_search_429_uses_retry_after_header(self, client: EuropePMCClient) -> None:
        """search() uses the Retry-After header value as the sleep delay on 429."""
        responses.add(
            responses.GET, SEARCH_URL,
            body="Too Many Requests", status=429,
            headers={"Retry-After": "7"},
        )
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_RESPONSE, status=200)

        with patch("epmcminer.api.client.time.sleep") as mock_sleep:
            client.search(query="depression", page_size=10)

        mock_sleep.assert_called_once_with(7.0)

    @responses.activate
    def test_search_429_non_numeric_retry_after_falls_back_to_backoff(
        self, client: EuropePMCClient
    ) -> None:
        """A non-numeric Retry-After header (e.g. HTTP-date) falls back to backoff delay."""
        responses.add(
            responses.GET, SEARCH_URL,
            body="Too Many Requests", status=429,
            headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"},
        )
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_RESPONSE, status=200)

        with patch("epmcminer.api.client.time.sleep") as mock_sleep:
            client.search(query="depression", page_size=10)

        # Backoff for attempt 0: _RETRY_BACKOFF_BASE * (2**0) = 1
        mock_sleep.assert_called_once_with(1)

    @responses.activate
    def test_search_connection_error_is_retried_and_succeeds(
        self, client: EuropePMCClient
    ) -> None:
        """A transient ConnectionError on search is retried and succeeds."""
        responses.add(
            responses.GET, SEARCH_URL,
            body=requests.exceptions.ConnectionError("dropped"),
        )
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_RESPONSE, status=200)

        with patch("epmcminer.api.client.time.sleep"):
            result = client.search(query="depression", page_size=10)

        assert result["hitCount"] == 2
        assert len(responses.calls) == 2

    @responses.activate
    def test_search_persistent_connection_error_raises_connection_error(
        self, client: EuropePMCClient
    ) -> None:
        """Persistent ConnectionError on search raises ConnectionError after all retries."""
        for _ in range(3):
            responses.add(
                responses.GET, SEARCH_URL,
                body=requests.exceptions.ConnectionError("dropped"),
            )

        with patch("epmcminer.api.client.time.sleep"), pytest.raises(ConnectionError):
            client.search(query="depression", page_size=10)

        assert len(responses.calls) == 3

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
    def test_html_response_raises_invalid_pdf_content_error(
        self, client: EuropePMCClient
    ) -> None:
        """A 200 response whose body is not PDF bytes raises InvalidPdfContentError."""
        html_body = b"<html><head><title>Preparing to download...</title></head></html>"
        responses.add(responses.GET, self.PDF_URL, body=html_body, status=200)

        with pytest.raises(InvalidPdfContentError):
            client.download_pdf(url=self.PDF_URL)

    @responses.activate
    def test_non_pdf_bytes_raise_invalid_pdf_content_error(
        self, client: EuropePMCClient
    ) -> None:
        """Any 200 response body not starting with %PDF raises InvalidPdfContentError."""
        responses.add(responses.GET, self.PDF_URL, body=b"not a pdf", status=200)

        with pytest.raises(InvalidPdfContentError):
            client.download_pdf(url=self.PDF_URL)

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

        with patch("epmcminer.api.client.time.sleep"), pytest.raises(APIError) as exc_info:
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

        with patch("epmcminer.api.client.time.sleep") as mock_sleep, pytest.raises(APIError):
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

        with patch("epmcminer.api.client.time.sleep"), pytest.raises(ConnectionError):
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

        with patch("epmcminer.api.client.time.sleep") as mock_sleep, pytest.raises(ConnectionError):
            client.download_pdf(url=self.PDF_URL)

        assert mock_sleep.call_count == 2
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1, 2]

    @responses.activate
    def test_4xx_error_not_retried(self, client: EuropePMCClient) -> None:
        """A 4xx HTTP response raises APIError immediately without retrying."""
        responses.add(responses.GET, self.PDF_URL, body="Forbidden", status=403)

        with patch("epmcminer.api.client.time.sleep") as mock_sleep, pytest.raises(APIError):
            client.download_pdf(url=self.PDF_URL)

        mock_sleep.assert_not_called()
        assert len(responses.calls) == 1

    @responses.activate
    def test_timeout_is_retried_and_succeeds(self, client: EuropePMCClient) -> None:
        """A transient Timeout is retried and succeeds on a later attempt."""
        responses.add(
            responses.GET, self.PDF_URL, body=requests.exceptions.Timeout("timed out")
        )
        responses.add(responses.GET, self.PDF_URL, body=self.PDF_BYTES, status=200)

        with patch("epmcminer.api.client.time.sleep"):
            result = client.download_pdf(url=self.PDF_URL)

        assert result == self.PDF_BYTES
        assert len(responses.calls) == 2

    @responses.activate
    def test_timeout_exhausted_raises_connection_error(self, client: EuropePMCClient) -> None:
        """A persistent Timeout raises ConnectionError after all retries are exhausted."""
        for _ in range(3):
            responses.add(
                responses.GET, self.PDF_URL, body=requests.exceptions.Timeout("timed out")
            )

        with patch("epmcminer.api.client.time.sleep"), pytest.raises(ConnectionError):
            client.download_pdf(url=self.PDF_URL)

        assert len(responses.calls) == 3

    @responses.activate
    def test_cancel_event_set_before_first_attempt_skips_all_requests(
        self, client: EuropePMCClient
    ) -> None:
        """When cancel_event is already set, no HTTP request is made."""
        cancel_event = threading.Event()
        cancel_event.set()

        with pytest.raises(ConnectionError):
            client.download_pdf(url=self.PDF_URL, cancel_event=cancel_event)

        assert len(responses.calls) == 0

    @responses.activate
    def test_cancel_event_during_backoff_sleep_aborts_retries(
        self, client: EuropePMCClient
    ) -> None:
        """Setting cancel_event during a backoff sleep aborts further retry attempts."""
        cancel_event = threading.Event()
        responses.add(
            responses.GET, self.PDF_URL, body=requests.exceptions.ConnectionError("drop")
        )

        def fake_wait(timeout: float) -> bool:
            cancel_event.set()
            return True  # True means the event fired (cancelled)

        with (
            patch.object(cancel_event, "wait", side_effect=fake_wait),
            pytest.raises(ConnectionError),
        ):
            client.download_pdf(url=self.PDF_URL, cancel_event=cancel_event)

        # Only one HTTP attempt — cancelled during the sleep after the first failure.
        assert len(responses.calls) == 1

    @responses.activate
    def test_cancel_event_not_set_uses_time_sleep(self, client: EuropePMCClient) -> None:
        """When cancel_event is not provided, time.sleep is used for backoff."""
        cancel_event = threading.Event()  # not set
        responses.add(
            responses.GET, self.PDF_URL, body=requests.exceptions.ConnectionError("drop")
        )
        responses.add(responses.GET, self.PDF_URL, body=self.PDF_BYTES, status=200)

        with patch("epmcminer.api.client.time.sleep") as mock_sleep:
            result = client.download_pdf(url=self.PDF_URL, cancel_event=cancel_event)

        assert result == self.PDF_BYTES
        # cancel_event was not set, so time.sleep was NOT used (cancel_event.wait was used)
        mock_sleep.assert_not_called()

    @responses.activate
    def test_429_is_retried_and_succeeds_with_retry_after_header(
        self, client: EuropePMCClient
    ) -> None:
        """A 429 with a Retry-After header is retried using the header value as delay."""
        responses.add(
            responses.GET, self.PDF_URL,
            body="Too Many Requests", status=429,
            headers={"Retry-After": "3"},
        )
        responses.add(responses.GET, self.PDF_URL, body=self.PDF_BYTES, status=200)

        with patch("epmcminer.api.client.time.sleep") as mock_sleep:
            result = client.download_pdf(url=self.PDF_URL)

        assert result == self.PDF_BYTES
        assert len(responses.calls) == 2
        mock_sleep.assert_called_once_with(3.0)

    @responses.activate
    def test_429_uses_exponential_backoff_when_no_retry_after_header(
        self, client: EuropePMCClient
    ) -> None:
        """A 429 without Retry-After falls back to exponential backoff (1 s, 2 s)."""
        for _ in range(3):
            responses.add(responses.GET, self.PDF_URL, body="Too Many Requests", status=429)

        with patch("epmcminer.api.client.time.sleep") as mock_sleep, pytest.raises(APIError):
            client.download_pdf(url=self.PDF_URL)

        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1, 2]

    @responses.activate
    def test_429_exhausted_raises_api_error(self, client: EuropePMCClient) -> None:
        """A persistent 429 raises APIError(429) after all retries are exhausted."""
        for _ in range(3):
            responses.add(responses.GET, self.PDF_URL, body="Too Many Requests", status=429)

        with patch("epmcminer.api.client.time.sleep"), pytest.raises(APIError) as exc_info:
            client.download_pdf(url=self.PDF_URL)

        assert exc_info.value.status_code == 429
        assert len(responses.calls) == 3

    @responses.activate
    def test_5xx_cancel_during_backoff_aborts_retries(self, client: EuropePMCClient) -> None:
        """Setting cancel_event during a 5xx backoff sleep aborts further retry attempts."""
        cancel_event = threading.Event()
        responses.add(responses.GET, self.PDF_URL, body="Service Unavailable", status=503)

        def fake_wait(timeout: float) -> bool:
            cancel_event.set()
            return True  # event fired — cancelled

        with (
            patch.object(cancel_event, "wait", side_effect=fake_wait),
            pytest.raises(ConnectionError),
        ):
            client.download_pdf(url=self.PDF_URL, cancel_event=cancel_event)

        # One HTTP attempt — cancelled during the sleep after the first 5xx response.
        assert len(responses.calls) == 1

    @responses.activate
    def test_429_is_interruptible_via_cancel_event(self, client: EuropePMCClient) -> None:
        """A 429 retry delay is interruptible via cancel_event.wait."""
        cancel_event = threading.Event()
        responses.add(responses.GET, self.PDF_URL, body="Too Many Requests", status=429)

        def fake_wait(timeout: float) -> bool:
            cancel_event.set()
            return True  # event fired — cancelled

        with (
            patch.object(cancel_event, "wait", side_effect=fake_wait),
            pytest.raises(ConnectionError),
        ):
            client.download_pdf(url=self.PDF_URL, cancel_event=cancel_event)

        assert len(responses.calls) == 1
