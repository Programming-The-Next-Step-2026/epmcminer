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
