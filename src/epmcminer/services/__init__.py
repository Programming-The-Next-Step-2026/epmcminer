"""epmcminer services package."""

from epmcminer.api.client import EuropePMCClient
from epmcminer.services.download_service import DownloadService
from epmcminer.services.report_service import ReportService
from epmcminer.services.search_service import SearchService


def create_application_services() -> tuple[SearchService, DownloadService, ReportService]:
    """Create and wire all application services with a shared API client.

    Returns:
        A tuple of (SearchService, DownloadService, ReportService) ready for
        injection into the GUI screens.
    """
    client = EuropePMCClient()
    search_service = SearchService(client=client)
    download_service = DownloadService(client=client, search_service=search_service)
    report_service = ReportService()
    return search_service, download_service, report_service
