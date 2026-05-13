"""Report service — generates report.csv, Excel export, and PDF export."""


class ReportService:
    """Generates download-summary reports in multiple formats.

    Produces a CSV report, an Excel workbook, and a PDF summary document
    from a DownloadResult. All file I/O runs in the caller's thread; callers
    are responsible for offloading to a QThread worker.
    """
