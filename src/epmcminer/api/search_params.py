"""SearchParams data model."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal


@dataclass
class SearchParams:
    """Encapsulates all parameters for a Europe PMC search request.

    Attributes:
        query: Free-text search query, e.g. ``"depression AND therapy"``.
        date_from: Start of the publication date range in ISO format (YYYY-MM-DD).
        date_to: End of the publication date range in ISO format (YYYY-MM-DD).
        publication_types: List of Europe PMC publication type strings to filter by.
        licenses: List of license identifiers to filter by, e.g. ``["CC-BY"]``.
        author_orcids: List of author ORCID identifiers. Combined with OR logic.
            May be empty to search across all authors.
        sort_order: Result ordering. One of ``"relevance"``, ``"date"``, or
            ``"citations"``.
        count: Number of papers to successfully download. Must be greater than 0.
        output_folder: Local filesystem path to the folder where downloads are saved.
            Must be set before calling :meth:`DownloadService.download`; may be
            ``None`` when the params are only used for a search preview.

    Raises:
        ValueError: If ``count`` is not greater than 0.
        ValueError: If ``date_from`` or ``date_to`` is not a valid ISO-8601 date (YYYY-MM-DD).
        ValueError: If ``date_from`` is later than ``date_to``.

    """

    query: str
    date_from: str
    date_to: str
    publication_types: list[str] = field(default_factory=list)
    licenses: list[str] = field(default_factory=list)
    author_orcids: list[str] = field(default_factory=list)
    sort_order: Literal["relevance", "date", "citations"] = "relevance"
    count: int = 10
    output_folder: Path | None = None

    def __post_init__(self) -> None:
        """Validate field values after initialisation.

        Raises:
            ValueError: If ``count`` is not greater than 0.
            ValueError: If ``date_from`` or ``date_to`` is not a valid ISO-8601 date.
            ValueError: If ``date_from`` is later than ``date_to``.

        """
        if self.count <= 0:
            raise ValueError(f"count must be greater than 0, got {self.count}.")
        try:
            parsed_from = date.fromisoformat(self.date_from)
        except ValueError as exc:
            raise ValueError(
                f"date_from must be a valid ISO-8601 date (YYYY-MM-DD), got {self.date_from!r}.",
            ) from exc
        try:
            parsed_to = date.fromisoformat(self.date_to)
        except ValueError as exc:
            raise ValueError(
                f"date_to must be a valid ISO-8601 date (YYYY-MM-DD), got {self.date_to!r}.",
            ) from exc
        if parsed_from > parsed_to:
            raise ValueError(
                f"date_from ({self.date_from}) must not be later than date_to ({self.date_to}).",
            )
