# Copyright 2025 Entalpic
import os
import sys
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from subprocess import run
from unittest.mock import patch

import pytest

from siesta.cli import app as app

os.environ["PYTHONBREAKPOINT"] = "ipdb.set_trace"


@pytest.fixture(autouse=True)
def mock_user_pat():
    """Mock get_user_pat to always return a fake PAT.

    This fixture is automatically used in all tests.
    """
    with patch(
        "siesta.utils.github.get_user_pat", return_value="fake-github-pat-for-testing"
    ):
        yield


@pytest.fixture
def capture_output():
    @contextmanager
    def c():
        """Context manager to capture stdout for testing.

        Example
        -------

        .. code-block:: python

            with capture_output() as output:
                app(["show-deps"])
            assert "numpy" in output.getvalue()

        Returns
        -------
        StringIO
            The captured stdout buffer.
        """
        stdout = StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = stdout
            yield stdout
        finally:
            sys.stdout = old_stdout

    return c


@pytest.fixture
def temp_project_with_git_and_remote(tmp_path):
    """Create a temporary project directory with a basic structure.

    Function-scoped to ensure a fresh directory for each test.
    """
    # Create a basic src structure
    src = tmp_path / "src" / "mypackage"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("# Test package")

    # Create a basic git repo to test URL detection
    run(["git", "init"], cwd=str(tmp_path))
    run(
        ["git", "remote", "add", "origin", "git@github.com:test/test.git"],
        cwd=str(tmp_path),
    )

    return tmp_path


@pytest.fixture(scope="module")
def module_test_path(tmp_path_factory):
    """Create a shared test directory with quickstart project setup."""
    tmp_path = tmp_path_factory.mktemp("shared-test-dir")
    current_dir = Path.cwd()
    try:
        os.chdir(tmp_path)  # Change to temp directory
        app(["project", "quickstart", "--local", "--overwrite"])
    finally:
        os.chdir(current_dir)  # Always restore original directory
    return tmp_path


@pytest.fixture
def tmp_path_chdir(tmp_path):
    """Change the current directory to the temporary path."""
    current_dir = Path.cwd()
    test_path = tmp_path / "test_siesta"
    test_path.mkdir(parents=True, exist_ok=True)
    os.chdir(test_path)
    yield test_path
    os.chdir(current_dir)
