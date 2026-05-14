"""Europe PMC API HTTP client — raw HTTP calls only, no business logic."""

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"


class EpmcClient:
    """Thin HTTP client for the Europe PMC REST API.

    Responsible only for making HTTP requests and returning raw response
    data. All business logic belongs in the service layer.
    """
