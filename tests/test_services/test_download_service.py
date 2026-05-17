"""Tests for epmcminer.services.download_service."""

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from epmcminer.api.client import APIError, EuropePMCClient
from epmcminer.api.download_result import DownloadResult
from epmcminer.api.models import SearchParams
from epmcminer.services.download_service import DOWNLOAD_PAGE_SIZE, DownloadService
from epmcminer.services.search_service import SearchService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PDF_URL = "https://europepmc.org/articles/PMC123?pdf=render"
_PDF_BYTES = b"%PDF-1.4 test content"
_QUERY = "depression AND (FIRST_PDATE:[2020-01-01 TO 2024-12-31])"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_params(output_folder: Path, **overrides: object) -> SearchParams:
    """Return a SearchParams with sensible defaults for download tests."""
    defaults: dict = {
        "query": "depression",
        "date_from": "2020-01-01",
        "date_to": "2024-12-31",
        "sort_order": "relevance",
        "count": 10,
        "output_folder": output_folder,
    }
    defaults.update(overrides)
    return SearchParams(**defaults)


def make_raw_paper(
    pmid: str = "12345",
    doi: str = "10.1234/test",
    title: str = "Test Paper",
    pdf_url: str | None = _PDF_URL,
) -> dict:
    """Return a raw API result dict with optional PDF link."""
    raw: dict = {
        "pmid": pmid,
        "doi": doi,
        "title": title,
        "authorString": "Smith J",
        "journalTitle": "Test Journal",
        "pubYear": "2022",
        "abstractText": "Abstract.",
    }
    if pdf_url is not None:
        raw["fullTextUrlList"] = {
            "fullTextUrl": [{"documentStyle": "pdf", "url": pdf_url}]
        }
    return raw


def make_search_response(
    papers: list[dict],
    next_cursor: str = "AoE=",
    hit_count: int | None = None,
) -> dict:
    """Return a minimal search response dict."""
    return {
        "hitCount": hit_count if hit_count is not None else len(papers),
        "nextCursorMark": next_cursor,
        "resultList": {"result": papers},
    }


EMPTY_RESPONSE = make_search_response([], next_cursor="*", hit_count=0)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client(mocker: pytest.MonkeyPatch) -> MagicMock:
    """Return a MagicMock standing in for EuropePMCClient."""
    return mocker.MagicMock(spec=EuropePMCClient)


@pytest.fixture
def mock_search_service(mocker: pytest.MonkeyPatch) -> MagicMock:
    """Return a MagicMock SearchService with build_query pre-configured."""
    svc = mocker.MagicMock(spec=SearchService)
    svc.build_query.return_value = _QUERY
    return svc


@pytest.fixture
def service(mock_client: MagicMock, mock_search_service: MagicMock) -> DownloadService:
    """Return a DownloadService backed by mock dependencies."""
    return DownloadService(client=mock_client, search_service=mock_search_service)


# ---------------------------------------------------------------------------
# DownloadService.download
# ---------------------------------------------------------------------------


