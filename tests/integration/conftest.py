"""Shared fixtures for the integration test suite."""

from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def vcr_cassette_dir(request: pytest.FixtureRequest) -> str:
    """Store all VCR cassettes in tests/integration/cassettes/.

    pytest-recording uses this fixture to resolve the cassette directory for
    every test in the module. Cassettes are named after the test class and
    function: ``{ClassName}.{test_function}.yaml``.
    """
    return str(Path(__file__).parent / "cassettes")
