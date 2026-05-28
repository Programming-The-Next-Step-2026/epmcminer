"""Report service — generates report.csv, Excel export, and PDF export."""

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from epmcminer.api.search_params import SearchParams
from epmcminer.services.download_result import DownloadResult
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

# ---------------------------------------------------------------------------
# PDF theme constants
# ---------------------------------------------------------------------------

_PDF_PAGE_MARGIN = 1.5 * cm
_PDF_USABLE_WIDTH = A4[0] - 2 * _PDF_PAGE_MARGIN
_PDF_STAT_COL_WIDTH = _PDF_USABLE_WIDTH / 3
_PDF_PARAM_LABEL_COL = 90.0  # pt — fixed width for the parameter name column

_PDF_BG = HexColor("#0b0b0d")
_PDF_CARD = HexColor("#1c1c1f")
_PDF_ACCENT = HexColor("#ff7a3d")
_PDF_TEXT = HexColor("#ededed")
_PDF_MUTED = HexColor("#8a8a8d")
_PDF_DANGER = HexColor("#f87171")
_PDF_BORDER = HexColor("#2c2c2f")


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _draw_pdf_bg(canvas: Any, doc: Any) -> None:
    """Draw the dark page background on every PDF page.

    Args:
        canvas: The reportlab canvas for the current page.
        doc: The reportlab document template.
    """
    canvas.saveState()
    canvas.setFillColor(_PDF_BG)
    w, h = doc.pagesize
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.restoreState()


