"""epmcminer — Europe PMC literature retrieval toolkit.

Exports the public API for programmatic use without the GUI.
"""

from epmcminer.services import create_application_services
from epmcminer.services.download_service import DownloadService
from epmcminer.services.models import DownloadResult, Paper, SearchParams, SearchResult
from epmcminer.services.report_service import ReportService
from epmcminer.services.search_service import SearchService

__all__ = [
    "create_application_services",
    "DownloadResult",
    "DownloadService",
    "Paper",
    "ReportService",
    "SearchParams",
    "SearchResult",
    "SearchService",
]
