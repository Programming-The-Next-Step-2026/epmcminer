# epmcminer — Architecture Overview

epmcminer is a PyQt6 desktop application that lets researchers search the **Europe PMC REST API** for open-access academic papers and bulk-download their PDFs. The wizard flow is: **Search → Preview → Download → Summary**.

---

## Three-layer separation

```
GUI  ──►  Service  ──►  API Client  ──►  Europe PMC / ORCID
  ◄──        ◄──              ◄──
```

- **GUI** (`gui/`) emits Qt signals and reads typed dataclasses. It never touches `requests`, never constructs a query string, never reads raw dicts.
- **Services** (`services/`) own all business logic: query building, parallelism, skip logic, report generation. They never import from `gui/`.
- **API clients** (`api/client.py`, `api/orcid_client.py`) are thin wrappers — HTTP calls only, no business logic.

Every service receives its dependencies through `__init__` (dependency injection). There are no module-level singletons. `services/__init__.py::create_application_services()` is the single wiring point — it creates one `EuropePMCClient`, passes it to both `SearchService` and `DownloadService`, then returns the four services as a tuple for `MainWindow` to inject into each screen.

---

## Data models

All inter-layer data transfer uses typed dataclasses — raw dicts never cross a layer boundary.

| Class | Location | Purpose |
|---|---|---|
| `Paper` | `api/paper.py` | Single result: pmid, doi, title, authors, journal, year, abstract, pdf\_url |
| `SearchParams` | `api/search_params.py` | All user inputs: query, dates, pub types, licenses, ORCIDs, count, output\_folder. Validates itself in `__post_init__`: count > 0, dates are valid ISO-8601, date\_from ≤ date\_to |
| `SearchResult` | `api/search_result.py` | papers list, total\_found, estimated\_downloadable |
| `DownloadResult` | `services/download_result.py` | One per attempted paper: paper, status (Literal), reason, file\_path, active\_threads |

`DownloadResult` lives in `services/` not `api/` — it is the output of business logic (skip decisions, write operations), not an HTTP response model. The `STATUS_*` ClassVars are typed `ClassVar[Literal["downloaded"]]` etc. so mypy verifies every status string at call sites.

---

## API layer

### `EuropePMCClient`

Uses a persistent `requests.Session` for connection reuse. Two public methods:

**`search(query, page_size, sort, cursor_mark)`** — hits the Europe PMC search endpoint with `format=json`, `resultType=core`. The `core` result type embeds `fullTextUrlList` inline, avoiding a second API call to resolve PDF URLs. Every query is wrapped with `(HAS_FT:Y OR HAS_FREE_FULLTEXT:Y)` to restrict to open-access papers.

**`download_pdf(url, cancel_event)`** — fetches a direct PDF URL. Both methods share the same retry policy: up to 3 attempts, exponential backoff (1 s, 2 s), honouring `Retry-After` on HTTP 429. Backoff sleeps use `Event.wait(timeout=delay)` rather than `time.sleep()` so they wake immediately when a cancellation is requested. On HTTP 200 the response body is validated against the `%PDF` magic bytes — if the server returned an HTML challenge page, `InvalidPdfContentError` is raised and the paper is skipped rather than written as garbage.

### `OrcidClient`

Single method `check_exists(orcid)` — GET to `pub.orcid.org/v3.0/{orcid}`. Returns `True` on HTTP 200, `False` otherwise. Raises `ConnectionError` on network failures (including timeouts).

---

## Service layer

### `SearchService`

**`build_query(params)`** — pure string construction. Multi-word queries without explicit boolean operators are auto-joined with AND. Handles the Europe PMC pub-type mapping quirk (stored lowercase; two types have non-obvious spellings). Prepends a catch-all clause so regular journal articles are not excluded by explicit pub-type filters. The free-full-text filter is not added here — it is the client's invariant applied on every request.

**`preview(params)`** — fetches one page (10 results), maps raw dicts to `Paper` via `paper_from_raw()`, counts papers with a `pdf_url`, returns a `SearchResult`.

`paper_from_raw()` is a module-level helper (not a method). It handles the pmid/id duality: MED (PubMed) records carry a `pmid` field; non-MED records (preprints etc.) only carry the generic `id` field.

### `DownloadService`

**`download(params, progress_callback, cancel_event)`** — two-phase loop to minimise overshoot:

- **Batch mode** (remaining ≥ 10): fetch a full page, download all papers in parallel using `ThreadPoolExecutor(max_workers=2)`. `progress_callback` fires as each individual paper completes, not at page boundaries.
- **Single-paper mode** (remaining < 10): fetch and download one at a time so the loop can stop exactly at the target count.