class ReportService:
    """Generates download-summary reports in multiple formats.

    Produces a CSV report, an Excel workbook, and a PDF summary document
    from a list of DownloadResult objects. All file I/O runs in the caller's
    thread; callers are responsible for offloading to a QThread worker.
    """

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

        Examples:
            >>> from pathlib import Path
            >>> report_path = service.save_csv(results, params, Path("/tmp/my_run"))
            >>> print(report_path.name)
            report.csv
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

        Examples:
            >>> from pathlib import Path
            >>> service.export_excel(results, params, Path("/tmp/my_run/report.xlsx"))
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._build_dataframe(results, params).to_excel(output_path, index=False, engine="openpyxl")
        _logger.info("Saved Excel report to %s", output_path)

    def export_pdf(
        self,
        results: list[DownloadResult],
        params: SearchParams,
        output_path: Path,
        total_found: int = 0,
    ) -> None:
        """Export the report as a styled PDF mirroring the summary screen layout.

        The PDF uses the application's dark colour palette and is organised into
        three sections: a stat row (downloaded / skipped / total), a search
        parameters card, and an optional skipped-papers list.

        Args:
            results: List of DownloadResult objects from the download phase.
            params: The SearchParams used to produce the results.
            output_path: Full file path (including filename) for the PDF output.
            total_found: Total number of papers found in the API search; displayed
                in the "Total results" stat block. Defaults to 0 when not provided.

        Raises:
            OSError: If the file cannot be written.

        Examples:
            >>> from pathlib import Path
            >>> out = Path("/tmp/my_run/report.pdf")
            >>> service.export_pdf(results, params, out, total_found=1024)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=_PDF_PAGE_MARGIN,
            rightMargin=_PDF_PAGE_MARGIN,
            topMargin=_PDF_PAGE_MARGIN,
            bottomMargin=_PDF_PAGE_MARGIN,
        )
        styles = self._make_pdf_styles()
        story = self._build_pdf_story(results, params, total_found, styles)
        doc.build(story, onFirstPage=_draw_pdf_bg, onLaterPages=_draw_pdf_bg)
        _logger.info("Saved PDF report to %s", output_path)

    # ------------------------------------------------------------------
    # PDF helper methods
    # ------------------------------------------------------------------

    def _make_pdf_styles(self) -> dict[str, ParagraphStyle]:
        """Create and return all paragraph styles used in the PDF export.

        Returns:
            A mapping from style name to ParagraphStyle instance.
        """
        return {
            "title": ParagraphStyle(
                "pdf_title",
                fontSize=22,
                textColor=_PDF_ACCENT,
                fontName="Helvetica-Bold",
                spaceAfter=2,
                leading=26,
            ),
            "subtitle": ParagraphStyle(
                "pdf_subtitle",
                fontSize=10,
                textColor=_PDF_MUTED,
                leading=13,
            ),
            "section": ParagraphStyle(
                "pdf_section",
                fontSize=11,
                textColor=_PDF_MUTED,
                fontName="Helvetica-Bold",
                spaceBefore=8,
                spaceAfter=0,
                leading=14,
            ),
            "stat_label": ParagraphStyle(
                "pdf_stat_label",
                fontSize=10,
                textColor=_PDF_MUTED,
                leading=13,
            ),
            "stat_value_accent": ParagraphStyle(
                "pdf_stat_val_accent",
                fontSize=24,
                textColor=_PDF_ACCENT,
                fontName="Helvetica-Bold",
                leading=28,
                spaceAfter=2,
            ),
            "stat_value_danger": ParagraphStyle(
                "pdf_stat_val_danger",
                fontSize=24,
                textColor=_PDF_DANGER,
                fontName="Helvetica-Bold",
                leading=28,
                spaceAfter=2,
            ),
            "stat_sub": ParagraphStyle(
                "pdf_stat_sub",
                fontSize=9,
                textColor=_PDF_MUTED,
                leading=12,
            ),
            "param_label": ParagraphStyle(
                "pdf_param_label",
                fontSize=10,
                textColor=_PDF_MUTED,
                leading=14,
            ),
            "param_value": ParagraphStyle(
                "pdf_param_value",
                fontSize=10,
                textColor=_PDF_TEXT,
                fontName="Helvetica-Bold",
                leading=14,
            ),
            "paper_title": ParagraphStyle(
                "pdf_paper_title",
                fontSize=12,
                textColor=_PDF_TEXT,
                fontName="Helvetica-Bold",
                leading=16,
            ),
            "paper_meta": ParagraphStyle(
                "pdf_paper_meta",
                fontSize=10,
                textColor=_PDF_MUTED,
                leading=14,
            ),
            "paper_reason": ParagraphStyle(
                "pdf_paper_reason",
                fontSize=10,
                textColor=_PDF_DANGER,
                leading=14,
            ),
            "paper_filepath": ParagraphStyle(
                "pdf_paper_filepath",
                fontSize=9,
                textColor=_PDF_MUTED,
                leading=12,
            ),
        }

    def _build_pdf_story(
        self,
        results: list[DownloadResult],
        params: SearchParams,
        total_found: int,
        styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
        """Assemble all flowable elements into the PDF story list.

        Args:
            results: Download results for this run.
            params: Search parameters for this run.
            total_found: Total API result count.
            styles: Paragraph styles returned by :meth:`_make_pdf_styles`.

        Returns:
            A list of reportlab flowable objects ready to pass to ``doc.build()``.
        """
        story: list = []
        story.extend(self._pdf_header(styles))
        story.append(self._pdf_stat_row(results, total_found, styles))
        story.append(Spacer(1, 0.4 * cm))
        story.extend(self._pdf_params_card(params, styles))
        downloaded_items = self._pdf_downloaded_section(results, styles)
        if downloaded_items:
            story.append(Spacer(1, 0.3 * cm))
            story.extend(downloaded_items)
        skipped_items = self._pdf_skipped_section(results, styles)
        if skipped_items:
            story.append(Spacer(1, 0.3 * cm))
            story.extend(skipped_items)
        return story

    def _pdf_header(self, styles: dict[str, ParagraphStyle]) -> list:
        """Build the title and timestamp header flowables.

        Args:
            styles: Paragraph styles mapping.

        Returns:
            List of flowable elements for the header section.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        return [
            Paragraph("epmcminer", styles["title"]),
            Paragraph(f"Download report  ·  Generated {timestamp}", styles["subtitle"]),
            Spacer(1, 0.4 * cm),
        ]

    def _pdf_stat_row(
        self,
        results: list[DownloadResult],
        total_found: int,
        styles: dict[str, ParagraphStyle],
    ) -> Table:
        """Build the three-column stat card table.

        Args:
            results: Download results used to derive downloaded/skipped counts.
            total_found: Total API result count for the "Total results" card.
            styles: Paragraph styles mapping.

        Returns:
            A reportlab Table containing the three stat cards side by side.
        """
        downloaded = sum(1 for r in results if r.status == DownloadResult.STATUS_DOWNLOADED)
        not_downloaded = len(results) - downloaded

        def _make_cell(
            label: str, value: str, value_style_key: str, sub: str
        ) -> list[Paragraph]:
            return [
                Paragraph(label, styles["stat_label"]),
                Paragraph(value, styles[value_style_key]),
                Paragraph(sub, styles["stat_sub"]),
            ]

        data = [[
            _make_cell(
                "Downloaded", str(downloaded), "stat_value_accent",
                f"of {len(results)} processed",
            ),
            _make_cell(
                "Skipped", str(not_downloaded), "stat_value_danger",
                "see reasons below",
            ),
            _make_cell(
                "Total results", f"{total_found:,}", "stat_value_accent",
                "found in Europe PMC",
            ),
        ]]

        w = _PDF_STAT_COL_WIDTH
        table = Table(data, colWidths=[w, w, w])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _PDF_CARD),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("LINEAFTER", (0, 0), (1, -1), 0.5, _PDF_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return table

    def _pdf_params_card(
        self,
        params: SearchParams,
        styles: dict[str, ParagraphStyle],
    ) -> list:
        """Build the search parameters card flowables.

        Always includes Query, Sort, and Date. Conditionally appends License,
        Publication types, and Authors when those fields are non-empty.

        Args:
            params: Search parameters to display.
            styles: Paragraph styles mapping.

        Returns:
            List of flowable elements for the parameters section.
        """
        rows: list[tuple[str, str]] = [
            ("Query", params.query),
            ("Sort", params.sort_order.capitalize()),
            ("Date", f"{params.date_from}  →  {params.date_to}"),
        ]
        if params.licenses:
            rows.append(("License", ", ".join(params.licenses)))
        if params.publication_types:
            rows.append(("Publication types", ", ".join(params.publication_types)))
        if params.author_orcids:
            rows.append(("Authors", f"{len(params.author_orcids)} ORCIDs"))

        label_w = _PDF_PARAM_LABEL_COL
        value_w = _PDF_USABLE_WIDTH - label_w
        table_data = [
            [
                Paragraph(label, styles["param_label"]),
                Paragraph(value, styles["param_value"]),
            ]
            for label, value in rows
        ]

        n = len(rows)
        style_commands: list = [
            ("BACKGROUND", (0, 0), (-1, -1), _PDF_CARD),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for i in range(n - 1):
            style_commands.append(("LINEBELOW", (0, i), (-1, i), 0.5, _PDF_BORDER))

        table = Table(table_data, colWidths=[label_w, value_w])
        table.setStyle(TableStyle(style_commands))
        return [Paragraph("Search parameters", styles["section"]), Spacer(1, 4), table]

    def _pdf_downloaded_section(
        self,
        results: list[DownloadResult],
        styles: dict[str, ParagraphStyle],
    ) -> list:
        """Build the downloaded papers section flowables.

        Returns an empty list when no papers were downloaded successfully.

        Args:
            results: Download results; downloaded ones are listed here.
            styles: Paragraph styles mapping.

        Returns:
            List of flowable elements for the downloaded papers section, or ``[]``
            when no result has status ``"downloaded"``.
        """
        downloaded = [r for r in results if r.status == DownloadResult.STATUS_DOWNLOADED]
        if not downloaded:
            return []

        items: list = [Paragraph("Downloaded papers", styles["section"]), Spacer(1, 4)]
        for i, result in enumerate(downloaded):
            meta_parts = [result.paper.authors, result.paper.journal, result.paper.year]
            meta_str = " · ".join(p for p in meta_parts if p)
            cell_content: list = [
                Paragraph(result.paper.title or "", styles["paper_title"]),
                Spacer(1, 2),
                Paragraph(meta_str or "—", styles["paper_meta"]),
            ]
            if result.file_path is not None:
                cell_content += [
                    Spacer(1, 2),
                    Paragraph(result.file_path.name, styles["paper_filepath"]),
                ]
            row_table = Table([[cell_content]], colWidths=[_PDF_USABLE_WIDTH])
            row_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), _PDF_CARD),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            items.append(row_table)
            if i < len(downloaded) - 1:
                items.append(Spacer(1, 3))
        return items

    def _pdf_skipped_section(
        self,
        results: list[DownloadResult],
        styles: dict[str, ParagraphStyle],
    ) -> list:
        """Build the skipped/failed papers section flowables.

        Returns an empty list when all papers were downloaded successfully.

        Args:
            results: Download results; non-downloaded ones are listed here.
            styles: Paragraph styles mapping.

        Returns:
            List of flowable elements for the skipped papers section, or ``[]``
            when every result has status ``"downloaded"``.
        """
        not_downloaded = [r for r in results if r.status != DownloadResult.STATUS_DOWNLOADED]
        if not not_downloaded:
            return []

        items: list = [Paragraph("Skipped papers", styles["section"]), Spacer(1, 4)]
        for i, result in enumerate(not_downloaded):
            meta_parts = [result.paper.authors, result.paper.journal, result.paper.year]
            meta_str = " · ".join(p for p in meta_parts if p)
            cell_content: list = [
                Paragraph(result.paper.title or "", styles["paper_title"]),
                Spacer(1, 2),
                Paragraph(meta_str or "—", styles["paper_meta"]),
                Spacer(1, 2),
                Paragraph(result.reason or "Unknown reason", styles["paper_reason"]),
            ]
            row_table = Table([[cell_content]], colWidths=[_PDF_USABLE_WIDTH])
            row_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), _PDF_CARD),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            items.append(row_table)
            if i < len(not_downloaded) - 1:
                items.append(Spacer(1, 3))
        return items

    # ------------------------------------------------------------------
    # Shared DataFrame builder (used by save_csv and export_excel)
    # ------------------------------------------------------------------

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
