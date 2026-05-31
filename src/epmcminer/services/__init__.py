"""epmcminer services package."""

from epmcminer.api.client import EuropePMCClient
from epmcminer.api.orcid_client import OrcidClient
from epmcminer.services.download_service import DownloadService
from epmcminer.services.orcid_validation_service import OrcidValidationService
from epmcminer.services.report_service import ReportService
from epmcminer.services.search_service import SearchService


def create_application_services() -> tuple[
    SearchService, DownloadService, ReportService, OrcidValidationService
]:
    """Create and wire all application services with their required dependencies.

    Returns:
        A 4-tuple of ``(SearchService, DownloadService, ReportService,
        OrcidValidationService)`` ready for injection into the GUI screens.

    Examples:
        >>> search, download, report, orcid = create_application_services()
        >>> type(search).__name__
        'SearchService'
        >>> type(report).__name__
        'ReportService'

    """
    client = EuropePMCClient()
    search_service = SearchService(client=client)
    download_service = DownloadService(client=client, search_service=search_service)
    report_service = ReportService()
    orcid_client = OrcidClient()
    orcid_validation_service = OrcidValidationService(client=orcid_client)
    return search_service, download_service, report_service, orcid_validation_service
