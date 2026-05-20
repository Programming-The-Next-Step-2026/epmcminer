"""Re-export hub for data model types used by the GUI layer.

GUI modules should import all data models from here so they depend only on the
service layer and not directly on ``epmcminer.api``.
"""

from epmcminer.api.download_result import DownloadResult
from epmcminer.api.paper import Paper
from epmcminer.api.search_params import SearchParams
from epmcminer.api.search_result import SearchResult

__all__ = ["DownloadResult", "Paper", "SearchParams", "SearchResult"]
