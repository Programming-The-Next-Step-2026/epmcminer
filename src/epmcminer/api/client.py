"""Europe PMC API HTTP client — raw HTTP calls only, no business logic."""

import threading
import time
from typing import Any, cast

import requests

from epmcminer.utils.logger import get_logger

_logger = get_logger(__name__)

SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
FREE_FULL_TEXT_FILTER = "HAS_FT:Y OR HAS_FREE_FULLTEXT:Y"
RESPONSE_FORMAT = "json"
RESULT_TYPE = "core"
DEFAULT_SOURCE = "MED"
DEFAULT_CURSOR_MARK = "*"
PDF_DOCUMENT_STYLE = "pdf"
SORT_BY_DATE = "P_PDATE_D desc"
SORT_BY_CITATIONS = "CITED desc"
REQUEST_TIMEOUT = 30

_HTTP_429_TOO_MANY_REQUESTS = 429
# Both search and PDF download share the same retry policy.
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 1

_PDF_MAGIC_BYTES = b"%PDF"


def _parse_retry_after(response: requests.Response) -> float | None:
    """Return the Retry-After delay in seconds, or None if the header is absent or invalid.

    Args:
        response: The HTTP response that included a Retry-After header.

    Returns:
        The number of seconds to wait as a float, or None.

    """
    header = response.headers.get("Retry-After")
    if header is None:
        return None
    try:
        return float(header)
    except ValueError:
        return None


class InvalidPdfContentError(Exception):
    """Raised when a 200 response body does not contain valid PDF bytes.

    This typically occurs when the server returns an HTML challenge or error page
    instead of the PDF file (e.g. a bot-detection Proof-of-Work page).
    """


class APIError(Exception):
    """Raised when the Europe PMC API returns a non-200 HTTP response.

    Attributes:
        status_code: The HTTP status code returned by the API.
        body: The raw response body text.

    """

    def __init__(self, status_code: int, body: str) -> None:
        """Initialise APIError with status code and response body.

        Args:
            status_code: The HTTP status code returned by the API.
            body: The raw response body text.

        """
        super().__init__(f"Europe PMC API error {status_code}: {body}")
        self.status_code = status_code
        self.body = body


