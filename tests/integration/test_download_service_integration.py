"""Integration tests for DownloadService — hits the real Europe PMC API.

This directory sits outside the unit-test tree defined in CLAUDE.md so that
integration tests can be excluded from CI with ``-m "not integration"`` without
touching the mirrored unit-test structure under tests/test_services/.

Run with:
    pytest -m integration

Skip during normal development/CI with:
    pytest -m "not integration"
"""

import threading
from pathlib import Path

import pytest

from epmcminer.api.client import EuropePMCClient
from epmcminer.api.download_result import DownloadResult
from epmcminer.api.models import SearchParams
from epmcminer.services.download_service import DownloadService
from epmcminer.services.search_service import SearchService

COMMON_QUERY = "depression"
DATE_FROM = "2020-01-01"
DATE_TO = "2024-12-31"


def make_params(output_folder: Path, **overrides: object) -> SearchParams:
    """Return a SearchParams with sensible defaults for integration tests."""
    defaults: dict = {
        "query": COMMON_QUERY,
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
        "sort_order": "relevance",
        "count": 1,
        "output_folder": output_folder,
    }
    defaults.update(overrides)
    return SearchParams(**defaults)


@pytest.fixture(scope="module")
def client() -> EuropePMCClient:
    """Shared EuropePMCClient for integration tests."""
    return EuropePMCClient()


@pytest.fixture(scope="module")
def search_service(client: EuropePMCClient) -> SearchService:
    """Shared SearchService backed by a real EuropePMCClient."""
    return SearchService(client=client)


@pytest.fixture(scope="module")
def service(client: EuropePMCClient, search_service: SearchService) -> DownloadService:
    """Shared DownloadService backed by real dependencies."""
    return DownloadService(client=client, search_service=search_service)


# ---------------------------------------------------------------------------
# DownloadService.download
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDownloadIntegration:
    """Integration tests for DownloadService.download."""

    def test_download_creates_pdfs_directory(
        self, service: DownloadService, tmp_path: Path
    ) -> None:
        """download() creates the pdfs/ subdirectory inside output_folder."""
        service.download(
            make_params(tmp_path),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert (tmp_path / "pdfs").is_dir()

    def test_download_returns_list_of_download_results(
        self, service: DownloadService, tmp_path: Path
    ) -> None:
        """download() returns a list of DownloadResult objects."""
        results = service.download(
            make_params(tmp_path),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        assert isinstance(results, list)
        assert all(isinstance(r, DownloadResult) for r in results)

    def test_download_achieves_at_least_one_success(
        self, service: DownloadService, tmp_path: Path
    ) -> None:
        """A broad query with count=1 results in at least one downloaded file."""
        results = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        downloaded = [r for r in results if r.status == "downloaded"]
        assert len(downloaded) >= 1

    def test_downloaded_file_exists_on_disk(
        self, service: DownloadService, tmp_path: Path
    ) -> None:
        """Each result with status='downloaded' has a file_path that exists on disk."""
        results = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        for result in results:
            if result.status == "downloaded":
                assert result.file_path is not None
                assert result.file_path.exists()
                assert result.file_path.stat().st_size > 0

    def test_downloaded_file_is_valid_pdf(
        self, service: DownloadService, tmp_path: Path
    ) -> None:
        """The saved file starts with the PDF magic bytes ``%PDF``."""
        results = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        for result in results:
            if result.status == "downloaded":
                assert result.file_path.read_bytes()[:4] == b"%PDF"
                return

        pytest.skip("No paper was successfully downloaded — cannot verify PDF content")

    def test_progress_callback_called_for_each_result(
        self, service: DownloadService, tmp_path: Path
    ) -> None:
        """progress_callback is called once per paper processed."""
        calls: list[DownloadResult] = []

        results = service.download(
            make_params(tmp_path, count=1),
            progress_callback=calls.append,
            cancel_event=threading.Event(),
        )

        assert len(calls) == len(results)

    def test_cancel_event_stops_download(
        self, service: DownloadService, tmp_path: Path
    ) -> None:
        """A pre-set cancel_event returns an empty list without calling the API."""
        cancel_event = threading.Event()
        cancel_event.set()

        results = service.download(
            make_params(tmp_path),
            progress_callback=lambda r: None,
            cancel_event=cancel_event,
        )

        assert results == []

    def test_already_downloaded_file_is_skipped_on_second_run(
        self, service: DownloadService, tmp_path: Path
    ) -> None:
        """Calling download() twice for the same paper skips it the second time."""
        first = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        if not any(r.status == "downloaded" for r in first):
            pytest.skip("First download produced no successes — cannot test skip logic")

        second = service.download(
            make_params(tmp_path, count=1),
            progress_callback=lambda r: None,
            cancel_event=threading.Event(),
        )

        skipped = [r for r in second if r.status == "skipped" and r.reason == "Already downloaded"]
        assert len(skipped) >= 1
