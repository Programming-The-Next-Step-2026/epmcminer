"""Tests for epmcminer.services.search_service."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from epmcminer.api.client import SORT_BY_CITATIONS, SORT_BY_DATE, APIError
from epmcminer.api.models import SearchParams, SearchResult
from epmcminer.services.search_service import PREVIEW_PAGE_SIZE, SearchService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_params(**overrides: object) -> SearchParams:
    """Return a SearchParams with sensible defaults; keyword args override specific fields."""
    defaults: dict = {
        "query": "depression",
        "date_from": "2020-01-01",
        "date_to": "2024-12-31",
        "publication_types": [],
        "licenses": [],
        "author_orcids": [],
        "sort_order": "relevance",
        "count": 10,
        "output_folder": Path("/tmp"),
    }
    defaults.update(overrides)
    return SearchParams(**defaults)


# ---------------------------------------------------------------------------
# Mock API responses
# ---------------------------------------------------------------------------

_PDF_URL = "https://europepmc.org/articles/PMC1234567?pdf=render"
_HTML_URL = "https://europepmc.org/articles/PMC1234567"

RAW_PAPER = {
    "pmid": "12345678",
    "id": "12345678",
    "source": "MED",
    "doi": "10.1000/xyz123",
    "title": "A study on depression",
    "authorString": "Smith J, Jones A",
    "journalTitle": "Journal of Psychiatry",
    "pubYear": "2022",
    "abstractText": "This study investigates depression.",
    "fullTextUrlList": {
        "fullTextUrl": [
            {"documentStyle": "html", "url": _HTML_URL},
            {"documentStyle": "pdf", "url": _PDF_URL},
        ]
    },
}

RAW_PAPER_NO_PDF = {
    "pmid": "87654321",
    "id": "87654321",
    "source": "MED",
    "doi": "10.2000/abc456",
    "title": "A study on anxiety",
    "authorString": "Jones A, Smith J",
    "journalTitle": "Journal of Psychology",
    "pubYear": "2021",
    "abstractText": "This study investigates anxiety.",
    "fullTextUrlList": {
        "fullTextUrl": [
            {"documentStyle": "html", "url": "https://europepmc.org/articles/PMC9876543"},
        ]
    },
}

RAW_PAPER_PPR = {
    "pmid": None,
    "id": "PPR123456",
    "source": "PPR",
    "doi": "10.3000/ppr123",
    "title": "A preprint on depression",
    "authorString": "Brown K",
    "journalTitle": "bioRxiv",
    "pubYear": "2023",
    "abstractText": "This preprint investigates depression.",
    "fullTextUrlList": {
        "fullTextUrl": [
            {"documentStyle": "pdf", "url": "https://www.biorxiv.org/content/ppr123.full.pdf"},
        ]
    },
}

MOCK_SEARCH_RESPONSE = {
    "hitCount": 100,
    "nextCursorMark": "AoE=",
    "resultList": {"result": [RAW_PAPER]},
}

TWO_PAPER_RESPONSE = {
    "hitCount": 200,
    "nextCursorMark": "AoE=",
    "resultList": {"result": [RAW_PAPER, RAW_PAPER_NO_PDF]},
}

PPR_RESPONSE = {
    "hitCount": 50,
    "nextCursorMark": "AoE=",
    "resultList": {"result": [RAW_PAPER_PPR]},
}

EMPTY_SEARCH_RESPONSE = {
    "hitCount": 0,
    "nextCursorMark": "*",
    "resultList": {"result": []},
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client(mocker) -> MagicMock:
    """Return a mock EuropePMCClient."""
    return mocker.MagicMock()


@pytest.fixture
def service(mock_client: MagicMock) -> SearchService:
    """Return a SearchService with a mock client."""
    return SearchService(client=mock_client)


# ---------------------------------------------------------------------------
# SearchService.build_query
# ---------------------------------------------------------------------------


class TestBuildQuery:
    """Tests for SearchService.build_query — pure function, no HTTP calls needed."""

    def test_single_keyword_no_operators_joined_with_and(self, service: SearchService) -> None:
        """Words without boolean operators are joined with AND."""
        result = service.build_query(make_params(query="depression therapy"))
        assert "depression AND therapy" in result

    def test_keyword_with_and_operator_unchanged(self, service: SearchService) -> None:
        """A query already containing AND is not modified."""
        result = service.build_query(make_params(query="depression AND therapy"))
        assert "depression AND therapy" in result
        assert "depression AND AND therapy" not in result

    def test_keyword_with_or_operator_unchanged(self, service: SearchService) -> None:
        """A query already containing OR is not modified."""
        result = service.build_query(make_params(query="depression OR anxiety"))
        assert "depression OR anxiety" in result

    def test_date_range_rendered_as_first_pdate(self, service: SearchService) -> None:
        """Date range is rendered as a FIRST_PDATE filter."""
        result = service.build_query(make_params(date_from="2020-01-01", date_to="2024-12-31"))
        assert "FIRST_PDATE:[2020-01-01 TO 2024-12-31]" in result

    def test_single_publication_type(self, service: SearchService) -> None:
        """A single publication type produces a PUB_TYPE clause."""
        result = service.build_query(make_params(publication_types=["Review"]))
        assert 'PUB_TYPE:("Review")' in result

    def test_multiple_publication_types_joined_with_or(self, service: SearchService) -> None:
        """Multiple publication types are joined with OR."""
        result = service.build_query(make_params(publication_types=["Review", "Meta analysis"]))
        assert 'PUB_TYPE:("Review")' in result
        assert 'PUB_TYPE:("Meta analysis")' in result
        assert " OR " in result

    def test_no_publication_types_omits_clause(self, service: SearchService) -> None:
        """An empty publication_types list produces no PUB_TYPE clause."""
        assert "PUB_TYPE" not in service.build_query(make_params(publication_types=[]))

    def test_single_license(self, service: SearchService) -> None:
        """A single license produces a LICENSE clause."""
        result = service.build_query(make_params(licenses=["CC-BY"]))
        assert 'LICENSE:"CC-BY"' in result

    def test_multiple_licenses_joined_with_or(self, service: SearchService) -> None:
        """Multiple licenses are joined with OR."""
        result = service.build_query(make_params(licenses=["CC-BY", "CC0"]))
        assert 'LICENSE:"CC-BY"' in result
        assert 'LICENSE:"CC0"' in result

    def test_no_licenses_omits_clause(self, service: SearchService) -> None:
        """An empty licenses list produces no LICENSE clause."""
        assert "LICENSE" not in service.build_query(make_params(licenses=[]))

    def test_single_author_orcid(self, service: SearchService) -> None:
        """A single ORCID produces an AUTHORID clause."""
        result = service.build_query(make_params(author_orcids=["0000-0001-2345-6789"]))
        assert 'AUTHORID:"0000-0001-2345-6789"' in result

    def test_multiple_author_orcids_joined_with_or(self, service: SearchService) -> None:
        """Multiple ORCIDs are joined with OR."""
        result = service.build_query(
            make_params(author_orcids=["0000-0001-2345-6789", "0000-0009-8765-4321"])
        )
        assert 'AUTHORID:"0000-0001-2345-6789"' in result
        assert 'AUTHORID:"0000-0009-8765-4321"' in result

    def test_empty_author_orcids_omits_clause(self, service: SearchService) -> None:
        """An empty author_orcids list produces no AUTHORID clause."""
        assert "AUTHORID" not in service.build_query(make_params(author_orcids=[]))

    def test_single_keyword_no_spaces_unchanged(self, service: SearchService) -> None:
        """A single-word query is passed through without modification."""
        result = service.build_query(make_params(query="depression"))
        assert result.startswith("depression AND (FIRST_PDATE")

    def test_keyword_with_not_operator_unchanged(self, service: SearchService) -> None:
        """A query already containing NOT is not modified."""
        result = service.build_query(make_params(query="depression NOT anxiety"))
        assert "depression NOT anxiety" in result
        assert "depression AND NOT" not in result

    def test_free_full_text_filter_always_present(self, service: SearchService) -> None:
        """HAS_FT:Y OR HAS_FREE_FULLTEXT:Y is always appended."""
        assert "HAS_FT:Y OR HAS_FREE_FULLTEXT:Y" in service.build_query(make_params())

    def test_all_filters_combined(self, service: SearchService) -> None:
        """All active filters appear in the final query string."""
        params = make_params(
            query="depression therapy",
            date_from="2020-01-01",
            date_to="2024-12-31",
            publication_types=["Review"],
            licenses=["CC-BY"],
            author_orcids=["0000-0001-2345-6789"],
        )
        result = service.build_query(params)
        assert "depression AND therapy" in result
        assert "FIRST_PDATE:[2020-01-01 TO 2024-12-31]" in result
        assert 'PUB_TYPE:("Review")' in result
        assert 'LICENSE:"CC-BY"' in result
        assert 'AUTHORID:"0000-0001-2345-6789"' in result
        assert "HAS_FT:Y OR HAS_FREE_FULLTEXT:Y" in result


# ---------------------------------------------------------------------------
# SearchService.preview
# ---------------------------------------------------------------------------


class TestPreview:
    """Tests for SearchService.preview."""

    def test_preview_returns_search_result(
        self, service: SearchService, mock_client
    ) -> None:
        """preview returns a SearchResult instance."""
        mock_client.search.return_value = MOCK_SEARCH_RESPONSE

        assert isinstance(service.preview(make_params()), SearchResult)

    def test_preview_maps_raw_fields_to_paper(
        self, service: SearchService, mock_client
    ) -> None:
        """Raw API fields are mapped to the correct Paper attributes."""
        mock_client.search.return_value = MOCK_SEARCH_RESPONSE

        paper = service.preview(make_params()).papers[0]

        assert paper.pmid == "12345678"
        assert paper.doi == "10.1000/xyz123"
        assert paper.title == "A study on depression"
        assert paper.authors == "Smith J, Jones A"
        assert paper.journal == "Journal of Psychiatry"
        assert paper.year == "2022"
        assert paper.abstract == "This study investigates depression."

    def test_preview_sets_pdf_url_from_full_text_url_list(
        self, service: SearchService, mock_client
    ) -> None:
        """pdf_url is extracted directly from fullTextUrlList in the search response."""
        mock_client.search.return_value = MOCK_SEARCH_RESPONSE

        assert service.preview(make_params()).papers[0].pdf_url == _PDF_URL

    def test_preview_pdf_url_none_when_no_pdf_entry(
        self, service: SearchService, mock_client
    ) -> None:
        """pdf_url is None when fullTextUrlList contains no pdf documentStyle."""
        mock_client.search.return_value = {
            "hitCount": 1,
            "nextCursorMark": "*",
            "resultList": {"result": [RAW_PAPER_NO_PDF]},
        }

        assert service.preview(make_params()).papers[0].pdf_url is None

    def test_preview_total_found_from_hit_count(
        self, service: SearchService, mock_client
    ) -> None:
        """total_found in SearchResult reflects the API hitCount."""
        mock_client.search.return_value = MOCK_SEARCH_RESPONSE

        assert service.preview(make_params()).total_found == 100

    def test_preview_estimated_downloadable_counts_papers_with_pdf(
        self, service: SearchService, mock_client
    ) -> None:
        """estimated_downloadable counts only papers with a non-None pdf_url."""
        mock_client.search.return_value = TWO_PAPER_RESPONSE

        assert service.preview(make_params()).estimated_downloadable == 1

    def test_preview_estimated_downloadable_zero_when_no_pdfs(
        self, service: SearchService, mock_client
    ) -> None:
        """estimated_downloadable is 0 when no papers have a PDF entry."""
        mock_client.search.return_value = {
            "hitCount": 2,
            "nextCursorMark": "*",
            "resultList": {"result": [RAW_PAPER_NO_PDF, RAW_PAPER_NO_PDF]},
        }

        assert service.preview(make_params()).estimated_downloadable == 0

    def test_preview_ppr_paper_uses_id_as_pmid(
        self, service: SearchService, mock_client
    ) -> None:
        """For papers without a pmid (e.g. preprints), the id field is used."""
        mock_client.search.return_value = PPR_RESPONSE

        paper = service.preview(make_params()).papers[0]

        assert paper.pmid == "PPR123456"

    def test_preview_ppr_paper_pdf_url_from_full_text_url_list(
        self, service: SearchService, mock_client
    ) -> None:
        """PDF URL is extracted from fullTextUrlList for non-MED papers too."""
        mock_client.search.return_value = PPR_RESPONSE

        paper = service.preview(make_params()).papers[0]

        assert paper.pdf_url == "https://www.biorxiv.org/content/ppr123.full.pdf"

    def test_preview_does_not_call_get_pdf_url(
        self, service: SearchService, mock_client
    ) -> None:
        """preview reads PDF URLs from the search response; get_pdf_url is not called."""
        mock_client.search.return_value = MOCK_SEARCH_RESPONSE

        service.preview(make_params())

        mock_client.get_pdf_url.assert_not_called()

    def test_preview_uses_preview_page_size(
        self, service: SearchService, mock_client
    ) -> None:
        """preview always requests exactly PREVIEW_PAGE_SIZE results."""
        mock_client.search.return_value = MOCK_SEARCH_RESPONSE

        service.preview(make_params())

        assert mock_client.search.call_args.kwargs["page_size"] == PREVIEW_PAGE_SIZE

    def test_preview_sort_relevance_passes_none_to_client(
        self, service: SearchService, mock_client
    ) -> None:
        """sort_order='relevance' passes sort=None to client.search."""
        mock_client.search.return_value = MOCK_SEARCH_RESPONSE

        service.preview(make_params(sort_order="relevance"))

        assert mock_client.search.call_args.kwargs["sort"] is None

    def test_preview_sort_date_passes_sort_by_date(
        self, service: SearchService, mock_client
    ) -> None:
        """sort_order='date' passes SORT_BY_DATE to client.search."""
        mock_client.search.return_value = MOCK_SEARCH_RESPONSE

        service.preview(make_params(sort_order="date"))

        assert mock_client.search.call_args.kwargs["sort"] == SORT_BY_DATE

    def test_preview_sort_citations_passes_sort_by_citations(
        self, service: SearchService, mock_client
    ) -> None:
        """sort_order='citations' passes SORT_BY_CITATIONS to client.search."""
        mock_client.search.return_value = MOCK_SEARCH_RESPONSE

        service.preview(make_params(sort_order="citations"))

        assert mock_client.search.call_args.kwargs["sort"] == SORT_BY_CITATIONS

    def test_preview_missing_full_text_url_list_returns_none_pdf(
        self, service: SearchService, mock_client
    ) -> None:
        """A paper with no fullTextUrlList field in the response gets pdf_url=None."""
        raw_no_ft = {
            "pmid": "11111111",
            "id": "11111111",
            "source": "MED",
            "doi": "10.9999/noft",
            "title": "No full text paper",
            "authorString": "Nobody A",
            "journalTitle": "Journal X",
            "pubYear": "2021",
            "abstractText": "Abstract.",
        }
        mock_client.search.return_value = {
            "hitCount": 1,
            "nextCursorMark": "*",
            "resultList": {"result": [raw_no_ft]},
        }

        paper = service.preview(make_params()).papers[0]

        assert paper.pdf_url is None

    def test_preview_propagates_api_error(
        self, service: SearchService, mock_client
    ) -> None:
        """APIError raised by client.search is not caught and propagates to the caller."""
        mock_client.search.side_effect = APIError(500, "Internal Server Error")

        with pytest.raises(APIError):
            service.preview(make_params())

    def test_preview_propagates_connection_error(
        self, service: SearchService, mock_client
    ) -> None:
        """ConnectionError raised by client.search propagates to the caller."""
        mock_client.search.side_effect = ConnectionError("timeout")

        with pytest.raises(ConnectionError):
            service.preview(make_params())

    def test_preview_empty_results(
        self, service: SearchService, mock_client
    ) -> None:
        """preview with no API results returns an empty SearchResult."""
        mock_client.search.return_value = EMPTY_SEARCH_RESPONSE

        result = service.preview(make_params())

        assert result.papers == []
        assert result.total_found == 0
        assert result.estimated_downloadable == 0
