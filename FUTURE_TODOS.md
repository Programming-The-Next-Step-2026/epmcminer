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
