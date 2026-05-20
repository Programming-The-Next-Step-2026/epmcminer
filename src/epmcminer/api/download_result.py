"""DownloadResult data model."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal

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
        active_threads: Number of download threads still running at the
            moment this result was emitted (not counting the thread that
            just finished).
    """

    STATUS_DOWNLOADED: ClassVar[str] = "downloaded"
    STATUS_SKIPPED: ClassVar[str] = "skipped"
    STATUS_FAILED: ClassVar[str] = "failed"

    paper: Paper
    status: Literal["downloaded", "skipped", "failed"]
    reason: str | None
    file_path: Path | None
    active_threads: int = 0
