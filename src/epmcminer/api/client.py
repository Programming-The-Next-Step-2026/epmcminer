"""Europe PMC API HTTP client — raw HTTP calls only, no business logic."""

import requests

SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
FULL_TEXT_LINKS_URL = (
    "https://www.ebi.ac.uk/europepmc/webservices/rest/{source}/{pmid}/fullTextLinks"
)
FREE_FULL_TEXT_FILTER = "HAS_FT:Y OR HAS_FREE_FULLTEXT:Y"
RESPONSE_FORMAT = "json"
RESULT_TYPE = "core"
DEFAULT_SOURCE = "MED"
DEFAULT_CURSOR_MARK = "*"
PDF_DOCUMENT_STYLE = "pdf"


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
        sort: str,
        page_size: int,
        cursor_mark: str = DEFAULT_CURSOR_MARK,
    ) -> dict:
        """Query the Europe PMC search endpoint.

        Appends the free-full-text availability filter to every query so
        that only open-access papers with a retrievable PDF are returned.

        Args:
            query: The search query string.
            sort: Sort order for results, e.g. ``"relevance"``, ``"date"``,
                or ``"cited"``.
            page_size: Maximum number of results to return per page.
            cursor_mark: Pagination cursor. Use ``"*"`` for the first page
                and the ``nextCursorMark`` value from the previous response
                for subsequent pages.

        Returns:
            The raw JSON response from the API as a dict.

        Raises:
            APIError: If the API returns a non-200 HTTP status code.
            ConnectionError: If the HTTP request cannot be completed.
        """
        full_query = f"({query}) AND ({FREE_FULL_TEXT_FILTER})"
        params = {
            "query": full_query,
            "format": RESPONSE_FORMAT,
            "resultType": RESULT_TYPE,
            "pageSize": page_size,
            "cursorMark": cursor_mark,
            "sort": sort,
        }
        response = self._session.get(SEARCH_URL, params=params)
        if response.status_code != 200:
            raise APIError(response.status_code, response.text)
        return response.json()

    def get_pdf_url(self, pmid: str, source: str = DEFAULT_SOURCE) -> str | None:
        """Resolve the full-text PDF URL for a given paper.

        Queries the Europe PMC full-text links endpoint and returns the
        first entry whose ``documentStyle`` is ``"pdf"``.

        Args:
            pmid: The PubMed identifier of the paper.
            source: The Europe PMC source database. Defaults to ``"MED"``
                (MEDLINE/PubMed).

        Returns:
            The PDF URL string, or ``None`` if no PDF link is available.

        Raises:
            APIError: If the API returns a non-200 HTTP status code.
            ConnectionError: If the HTTP request cannot be completed.
        """
        url = FULL_TEXT_LINKS_URL.format(source=source, pmid=pmid)
        response = self._session.get(url, params={"format": RESPONSE_FORMAT})
        if response.status_code != 200:
            raise APIError(response.status_code, response.text)
        data = response.json()
        entries = data.get("fullTextUrlList", {}).get("fullTextUrl", [])
        for entry in entries:
            if entry.get("documentStyle") == PDF_DOCUMENT_STYLE:
                return entry["url"]
        return None
