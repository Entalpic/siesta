# Copyright 2025 Entalpic
import os
from pathlib import Path
from subprocess import run

import pytest

from siesta.cli import app


@pytest.fixture
def existing_uv_project(tmp_path):
    """Create a temporary directory with an existing uv project."""
    current_dir = Path.cwd()
    test_path = tmp_path / "existing_project"
    test_path.mkdir(parents=True, exist_ok=True)
    os.chdir(test_path)

    # Initialize a basic uv project and create uv.lock
    run(["uv", "init", "--lib", "--name=existing_project"], check=True)
    # Run uv sync to create the uv.lock file
    run(["uv", "sync"], check=True)

    yield test_path
    os.chdir(current_dir)


def test_setup_tests_creates_tests_directory(existing_uv_project, capture_output):
    """Test that setup-tests creates the tests directory with example test."""
    with capture_output() as output:
        app(["project", "setup-tests"])

    output_text = output.getvalue()
    assert "Tests infra written" in output_text
    assert "Test actions config written" in output_text
    assert "Testing infrastructure set up successfully" in output_text

    # Check tests directory exists
    assert (existing_uv_project / "tests").exists()
    assert (existing_uv_project / "tests" / "test_import.py").exists()

    # Check test file content
    test_content = (existing_uv_project / "tests" / "test_import.py").read_text()
    assert "import existing_project" in test_content
    assert "def test_import" in test_content


def test_setup_tests_creates_github_actions(existing_uv_project, capture_output):
    """Test that setup-tests creates GitHub Actions workflow."""
    with capture_output():
        app(["project", "setup-tests"])

    # Check GitHub Actions directory exists
    assert (existing_uv_project / ".github").exists()
    assert (existing_uv_project / ".github" / "workflows").exists()
    assert (existing_uv_project / ".github" / "workflows" / "test.yml").exists()


def test_setup_tests_without_actions(existing_uv_project, capture_output):
    """Test that setup-tests can skip GitHub Actions setup."""
    with capture_output() as output:
        # Use --deps to install deps but --no-actions to skip actions
        # Pass project name and -i (interactive) to test explicit flag handling
        app(
            [
                "project",
                "setup-tests",
                "--project-name=existing_project",
                "--deps",
                "--no-actions",
                "-i",
            ]
        )

    output_text = output.getvalue()
    assert "Tests infra written" in output_text

    # Check tests directory exists
    assert (existing_uv_project / "tests").exists()

    # Check GitHub Actions was NOT created
    assert not (existing_uv_project / ".github").exists()


def test_setup_tests_skips_existing_tests_directory(
    existing_uv_project, capture_output
):
    """Test that setup-tests warns and skips if tests directory already exists."""
    # Create tests directory first
    (existing_uv_project / "tests").mkdir()
    (existing_uv_project / "tests" / "existing_test.py").write_text("# existing test")

    with capture_output() as output:
        app(["project", "setup-tests"])

    output_text = output.getvalue()
    assert "Tests directory already exists" in output_text

    # Check existing test file is preserved
    assert (existing_uv_project / "tests" / "existing_test.py").exists()
    # Check no new test file was created
    assert not (existing_uv_project / "tests" / "test_import.py").exists()


def test_setup_tests_respects_no_actions(existing_uv_project, capture_output):
    """Test that user flags take precedence (--no-actions)."""
    with capture_output() as output:
        # User specifies --no-actions, defaults should not override it
        app(["project", "setup-tests", "--no-actions"])

    output_text = output.getvalue()
    assert "Tests infra written" in output_text
    # deps should default to True
    assert "Test dependencies installed" in output_text

    # Check tests directory exists (deps=True by default)
    assert (existing_uv_project / "tests").exists()

    # Check GitHub Actions was NOT created (user specified --no-actions)
    assert not (existing_uv_project / ".github").exists()


def test_setup_tests_respects_no_deps(existing_uv_project, capture_output):
    """Test that user flags take precedence (--no-deps)."""
    with capture_output() as output:
        # User specifies --no-deps, defaults should not override it
        app(["project", "setup-tests", "--no-deps"])

    output_text = output.getvalue()
    assert "Tests infra written" in output_text
    # deps should be False (user specified --no-deps)
    assert "Test dependencies installed" not in output_text
    # actions should default to True
    assert "Test actions config written" in output_text

    # Check tests directory exists
    assert (existing_uv_project / "tests").exists()

    # Check GitHub Actions WAS created (actions=True by default)
    assert (existing_uv_project / ".github" / "workflows" / "test.yml").exists()


def test_setup_tests_interactive_flag(existing_uv_project, capture_output):
    """Test that -i/--interactive enables prompts instead of using defaults."""
    with capture_output() as output:
        # Use -i with explicit flags to avoid prompts in test
        # -i should override default behavior (which would auto-accept)
        app(
            [
                "project",
                "setup-tests",
                "-i",  # interactive mode
                "--project-name=existing_project",  # explicitly set to avoid prompt
                "--deps",  # explicitly set to avoid prompt
                "--no-actions",  # explicitly set to avoid prompt
            ]
        )

    output_text = output.getvalue()
    assert "Tests infra written" in output_text
    assert "Test dependencies installed" in output_text

    # Check tests directory exists
    assert (existing_uv_project / "tests").exists()

    # Check GitHub Actions was NOT created (we specified --no-actions)
    assert not (existing_uv_project / ".github").exists()
