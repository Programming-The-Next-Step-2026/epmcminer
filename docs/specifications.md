# epmcminer — Feature Specifications & User Stories

## Table of Contents

- [Feature specifications](#feature-specifications)
  * [F1: Keyword search input](#f1-keyword-search-input)
  * [F2: Search filters](#f2-search-filters)
  * [F3: Results preview screen](#f3-results-preview-screen)
  * [F4: Sort order](#f4-sort-order)
  * [F5: Download settings](#f5-download-settings)
  * [F6: Parallel downloading with progress tracking](#f6-parallel-downloading-with-progress-tracking)
  * [F7: Output folder structure](#f7-output-folder-structure)
  * [F8: Summary report screen](#f8-summary-report-screen)
  * [F9: Europe PMC API integration](#f9-europe-pmc-api-integration)
  * [F10: Logging](#f10-logging)
- [User stories](#user-stories)
  * [US1: Searching and downloading papers (primary happy path)](#us1-searching-and-downloading-papers-primary-happy-path)
  * [US2: Adjusting filters after preview](#us2-adjusting-filters-after-preview)
  * [US3: Repeat run into the same folder](#us3-repeat-run-into-the-same-folder)
  * [US4: Exporting the summary report](#us4-exporting-the-summary-report)

---

## Feature specifications

### F1: Keyword search input

Users can enter a search query using free text. If no boolean operators are specified, AND logic is assumed between words. Users can explicitly use AND, OR, or NOT operators (uppercase) to control query logic. The query field accepts up to 500 characters.

---

### F2: Search filters

The following filters are available on the search screen.

**Date range**
Two date pickers for start and end date. Default: start = 5 years ago, end = today. The start date can be set as far back as 1 January 1900. The end date is capped at today.

**Publication type**
A tag-style input field pre-loaded with the following default types: Review, Meta analysis, Clinical trial, Systematic review, Comparative study, Observational study, Randomized controlled trial, Twin study, Validation study, Case reports, Dataset, Corrected and republished article, Clinical study, Evaluation study, Multicenter study, Observational study (veterinary). The user can remove any tag or add new ones from a dropdown of all types available in the Europe PMC API. At least one type must be selected.

**License**
A tag-style input field. Default: CC-BY. Options match those available on the Europe PMC website. At least one license must be selected.

**Author (ORCID)**
A tag-style input field. The user can add one or more ORCID identifiers (bare format `0000-0000-0000-0000` or with the `https://orcid.org/` prefix — the prefix is stripped automatically). Multiple ORCIDs use OR logic. The field can be left empty to search across all authors.

Each ORCID is validated in two steps as soon as it is added:

1. **Format check** (synchronous) — verifies the four-group pattern and the ISO 7064 MOD 11-2 checksum digit. Invalid ORCIDs are shown as a red pill immediately.
2. **Registry check** (asynchronous) — queries the ORCID public API (`pub.orcid.org`) to confirm the identifier exists. While the check is in flight the pill is shown in grey ("pending"). On success it turns orange; on failure it turns red. If the network is unreachable the pill stays grey so the user can still proceed (fail-open).

Red pills (invalid format or not found in the registry) are **excluded** from the search query. Pending (grey) ORCIDs — where the registry was unreachable — are still included so the user can proceed without network access. The validation is informational and does not block submission.

**Full-text availability**
Not a user-facing filter — hardcoded requirement that all results must have a freely available full text (`HAS_FT:Y OR HAS_FREE_FULLTEXT:Y`). This is communicated to the user via a lock icon in the action bar.

---

### F3: Results preview screen

When the user clicks "Continue to preview", a progress animation is displayed while the app queries the API and gathers results. This uses the same visual style as the download progress bar for consistency. Once results are ready, the animation is replaced by the preview content, which includes:

- Total number of results found in the API matching the query
- Estimated PDF availability as a percentage of the previewed results (e.g. `~62%`)
- A list of the first 10 results showing: title, authors, journal, year, DOI
- Download settings (number of papers and output folder) above the results list
- A sort order selector (see F4) in the results list header
- A "Back" button to return to Screen 1 and adjust filters
- A "Start download" button, disabled until the count is ≥ 1, an output folder is set, and the folder is writable

When either button ("Continue to preview" or "Start download") is disabled, an inline hint in the action bar explains which field still needs attention.

If the API call fails, the loading animation is replaced by an error message and a "Try again" button that re-runs the same query.

---

### F4: Sort order

A sort order selector is shown in the results preview header on Screen 2. Options are Relevance (default), Date (newest first), and Citations (most cited first). When the user changes the sort order:

- The results list is immediately replaced by the same progress animation used when first loading the preview
- The app re-queries the Europe PMC API with the updated sort parameter
- Once results return, the animation is replaced by the refreshed top 10 results and updated stat cards
- The sort order selected at the time the user clicks "Start download" is the one applied to the full download and recorded in the final report

---

### F5: Download settings

These settings are configured on Screen 2 (the preview screen) after the user has seen what results are available.

**Number of papers**: an integer input specifying the number of successfully downloaded papers desired. Default: 50. Accepted range: 1–10,000. The tool keeps retrieving results until that many papers are downloaded or the API returns no more results. Skipped papers do not count toward this total.

**Output folder**: the user selects a local folder via a folder picker dialog. The folder must be writable; if a non-writable directory is selected the "Start download" button remains disabled and a hint explains the reason.

---

### F6: Parallel downloading with progress tracking

PDFs are downloaded in parallel using multithreading. Screen 3 shows:

- A full-width progress bar with a percentage label and a count label (e.g. `46%  downloaded 23 out of 50  –  processed 31 results`)
- Estimated time remaining displayed to the right (e.g. `~3 min` or `~45s`)
- Animated thread indicators showing the number of active download threads (e.g. `2 threads running`)
- A live status log: each row appears when a paper finishes, showing a status icon (✓ downloaded / – skipped / ✗ failed), the filename or DOI, and either the file size (for downloads) or the skip/failure reason
- The output folder path echoed in the action bar
- A cancel button (✕ Cancel) to stop after the current batch

The UI remains responsive during downloading (non-blocking).

`report.csv` is saved automatically when the download finishes — including when it is cancelled. Already-downloaded PDF files are kept on cancellation. If saving the CSV fails, a toast notification is shown. A fatal download error (unhandled exception in the worker) also surfaces as a toast.

---

### F7: Output folder structure

Downloaded content is saved in the user-specified folder as follows:

```
output_folder/
  pdfs/
    {doi}_{title}.pdf
    ...
  logs/
    YYYY-MM-DD_HH-MM.log
  report.csv
```

PDF filenames are constructed as `{doi}_{title}.pdf` with special characters sanitised. If a PDF already exists in the folder from a previous run, it is skipped and noted in the report. One log file is created per run, timestamped at start time.

---

### F8: Summary report screen

After downloading completes, Screen 4 shows a summary containing:

- Stat cards: number of papers downloaded, number skipped, and total results found in the API
- A search parameters card: query, sort order, date range, license(s), publication types, and author ORCIDs (if any)
- A skipped papers list (hidden when all papers were downloaded): each row shows title, authors, journal, year, and the skip or failure reason

`report.csv` is saved automatically to the output folder on download completion. It has one row per paper processed (downloads and skips alike) with columns: title, authors, journal, year, doi, status, reason, file_path, query, sort_order, date_from, date_to, licenses, publication_types.

Three buttons in the action bar:
- **＋ New search** — resets the wizard to Screen 1 so the user can run a different query
- **Export Excel** — opens a save dialog and writes an `.xlsx` file with the same columns as `report.csv`; runs in a background thread so the UI stays responsive
- **Export PDF** — opens a save dialog and writes a portrait A4 PDF that mirrors the summary screen layout (stat block, parameters card, skipped papers list); also runs in a background thread

Both exports show a toast notification on success (filename) or failure (error message).

---

### F9: Europe PMC API integration

A dedicated API module handles all communication with Europe PMC:

- Constructs and sends search queries with all filter parameters and sort order
- Paginates through results to reach the requested count of successful downloads
- Retrieves full metadata per paper
- Resolves and downloads PDF files from full-text URLs
- Handles API errors, rate limits, and timeouts gracefully, logging all failures

---

### F10: Logging

Each run produces a timestamped log file in `output_folder/logs/`. The log records:

- Run start and end time
- Full query sent to the API, including sort order
- Each download attempt and its outcome
- Any API errors or unexpected failures

---

## User stories

### US1: Searching and downloading papers (primary happy path)

**As** a psychology researcher, **I want** to search for papers on a topic with specific filters and download a set number of available PDFs into a folder on my computer, **so that** I can efficiently build a literature collection without manually searching and downloading.

**Preconditions:**
- epmcminer is installed and running
- The user has an internet connection

**Steps:**

1. User opens epmcminer.
2. User enters keywords and configures filters: date range, publication types, license, and optionally one or more author ORCIDs.
3. User clicks "Continue to preview". A progress animation is shown while the app queries the Europe PMC API.
4. The app displays the results preview: total results found, estimated downloadable count, and the first 10 papers.
5. User optionally changes the sort order. The progress animation plays again, the API is re-queried, and the preview refreshes live with the updated results.
6. User reviews the preview, sets count and selects an output folder.
7. User clicks "Start download".
8. The app downloads papers in parallel. Screen 3 shows a progress bar, estimated time remaining, active thread indicators, and a live status log.
9. Download completes. Screen 4 shows the summary: stat cards (downloaded / skipped / total found), the search parameters used, and a list of any skipped papers with their reasons.
10. User optionally exports the report as Excel or PDF.

**Postconditions:**
- PDFs are saved in `output_folder/pdfs/`
- `report.csv` is saved in `output_folder/`
- A timestamped log file is saved in `output_folder/logs/`
- Any previously existing PDFs in the folder were skipped and noted in the report

---

### US2: Adjusting filters after preview

**As** a psychology researcher, **I want** to go back and refine my search after seeing the preview results, **so that** I don't waste time downloading papers that are not relevant.

**Steps:**

1. User reaches Screen 2 and finds the preview results unsatisfactory.
2. User clicks "Back".
3. The app returns to Screen 1 with all previously entered filters intact.
4. User adjusts one or more filters and clicks "Continue to preview" again.
5. Flow continues as per US1 from step 3.

---

### US3: Repeat run into the same folder

**As** a psychology researcher, **I want** to run the same or a similar search into a folder I have used before, **so that** I can top up my collection without re-downloading papers I already have.

**Steps:**

1. User runs epmcminer and selects an output folder that already contains previously downloaded PDFs.
2. The app proceeds normally through search, preview, and download.
3. During downloading, any PDF whose filename already exists in `output_folder/pdfs/` is skipped automatically.
4. Skipped-because-already-exists papers are listed in the summary report with the reason "Already downloaded".

---

### US4: Exporting the summary report

**As** a psychology researcher, **I want** to export the summary report after a download, **so that** I have a record of what was retrieved that I can share or archive.

**Steps:**

1. User reaches Screen 4 after a completed download.
2. User reviews the summary table.
3. User clicks "Export" and selects a format: Excel (.xlsx) or PDF (.pdf).
4. The app generates and saves the file to a location chosen by the user via a save dialog.
