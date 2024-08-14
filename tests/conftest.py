"""Pytest configuration."""

from pathlib import Path

import pytest
from invoke.context import MockContext

from .configuration import TEST_TMP_CACHE, clear_test_cache


@pytest.fixture
def fix_test_cache() -> Path:
    """Fixture to clear and return the test cache directory for use.

    Returns:
        Path: Path to the test cache directory

    """
    clear_test_cache()
    return TEST_TMP_CACHE


@pytest.fixture
def ctx() -> MockContext:
    """Mock Invoke Context.

    Adapted from:
    https://github.com/pyinvoke/invocations/blob/8a277c304dd7aaad03888ee42d811c468e7fb37d/tests/conftest.py#L5-L11

    Additional documentation: https://docs.pyinvoke.org/en/stable/concepts/testing.html

    Returns:
        MockContext: simulated Invoke context

    """
    MockContext.run_command = property(lambda self: self.run.call_args[0][0])  # type: ignore[attr-defined]
    return MockContext(run=True)
