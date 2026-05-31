"""ORCID identifier utilities — format validation and normalisation.

Pure functions with no external dependencies. Safe to import anywhere in the
application, including before a QApplication instance exists.
"""

import re

_ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
_URL_PREFIXES = ("https://orcid.org/", "http://orcid.org/")


def normalise_orcid(orcid: str) -> str:
    """Strip URL prefix and surrounding whitespace from an ORCID string.

    Args:
        orcid: Raw ORCID string, with or without an ``https://orcid.org/`` prefix.

    Returns:
        The bare ORCID identifier, e.g. ``"0000-0001-5109-3700"``.

    Examples:
        >>> normalise_orcid("https://orcid.org/0000-0001-5109-3700")
        '0000-0001-5109-3700'
        >>> normalise_orcid("  0000-0001-5109-3700  ")
        '0000-0001-5109-3700'

    """
    orcid = orcid.strip()
    for prefix in _URL_PREFIXES:
        if orcid.startswith(prefix):
            orcid = orcid[len(prefix) :]
            break
    return orcid


def _compute_checksum(digits15: str) -> str:
    """Compute the ISO 7064 MOD 11-2 check character for the first 15 ORCID digits.

    Args:
        digits15: The first 15 digits of an ORCID with dashes removed.

    Returns:
        The expected check character: ``"0"``–``"9"`` or ``"X"`` (representing 10).

    """
    total = 0
    for char in digits15:
        total = (total + int(char)) * 2
    remainder = total % 11
    result = (12 - remainder) % 11
    return "X" if result == 10 else str(result)


def validate_orcid_format(orcid: str) -> bool:
    """Validate an ORCID identifier by pattern and ISO 7064 MOD 11-2 checksum.

    Accepts ORCIDs with or without the ``https://orcid.org/`` URL prefix and
    strips surrounding whitespace before validating.

    Args:
        orcid: The ORCID string to validate.

    Returns:
        ``True`` if the format is correct and the checksum digit matches,
        ``False`` otherwise.

    Examples:
        >>> validate_orcid_format("0000-0001-5109-3700")
        True
        >>> validate_orcid_format("0000-0001-5109-3701")
        False
        >>> validate_orcid_format("https://orcid.org/0000-0001-5109-3700")
        True

    """
    bare = normalise_orcid(orcid)
    if not _ORCID_PATTERN.match(bare):
        return False
    digits = bare.replace("-", "")
    return digits[15] == _compute_checksum(digits[:15])
