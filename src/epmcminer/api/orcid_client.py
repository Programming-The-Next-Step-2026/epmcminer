"""HTTP client for the ORCID public registry API.

Handles existence checks against the ORCID public API (pub.orcid.org). All
methods are thin wrappers around HTTP calls — no business logic lives here.
"""

import requests

ORCID_API_BASE = "https://pub.orcid.org/v3.0"

_ACCEPT_HEADER = "application/json"
_REQUEST_TIMEOUT = 10


class OrcidClient:
    """Client for the ORCID public registry API.

    Provides a single method to check whether an ORCID identifier exists in
    the public registry. Uses a persistent :class:`requests.Session` for
    connection reuse.

    Examples:
        >>> client = OrcidClient()
        >>> client.check_exists("0000-0001-5109-3700")
        True
    """

    def __init__(self) -> None:
        """Initialise the client with a new requests Session."""
        self._session = requests.Session()

    def check_exists(self, orcid: str) -> bool:
        """Check whether an ORCID identifier exists in the public registry.

        Sends a GET request to ``{ORCID_API_BASE}/{orcid}`` and interprets
        the HTTP status code: 200 means the record exists, any other status
        (including 404) means it does not.

        Args:
            orcid: The bare ORCID identifier, e.g. ``"0000-0001-5109-3700"``.
                Must not include the ``https://orcid.org/`` URL prefix.

        Returns:
            ``True`` if the ORCID exists in the public registry (HTTP 200),
            ``False`` otherwise (HTTP 404 or any other non-200 status).

        Raises:
            ConnectionError: If a network-level failure (connection error or
                timeout) prevents the request from completing.
        """
        url = f"{ORCID_API_BASE}/{orcid}"
        try:
            response = self._session.get(
                url,
                headers={"Accept": _ACCEPT_HEADER},
                timeout=_REQUEST_TIMEOUT,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            raise ConnectionError(str(exc)) from exc
        return response.status_code == 200
