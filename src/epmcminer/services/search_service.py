"""Search service — builds queries, calls the API client, returns SearchResult."""


class SearchService:
    """Orchestrates paper search operations against the Europe PMC API.

    Accepts SearchParams from the GUI layer, constructs the API query,
    delegates HTTP calls to EpmcClient, and returns a typed SearchResult.
    """
