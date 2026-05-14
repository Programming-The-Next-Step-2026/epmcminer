"""Integration tests for SearchService — hits the real Europe PMC API.

This directory sits outside the unit-test tree defined in CLAUDE.md so that
integration tests can be excluded from CI with ``-m "not integration"`` without
touching the mirrored unit-test structure under tests/test_services/.

Run with:
    pytest -m integration

Skip during normal development/CI with:
    pytest -m "not integration"
"""

from pathlib import Path

import pytest

from epmcminer.api.client import EuropePMCClient
from epmcminer.api.models import SearchParams, SearchResult
from epmcminer.services.search_service import SearchService

COMMON_QUERY = "depression"
DATE_FROM = "2020-01-01"
DATE_TO = "2024-12-31"


def make_params(**overrides: object) -> SearchParams:
    """Return a SearchParams with sensible defaults for integration tests."""
    defaults: dict = {
        "query": COMMON_QUERY,
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
        "publication_types": [],
        "licenses": [],
        "author_orcids": [],
        "sort_order": "relevance",
        "count": 10,
        "output_folder": Path("/tmp"),
    }
    defaults.update(overrides)
    return SearchParams(**defaults)


@pytest.fixture(scope="module")
def service() -> SearchService:
    """Shared SearchService backed by a real EuropePMCClient."""
    return SearchService(client=EuropePMCClient())


# ---------------------------------------------------------------------------
# SearchService.build_query
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestBuildQueryIntegration:
    """Integration tests verifying build_query output produces valid API results."""

    def test_built_query_returns_results(self, service: SearchService) -> None:
        """A query built from SearchParams returns a non-zero hit count from the API."""
        result = service.preview(make_params())
        assert result.total_found > 0

    def test_built_query_with_all_filters_returns_results(
        self, service: SearchService
    ) -> None:
        """A query with publication type and license filters still returns results."""
        result = service.preview(
            make_params(publication_types=["Review"], licenses=["CC BY"])
        )
        assert result.total_found > 0

    def test_built_query_date_range_respected(self, service: SearchService) -> None:
        """Narrowing the date range reduces the total result count."""
        broad = service.preview(make_params(date_from="2010-01-01", date_to="2024-12-31"))
        narrow = service.preview(make_params(date_from="2023-01-01", date_to="2023-12-31"))
        assert narrow.total_found < broad.total_found


# ---------------------------------------------------------------------------
# SearchService.preview
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPreviewIntegration:
    """Integration tests for SearchService.preview."""

    def test_preview_returns_search_result(self, service: SearchService) -> None:
        """preview returns a SearchResult instance."""
        assert isinstance(service.preview(make_params()), SearchResult)

    def test_preview_papers_list_non_empty(self, service: SearchService) -> None:
        """preview returns at least one paper for a common query."""
        result = service.preview(make_params())
        assert len(result.papers) > 0

    def test_preview_total_found_positive(self, service: SearchService) -> None:
        """total_found is greater than zero for a broad query."""
        result = service.preview(make_params())
        assert result.total_found > 0

    def test_preview_estimated_downloadable_positive(
        self, service: SearchService
    ) -> None:
        """At least one paper in a broad preview has a PDF URL."""
        result = service.preview(make_params())
        assert result.estimated_downloadable > 0

    def test_preview_paper_fields_populated(self, service: SearchService) -> None:
        """Each returned paper has a non-empty title and pmid."""
        result = service.preview(make_params())
        for paper in result.papers:
            assert paper.title
            assert paper.pmid

    def test_preview_pdf_url_is_string_or_none(self, service: SearchService) -> None:
        """Each paper's pdf_url is either a string or None — never another type."""
        result = service.preview(make_params())
        for paper in result.papers:
            assert paper.pdf_url is None or isinstance(paper.pdf_url, str)

    def test_preview_pdf_url_starts_with_https(self, service: SearchService) -> None:
        """Any non-None pdf_url starts with https://."""
        result = service.preview(make_params())
        for paper in result.papers:
            if paper.pdf_url is not None:
                assert paper.pdf_url.startswith("https://")

    def test_preview_sort_by_date_returns_results(
        self, service: SearchService
    ) -> None:
        """preview with sort_order='date' returns results without error."""
        result = service.preview(make_params(sort_order="date"))
        assert result.total_found > 0

    def test_preview_sort_by_citations_returns_results(
        self, service: SearchService
    ) -> None:
        """preview with sort_order='citations' returns results without error."""
        result = service.preview(make_params(sort_order="citations"))
        assert result.total_found > 0

    def test_preview_no_results_for_impossible_query(
        self, service: SearchService
    ) -> None:
        """An impossible query returns zero papers without raising."""
        result = service.preview(
            make_params(query="xyzzy_impossible_query_string_that_matches_nothing_12345")
        )
        assert result.papers == []
        assert result.total_found == 0
        assert result.estimated_downloadable == 0
