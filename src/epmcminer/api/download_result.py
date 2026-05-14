"""DownloadResult data model."""

from dataclasses import dataclass
from pathlib import Path

from epmcminer.api.paper import Paper


@dataclass
class DownloadResult:
    """Holds the outcome of a single PDF download attempt.

    Attributes:
        paper: The paper that was processed.
        status: Outcome of the download attempt. One of ``"downloaded"``,
            ``"skipped"``, or ``"failed"``.
        reason: Human-readable explanation of why the paper was skipped or
            failed. ``None`` when ``status`` is ``"downloaded"``.
        file_path: Absolute path to the saved PDF file, or ``None`` when
            the paper was not downloaded.
    """

    paper: Paper
    status: str
    reason: str | None
    file_path: Path | None
