"""Download service — parallel PDF downloads, skip logic, folder structure."""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from epmcminer.api.client import (
    DEFAULT_CURSOR_MARK,
    APIError,
    EuropePMCClient,
)
from epmcminer.api.download_result import DownloadResult
from epmcminer.api.models import Paper, SearchParams
from epmcminer.services.search_service import SORT_ORDER_MAP, SearchService, pdf_url_from_raw
from epmcminer.utils.file_utils import build_pdf_filename
from epmcminer.utils.logger import get_logger, setup_logger

_logger = get_logger(__name__)

DOWNLOAD_PAGE_SIZE = 10

_REASON_NO_PDF = "PDF unavailable"
_REASON_ALREADY_DOWNLOADED = "Already downloaded"


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

        Uses two phases to minimise overshoot:
        - Batch mode (remaining >= DOWNLOAD_PAGE_SIZE): fetches a full page and
          downloads all papers in parallel.
        - Single-paper mode (remaining < DOWNLOAD_PAGE_SIZE): fetches and
          downloads one paper at a time so the loop can stop as soon as the
          target is reached.

        Args:
            params: A SearchParams instance containing the search query,
                filters, desired count, and output folder.
            progress_callback: Called once per download attempt with the
                resulting DownloadResult (success, skip, or failure).
            cancel_event: When set, the download loop stops after the current
                paper or page finishes.

        Returns:
            A list of DownloadResult objects, one per paper processed.

        Raises:
            APIError: If the Europe PMC search API returns a non-200 response.
            ConnectionError: If an HTTP request cannot be completed.
        """
        setup_logger(params.output_folder)

        pdfs_dir = params.output_folder / "pdfs"
        pdfs_dir.mkdir(parents=True, exist_ok=True)

        query = self._search_service.build_query(params)
        sort = SORT_ORDER_MAP.get(params.sort_order)

        all_results: list[DownloadResult] = []
        success_count = 0
        cursor_mark = DEFAULT_CURSOR_MARK

        while success_count < params.count:
            if cancel_event.is_set():
                break

            remaining = params.count - success_count
            page_size = DOWNLOAD_PAGE_SIZE if remaining >= DOWNLOAD_PAGE_SIZE else 1

            data = self._client.search(
                query=query,
                page_size=page_size,
                sort=sort,
                cursor_mark=cursor_mark,
            )
            raw_results: list[dict] = data.get("resultList", {}).get("result", [])
            if not raw_results:
                break

            if page_size == DOWNLOAD_PAGE_SIZE:
                page_results = self._download_page(raw_results, pdfs_dir, progress_callback)
                for result in page_results:
                    all_results.append(result)
                    if result.status == DownloadResult.STATUS_DOWNLOADED:
                        success_count += 1
            else:
                result = self._download_one(raw_results[0], pdfs_dir)
                progress_callback(result)
                all_results.append(result)
                if result.status == DownloadResult.STATUS_DOWNLOADED:
                    success_count += 1

            next_cursor: str = data.get("nextCursorMark", "")
            if not next_cursor or next_cursor == cursor_mark:
                break
            cursor_mark = next_cursor

        return all_results

    def _download_page(
        self,
        raw_results: list[dict],
        pdfs_dir: Path,
        progress_callback: Callable[[DownloadResult], None],
    ) -> list[DownloadResult]:
        """Download papers from one API page in parallel, calling progress_callback
        immediately as each individual download completes.

        Args:
            raw_results: List of raw result dicts from the API.
            pdfs_dir: Directory where PDFs are saved.
            progress_callback: Called once per completed download.

        Returns:
            A list of DownloadResult objects in completion order.
        """
        results: list[DownloadResult] = []
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._download_one, raw, pdfs_dir): raw
                for raw in raw_results
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                progress_callback(result)
        return results

    def _download_one(self, raw: dict, pdfs_dir: Path) -> DownloadResult:
        """Attempt to download a single paper's PDF.

        Args:
            raw: A single result dict from the Europe PMC core search response.
            pdfs_dir: Directory where the PDF should be saved.

        Returns:
            A DownloadResult describing the outcome.
        """
        pmid = raw.get("pmid") or raw.get("id", "")
        pdf_url = pdf_url_from_raw(raw)
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
                paper=paper,
                status=DownloadResult.STATUS_SKIPPED,
                reason=_REASON_NO_PDF,
                file_path=None,
            )

        file_path = pdfs_dir / build_pdf_filename(paper.doi, paper.title)

        if file_path.exists():
            _logger.info("Skipping %s: already downloaded at %s", pmid, file_path)
            return DownloadResult(
                paper=paper,
                status=DownloadResult.STATUS_SKIPPED,
                reason=_REASON_ALREADY_DOWNLOADED,
                file_path=file_path,
            )

        try:
            pdf_bytes = self._client.download_pdf(pdf_url)
        except APIError as exc:
            _logger.warning("Failed to download %s: HTTP %s", pmid, exc.status_code)
            return DownloadResult(
                paper=paper,
                status=DownloadResult.STATUS_FAILED,
                reason=str(exc.status_code),
                file_path=None,
            )
        except ConnectionError as exc:
            _logger.warning("Connection error downloading %s: %s", pmid, exc)
            return DownloadResult(
                paper=paper,
                status=DownloadResult.STATUS_FAILED,
                reason="Connection error",
                file_path=None,
            )

        try:
            file_path.write_bytes(pdf_bytes)
        except OSError as exc:
            _logger.warning("Failed to write %s: %s", file_path, exc)
            return DownloadResult(
                paper=paper, status=DownloadResult.STATUS_FAILED, reason="Write error", file_path=None
            )
        _logger.info("Downloaded %s to %s", pmid, file_path)
        return DownloadResult(
            paper=paper, status=DownloadResult.STATUS_DOWNLOADED, reason=None, file_path=file_path
        )
