"""Download service — parallel PDF downloads, skip logic, folder structure."""


class DownloadService:
    """Manages parallel PDF downloads for a list of papers.

    Applies skip logic (already downloaded, no open-access PDF), constructs
    the output folder structure, and returns a DownloadResult summarising
    the operation.
    """
