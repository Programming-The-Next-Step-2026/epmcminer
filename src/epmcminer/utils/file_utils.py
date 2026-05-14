"""Path sanitisation and filename construction utilities."""

import re
from pathlib import Path

MAX_FILENAME_COMPONENT_LENGTH = 80

_INVALID_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def sanitise_filename(text: str, max_length: int = MAX_FILENAME_COMPONENT_LENGTH) -> str:
    """Replace filesystem-invalid characters and normalise whitespace.

    Replaces characters that are forbidden in filenames on Windows and
    Unix (``\\ / : * ? " < > |`` and ASCII control characters) with
    underscores, collapses runs of whitespace into a single underscore,
    and truncates the result to ``max_length``.

    Args:
        text: The raw string to sanitise (e.g. a DOI or paper title).
        max_length: Maximum number of characters in the returned string.
            Defaults to ``MAX_FILENAME_COMPONENT_LENGTH``.

    Returns:
        A sanitised string safe to use as a filename component. Returns
        ``"_"`` if the input is empty or contains only invalid characters.
    """
    sanitised = _INVALID_CHARS.sub("_", text)
    sanitised = re.sub(r"\s+", "_", sanitised)
    sanitised = sanitised[:max_length]
    return sanitised if sanitised.strip("_") else "_"


def build_pdf_filename(doi: str, title: str) -> str:
    """Construct a PDF filename from DOI and title.

    Sanitises each component and joins them with an underscore.

    Args:
        doi: The paper's DOI string. Uses ``"no_doi"`` when empty.
        title: The paper's title string. Uses ``"no_title"`` when empty.

    Returns:
        A filename string in the format ``{sanitised_doi}_{sanitised_title}.pdf``.
    """
    doi_part = sanitise_filename(doi) if doi else "no_doi"
    title_part = sanitise_filename(title) if title else "no_title"
    return f"{doi_part}_{title_part}.pdf"


def ensure_output_structure(output_folder: Path) -> None:
    """Create the standard subdirectory layout inside output_folder.

    Creates ``output_folder/pdfs/`` and ``output_folder/logs/``, including
    any missing parent directories. Safe to call repeatedly.

    Args:
        output_folder: Root directory for a download session.
    """
    (output_folder / "pdfs").mkdir(parents=True, exist_ok=True)
    (output_folder / "logs").mkdir(parents=True, exist_ok=True)
