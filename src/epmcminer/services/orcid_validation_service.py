"""Service layer for ORCID identifier validation.

Orchestrates synchronous format validation and asynchronous existence checks
against the ORCID public registry. All pure logic is delegated to
:mod:`epmcminer.utils.orcid_utils`; all HTTP calls are delegated to
:class:`epmcminer.api.orcid_client.OrcidClient`.
"""

from epmcminer.api.orcid_client import OrcidClient
from epmcminer.utils.orcid_utils import normalise_orcid, validate_orcid_format


class OrcidValidationService:
    """Validates ORCID identifiers by format and registry existence.

    This service is the single point of contact for ORCID validation in the
    application. Format validation is synchronous and can be called freely on
    the main thread. Existence checking is an HTTP call and must be run in a
    :class:`~PyQt6.QtCore.QThread` worker to avoid blocking the GUI.

    Args:
        client: An :class:`~epmcminer.api.orcid_client.OrcidClient` instance
            used to make existence-check requests to the ORCID public API.

    Examples:
        >>> from epmcminer.api.orcid_client import OrcidClient
        >>> service = OrcidValidationService(client=OrcidClient())
        >>> service.validate_format("0000-0001-5109-3700")
        True

    """

    def __init__(self, client: OrcidClient) -> None:
        """Initialise the service with an ORCID API client."""
        self._client = client

    def validate_format(self, orcid: str) -> bool:
        """Validate an ORCID identifier by pattern and ISO 7064 MOD 11-2 checksum.

        This method is purely local — it performs no network calls and is safe
        to invoke on the main thread.

        Args:
            orcid: The ORCID string to validate. May include an optional
                ``https://orcid.org/`` URL prefix and surrounding whitespace.

        Returns:
            ``True`` if the format and checksum are correct, ``False`` otherwise.

        Examples:
            >>> from unittest.mock import MagicMock
            >>> service = OrcidValidationService(client=MagicMock())
            >>> service.validate_format("0000-0001-5109-3700")
            True
            >>> service.validate_format("not-an-orcid")
            False
            >>> service.validate_format("https://orcid.org/0000-0001-5109-3700")
            True

        """
        return validate_orcid_format(orcid)

    def check_exists(self, orcid: str) -> bool:
        """Check whether an ORCID exists in the public registry.

        Delegates to :meth:`~epmcminer.api.orcid_client.OrcidClient.check_exists`.
        This method makes an HTTP request and **must** be called from a background
        thread (e.g. a :class:`~PyQt6.QtCore.QThread` worker) to avoid blocking
        the GUI.

        Args:
            orcid: The bare ORCID identifier to look up (no URL prefix).

        Returns:
            ``True`` if the ORCID is found in the registry, ``False`` otherwise.

        Raises:
            ConnectionError: If a network-level failure prevents the request
                from completing.

        Examples:
            >>> from unittest.mock import MagicMock
            >>> client = MagicMock()
            >>> client.check_exists.return_value = True
            >>> service = OrcidValidationService(client=client)
            >>> service.check_exists("0000-0001-5109-3700")
            True

        """
        return self._client.check_exists(orcid)

    def normalise(self, orcid: str) -> str:
        """Strip the URL prefix and surrounding whitespace from an ORCID string.

        This method is purely local — it performs no network calls and is safe
        to invoke on the main thread.

        Args:
            orcid: Raw ORCID string, with or without an ``https://orcid.org/``
                or ``http://orcid.org/`` prefix.

        Returns:
            The bare ORCID identifier, e.g. ``"0000-0001-5109-3700"``.

        Examples:
            >>> from unittest.mock import MagicMock
            >>> service = OrcidValidationService(client=MagicMock())
            >>> service.normalise("https://orcid.org/0000-0001-5109-3700")
            '0000-0001-5109-3700'
            >>> service.normalise("  0000-0001-5109-3700  ")
            '0000-0001-5109-3700'

        """
        return normalise_orcid(orcid)