Pagination uses Europe PMC's cursor system: each response includes a `nextCursorMark`. The loop advances until the cursor stops changing (end of results) or the target count is reached.

**Skip logic in `_download_one`**: a paper is skipped (not failed) when there is no `pdf_url`, when the file already exists on disk, or when the server returns a non-PDF body. Failures are reserved for unrecoverable HTTP errors and write errors.

**`active_threads` counter**: a shared `int` inside `_download_page`, protected by a `threading.Lock`. The counter is captured before decrement — so each `DownloadResult` reports the thread count *including* the finishing thread, matching the intuitive peak value.

**Why `MAX_WORKERS=2`**: Europe PMC rate-limits at higher concurrency. Two workers sustain throughput without triggering HTTP 429s. The retry/backoff logic handles the cases where 429s occur anyway.

### `ReportService`

Generates three export formats from the same `list[DownloadResult]`:

- **CSV** via pandas `to_csv`
- **Excel** via pandas + openpyxl `to_excel`
- **PDF** via reportlab `SimpleDocTemplate` — mirrors the Summary screen's dark colour palette with a three-column stat card (downloaded / skipped / total found), a search-parameters card, and per-paper sections for downloaded and skipped papers.

### `OrcidValidationService`

Two-stage validation: `validate_format()` checks the ORCID pattern and ISO 7064 MOD 11-2 checksum locally (no network). `check_exists()` delegates to `OrcidClient` and must be called from a background thread.

---

## GUI layer

### `MainWindow` (`app.py`)

Owns a `QStackedWidget` holding the four screens and a step-indicator bar. Screens communicate back to `MainWindow` exclusively via Qt signals — a screen never navigates itself and never imports another screen.

`create_application_services()` is called once in `MainWindow.__init__` and the resulting service instances are injected into each screen constructor.

### Threading model

Every blocking operation (API calls, file I/O) runs in a `QThread` worker subclass. The pattern used throughout:

1. Instantiate a worker dataclass with the data it needs.
2. Connect its signals (`result_ready`, `error_occurred`, `progress`) to GUI slots.
3. Call `worker.start()`.
4. Slots update the UI on the main thread when signals fire — Qt's signal/slot mechanism guarantees thread-safe delivery into the event loop.

**Download cancellation** (screen 3): `DownloadWorker` holds a `threading.Event`. The cancel button sets it; the download loop checks it between pages; `Event.wait()` in the HTTP client's backoff sleep wakes immediately when set; in-flight HTTP requests complete naturally without retry.

**Preview cancellation** (screen 2): `PreviewWorker` carries its own `cancel_event`. When a new search fires while a preview is still loading, the old worker's event is set and its result/error signals are silently discarded — the main thread starts the new worker immediately without blocking on `wait()`.

### Reusable widgets

| Widget | Description |
|---|---|
| `TagInput` | Free-text or dropdown tag entry. Uses a custom `QLayout` subclass (`FlowLayout`) that wraps tags onto new lines. ORCID fields fire a background worker to validate against the public registry on confirm. |
| `ProgressWidget` | Dual-mode: loading (indeterminate bar + animated pulsing dots) and progress (determinate bar, percentage, count, live ETA, active-thread dot indicators). |
| `DatePicker` | Custom calendar popup replacing the default QDateEdit widget. |
| `Toast` | Slide-in success/failure notification using `QGraphicsOpacityEffect` for the fade animation. |

---

## Testing

**618 tests** across unit and integration suites.

- **Unit tests** mock all HTTP with the `responses` library or `pytest-mock`. GUI tests run headless with a `QApplication` fixture.
- **Integration tests** use `pytest-recording` (VCR cassettes). Real HTTP responses are captured once and replayed deterministically. `--block-network` is set as the default pytest `addopts` so any un-mocked request fails loudly. To re-record: `pytest tests/integration/ --record-mode=all --override-ini="addopts="`.
- **Coverage**: 96% overall; services and API layer at 100%.

---

## Tooling

| Tool | Configuration |
|---|---|
| **ruff** | Rules: E, F, W, I, B (bugbear), C4 (comprehensions), UP (pyupgrade), SIM (simplify). Ignores B008, SIM108. |
| **mypy** | `disallow_untyped_defs`, `disallow_any_generics`, `warn_return_any`, `warn_unused_ignores`. 0 errors. |
| **pytest** | `--block-network` default; VCR cassettes for integration tests. |
