# Copyright 2025 Entalpic
import os
from pathlib import Path
from subprocess import run

import pytest

import siesta.cli.project_app as cli
from siesta.cli.main_app import app


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
        try:
            app(["project", "setup-tests"])
        except SystemExit as e:
            assert e.code == 0

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
        try:
            app(["project", "setup-tests"])
        except SystemExit as e:
            assert e.code == 0

    # Check GitHub Actions directory exists
    assert (existing_uv_project / ".github").exists()
    assert (existing_uv_project / ".github" / "workflows").exists()
    assert (existing_uv_project / ".github" / "workflows" / "test.yml").exists()


def test_setup_tests_without_actions(existing_uv_project, capture_output):
    """Test that setup-tests can skip GitHub Actions setup."""
    with capture_output() as output:
        # Use --deps to install deps but --no-actions to skip actions
        # Pass project name and -i (interactive) to test explicit flag handling
        try:
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
        except SystemExit as e:
            assert e.code == 0

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
        try:
            app(["project", "setup-tests"])
        except SystemExit as e:
            assert e.code == 0

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
        try:
            app(["project", "setup-tests", "--no-actions"])
        except SystemExit as e:
            assert e.code == 0

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
        try:
            app(["project", "setup-tests", "--no-deps"])
        except SystemExit as e:
            assert e.code == 0

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
        try:
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
        except SystemExit as e:
            assert e.code == 0

    output_text = output.getvalue()
    assert "Tests infra written" in output_text
    assert "Test dependencies installed" in output_text

    # Check tests directory exists
    assert (existing_uv_project / "tests").exists()

    # Check GitHub Actions was NOT created (we specified --no-actions)
    assert not (existing_uv_project / ".github").exists()


def test_setup_tests_collects_decisions_before_mutations(
    existing_uv_project, monkeypatch
):
    """Test setup-tests collects prompts before mutating project state."""
    monkeypatch.chdir(existing_uv_project)
    events: list[str] = []
    answers = iter([True, True])

    monkeypatch.setattr(
        "siesta.cli.project_app.logger.confirm",
        lambda _msg: events.append("confirm") or next(answers),
    )
    monkeypatch.setattr(
        cli,
        "run_command",
        lambda cmd, **_kwargs: events.append(f"run:{' '.join(cmd)}") or True,
    )
    monkeypatch.setattr(
        cli,
        "write_tests_infra",
        lambda *_args, **_kwargs: events.append("write_tests_infra"),
    )
    monkeypatch.setattr(
        cli,
        "write_test_actions_config",
        lambda *_args, **_kwargs: events.append("write_test_actions_config"),
    )

    try:
        app(["project", "setup-tests", "-i", "--project-name=existing_project"])
    except SystemExit as e:
        assert e.code == 0

    first_mutation = next(i for i, event in enumerate(events) if event != "confirm")
    confirm_indices = [i for i, event in enumerate(events) if event == "confirm"]
    assert confirm_indices
    assert max(confirm_indices) < first_mutation
    assert events[first_mutation].startswith("run:")
    assert "write_tests_infra" in events
    assert "write_test_actions_config" in events
