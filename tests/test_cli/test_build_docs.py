# Copyright 2025 Entalpic
import os
import shutil
from pathlib import Path

import pytest

from siesta.cli import app


def a_in_b_str_no_space(a, b):
    """Check if a is in b ignoring spaces.

    This is useful for comparing output messages from the CLI to those expected
    in the tests without relying on terminal width which can cause the test to
    fail by introducing extra spaces (for instance line breaks).
    """
    a = a.replace(" ", "").replace("\n", "").replace("\t", "")
    b = b.replace(" ", "").replace("\n", "").replace("\t", "")
    return a in b


@pytest.fixture
def module_test_path_no_docs(tmp_path_factory):
    """Create a shared test directory with quickstart project setup and docs."""
    tmp_path = tmp_path_factory.mktemp("shared-test-dir")
    current_dir = Path.cwd()
    try:
        os.chdir(tmp_path)  # Change to temp directory
        app(["project", "quickstart", "--overwrite"])
        shutil.rmtree(tmp_path / "docs")
    finally:
        os.chdir(current_dir)  # Always restore original directory
    return tmp_path


def test_build_docs_path_not_found(capture_output):
    """Test build_docs fails when path doesn't exist."""
    with pytest.raises(SystemExit) as exc_info:
        with capture_output() as output:
            app(["docs", "build", "--path", "nonexistent/path"])
        assert a_in_b_str_no_space("Path not found", output.getvalue())

    assert exc_info.value.code == 1


def test_build_docs_no_makefile(tmp_path, monkeypatch, capture_output):
    """Test build_docs fails when Makefile doesn't exist."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        with capture_output() as output:
            app(["docs", "build"])
        assert a_in_b_str_no_space("Makefile not found", output.getvalue())

    assert exc_info.value.code == 1


def test_build_docs_successful(module_test_path, monkeypatch, capture_output):
    """Test successful docs build."""
    monkeypatch.chdir(module_test_path)

    with capture_output() as output:
        app(["docs", "build"])

    # Verify success message
    assert a_in_b_str_no_space(
        "Local docs built in docs/build/html/index.html",
        output.getvalue(),
    )


def test_build_docs_with_uv(module_test_path, monkeypatch, capture_output):
    """Test docs build with uv when uv.lock exists."""
    monkeypatch.chdir(module_test_path)

    # Create mock uv.lock file
    Path("uv.lock").touch()

    with capture_output() as output:
        app(["docs", "build"])

    # Verify success message
    assert a_in_b_str_no_space(
        "Local docs built in docs/build/html/index.html",
        output.getvalue(),
    )

    # Cleanup
    Path("uv.lock").unlink()


def test_build_docs_command_failure(
    module_test_path_no_docs, monkeypatch, capture_output
):
    """Test build_docs handles command failures."""
    monkeypatch.chdir(module_test_path_no_docs)

    with pytest.raises(SystemExit) as exc_info:
        with capture_output() as output:
            app(["docs", "build"])
        assert a_in_b_str_no_space("Failed to build the docs", output.getvalue())

    assert exc_info.value.code == 1
