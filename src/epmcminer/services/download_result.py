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
        active_threads: Number of download threads that were running at the
            moment this result was emitted, including the thread that just
            finished.

    Examples:
        >>> from pathlib import Path
        >>> from epmcminer.api.paper import Paper
        >>> paper = Paper(
        ...     pmid="1", doi="10.1/test", title="Sleep study", authors="Smith J",
        ...     journal="Sleep", year="2023", abstract="", pdf_url=None,
        ... )
        >>> result = DownloadResult(
        ...     paper=paper, status=DownloadResult.STATUS_DOWNLOADED,
        ...     reason=None, file_path=Path("/tmp/paper.pdf"),
        ... )
        >>> result.status
        'downloaded'
        >>> result.reason is None
        True

    """

    STATUS_DOWNLOADED: ClassVar[Literal["downloaded"]] = "downloaded"
    STATUS_SKIPPED: ClassVar[Literal["skipped"]] = "skipped"
    STATUS_FAILED: ClassVar[Literal["failed"]] = "failed"

    paper: Paper
    status: Literal["downloaded", "skipped", "failed"]
    reason: str | None
    file_path: Path | None
    active_threads: int = 0
