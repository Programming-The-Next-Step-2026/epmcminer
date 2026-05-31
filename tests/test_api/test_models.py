"""Tests for epmcminer.api models."""

from pathlib import Path

import pytest

from epmcminer.api.paper import Paper
from epmcminer.api.search_params import SearchParams
from epmcminer.api.search_result import SearchResult
from epmcminer.services.models import DownloadResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_search_params() -> SearchParams:
    """Return a fully-populated, valid SearchParams instance."""
    return SearchParams(
        query="depression AND therapy",
        date_from="2020-01-01",
        date_to="2024-12-31",
        publication_types=["Review", "Meta analysis"],
        licenses=["CC-BY"],
        author_orcids=[],
        sort_order="relevance",
        count=10,
        output_folder=Path("/tmp/output"),
    )


@pytest.fixture
def valid_paper() -> Paper:
    """Return a fully-populated Paper instance."""
    return Paper(
        pmid="12345678",
        doi="10.1000/xyz123",
        title="A study on depression",
        authors="Smith J, Jones A",
        journal="Journal of Psychiatry",
        year="2022",
        abstract="This study investigates...",
        pdf_url="https://example.com/paper.pdf",
    )


@pytest.fixture
def valid_search_result(valid_paper: Paper) -> SearchResult:
    """Return a SearchResult with one paper."""
    return SearchResult(
        papers=[valid_paper],
        total_found=42,
        estimated_downloadable=30,
    )


# ---------------------------------------------------------------------------
# SearchParams
# ---------------------------------------------------------------------------


class TestSearchParams:
    """Tests for SearchParams dataclass."""

    def test_valid_construction(self, valid_search_params: SearchParams) -> None:
        """A valid SearchParams instance is created without errors."""
        assert valid_search_params.query == "depression AND therapy"
        assert valid_search_params.count == 10

    def test_count_of_one_is_valid(self) -> None:
        """count = 1 is the minimum allowed value."""
        params = SearchParams(
            query="test",
            date_from="2020-01-01",
            date_to="2024-12-31",
            publication_types=["Review"],
            licenses=["CC-BY"],
            author_orcids=[],
            sort_order="relevance",
            count=1,
            output_folder=Path("/tmp"),
        )
        assert params.count == 1

    def test_count_zero_raises_value_error(self, valid_search_params: SearchParams) -> None:
        """count = 0 raises ValueError with a descriptive message."""
        with pytest.raises(ValueError, match="count"):
            SearchParams(
                query="test",
                date_from="2020-01-01",
                date_to="2024-12-31",
                publication_types=["Review"],
                licenses=["CC-BY"],
                author_orcids=[],
                sort_order="relevance",
                count=0,
                output_folder=Path("/tmp"),
            )

    def test_negative_count_raises_value_error(self) -> None:
        """Negative count raises ValueError with a descriptive message."""
        with pytest.raises(ValueError, match="count"):
            SearchParams(
                query="test",
                date_from="2020-01-01",
                date_to="2024-12-31",
                publication_types=["Review"],
                licenses=["CC-BY"],
                author_orcids=[],
                sort_order="relevance",
                count=-5,
                output_folder=Path("/tmp"),
            )

    def test_empty_author_orcids_allowed(self) -> None:
        """author_orcids can be an empty list."""
        params = SearchParams(
            query="test",
            date_from="2020-01-01",
            date_to="2024-12-31",
            publication_types=["Review"],
            licenses=["CC-BY"],
            author_orcids=[],
            sort_order="relevance",
            count=5,
            output_folder=Path("/tmp"),
        )
        assert params.author_orcids == []

    def test_output_folder_stored_as_path(self) -> None:
        """output_folder is stored as a Path instance."""
        params = SearchParams(
            query="test",
            date_from="2020-01-01",
            date_to="2024-12-31",
            publication_types=["Review"],
            licenses=["CC-BY"],
            author_orcids=[],
            sort_order="date",
            count=5,
            output_folder=Path("/tmp/papers"),
        )
        assert isinstance(params.output_folder, Path)

    def test_output_folder_defaults_to_none(self) -> None:
        """output_folder defaults to None when not provided."""
        params = SearchParams(
            query="test",
            date_from="2020-01-01",
            date_to="2024-12-31",
            count=1,
        )
        assert params.output_folder is None

    def test_output_folder_none_does_not_raise(self) -> None:
        """Constructing SearchParams without output_folder does not raise."""
        SearchParams(
            query="test",
            date_from="2020-01-01",
            date_to="2024-12-31",
            count=1,
        )  # must not raise

    def test_invalid_date_from_raises_value_error(self) -> None:
        """A non-ISO date_from raises ValueError."""
        with pytest.raises(ValueError, match="date_from"):
            SearchParams(query="test", date_from="not-a-date", date_to="2024-12-31", count=1)

    def test_invalid_date_to_raises_value_error(self) -> None:
        """A non-ISO date_to raises ValueError."""
        with pytest.raises(ValueError, match="date_to"):
            SearchParams(query="test", date_from="2020-01-01", date_to="31/12/2024", count=1)

    def test_date_from_after_date_to_raises_value_error(self) -> None:
        """date_from later than date_to raises ValueError."""
        with pytest.raises(ValueError, match="date_from"):
            SearchParams(query="test", date_from="2025-01-01", date_to="2020-01-01", count=1)

    def test_equal_dates_are_valid(self) -> None:
        """date_from equal to date_to is a valid single-day range."""
        params = SearchParams(query="test", date_from="2023-06-15", date_to="2023-06-15", count=1)
        assert params.date_from == params.date_to