class EuropePMCClient:
    """HTTP client for the Europe PMC REST API.

    Makes raw HTTP requests and returns parsed JSON. Contains no business
    logic — all interpretation of results belongs in the service layer.
    Uses a persistent requests.Session for connection reuse.
    """

    def __init__(self) -> None:
        """Initialise the client with a new requests Session."""
        self._session = requests.Session()

    def search(
        self,
        query: str,
        page_size: int,
        sort: str | None = None,
        cursor_mark: str = DEFAULT_CURSOR_MARK,
    ) -> dict[str, Any]:
        """Query the Europe PMC search endpoint.

        Appends the free-full-text availability filter to every query so
        that only open-access papers with a retrievable PDF are returned.

        Args:
            query: The search query string.
            page_size: Maximum number of results to return per page.
            sort: API sort string, e.g. ``SORT_BY_DATE`` or
                ``SORT_BY_CITATIONS``. Omit (or pass ``None``) to use
                the default relevance ordering.
            cursor_mark: Pagination cursor. Use ``DEFAULT_CURSOR_MARK``
                for the first page and the ``nextCursorMark`` value from
                the previous response for subsequent pages.

        Returns:
            The raw JSON response from the API as a dict.

        Raises:
            APIError: If the API returns a non-200, non-retryable HTTP status code, or if
                a 429 persists after all retry attempts.
            ConnectionError: If the HTTP request cannot be completed after all retries.

        Examples:
            >>> client = EuropePMCClient()
            >>> data = client.search("depression AND therapy", page_size=10)
            >>> print(data["hitCount"])
            4231
            >>> print(data["resultList"]["result"][0]["title"])
            'Cognitive behavioural therapy for depression: a meta-analysis'

        """
        full_query = f"({query}) AND ({FREE_FULL_TEXT_FILTER})"
        params: dict[str, Any] = {
            "query": full_query,
            "format": RESPONSE_FORMAT,
            "resultType": RESULT_TYPE,
            "pageSize": page_size,
            "cursorMark": cursor_mark,
        }
        if sort is not None:
            params["sort"] = sort

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._session.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_BACKOFF_BASE * (2**attempt)
                    _logger.warning(
                        "search transient error (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                continue
            if response.status_code == 200:
                return cast(dict[str, Any], response.json())
            if response.status_code == _HTTP_429_TOO_MANY_REQUESTS:
                delay = _parse_retry_after(response) or (_RETRY_BACKOFF_BASE * (2**attempt))
                last_exc = APIError(response.status_code, response.text)
                if attempt < _MAX_RETRIES - 1:
                    _logger.warning(
                        "search HTTP 429 (attempt %d/%d), retrying in %.1fs",
                        attempt + 1,
                        _MAX_RETRIES,
                        delay,
                    )
                    time.sleep(delay)
                continue
            raise APIError(response.status_code, response.text)

        # All retries exhausted.
        if isinstance(
            last_exc,
            (requests.exceptions.ConnectionError, requests.exceptions.Timeout),
        ):
            raise ConnectionError(str(last_exc)) from last_exc
        raise last_exc if last_exc is not None else APIError(0, "unknown")

    def download_pdf(
        self,
        url: str,
        cancel_event: threading.Event | None = None,
    ) -> bytes:
        """Download a PDF from a direct URL.

        Retries up to ``_MAX_RETRIES`` times on connection errors, timeouts,
        HTTP 5xx responses, and HTTP 429 (Too Many Requests) using exponential
        backoff (1 s, 2 s).  HTTP 429 retries honour the ``Retry-After`` response
        header when present, falling back to the same exponential schedule.
        Other HTTP 4xx errors are not retried as they indicate a client-side problem.

        Backoff sleeps are interruptible: when ``cancel_event`` is provided,
        ``Event.wait`` is used instead of ``time.sleep`` so that setting the
        event wakes the sleeping thread immediately.

        Args:
            url: The direct URL to the open-access PDF file.
            cancel_event: Optional cancellation signal.  When set, the retry
                loop exits as soon as the current backoff sleep finishes (or
                immediately if set before the next attempt) and raises
                ``ConnectionError``.

        Returns:
            The raw bytes of the PDF file.

        Raises:
            APIError: If the server returns a non-retryable HTTP 4xx status code,
                or if a 5xx or 429 error persists after all retry attempts.
            ConnectionError: If the connection fails on all retry attempts, if a
                timeout persists after all retry attempts, or if ``cancel_event``
                is set.

        Examples:
            >>> client = EuropePMCClient()
            >>> pdf_bytes = client.download_pdf("https://europepmc.org/articles/PMC1234567?pdf=render")
            >>> pdf_bytes[:4]
            b'%PDF'

            With cancellation support:

            >>> import threading
            >>> cancel = threading.Event()
            >>> pdf_bytes = client.download_pdf(url, cancel_event=cancel)

        """
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            if cancel_event is not None and cancel_event.is_set():
                break
            try:
                response = self._session.get(url, timeout=REQUEST_TIMEOUT)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_BACKOFF_BASE * (2**attempt)
                    _logger.warning(
                        "download_pdf transient error (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        delay,
                        exc,
                    )
                    if cancel_event is not None:
                        if cancel_event.wait(timeout=delay):
                            break  # cancelled during sleep — exit immediately
                    else:
                        time.sleep(delay)
                continue
            else:
                if response.status_code == 200:
                    if not response.content.startswith(_PDF_MAGIC_BYTES):
                        raise InvalidPdfContentError(
                            f"Response from {url!r} is not a valid PDF "
                            f"(got {response.content[:16]!r})",
                        )
                    return cast(bytes, response.content)
                if response.status_code == _HTTP_429_TOO_MANY_REQUESTS:
                    # Rate-limited: honour the Retry-After hint; fall back to
                    # the same exponential schedule used for 5xx errors.
                    delay = _parse_retry_after(response) or (_RETRY_BACKOFF_BASE * (2**attempt))
                    last_exc = APIError(response.status_code, response.text)
                    if attempt < _MAX_RETRIES - 1:
                        _logger.warning(
                            "download_pdf HTTP 429 (attempt %d/%d), retrying in %.1fs",
                            attempt + 1,
                            _MAX_RETRIES,
                            delay,
                        )
                        if cancel_event is not None:
                            if cancel_event.wait(timeout=delay):
                                break  # cancelled during sleep — exit immediately
                        else:
                            time.sleep(delay)
                    continue
                if 400 <= response.status_code < 500:
                    raise APIError(response.status_code, response.text)
                # 5xx: treat as transient and retry
                last_exc = APIError(response.status_code, response.text)
                if attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_BACKOFF_BASE * (2**attempt)
                    _logger.warning(
                        "download_pdf HTTP %d (attempt %d/%d), retrying in %ds",
                        response.status_code,
                        attempt + 1,
                        _MAX_RETRIES,
                        delay,
                    )
                    if cancel_event is not None:
                        if cancel_event.wait(timeout=delay):
                            break  # cancelled during sleep — exit immediately
                    else:
                        time.sleep(delay)
        if cancel_event is not None and cancel_event.is_set():
            raise ConnectionError("Download cancelled")
        if isinstance(
            last_exc,
            (requests.exceptions.ConnectionError, requests.exceptions.Timeout),
        ):
            raise ConnectionError(str(last_exc)) from last_exc
        raise last_exc if last_exc is not None else APIError(0, "unknown")
