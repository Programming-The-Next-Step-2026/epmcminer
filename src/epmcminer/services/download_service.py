"""Download service — parallel PDF downloads, skip logic, folder structure."""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from epmcminer.api.client import (
    DEFAULT_CURSOR_MARK,
    PDF_DOCUMENT_STYLE,
    SORT_BY_CITATIONS,
    SORT_BY_DATE,
    APIError,
    EuropePMCClient,
)
from epmcminer.api.download_result import DownloadResult
from epmcminer.api.models import Paper, SearchParams
from epmcminer.services.search_service import SearchService
from epmcminer.utils.file_utils import sanitise_filename
from epmcminer.utils.logger import get_logger

_logger = get_logger(__name__)

DOWNLOAD_PAGE_SIZE = 25

_SORT_ORDER_MAP: dict[str, str | None] = {
    "relevance": None,
    "date": SORT_BY_DATE,
    "citations": SORT_BY_CITATIONS,
}

_STATUS_DOWNLOADED = "downloaded"
_STATUS_SKIPPED = "skipped"
_STATUS_FAILED = "failed"
_REASON_NO_PDF = "PDF unavailable"
_REASON_ALREADY_DOWNLOADED = "Already downloaded"


def _pdf_url_from_raw(raw: dict) -> str | None:
    """Extract the PDF URL from a raw core search result.

    Args:
        raw: A single result dict from the Europe PMC core search response.

    Returns:
        The PDF URL string, or None if no PDF link is present.
    """
    entries = raw.get("fullTextUrlList", {}).get("fullTextUrl", [])
    for entry in entries:
        if entry.get("documentStyle") == PDF_DOCUMENT_STYLE:
            return entry["url"]
    return None


class DownloadService:
    """Manages parallel PDF downloads for a list of papers.

    Applies skip logic (already downloaded, no open-access PDF), constructs
    the output folder structure, and returns a DownloadResult list summarising
    the operation.
    """

    MAX_WORKERS = 4

    def __init__(self, client: EuropePMCClient, search_service: SearchService) -> None:
        """Initialise DownloadService with injected API client and search service.

        Args:
            client: An EuropePMCClient instance for HTTP requests and PDF downloads.
            search_service: A SearchService instance used to build the API query string.
        """
        self._client = client
        self._search_service = search_service

    def download(
        self,
        params: SearchParams,
        progress_callback: Callable[[DownloadResult], None],
        cancel_event: threading.Event,
    ) -> list[DownloadResult]:
        """Download up to params.count PDFs matching the search parameters.

        Fetches results in pages, downloads PDFs in parallel, and calls
        progress_callback after each individual download attempt.
        Stops early if cancel_event is set.

        Args:
            params: A SearchParams instance containing the search query,
                filters, desired count, and output folder.
            progress_callback: Called once per download attempt with the
                resulting DownloadResult (success, skip, or failure).
            cancel_event: When set, the download loop stops cleanly after
                the current page finishes.

        Returns:
            A list of DownloadResult objects, one per paper processed.

        Raises:
            APIError: If the Europe PMC search API returns a non-200 response.
            ConnectionError: If an HTTP request cannot be completed.
        """
        pdfs_dir = params.output_folder / "pdfs"
        pdfs_dir.mkdir(parents=True, exist_ok=True)

        query = self._search_service.build_query(params)
        sort = _SORT_ORDER_MAP.get(params.sort_order)

        all_results: list[DownloadResult] = []
        success_count = 0
        cursor_mark = DEFAULT_CURSOR_MARK

        while success_count < params.count:
            if cancel_event.is_set():
                break

            data = self._client.search(
                query=query,
                page_size=DOWNLOAD_PAGE_SIZE,
                sort=sort,
                cursor_mark=cursor_mark,
            )
            raw_results: list[dict] = data.get("resultList", {}).get("result", [])
            if not raw_results:
                break

            page_results = self._download_page(raw_results, pdfs_dir)
            for result in page_results:
                all_results.append(result)
                progress_callback(result)
                if result.status == _STATUS_DOWNLOADED:
                    success_count += 1

            next_cursor: str = data.get("nextCursorMark", "")
            if not next_cursor or next_cursor == cursor_mark:
                break
            cursor_mark = next_cursor

        return all_results

    def _download_page(self, raw_results: list[dict], pdfs_dir: Path) -> list[DownloadResult]:
        """Download papers from one API page in parallel.

        Args:
            raw_results: List of raw result dicts from the API.
            pdfs_dir: Directory where PDFs are saved.

        Returns:
            A list of DownloadResult objects in completion order.
        """
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._download_one, raw, pdfs_dir): raw
                for raw in raw_results
            }
            return [future.result() for future in as_completed(futures)]

    def _download_one(self, raw: dict, pdfs_dir: Path) -> DownloadResult:
        """Attempt to download a single paper's PDF.

        Args:
            raw: A single result dict from the Europe PMC core search response.
            pdfs_dir: Directory where the PDF should be saved.

        Returns:
            A DownloadResult describing the outcome.
        """
        pmid = raw.get("pmid") or raw.get("id", "")
        pdf_url = _pdf_url_from_raw(raw)
        paper = Paper(
            pmid=pmid,
            doi=raw.get("doi", ""),
            title=raw.get("title", ""),
            authors=raw.get("authorString", ""),
            journal=raw.get("journalTitle", ""),
            year=raw.get("pubYear", ""),
            abstract=raw.get("abstractText", ""),
            pdf_url=pdf_url,
        )

        _logger.info("Processing paper: %s", pmid)

        if pdf_url is None:
            _logger.info("Skipping %s: PDF unavailable", pmid)
            return DownloadResult(
                paper=paper, status=_STATUS_SKIPPED, reason=_REASON_NO_PDF, file_path=None
            )

        doi_part = sanitise_filename(paper.doi) if paper.doi else "no_doi"
        title_part = sanitise_filename(paper.title) if paper.title else "no_title"
        file_path = pdfs_dir / f"{doi_part}_{title_part}.pdf"

        if file_path.exists():
            _logger.info("Skipping %s: already downloaded at %s", pmid, file_path)
            return DownloadResult(
                paper=paper,
                status=_STATUS_SKIPPED,
                reason=_REASON_ALREADY_DOWNLOADED,
                file_path=file_path,
            )

        try:
            pdf_bytes = self._client.download_pdf(pdf_url)
        except APIError as exc:
            _logger.warning("Failed to download %s: HTTP %s", pmid, exc.status_code)
            return DownloadResult(
                paper=paper,
                status=_STATUS_FAILED,
                reason=str(exc.status_code),
                file_path=None,
            )

        file_path.write_bytes(pdf_bytes)
        _logger.info("Downloaded %s to %s", pmid, file_path)
        return DownloadResult(
            paper=paper, status=_STATUS_DOWNLOADED, reason=None, file_path=file_path
        )
