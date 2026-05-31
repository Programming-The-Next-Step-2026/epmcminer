"""Integration tests for EuropePMCClient.

HTTP interactions are recorded as VCR cassettes in tests/integration/cassettes/
and replayed deterministically in CI — no live network access required.

Re-record cassettes when the API changes:
    pytest -m integration --vcr-record=all
"""

import pytest

from epmcminer.api.client import (
    DEFAULT_CURSOR_MARK,
    SORT_BY_CITATIONS,
    SORT_BY_DATE,
    APIError,
    EuropePMCClient,
    InvalidPdfContentError,
)

pytestmark = [pytest.mark.vcr, pytest.mark.integration]

KNOWN_PMID = "28796235"  # A real open-access paper (PMID for a stable OA article)
COMMON_QUERY = "depression"
SMALL_PAGE_SIZE = 5
PDF_SEARCH_PAGE_SIZE = 20  # Larger pool so transient 5xx on one paper doesn't fail the test


@pytest.fixture(scope="module")
def client() -> EuropePMCClient:
    """Shared EuropePMCClient for the integration test module."""
    return EuropePMCClient()


# ---------------------------------------------------------------------------
# EuropePMCClient.search
# ---------------------------------------------------------------------------


class TestSearchIntegration:
    """Integration tests for EuropePMCClient.search."""

    def test_search_returns_results(self, client: EuropePMCClient) -> None:
        """A real search returns a non-empty hit count and result list."""
        result = client.search(query=COMMON_QUERY, page_size=SMALL_PAGE_SIZE)

        assert result["hitCount"] > 0
        assert len(result["resultList"]["result"]) > 0

    def test_search_result_structure(self, client: EuropePMCClient) -> None:
        """Each result contains the expected core fields."""
        result = client.search(query=COMMON_QUERY, page_size=SMALL_PAGE_SIZE)

        paper = result["resultList"]["result"][0]
        assert "pmid" in paper or "id" in paper
        assert "title" in paper

    def test_search_respects_page_size(self, client: EuropePMCClient) -> None:
        """The number of results does not exceed the requested page size."""
        result = client.search(query=COMMON_QUERY, page_size=SMALL_PAGE_SIZE)

        assert len(result["resultList"]["result"]) <= SMALL_PAGE_SIZE

    def test_search_returns_cursor_mark(self, client: EuropePMCClient) -> None:
        """A successful search response includes a nextCursorMark for pagination."""
        result = client.search(query=COMMON_QUERY, page_size=SMALL_PAGE_SIZE)

        assert "nextCursorMark" in result

    def test_search_pagination_advances_cursor(self, client: EuropePMCClient) -> None:
        """Using nextCursorMark from page 1 returns a different page of results."""
        page1 = client.search(query=COMMON_QUERY, page_size=SMALL_PAGE_SIZE)
        next_cursor = page1["nextCursorMark"]

        page2 = client.search(
            query=COMMON_QUERY, page_size=SMALL_PAGE_SIZE, cursor_mark=next_cursor
        )

        ids_page1 = {r.get("pmid") or r.get("id") for r in page1["resultList"]["result"]}
        ids_page2 = {r.get("pmid") or r.get("id") for r in page2["resultList"]["result"]}
        assert ids_page1 != ids_page2

    def test_search_sort_by_date(self, client: EuropePMCClient) -> None:
        """Sort by date returns results without API errors."""
        result = client.search(query=COMMON_QUERY, page_size=SMALL_PAGE_SIZE, sort=SORT_BY_DATE)

        assert result["hitCount"] > 0

    def test_search_sort_by_citations(self, client: EuropePMCClient) -> None:
        """Sort by citations returns results without API errors."""
        result = client.search(
            query=COMMON_QUERY, page_size=SMALL_PAGE_SIZE, sort=SORT_BY_CITATIONS
        )

        assert result["hitCount"] > 0

    def test_search_default_cursor_mark(self, client: EuropePMCClient) -> None:
        """Using the default cursor mark returns the first page."""
        result = client.search(
            query=COMMON_QUERY, page_size=SMALL_PAGE_SIZE, cursor_mark=DEFAULT_CURSOR_MARK
        )

        assert len(result["resultList"]["result"]) > 0

    def test_search_invalid_query_returns_zero_hits(self, client: EuropePMCClient) -> None:
        """A query designed to match nothing returns zero hits, not an error."""
        result = client.search(
            query="xyzzy_impossible_query_string_that_matches_nothing_12345",
            page_size=SMALL_PAGE_SIZE,
        )

        assert result["hitCount"] == 0
        assert result["resultList"]["result"] == []


# ---------------------------------------------------------------------------
# EuropePMCClient.download_pdf
# ---------------------------------------------------------------------------


class TestDownloadPdfIntegration:
    """Integration tests for EuropePMCClient.download_pdf."""

    def _collect_pdf_urls(self, client: EuropePMCClient) -> list[str]:
        """Return all PDF URLs from a search result page, for use as a candidate pool."""
        result = client.search(query=COMMON_QUERY, page_size=PDF_SEARCH_PAGE_SIZE)
        urls: list[str] = []
        for paper in result["resultList"]["result"]:
            for entry in paper.get("fullTextUrlList", {}).get("fullTextUrl", []):
                if entry.get("documentStyle") == "pdf":
                    urls.append(entry["url"])
        return urls

    def test_download_pdf_returns_bytes_for_oa_paper(self, client: EuropePMCClient) -> None:
        """download_pdf returns valid PDF bytes for at least one URL in the result pool.

        Tries each candidate URL in turn; server-side 5xx errors and URLs that
        return non-PDF content (e.g. HTML landing pages) are skipped so that a
        single bad link does not fail the test.
        """
        urls = self._collect_pdf_urls(client)
        if not urls:
            pytest.skip("No paper with an embedded PDF URL found in search results")
        for url in urls:
            try:
                pdf_bytes = client.download_pdf(url=url)
                assert len(pdf_bytes) > 0
                return
            except (APIError, InvalidPdfContentError):
                continue
        pytest.skip("All candidate PDF URLs returned errors or non-PDF content — API degraded")

    def test_download_pdf_content_starts_with_pdf_header(self, client: EuropePMCClient) -> None:
        """The downloaded bytes begin with the PDF magic bytes ``%PDF``.

        Tries each candidate URL in turn; server-side 5xx errors and URLs that
        return non-PDF content (e.g. HTML landing pages) are skipped so that a
        single bad link does not fail the test.
        """
        urls = self._collect_pdf_urls(client)
        if not urls:
            pytest.skip("No paper with an embedded PDF URL found in search results")
        for url in urls:
            try:
                pdf_bytes = client.download_pdf(url=url)
                assert pdf_bytes[:4] == b"%PDF"
                return
            except (APIError, InvalidPdfContentError):
                continue
        pytest.skip("All candidate PDF URLs returned errors or non-PDF content — API degraded")