# ---------------------------------------------------------------------------
# Paper
# ---------------------------------------------------------------------------


class TestPaper:
    """Tests for Paper dataclass."""

    def test_valid_construction(self, valid_paper: Paper) -> None:
        """A fully-populated Paper is created without errors."""
        assert valid_paper.pmid == "12345678"
        assert valid_paper.pdf_url == "https://example.com/paper.pdf"

    def test_pdf_url_can_be_none(self) -> None:
        """pdf_url accepts None for papers without an open-access PDF."""
        paper = Paper(
            pmid="99999",
            doi="10.0000/none",
            title="No PDF paper",
            authors="Author A",
            journal="Some Journal",
            year="2021",
            abstract="Abstract text.",
            pdf_url=None,
        )
        assert paper.pdf_url is None


# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_valid_construction(self, valid_search_result: SearchResult) -> None:
        """A SearchResult is created with the expected fields."""
        assert valid_search_result.total_found == 42
        assert valid_search_result.estimated_downloadable == 30
        assert len(valid_search_result.papers) == 1

    def test_empty_papers_list(self) -> None:
        """SearchResult can hold an empty papers list."""
        result = SearchResult(papers=[], total_found=0, estimated_downloadable=0)
        assert result.papers == []


# ---------------------------------------------------------------------------
# DownloadResult
# ---------------------------------------------------------------------------


class TestDownloadResult:
    """Tests for DownloadResult dataclass."""

    def test_successful_download(self, valid_paper: Paper) -> None:
        """A downloaded result has status 'downloaded' and a file_path."""
        result = DownloadResult(
            paper=valid_paper,
            status="downloaded",
            reason=None,
            file_path=Path("/tmp/output/pdfs/paper.pdf"),
        )
        assert result.status == "downloaded"
        assert result.reason is None
        assert result.file_path is not None

    def test_skipped_result(self, valid_paper: Paper) -> None:
        """A skipped result has a reason and no file_path."""
        result = DownloadResult(
            paper=valid_paper,
            status="skipped",
            reason="Already downloaded",
            file_path=None,
        )
        assert result.status == "skipped"
        assert result.reason == "Already downloaded"
        assert result.file_path is None

    def test_failed_result(self, valid_paper: Paper) -> None:
        """A failed result has a reason and no file_path."""
        result = DownloadResult(
            paper=valid_paper,
            status="failed",
            reason="HTTP 404",
            file_path=None,
        )
        assert result.status == "failed"
        assert result.reason == "HTTP 404"
