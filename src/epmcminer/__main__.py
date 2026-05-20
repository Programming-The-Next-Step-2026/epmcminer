"""Allow running epmcminer as a package with ``python -m epmcminer``.

Not listed in CLAUDE.md's package structure, but required by the Python
stdlib convention for runnable packages and the acceptance criterion that
``python -m epmcminer`` launches the application.
"""

from epmcminer.main import main

main()
