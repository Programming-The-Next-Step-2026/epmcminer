# CLAUDE.md

Read this file completely before writing any code. Every implementation decision
must be consistent with the rules defined here.

---

## Project overview

epmcminer is a PyQt6 desktop application that allows researchers to search for
and download open-access academic papers from the Europe PMC API. The application
follows a four-screen wizard flow: Search → Preview → Download → Summary.

---

## Package structure

```
src/epmcminer/
├── __init__.py
├── main.py                     # Entry point — creates QApplication and MainWindow
├── api/
│   ├── __init__.py
│   ├── client.py               # Europe PMC HTTP client (raw API calls only)
│   └── MODEL FILES             # Dataclasses, one file per class: Paper, SearchParams, SearchResult, DownloadResult
├── services/
│   ├── __init__.py
│   ├── search_service.py       # Builds queries, calls client, returns SearchResult
│   ├── download_service.py     # Parallel PDF downloads, skip logic, folder structure
│   └── report_service.py       # Generates report.csv, Excel export, PDF export
├── gui/
│   ├── __init__.py
│   ├── app.py                  # MainWindow: QMainWindow, screen navigation, step indicator
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── screen_search.py    # Screen 1: search query and filter inputs
│   │   ├── screen_preview.py   # Screen 2: results preview + download settings
│   │   ├── screen_download.py  # Screen 3: progress bar + live log
│   │   └── screen_summary.py   # Screen 4: stats + skipped papers + export
│   └── widgets/
│       ├── __init__.py
│       ├── tag_input.py        # Reusable tag input widget (used on all filter fields)
│       └── progress_widget.py  # Reusable animated progress/loading widget
└── utils/
    ├── __init__.py
    ├── logger.py               # Timestamped file logger setup
    └── file_utils.py           # Path sanitisation, filename construction

tests/
├── __init__.py
├── test_api/
│   ├── __init__.py
│   └── test_client.py
├── test_services/
│   ├── __init__.py
│   ├── test_search_service.py
│   ├── test_download_service.py
│   └── test_report_service.py
└── test_utils/
    ├── __init__.py
    └── test_file_utils.py
```

Do not create files outside this structure without a clear reason documented
in a comment and do not alter any existing files besides those mentioned in the structure.

---

## Architecture rules

### Service layer pattern

The service layer is the ONLY place where business logic lives.

1. GUI screens call services. Services never import anything from `gui/`.
2. Services call the API client. GUI screens never import anything from `api/`.
3. The API client makes HTTP requests only — no business logic.
4. Data flows one way: `GUI → Service → API client → Service → GUI`.

**BAD — business logic in the GUI:**
```python
# screen_preview.py
import requests
response = requests.get("https://www.ebi.ac.uk/europepmc/...")
papers = [p for p in response.json() if p.get("hasPDF")]
```

**GOOD — GUI delegates to a service:**
```python
# screen_preview.py
result = self.search_service.preview(params)
```

### Dependency injection

Pass all service dependencies via `__init__` parameters. Never instantiate
services inside GUI classes or use module-level singletons.

**BAD:**
```python
class ScreenPreview(QWidget):
    def __init__(self):
        self.service = SearchService()  # hidden dependency
```

**GOOD:**
```python
class ScreenPreview(QWidget):
    def __init__(self, search_service: SearchService, parent=None):
        self.search_service = search_service
```

### Data models

Use dataclasses for all data transfer objects. Never pass raw dicts between
layers. All fields must be typed. Ensure sensible data validation is used.

### Long-running operations

All API calls and file I/O must run in a `QThread` worker, never in the main
thread. Use Qt signals to communicate results back to the GUI.

### Error handling

Services raise specific, descriptive exceptions. GUI screens catch them and
display user-friendly error messages. Never swallow exceptions silently with
a bare `except:` or `except Exception: pass`. Always log exceptions with the logger.

---

## Coding conventions

- **Python version:** 3.11+
- **Style guide:** Google Python Style Guide
  (https://google.github.io/styleguide/pyguide.html)
- **Linter:** ruff
- **Type hints:** mandatory on every function (parameters and return type)
- **Line length:** 100 characters maximum
- **Constants:** define named constants at the top of the module — no magic
  numbers or hardcoded strings inline
- **Logging:** always use the logger from `utils/logger.py` — never `print()
- **Documentation:** use docstrings on all public classes and functions, following the
  Google style (see example below). Use internal comments for complex logic, but do not overcomment obvious code.
- **Test Driven Development:** write tests before implementing functionality, and ensure all new code is covered by tests.
- **Code Reviews:** before committing and pushing, always review your code for adherence to these conventions and for overall code quality. Consider readability, maintainability, and consistency with the existing codebase.
- **Comitting:** make small, focused commits with clear messages describing the change. Avoid large, monolithic commits that are difficult to review. Only commit code that is complete and functional — do not commit half-finished work or code with known bugs or code that has not been reviewed. NEVER MERGE OR CREATE PULLREQUESTS!

---

## Docstring format

Use Google-style docstrings on every public class and function.

```python
def search(self, params: SearchParams) -> SearchResult:
    """Search Europe PMC for papers matching the given parameters.

    Args:
        params: A SearchParams dataclass containing the query string,
            active filters, sort order, and requested result count.

    Returns:
        A SearchResult containing the list of matching Paper objects
        and the total result count from the API.

    Raises:
        APIError: If the Europe PMC API returns a non-200 response.
        ConnectionError: If the HTTP request cannot be completed.
    """
```

---

## Testing conventions

- Framework: pytest
- Every public service method must have at least one unit test.
- Cover edge cases and as many sensible input combinations as possible.
- Mock all HTTP calls — never make real API calls in tests. Use
  `pytest-mock` or the `responses` library.
- Test file mirrors source file:
  `tests/test_services/test_search_service.py` tests
  `src/epmcminer/services/search_service.py`.
- Target: >80% coverage on `services/` and `api/`.
- Use `pytest.fixture` for shared setup. Do not repeat setup code.

---

## GUI conventions

- One `QWidget` subclass per screen, in its own file.
- Screens communicate with `MainWindow` exclusively via Qt signals.
  A screen never navigates itself or imports another screen.
- The step indicator and screen transitions are handled entirely by
  `MainWindow` in `app.py`.
- Reuse `TagInput` and `ProgressWidget` from `gui/widgets/` or other sharable components wherever
  applicable — do not reimplement them inline.

---

## What NOT to do

- Do not put API calls or file I/O in any file under `gui/`.
- Do not navigate between screens from within a screen — emit a signal instead.
- Do not create global or module-level mutable state.
- Do not use `print()` — use the logger.
- Do not hardcode the Europe PMC API base URL — define it as a constant
  in `api/client.py`.
- Do not commit secrets, tokens, or credentials.
- Do not modify `CLAUDE.md` — it is a project governance document.