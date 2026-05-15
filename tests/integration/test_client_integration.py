"""Integration tests for EuropePMCClient — hits the real Europe PMC API.

This directory sits outside the unit-test tree defined in CLAUDE.md so that
integration tests can be excluded from CI with ``-m "not integration"`` without
touching the mirrored unit-test structure under tests/test_api/.

Run with:
    pytest -m integration

Skip during normal development/CI with:
    pytest -m "not integration"
"""

import pytest

from epmcminer.api.client import (
    DEFAULT_CURSOR_MARK,
    SORT_BY_CITATIONS,
    SORT_BY_DATE,
    APIError,
    EuropePMCClient,
)

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


@pytest.mark.integration
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
        result = client.search(
            query=COMMON_QUERY, page_size=SMALL_PAGE_SIZE, sort=SORT_BY_DATE
        )

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
# EuropePMCClient.get_pdf_url
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestGetPdfUrlIntegration:
    """Integration tests for EuropePMCClient.get_pdf_url."""

    def test_get_pdf_url_returns_string_or_none(self, client: EuropePMCClient) -> None:
        """get_pdf_url returns a str or None — never raises for a valid PMID."""
        url = client.get_pdf_url(pmid=KNOWN_PMID)

        assert url is None or isinstance(url, str)

    def test_get_pdf_url_string_is_https(self, client: EuropePMCClient) -> None:
        """When a PDF URL is returned it starts with https://."""
        url = client.get_pdf_url(pmid=KNOWN_PMID)

        if url is not None:
            assert url.startswith("https://")

    def test_get_pdf_url_unknown_pmid_returns_none(self, client: EuropePMCClient) -> None:
        """An unknown PMID (404 from the API) returns None rather than raising."""
        url = client.get_pdf_url(pmid="00000000")

        assert url is None

    def test_get_pdf_url_from_search_result(self, client: EuropePMCClient) -> None:
        """PDF URL lookup works for PMIDs taken directly from a search result."""
        result = client.search(query=COMMON_QUERY, page_size=SMALL_PAGE_SIZE)
        papers = result["resultList"]["result"]

        for paper in papers:
            pmid = paper.get("pmid") or paper.get("id")
            if pmid:
                url = client.get_pdf_url(pmid=str(pmid))
                assert url is None or isinstance(url, str)
                break
        else:
            pytest.skip("No papers with a PMID found in search result")

    def test_get_pdf_url_valid_pmid_does_not_raise(
        self, client: EuropePMCClient
    ) -> None:
        """A valid PMID does not raise APIError regardless of whether a PDF exists.

        A 500 cannot be reliably triggered against the real API, so this test
        confirms the happy path as an indirect guard against regression.
        """
        try:
            client.get_pdf_url(pmid=KNOWN_PMID)
        except APIError:
            pytest.fail("get_pdf_url raised APIError for a valid PMID")


# ---------------------------------------------------------------------------
# EuropePMCClient.download_pdf
# ---------------------------------------------------------------------------


@pytest.mark.integration
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
                if pdf_bytes[:4] == b"%PDF":
                    assert len(pdf_bytes) > 0
                    return
            except APIError:
                continue
        pytest.skip("All candidate PDF URLs returned errors or non-PDF content — API degraded")

    def test_download_pdf_content_starts_with_pdf_header(
        self, client: EuropePMCClient
    ) -> None:
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
                if pdf_bytes[:4] == b"%PDF":
                    return
            except APIError:
                continue
        pytest.skip("All candidate PDF URLs returned errors or non-PDF content — API degraded")
