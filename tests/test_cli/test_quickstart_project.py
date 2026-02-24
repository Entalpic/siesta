# Copyright 2025 Entalpic
from pathlib import Path

from siesta.cli import app


def test_quickstart_project(tmp_path_chdir, capture_output):
    """Test project quickstart command creates expected project structure."""

    with capture_output() as output:
        app(["project", "quickstart"])

    assert "Failed to build the docs" not in output.getvalue()

    project_name = tmp_path_chdir.name

    # Check project structure
    assert Path(tmp_path_chdir, "src").exists()
    assert Path(tmp_path_chdir, "docs").exists()
    assert Path(tmp_path_chdir, ".pre-commit-config.yaml").exists()
    assert Path(tmp_path_chdir, ".readthedocs.yaml").exists()
    assert Path(tmp_path_chdir, "uv.lock").exists()
    assert Path(tmp_path_chdir, "tests").exists()
    assert Path(tmp_path_chdir, ".github").exists()
    assert Path(tmp_path_chdir, ".github", "workflows", "test.yml").exists()
    assert Path(tmp_path_chdir, "src", project_name).exists()
    assert Path(tmp_path_chdir, "src", project_name, "__init__.py").exists()


def test_quickstart_project_as_app(tmp_path_chdir, capture_output):
    """Test project quickstart --as-app creates app structure instead of library."""

    with capture_output() as output:
        app(["project", "quickstart", "--as-app"])

    assert "Failed to build the docs" not in output.getvalue()
    # Should not have src directory for app
    assert not Path(tmp_path_chdir, "src").exists()
    # But should still have docs
    assert Path(tmp_path_chdir, "docs").exists()


def test_quickstart_project_as_pkg(tmp_path_chdir, capture_output):
    """Test project quickstart --as-pkg creates package structure in root directory."""

    with capture_output() as output:
        app(["project", "quickstart", "--as-pkg"])

    assert "Failed to build the docs" not in output.getvalue()
    assert (tmp_path_chdir / "src").exists()
    assert (tmp_path_chdir / "src" / tmp_path_chdir.name).exists()


def test_quickstart_respects_no_tests(tmp_path_chdir, capture_output):
    """Test that user flags take precedence (--no-tests)."""

    with capture_output() as output:
        # User specifies --no-tests, defaults should not override it
        app(["project", "quickstart", "--no-tests"])

    output_text = output.getvalue()
    assert "Failed to build the docs" not in output_text

    # Check project structure - docs should exist (default)
    assert Path(tmp_path_chdir, "docs").exists()
    assert Path(tmp_path_chdir, "uv.lock").exists()

    # Check tests directory does NOT exist (user specified --no-tests)
    assert not Path(tmp_path_chdir, "tests").exists()

    # GitHub Actions should STILL be created (actions is independent of tests)
    assert Path(tmp_path_chdir, ".github").exists()
    assert Path(tmp_path_chdir, ".github", "workflows", "test.yml").exists()

    # User should be warned about having CI without tests
    assert "GitHub Actions CI without tests" in output_text


def test_quickstart_respects_no_actions(tmp_path_chdir, capture_output):
    """Test that user flags take precedence (--no-actions)."""

    with capture_output() as output:
        # User specifies --no-actions, defaults should not override it
        app(["project", "quickstart", "--no-actions"])

    assert "Failed to build the docs" not in output.getvalue()

    # Check project structure - tests should exist (default)
    assert Path(tmp_path_chdir, "tests").exists()
    assert Path(tmp_path_chdir, "docs").exists()

    # Check GitHub Actions does NOT exist (user specified --no-actions)
    assert not Path(tmp_path_chdir, ".github").exists()


def test_quickstart_respects_no_tests_and_no_actions(tmp_path_chdir, capture_output):
    """Test that user flags take precedence (both --no-tests and --no-actions)."""

    with capture_output() as output:
        # User specifies both --no-tests and --no-actions
        app(
            [
                "project",
                "quickstart",
                "--no-tests",
                "--no-actions",
            ]
        )

    assert "Failed to build the docs" not in output.getvalue()

    # Check project structure - docs should exist (default)
    assert Path(tmp_path_chdir, "docs").exists()
    assert Path(tmp_path_chdir, "uv.lock").exists()

    # Check tests directory does NOT exist (user specified --no-tests)
    assert not Path(tmp_path_chdir, "tests").exists()

    # Check GitHub Actions does NOT exist (user specified --no-actions)
    assert not Path(tmp_path_chdir, ".github").exists()
