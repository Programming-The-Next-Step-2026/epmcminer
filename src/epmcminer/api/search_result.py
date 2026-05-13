"""SearchResult data model."""

from dataclasses import dataclass


@dataclass
class SearchResult:
    """Holds the outcome of a Europe PMC search, including matched papers."""
