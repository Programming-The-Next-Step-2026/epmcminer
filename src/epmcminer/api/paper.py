"""Paper data model."""

from dataclasses import dataclass


@dataclass
class Paper:
    """Represents a single academic paper retrieved from Europe PMC.

    Attributes:
        pmid: PubMed identifier for the paper.
        doi: Digital Object Identifier, e.g. ``"10.1000/xyz123"``.
        title: Full paper title.
        authors: Author list formatted as ``"Smith J, Jones A"``.
        journal: Name of the publishing journal.
        year: Publication year as a four-digit string, e.g. ``"2022"``.
        abstract: Full abstract text.
        pdf_url: Direct URL to the open-access PDF, or ``None`` if unavailable.
    """

    pmid: str
    doi: str
    title: str
    authors: str
    journal: str
    year: str
    abstract: str
    pdf_url: str | None
