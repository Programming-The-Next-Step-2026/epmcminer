"""Download service — parallel PDF downloads, skip logic, folder structure."""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from epmcminer.api.client import (
    DEFAULT_CURSOR_MARK,
    APIError,
    EuropePMCClient,
    InvalidPdfContentError,
)
from epmcminer.api.search_params import SearchParams
from epmcminer.services.download_result import DownloadResult
from epmcminer.services.search_service import SORT_ORDER_MAP, SearchService, paper_from_raw
from epmcminer.utils.file_utils import build_pdf_filename
from epmcminer.utils.logger import get_logger, setup_logger

_logger = get_logger(__name__)

DOWNLOAD_PAGE_SIZE = 10

_REASON_NO_PDF = "PDF unavailable"
_REASON_ALREADY_DOWNLOADED = "Already downloaded"
_REASON_RATE_LIMITED = "Server rate limiting"


class DownloadService:
    """Manages parallel PDF downloads for a list of papers.

    Applies skip logic (already downloaded, no open-access PDF), constructs
    the output folder structure, and returns a DownloadResult list summarising
    the operation.

    Examples:
        >>> from unittest.mock import MagicMock
        >>> service = DownloadService(client=MagicMock(), search_service=MagicMock())
        >>> service.MAX_WORKERS
        2

    """

    MAX_WORKERS = 2  # reduced from 4 to limit concurrent request rate and avoid HTTP 429

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
            ValueError: If ``params.output_folder`` is ``None``.
            APIError: If the Europe PMC search API returns a non-200 response.
            ConnectionError: If an HTTP request cannot be completed.

        Examples:
            >>> import threading
            >>> from pathlib import Path
            >>> from unittest.mock import MagicMock
            >>> from epmcminer.api.search_params import SearchParams
            >>> service = DownloadService(client=MagicMock(), search_service=MagicMock())
            >>> params = SearchParams(
            ...     query="memory AND sleep",
            ...     date_from="2022-01-01",
            ...     date_to="2024-12-31",
            ...     count=5,
            ...     output_folder=Path("/tmp/my_run"),
            ... )
            >>> cancel = threading.Event()
            >>> results = service.download(  # doctest: +SKIP
            ...     params, progress_callback=print, cancel_event=cancel
            ... )
            >>> print(sum(1 for r in results if r.status == "downloaded"))  # doctest: +SKIP
            5

        """
        if params.output_folder is None:
            raise ValueError(
                "SearchParams.output_folder must be set before calling download().",
            )

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
            raw_results: list[dict[str, Any]] = data.get("resultList", {}).get("result", [])
            if not raw_results:
                break

            if page_size == DOWNLOAD_PAGE_SIZE:
                page_results = self._download_page(
                    raw_results,
                    pdfs_dir,
                    progress_callback,
                    cancel_event,
                )
                all_results.extend(page_results)
                success_count += sum(
                    1 for r in page_results if r.status == DownloadResult.STATUS_DOWNLOADED
                )
            else:
                result = self._download_one(raw_results[0], pdfs_dir, cancel_event)
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
        raw_results: list[dict[str, Any]],
        pdfs_dir: Path,
        progress_callback: Callable[[DownloadResult], None],
        cancel_event: threading.Event,
    ) -> list[DownloadResult]:
        """Download papers from one API page in parallel, calling progress_callback
        immediately as each individual download completes.

        Respects cancel_event: tasks that have not yet started HTTP work are
        short-circuited immediately; in-flight requests complete naturally.

        Args:
            raw_results: List of raw result dicts from the API.
            pdfs_dir: Directory where PDFs are saved.
            progress_callback: Called once per completed download.
            cancel_event: When set, queued tasks are skipped and no new
                HTTP requests are started.

        Returns:
            A list of DownloadResult objects in completion order.

        """
        results: list[DownloadResult] = []
        active = 0
        lock = threading.Lock()

        def run_one(raw: dict[str, Any]) -> DownloadResult:
            """Download one paper and maintain the shared active-thread counter."""
            nonlocal active
            if cancel_event.is_set():
                return DownloadResult(
                    paper=paper_from_raw(raw),
                    status=DownloadResult.STATUS_SKIPPED,
                    reason="Cancelled",
                    file_path=None,
                )
            with lock:
                active += 1
            result = self._download_one(raw, pdfs_dir, cancel_event)
            with lock:
                result.active_threads = active
                active -= 1
            return result

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            # Submit one at a time so cancellation can bail before all page
            # tasks are queued rather than waiting for a full batch to finish.
            futures: dict[Any, dict[str, Any]] = {}
            for raw in raw_results:
                if cancel_event.is_set():
                    break
                futures[executor.submit(run_one, raw)] = raw
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                progress_callback(result)
        return results

    def _download_one(
        self,
        raw: dict[str, Any],
        pdfs_dir: Path,
        cancel_event: threading.Event | None = None,
    ) -> DownloadResult:
        """Attempt to download a single paper's PDF.

        Args:
            raw: A single result dict from the Europe PMC core search response.
            pdfs_dir: Directory where the PDF should be saved.
            cancel_event: Optional cancellation signal forwarded to the HTTP
                client so that backoff sleeps are interruptible.  When set
                during a retry, the result will have status ``STATUS_SKIPPED``
                with reason ``"Cancelled"`` rather than ``STATUS_FAILED``.

        Returns:
            A DownloadResult describing the outcome.

        """
        paper = paper_from_raw(raw)
        _logger.info("Processing paper: %s", paper.pmid)

        if paper.pdf_url is None:
            _logger.info("Skipping %s: PDF unavailable", paper.pmid)
            return DownloadResult(
                paper=paper,
                status=DownloadResult.STATUS_SKIPPED,
                reason=_REASON_NO_PDF,
                file_path=None,
            )

        file_path = pdfs_dir / build_pdf_filename(paper.doi, paper.title)

        if file_path.exists():
            _logger.info("Skipping %s: already downloaded at %s", paper.pmid, file_path)
            return DownloadResult(
                paper=paper,
                status=DownloadResult.STATUS_SKIPPED,
                reason=_REASON_ALREADY_DOWNLOADED,
                file_path=file_path,
            )

        try:
            pdf_bytes = self._client.download_pdf(paper.pdf_url, cancel_event=cancel_event)
        except InvalidPdfContentError as exc:
            _logger.warning("Skipping %s: %s", paper.pmid, exc)
            return DownloadResult(
                paper=paper,
                status=DownloadResult.STATUS_SKIPPED,
                reason="Not a valid PDF",
                file_path=None,
            )
        except APIError as exc:
            _logger.warning("Failed to download %s: HTTP %s", paper.pmid, exc.status_code)
            reason = _REASON_RATE_LIMITED if exc.status_code == 429 else _REASON_NO_PDF
            return DownloadResult(
                paper=paper,
                status=DownloadResult.STATUS_FAILED,
                reason=reason,
                file_path=None,
            )
        except ConnectionError as exc:
            if cancel_event is not None and cancel_event.is_set():
                _logger.info("Download of %s cancelled during retry", paper.pmid)
                return DownloadResult(
                    paper=paper,
                    status=DownloadResult.STATUS_SKIPPED,
                    reason="Cancelled",
                    file_path=None,
                )
            _logger.warning("Connection error downloading %s: %s", paper.pmid, exc)
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
                paper=paper,
                status=DownloadResult.STATUS_FAILED,
                reason="Write error",
                file_path=None,
            )
        _logger.info("Downloaded %s to %s", paper.pmid, file_path)
        return DownloadResult(
            paper=paper,
            status=DownloadResult.STATUS_DOWNLOADED,
            reason=None,
            file_path=file_path,
        )
