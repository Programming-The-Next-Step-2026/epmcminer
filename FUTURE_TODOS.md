# Future TODOs

Issues identified during code review that were **not** fixed in-branch, with context for future resolution.

---

## Low — Docstring style: D413 blank line after last section

**Files:** `src/epmcminer/services/report_service.py` — `save_csv`, `export_excel`, `export_pdf`, `_build_dataframe`

**Detail:** `ruff --select ALL` flags D413 (missing blank line after the last docstring section). Not triggered by the project's configured rule set (`E, F, W, I`) and the CLAUDE.md example docstring itself does not include a trailing blank line, which is consistent with the Google Python Style Guide. No action required unless the ruff config is extended to include `D` rules.

---

## Low — Trailing commas: COM812

**Files:** `src/epmcminer/services/report_service.py` — `TableStyle([...])` list and `_build_dataframe` signature

**Detail:** `ruff --select ALL` flags COM812 (trailing comma missing). Not in the project's ruff config. Fixable automatically with `ruff --fix --select COM812` if COM812 is added to the lint config.

---

## Low — `datetime.now()` without timezone: DTZ005

**Files:** `src/epmcminer/utils/logger.py:30`

**Detail:** `ruff --select ALL` flags DTZ005 — `datetime.now()` returns naïve local time. For log file naming, local time is intentional (the user reads their local timestamp). Fix by passing `tz=datetime.timezone.utc` and formatting in UTC if cross-timezone consistency is ever needed, or suppress the rule with `# noqa: DTZ005` to make the intent explicit. No functional impact for the current single-user desktop use case.

---

## Low — D413 blank line after last section (utils)

**Files:** `src/epmcminer/utils/file_utils.py`, `src/epmcminer/utils/logger.py`

**Detail:** Same D413 rule as reported for `report_service.py`. Not in the project ruff config and not required by Google style. See the earlier entry for full context.

---

## Medium — Double free-text filter in search queries

**Files:** `src/epmcminer/services/search_service.py`, `src/epmcminer/api/client.py`

**Detail:** `FREE_FULL_TEXT_FILTER` is appended by both `SearchService.build_query()` and `EuropePMCClient.search()`. The final API query contains the clause twice: `(...AND (HAS_FT:Y OR HAS_FREE_FULLTEXT:Y)) AND (HAS_FT:Y OR HAS_FREE_FULLTEXT:Y)`. This doesn't break search results but wastes URL space and is confusing. To fix: decide which layer owns this rule (recommend removing it from `build_query()` since the client already handles it) and update `test_free_full_text_filter_always_present` accordingly.

---

## Medium — Module-level QStyleFactory creation in tag_input

**Files:** `src/epmcminer/gui/widgets/tag_input.py:106`

**Detail:** `_FUSION = QStyleFactory.create("Fusion")` runs at module import time. This is fragile if `tag_input` is ever imported before a `QApplication` is instantiated (e.g. in a non-GUI test or CLI context). Fix: use a lazy initializer — `_FUSION: QStyle | None = None` and a `_get_fusion_style()` helper that initializes on first call.

---

## Low — `SearchParams.output_folder` defaults to cwd

**Files:** `src/epmcminer/api/search_params.py:36`

**Detail:** `output_folder: Path = field(default_factory=Path)` creates `Path()` which resolves to the current working directory at runtime. If a caller omits this field, downloads silently land wherever the process was launched from. Fix: change to `output_folder: Path | None = None` with a `ValueError` raised in `__post_init__` if `None`, or require it as a positional argument with no default.

---

## Low — Cancellation latency in download page

**Files:** `src/epmcminer/services/download_service.py:140`

**Detail:** `_download_page()` submits all papers from one API page (up to 25) to a thread pool and waits for all futures before returning. `cancel_event` is only checked between pages, so cancellation can be delayed by up to 25 concurrent downloads. Fix: pass `cancel_event` into `_download_page`, check it before submitting each future, and use `executor.shutdown(cancel_futures=True)` on cancellation.

---

## Medium — Silent report.csv save failure in ScreenDownload

**Files:** `src/epmcminer/gui/screens/screen_download.py:406`

**Detail:** `_on_finished()` wraps `report_service.save_csv()` in a bare `except Exception` that only logs the error; no dialog is shown to the user. If saving the CSV fails (e.g. permissions issue, full disk), the user sees nothing and loses their report silently. Fix: display a `QMessageBox.warning()` inside the except block so the user is informed and can retry or choose a different output location.

---

## Low — OrcidValidationService: surface network errors in the UI

**Files:** `src/epmcminer/gui/screens/screen_search.py` — `_on_orcid_network_error`

**Detail:** When the ORCID registry check fails with a `ConnectionError`, the pill stays grey ("pending") forever — there is no tooltip, banner, or status label telling the user why. The fail-open behaviour is intentional and correct, but it is silent. Fix: add a subtle tooltip on the pending pill (e.g. "Could not verify — no network connection") or emit a one-line status message below the ORCID input so the user understands the grey state.

---

## Low — Dead production code: `ensure_output_structure`

**Files:** `src/epmcminer/utils/file_utils.py:51`

**Detail:** `ensure_output_structure(output_folder)` creates `pdfs/` and `logs/` subdirectories but is never called from any production code — `DownloadService` creates `pdfs/` itself inline. The function has tests that exercise it directly but those tests only confirm isolated behaviour, not actual usage. Cannot be deleted while the tests reference it. Fix: either wire it back into `DownloadService.__init__` / `download()` (and remove the duplicate `pdfs_dir.mkdir` inline), or remove it from both `file_utils.py` and `test_file_utils.py` after confirming the inline mkdir is sufficient.
