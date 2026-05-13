"""Convenience re-exports of all API data models.

Import all model classes from this module:

    from epmcminer.api.models import DownloadResult, Paper, SearchParams, SearchResult
"""

from epmcminer.api.download_result import DownloadResult
from epmcminer.api.paper import Paper
from epmcminer.api.search_params import SearchParams
from epmcminer.api.search_result import SearchResult

__all__ = ["DownloadResult", "Paper", "SearchParams", "SearchResult"]
