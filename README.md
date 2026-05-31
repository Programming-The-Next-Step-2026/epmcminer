# epmcminer

## Table of Contents

<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [Overview](#overview)
- [Screenshots](#screenshots)
- [Usage](#usage)
- [Python API](#python-api)
- [Development](#development)
- [Architecture](#architecture)
- [Specifications](#specifications)

<!-- TOC end -->

<!-- TOC --><a name="overview"></a>
## Overview

A desktop application for researchers that automates the retrieval of academic literature from the [Europe PubMed Central (Europe PMC) API](https://europepmc.org/RestfulWebService). It allows users to define a search query and a set of filters, preview matching results, and download up to a specified number of open-access papers — including their PDFs and metadata — into a structured local folder.

epmcminer is designed for researchers in psychology and adjacent fields who need to systematically collect literature without manual searching and downloading. It requires no programming knowledge and provides a clean, step-by-step interface that guides the user from query construction to a downloadable report of results.

epmcminer only retrieves papers that are freely and legally available in full text. Papers that cannot be downloaded are clearly flagged in the final report with a reason. All searches are logged locally for reproducibility, and previously downloaded papers are automatically skipped on repeat runs.

**Core capabilities:**
- Keyword search with AND/OR logic against the Europe PMC database
- Filtering by date range, publication type, license, and author (via ORCID)
- Live results preview with adjustable sort order before committing to a download
- Parallel downloading of up to a user-specified count of PDFs with a real-time progress indicator
- A summary report exportable as PDF or Excel, containing the search query, filters applied, download results, paper metadata, and reasons for any skipped papers

---

<!-- TOC --><a name="screenshots"></a>
## Screenshots

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/mockup_screen_1.png" width="90%"><br>
      Screen 1 - Search and filter configuration
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/mockup_screen_2.png" width="90%"><br>
      Screen 2 - Results preview and download settings
    </td>
  </tr>

  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/mockup_screen_3.png" width="90%"><br>
      Screen 3 - Download progress
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/mockup_screen_4.png" width="90%"><br>
      Screen 4 - Summary report
    </td>
  </tr>
</table>

<!-- TOC --><a name="usage"></a>
## Usage

### System prerequisites (Linux only)

PyQt6 requires two OpenGL/EGL system libraries that are not always present on minimal Linux installs:

```bash
sudo apt-get install -y libegl1 libgl1
```

macOS and Windows users do not need this step.

### Install and run

First, create and activate your virtual environment and install the package:

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

Then launch the application using either of the following:

```bash
# as a module
python -m epmcminer

# via the installed script
epmcminer
```

### Tutorial notebook

A step-by-step walkthrough of all four screens — with a worked example and sample output — is available as an interactive Jupyter notebook:

```bash
pip install jupyter
jupyter lab docs/vignette.ipynb
```

The notebook also renders statically on GitHub (including the Mermaid flowchart) if you'd rather read it without launching Jupyter.

---

<!-- TOC --><a name="python-api"></a>
## Python API

epmcminer can be used as a library without launching the GUI. All public classes and functions are importable directly from the top-level package.

### Available exports

| Name | What it is |
|---|---|
| `SearchParams` | Input model — configure your query, filters, and output folder |
| `SearchResult` | Output model returned by `SearchService.preview()` |
| `Paper` | A single paper with title, authors, DOI, PDF URL, etc. |
| `DownloadResult` | Outcome of one download attempt (downloaded / skipped / failed) |
| `SearchService` | Searches Europe PMC and returns `SearchResult` |
| `DownloadService` | Downloads PDFs in parallel and returns `list[DownloadResult]` |
| `ReportService` | Saves `report.csv`, Excel, or PDF exports from results |
| `OrcidValidationService` | Validates ORCID format (checksum) and registry existence |
| `create_application_services` | Factory that wires up all four services in one call |

### Example: search and preview results

```python
import threading
from pathlib import Path
import epmcminer

search, download, report, orcid = epmcminer.create_application_services()

params = epmcminer.SearchParams(
    query="depression AND therapy",
    date_from="2020-01-01",
    date_to="2024-12-31",
    publication_types=["Review", "Meta analysis"],
    licenses=["CC-BY"],
    count=10,
    output_folder=Path("/tmp/papers"),
)

result = search.preview(params)
print(f"{result.total_found} total results, ~{result.estimated_downloadable} with PDFs")
for paper in result.papers:
    print(paper.title, "—", paper.authors)
```

### Example: download PDFs

```python
results = download.download(
    params,
    progress_callback=lambda r: print(r.status, r.paper.title),
    cancel_event=threading.Event(),
)

downloaded = [r for r in results if r.status == epmcminer.DownloadResult.STATUS_DOWNLOADED]
print(f"Downloaded {len(downloaded)} PDFs to {params.output_folder}/pdfs/")
```

### Example: save a report

```python
report.save_csv(results, params, params.output_folder)
# report.csv is now in /tmp/papers/report.csv
```

---

<!-- TOC --><a name="development"></a>
## Development

### Setup

```bash
# activate local virtual environment (if set up previously)
source .venv/bin/activate

# install package with all dev dependencies from the root folder
pip install -e ".[dev]"
```

### Linting and formatting

```bash
# check for lint errors (ruff rules: E, F, W, I, B, C4, UP, SIM)
ruff check src/ tests/

# auto-fix lint errors where possible
ruff check --fix src/ tests/

# check formatting
ruff format --check src/ tests/

# apply formatting
ruff format src/ tests/
```

### Type checking

```bash
# run mypy across the full source tree
mypy src/epmcminer
```

### Testing

```bash
# run docstring examples as tests (pure utility functions only)
pytest --doctest-modules src/epmcminer/utils/

# run the full test suite (unit + integration, replays cassettes, no network)
pytest tests/

# run only unit tests (fast, no network, fully mocked)
pytest -m "not integration"

# run only integration tests (replays from cassettes, no network)
pytest -m integration

# run with coverage report
pytest --cov=src/epmcminer --cov-report=term-missing

# re-record integration cassettes against the live API
# (required when Europe PMC changes its response format)
pytest -m integration --record-mode=all --override-ini="addopts="
```

#### How integration tests work

The test suite uses two complementary layers:

**Unit tests** (`tests/test_api/`, `tests/test_services/`, `tests/test_gui/`) mock all HTTP
calls with the `responses` library. They run in under 10 seconds and never touch the network.

**Integration tests** (`tests/integration/`) verify that the real Europe PMC API contract
still holds. To avoid non-deterministic CI failures caused by rate limits and network
timeouts, HTTP conversations are recorded once as *VCR cassettes* (YAML files stored in
`tests/integration/cassettes/`) using [`pytest-recording`](https://github.com/kiwicom/pytest-recording).
CI replays these cassettes deterministically — no live API calls are made. The `--block-network`
flag ensures any accidental live call fails immediately rather than silently timing out.

---

<!-- TOC --><a name="architecture"></a>
## Architecture

A full description of the three-layer architecture (GUI → Service → API client), the data
models, the threading model, Qt signal/slot wiring, and the test strategy is in
[`docs/architecture.md`](docs/architecture.md).

---

<!-- TOC --><a name="specifications"></a>
## Specifications

Full feature specifications (F1–F10) and user stories (US1–US4) are in [`docs/specifications.md`](docs/specifications.md).
