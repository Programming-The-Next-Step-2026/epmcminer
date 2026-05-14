"""Report service — generates report.csv, Excel export, and PDF export."""

from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from epmcminer.api.download_result import DownloadResult
from epmcminer.api.models import SearchParams
from epmcminer.utils.logger import get_logger

_logger = get_logger(__name__)

REPORT_COLUMNS: list[str] = [
    "title",
    "authors",
    "journal",
    "year",
    "doi",
    "status",
    "reason",
    "file_path",
    "query",
    "sort_order",
    "date_from",
    "date_to",
    "licenses",
    "publication_types",
]

_CSV_FILENAME = "report.csv"


class ReportService:
    """Generates download-summary reports in multiple formats.

    Produces a CSV report, an Excel workbook, and a PDF summary document
    from a list of DownloadResult objects. All file I/O runs in the caller's
    thread; callers are responsible for offloading to a QThread worker.
    """

    def __init__(self) -> None:
        """Initialise ReportService."""

    def save_csv(
        self,
        results: list[DownloadResult],
        params: SearchParams,
        output_folder: Path,
    ) -> Path:
        """Save report.csv to output_folder.

        Called automatically after the download phase completes.

        Args:
            results: List of DownloadResult objects from the download phase.
            params: The SearchParams used to produce the results.
            output_folder: Directory where report.csv will be written.

        Returns:
            The absolute Path to the written report.csv file.

        Raises:
            OSError: If the file cannot be written.
        """
        output_folder.mkdir(parents=True, exist_ok=True)
        path = output_folder / _CSV_FILENAME
        self._build_dataframe(results, params).to_csv(path, index=False)
        _logger.info("Saved CSV report to %s", path)
        return path

    def export_excel(
        self,
        results: list[DownloadResult],
        params: SearchParams,
        output_path: Path,
    ) -> None:
        """Export the report as an Excel (.xlsx) file.

        Args:
            results: List of DownloadResult objects from the download phase.
            params: The SearchParams used to produce the results.
            output_path: Full file path (including filename) for the Excel output.

        Raises:
            OSError: If the file cannot be written.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._build_dataframe(results, params).to_excel(output_path, index=False, engine="openpyxl")
        _logger.info("Saved Excel report to %s", output_path)

    def export_pdf(
        self,
        results: list[DownloadResult],
        params: SearchParams,
        output_path: Path,
    ) -> None:
        """Export the report as a PDF file using reportlab.

        Args:
            results: List of DownloadResult objects from the download phase.
            params: The SearchParams used to produce the results.
            output_path: Full file path (including filename) for the PDF output.

        Raises:
            OSError: If the file cannot be written.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df = self._build_dataframe(results, params)
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=landscape(A4),
            leftMargin=1 * cm,
            rightMargin=1 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )
        styles = getSampleStyleSheet()
        story = [
            Paragraph("epmcminer Download Report", styles["Title"]),
            Spacer(1, 0.4 * cm),
        ]

        table_data = [REPORT_COLUMNS] + [
            [str(v) if v is not None else "" for v in row]
            for row in df.itertuples(index=False, name=None)
        ]
        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ])
        )
        story.append(table)
        doc.build(story)
        _logger.info("Saved PDF report to %s", output_path)

    def _build_dataframe(
        self, results: list[DownloadResult], params: SearchParams
    ) -> pd.DataFrame:
        """Build a pandas DataFrame from download results and search parameters.

        Args:
            results: List of DownloadResult objects.
            params: The SearchParams used to produce the results.

        Returns:
            A DataFrame with one row per result and columns matching REPORT_COLUMNS.
        """
        rows = [
            {
                "title": result.paper.title,
                "authors": result.paper.authors,
                "journal": result.paper.journal,
                "year": result.paper.year,
                "doi": result.paper.doi,
                "status": result.status,
                "reason": result.reason if result.reason is not None else "",
                "file_path": str(result.file_path) if result.file_path is not None else "",
                "query": params.query,
                "sort_order": params.sort_order,
                "date_from": params.date_from,
                "date_to": params.date_to,
                "licenses": ", ".join(params.licenses),
                "publication_types": ", ".join(params.publication_types),
            }
            for result in results
        ]
        return pd.DataFrame(rows, columns=REPORT_COLUMNS)
