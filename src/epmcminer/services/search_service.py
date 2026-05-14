"""Search service — builds Europe PMC queries and maps results to data models."""

import re

from epmcminer.api.client import (
    FREE_FULL_TEXT_FILTER,
    PDF_DOCUMENT_STYLE,
    SORT_BY_CITATIONS,
    SORT_BY_DATE,
    EuropePMCClient,
)
from epmcminer.api.models import Paper, SearchParams, SearchResult

PREVIEW_PAGE_SIZE = 10

_SORT_ORDER_MAP: dict[str, str | None] = {
    "relevance": None,
    "date": SORT_BY_DATE,
    "citations": SORT_BY_CITATIONS,
}


def _pdf_url_from_raw(raw: dict) -> str | None:
    """Extract the PDF URL from a raw core search result.

    The core search response embeds fullTextUrlList directly, avoiding a
    separate fullTextLinks API call. Returns the first entry whose
    documentStyle is 'pdf', or None if no such entry exists.

    Args:
        raw: A single result dict from the Europe PMC core search response.

    Returns:
        The PDF URL string, or None if no PDF link is present.
    """
    entries = raw.get("fullTextUrlList", {}).get("fullTextUrl", [])
    for entry in entries:
        if entry.get("documentStyle") == PDF_DOCUMENT_STYLE:
            return entry["url"]
    return None


class SearchService:
    """Orchestrates paper search operations against the Europe PMC API.

    Accepts SearchParams from the GUI layer, constructs the API query,
    delegates HTTP calls to EuropePMCClient, and returns typed SearchResult objects.
    """

    def __init__(self, client: EuropePMCClient) -> None:
        """Initialise SearchService with an injected API client.

        Args:
            client: An EuropePMCClient instance for making HTTP requests.
        """
        self._client = client

    def build_query(self, params: SearchParams) -> str:
        """Build a Europe PMC query string from SearchParams.

        Handles AND/OR keyword logic, date range, publication types,
        licenses, and author ORCIDs. The free-full-text availability
        filter is always appended and is not derived from params.

        Args:
            params: A SearchParams instance containing all search filters.

        Returns:
            A complete Europe PMC query string ready to pass to the API.
        """
        parts: list[str] = []

        query = params.query.strip()
        if not re.search(r"\b(AND|OR|NOT)\b", query):
            query = " AND ".join(query.split())
        parts.append(query)

        parts.append(f"(FIRST_PDATE:[{params.date_from} TO {params.date_to}])")

        if params.publication_types:
            clause = " OR ".join(f'PUB_TYPE:("{pt}")' for pt in params.publication_types)
            parts.append(f"({clause})")

        if params.licenses:
            clause = " OR ".join(f'LICENSE:"{lic}"' for lic in params.licenses)
            parts.append(f"({clause})")

        if params.author_orcids:
            clause = " OR ".join(f'AUTHORID:"{oid}"' for oid in params.author_orcids)
            parts.append(f"({clause})")

        parts.append(f"({FREE_FULL_TEXT_FILTER})")

        return " AND ".join(parts)

    def preview(self, params: SearchParams) -> SearchResult:
        """Fetch the first results for preview display.

        Builds a query from params, calls the API, extracts a PDF URL from each
        result's embedded fullTextUrlList, and returns a SearchResult with mapped
        Paper objects.

        Args:
            params: A SearchParams instance containing all search filters.

        Returns:
            A SearchResult containing up to PREVIEW_PAGE_SIZE Paper objects,
            the total hit count, and the estimated number of downloadable papers.

        Raises:
            APIError: If the Europe PMC API returns a non-200 response.
            ConnectionError: If the HTTP request cannot be completed.
        """
        query = self.build_query(params)
        sort = _SORT_ORDER_MAP.get(params.sort_order)
        data = self._client.search(query=query, page_size=PREVIEW_PAGE_SIZE, sort=sort)

        papers: list[Paper] = []
        for raw in data.get("resultList", {}).get("result", []):
            pmid = raw.get("pmid") or raw.get("id", "")
            pdf_url = _pdf_url_from_raw(raw)
            papers.append(
                Paper(
                    pmid=pmid,
                    doi=raw.get("doi", ""),
                    title=raw.get("title", ""),
                    authors=raw.get("authorString", ""),
                    journal=raw.get("journalTitle", ""),
                    year=raw.get("pubYear", ""),
                    abstract=raw.get("abstractText", ""),
                    pdf_url=pdf_url,
                )
            )

        estimated_downloadable = sum(1 for p in papers if p.pdf_url is not None)

        return SearchResult(
            papers=papers,
            total_found=data.get("hitCount", 0),
            estimated_downloadable=estimated_downloadable,
        )
