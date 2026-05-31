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

    Examples:
        >>> paper = Paper(
        ...     pmid="34567890",
        ...     doi="10.1234/example",
        ...     title="Sleep and memory consolidation",
        ...     authors="Walker MP, Stickgold R",
        ...     journal="Neuron",
        ...     year="2022",
        ...     abstract="Sleep plays a crucial role in memory.",
        ...     pdf_url="https://europepmc.org/articles/PMC1234567?pdf=render",
        ... )
        >>> paper.doi
        '10.1234/example'
        >>> paper.pdf_url is not None
        True

    """

    pmid: str
    doi: str
    title: str
    authors: str
    journal: str
    year: str
    abstract: str
    pdf_url: str | None
