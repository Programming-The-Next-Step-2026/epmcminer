"""SearchResult data model."""

from dataclasses import dataclass, field

from epmcminer.api.paper import Paper


@dataclass
class SearchResult:
    """Holds the outcome of a Europe PMC search request.

    Attributes:
        papers: List of papers returned by the search query.
        total_found: Total number of results reported by the API,
            which may exceed the length of ``papers``.
        estimated_downloadable: Number of papers in the previewed batch
            that have a freely available PDF URL.

    """

    papers: list[Paper] = field(default_factory=list)
    total_found: int = 0
    estimated_downloadable: int = 0