class TestDownload:
    """Tests for DownloadService.download."""

    def test_successful_download_returns_downloaded_status(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """A paper with a PDF URL is downloaded and its result has status='downloaded'."""
        mock_client.search.return_value = make_search_response(
            [make_raw_paper()], next_cursor="*"
        )
        mock_client.download_pdf.return_value = _PDF_BYTES

        results = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert len(results) == 1
        assert results[0].status == "downloaded"
        assert results[0].reason is None
        assert results[0].file_path is not None

    def test_successful_download_writes_file_to_disk(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """The PDF bytes from the API are written correctly to the output file."""
        mock_client.search.return_value = make_search_response(
            [make_raw_paper()], next_cursor="*"
        )
        mock_client.download_pdf.return_value = _PDF_BYTES

        results = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert results[0].file_path.read_bytes() == _PDF_BYTES

    def test_successful_download_result_has_paper_populated(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """The DownloadResult.paper field is populated with the correct pmid."""
        mock_client.search.return_value = make_search_response(
            [make_raw_paper(pmid="99999")], next_cursor="*"
        )
        mock_client.download_pdf.return_value = _PDF_BYTES

        results = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert results[0].paper.pmid == "99999"

    def test_skip_paper_without_pdf_url(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """A paper with no PDF URL is skipped with reason 'PDF unavailable'."""
        mock_client.search.return_value = make_search_response(
            [make_raw_paper(pdf_url=None)], next_cursor="*"
        )

        results = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert len(results) == 1
        assert results[0].status == "skipped"
        assert results[0].reason == "PDF unavailable"
        assert results[0].file_path is None

    def test_skip_already_downloaded_file(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """A paper whose file already exists is skipped with reason 'Already downloaded'."""
        paper = make_raw_paper(doi="10.1234/test", title="Test Paper")
        mock_client.search.return_value = make_search_response([paper], next_cursor="*")
        mock_client.download_pdf.return_value = _PDF_BYTES

        # First download — writes the file
        first = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )
        assert first[0].status == "downloaded"

        # Second download — same paper, file already exists
        second = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert second[0].status == "skipped"
        assert second[0].reason == "Already downloaded"

    def test_failed_download_on_http_error(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """An HTTP error during download returns status='failed' with the status code."""
        mock_client.search.return_value = make_search_response(
            [make_raw_paper()], next_cursor="*"
        )
        mock_client.download_pdf.side_effect = APIError(503, "Service Unavailable")

        results = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert len(results) == 1
        assert results[0].status == "failed"
        assert results[0].reason == "503"
        assert results[0].file_path is None

    def test_failed_download_on_connection_error(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """A ConnectionError from the client returns status='failed' instead of raising."""
        mock_client.search.return_value = make_search_response(
            [make_raw_paper()], next_cursor="*"
        )
        mock_client.download_pdf.side_effect = ConnectionError("Remote end closed connection")

        results = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert len(results) == 1
        assert results[0].status == "failed"
        assert results[0].reason == "Connection error"
        assert results[0].file_path is None

    def test_cancel_event_set_before_download_returns_empty(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """A pre-set cancel_event prevents any pages from being fetched."""
        cancel_event = threading.Event()
        cancel_event.set()

        results = service.download(
            make_params(tmp_path),
            progress_callback=lambda r: None,
            cancel_event=cancel_event,
        )

        mock_client.search.assert_not_called()
        assert results == []

    def test_cancel_event_set_during_first_page_stops_before_second(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """Setting cancel_event during the first search prevents a second page fetch."""
        cancel_event = threading.Event()
        paper = make_raw_paper(pdf_url=None)

        def search_side_effect(*args: object, **kwargs: object) -> dict:
            cancel_event.set()
            return make_search_response([paper], next_cursor="cursor2")

        mock_client.search.side_effect = search_side_effect

        results = service.download(
            make_params(tmp_path, count=10),
            progress_callback=lambda r: None,
            cancel_event=cancel_event,
        )

        assert mock_client.search.call_count == 1
        assert len(results) == 1

    def test_download_stops_when_count_reached(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """The loop does not fetch a second page once params.count successes are reached."""
        paper1 = make_raw_paper(pmid="1", doi="10.1/a", title="Paper A")
        paper2 = make_raw_paper(pmid="2", doi="10.1/b", title="Paper B")

        page1 = make_search_response([paper1], next_cursor="cursor2")
        page2 = make_search_response([paper2], next_cursor="*")
        mock_client.search.side_effect = [page1, page2]
        mock_client.download_pdf.return_value = _PDF_BYTES

        service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        mock_client.search.assert_called_once()

    def test_pagination_fetches_next_page(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """When one page is not enough, the next page is fetched using the cursor."""
        paper1 = make_raw_paper(pmid="1", doi="10.1/a", title="Paper A")
        paper2 = make_raw_paper(pmid="2", doi="10.1/b", title="Paper B")

        page1 = make_search_response([paper1], next_cursor="cursor2")
        page2 = make_search_response([paper2], next_cursor="*")
        mock_client.search.side_effect = [page1, page2]
        mock_client.download_pdf.return_value = _PDF_BYTES

        results = service.download(
            make_params(tmp_path, count=2),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert mock_client.search.call_count == 2
        assert sum(1 for r in results if r.status == "downloaded") == 2

    def test_stops_when_no_more_results(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """The loop stops when the API returns an empty result page."""
        paper = make_raw_paper(pmid="1", doi="10.1/a", title="A")
        page1 = make_search_response([paper], next_cursor="cursor2")

        mock_client.search.side_effect = [page1, EMPTY_RESPONSE]
        mock_client.download_pdf.return_value = _PDF_BYTES

        results = service.download(
            make_params(tmp_path, count=10),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert mock_client.search.call_count == 2
        assert len(results) == 1

    def test_progress_callback_called_once_per_attempt(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """progress_callback is called exactly once per paper processed."""
        paper_ok = make_raw_paper(pmid="1", doi="10.1/a", title="A")
        paper_skip = make_raw_paper(pmid="2", doi="10.1/b", title="B", pdf_url=None)

        mock_client.search.return_value = make_search_response(
            [paper_ok, paper_skip], next_cursor="*"
        )
        mock_client.download_pdf.return_value = _PDF_BYTES

        calls: list[DownloadResult] = []
        service.download(
            make_params(tmp_path, count=DOWNLOAD_PAGE_SIZE),  # batch mode
            progress_callback=calls.append,
            cancel_event=threading.Event(),
        )

        assert len(calls) == 2

    def test_progress_callback_receives_download_result(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """Each argument passed to progress_callback is a DownloadResult."""
        mock_client.search.return_value = make_search_response(
            [make_raw_paper()], next_cursor="*"
        )
        mock_client.download_pdf.return_value = _PDF_BYTES

        calls: list[DownloadResult] = []
        service.download(
            make_params(tmp_path, count=1),
            progress_callback=calls.append,
            cancel_event=threading.Event(),
        )

        assert all(isinstance(r, DownloadResult) for r in calls)

    def test_creates_pdfs_subdirectory(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """The pdfs/ subdirectory is created inside output_folder before any downloads."""
        mock_client.search.return_value = EMPTY_RESPONSE

        service.download(
            make_params(tmp_path),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert (tmp_path / "pdfs").is_dir()

    def test_empty_search_returns_empty_list(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """An empty search result returns an empty results list."""
        mock_client.search.return_value = EMPTY_RESPONSE

        results = service.download(
            make_params(tmp_path),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert results == []

    def test_returns_results_of_all_statuses(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """Results list contains downloaded, skipped, and failed outcomes."""
        paper_ok = make_raw_paper(pmid="1", doi="10.1/a", title="OK")
        paper_nopdf = make_raw_paper(pmid="2", doi="10.1/b", title="NoPDF", pdf_url=None)
        paper_fail = make_raw_paper(pmid="3", doi="10.1/c", title="Fail")

        mock_client.search.return_value = make_search_response(
            [paper_ok, paper_nopdf, paper_fail], next_cursor="*"
        )
        mock_client.download_pdf.side_effect = [_PDF_BYTES, APIError(500, "Error")]

        results = service.download(
            make_params(tmp_path, count=DOWNLOAD_PAGE_SIZE),  # batch mode
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        statuses = {r.status for r in results}
        assert "downloaded" in statuses
        assert "skipped" in statuses
        assert "failed" in statuses

    def test_failed_download_on_write_error(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """OSError writing PDF to disk returns status='failed' instead of raising."""
        mock_client.search.return_value = make_search_response(
            [make_raw_paper()], next_cursor="*"
        )
        mock_client.download_pdf.return_value = _PDF_BYTES

        with patch("epmcminer.services.download_service.Path.write_bytes",
                   side_effect=OSError("no space left")):
            results = service.download(
                make_params(tmp_path, count=1),
                progress_callback=lambda r: None,
                cancel_event=threading.Event(),
            )

        assert len(results) == 1
        assert results[0].status == "failed"
        assert results[0].reason == "Write error"

    def test_uses_full_page_size_in_batch_mode(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """Batch mode: search is called with page_size=DOWNLOAD_PAGE_SIZE when remaining >= it."""
        mock_client.search.return_value = make_search_response([], next_cursor="*")

        service.download(
            make_params(tmp_path, count=DOWNLOAD_PAGE_SIZE),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        _, kwargs = mock_client.search.call_args
        assert kwargs["page_size"] == DOWNLOAD_PAGE_SIZE

    def test_uses_page_size_one_in_single_paper_mode(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """When remaining < DOWNLOAD_PAGE_SIZE, search is called with page_size=1."""
        mock_client.search.return_value = make_search_response([], next_cursor="*")

        service.download(
            make_params(tmp_path, count=DOWNLOAD_PAGE_SIZE - 1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        _, kwargs = mock_client.search.call_args
        assert kwargs["page_size"] == 1

    def test_single_paper_mode_stops_at_exact_count(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """In single-paper mode, the loop exits as soon as success_count reaches params.count."""
        papers = [
            make_raw_paper(pmid=str(i), doi=f"10.1/{i:04d}", title=f"Paper {i}")
            for i in range(3)
        ]
        mock_client.search.side_effect = [
            make_search_response([papers[0]], next_cursor="c1"),
            make_search_response([papers[1]], next_cursor="c2"),
            make_search_response([papers[2]], next_cursor="c3"),
        ]
        mock_client.download_pdf.return_value = _PDF_BYTES

        results = service.download(
            make_params(tmp_path, count=3),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert mock_client.search.call_count == 3
        assert sum(1 for r in results if r.status == "downloaded") == 3

    def test_switches_to_single_paper_mode_after_batch(
        self, service: DownloadService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """After batch phase fills most of the quota, single-paper mode handles the remainder."""
        batch_papers = [
            make_raw_paper(pmid=str(i), doi=f"10.1/{i:04d}", title=f"Paper {i}")
            for i in range(DOWNLOAD_PAGE_SIZE)
        ]
        final_paper = make_raw_paper(
            pmid=str(DOWNLOAD_PAGE_SIZE),
            doi=f"10.1/{DOWNLOAD_PAGE_SIZE:04d}",
            title="Final Paper",
        )
        mock_client.search.side_effect = [
            make_search_response(batch_papers, next_cursor="after_batch"),
            make_search_response([final_paper], next_cursor="*"),
        ]
        mock_client.download_pdf.return_value = _PDF_BYTES

        results = service.download(
            make_params(tmp_path, count=DOWNLOAD_PAGE_SIZE + 1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        page_sizes = [call.kwargs["page_size"] for call in mock_client.search.call_args_list]
        assert page_sizes == [DOWNLOAD_PAGE_SIZE, 1]
        assert sum(1 for r in results if r.status == "downloaded") == DOWNLOAD_PAGE_SIZE + 1

    def test_build_query_is_called_with_params(
        self,
        service: DownloadService,
        mock_client: MagicMock,
        mock_search_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """SearchService.build_query is called once with the SearchParams."""
        mock_client.search.return_value = EMPTY_RESPONSE
        params = make_params(tmp_path)

        service.download(
            params,
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        mock_search_service.build_query.assert_called_once_with(params)
