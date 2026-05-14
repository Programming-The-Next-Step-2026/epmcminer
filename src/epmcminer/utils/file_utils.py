"""Path sanitisation and filename construction utilities."""

import re

MAX_FILENAME_COMPONENT_LENGTH = 200

_INVALID_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def sanitise_filename(text: str) -> str:
    """Replace filesystem-invalid characters and normalise whitespace.

    Replaces characters that are forbidden in filenames on Windows and
    Unix (``\\ / : * ? " < > |`` and ASCII control characters) with
    underscores, collapses runs of whitespace into a single underscore,
    and truncates the result to ``MAX_FILENAME_COMPONENT_LENGTH``.

    Args:
        text: The raw string to sanitise (e.g. a DOI or paper title).

    Returns:
        A sanitised string safe to use as a filename component. Returns
        ``"_"`` if the input is empty or contains only invalid characters.
    """
    sanitised = _INVALID_CHARS.sub("_", text)
    sanitised = re.sub(r"\s+", "_", sanitised)
    sanitised = sanitised[:MAX_FILENAME_COMPONENT_LENGTH]
    return sanitised if sanitised.strip("_") else "_"
