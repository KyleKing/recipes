"""Global variables for testing."""

from pathlib import Path

TEST_DIR: Path = Path(__file__).parent
"""Path to the `test` directory that contains this file and all other tests."""

TEST_DATA_DIR: Path = TEST_DIR / 'data'
"""Path to subdirectory with test data within the Test Directory."""
