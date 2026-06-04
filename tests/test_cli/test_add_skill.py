# Copyright 2025 Entalpic
"""Tests for ``siesta project add-skill <skill>``.

These tests intentionally avoid running ``uv init`` — ``add-skill`` only needs a
``pyproject.toml`` to detect the project name, so we write a minimal one
directly. That keeps the suite fast.
"""

from pathlib import Path

import pytest

from siesta.cli import app


def _seed_minimal_project(path: Path, name: str = "demo-project") -> None:
    """Create a minimal pyproject.toml so get_project_name() finds a name."""
    (path / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "0.0.0"\n'
    )


def test_add_skill_creates_agentic_surface(tmp_path_chdir, capture_output):
    """`add-skill agentic-exploration` materializes the workflow at CWD."""
    _seed_minimal_project(tmp_path_chdir, name="demo-project")

    with capture_output():
        try:
            app(["project", "add-skill", "agentic-exploration"])
        except SystemExit as e:
            assert e.code == 0

    assert Path(tmp_path_chdir, "Human.md").exists()
    assert Path(tmp_path_chdir, "AGENT.md").exists()
    skill_dir = Path(tmp_path_chdir, ".claude", "skills", "agentic-exploration")
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "templates").is_dir()

    # Lifecycle files must not be created at install time.
    for lifecycle in (
        "research_plan.md",
        "plan.md",
        "TODO.md",
        "notes.md",
        "handoff.md",
    ):
        assert not Path(tmp_path_chdir, lifecycle).exists()


def test_add_skill_substitutes_project_name(tmp_path_chdir, capture_output):
    """Project name from pyproject.toml is substituted into AGENT.md."""
    _seed_minimal_project(tmp_path_chdir, name="weather-vision")
    # Create src/ so layout is inferred as "lib" and the src/ bullet is present.
    (tmp_path_chdir / "src").mkdir()

    with capture_output():
        try:
            app(["project", "add-skill", "agentic-exploration"])
        except SystemExit as e:
            assert e.code == 0

    agent_text = Path(tmp_path_chdir, "AGENT.md").read_text()
    assert "# weather-vision" in agent_text
    # Hyphen→underscore for the package name slot.
    assert "src/weather_vision/" in agent_text


def test_add_skill_drops_test_line_when_no_tests_dir(tmp_path_chdir, capture_output):
    """When tests/ is absent, the test-command bullet line is dropped from AGENT.md."""
    _seed_minimal_project(tmp_path_chdir)
    # No tests/ directory in this project.

    with capture_output():
        try:
            app(["project", "add-skill", "agentic-exploration"])
        except SystemExit as e:
            assert e.code == 0

    agent_text = Path(tmp_path_chdir, "AGENT.md").read_text()
    assert "Test: `uv run pytest`" not in agent_text


def test_add_skill_keeps_test_line_when_tests_dir_present(
    tmp_path_chdir, capture_output
):
    """When tests/ exists, the test-command bullet is filled with uv run pytest."""
    _seed_minimal_project(tmp_path_chdir)
    (tmp_path_chdir / "tests").mkdir()

    with capture_output():
        try:
            app(["project", "add-skill", "agentic-exploration"])
        except SystemExit as e:
            assert e.code == 0

    agent_text = Path(tmp_path_chdir, "AGENT.md").read_text()
    assert "Test: `uv run pytest`" in agent_text


def test_add_skill_drops_docs_line_when_no_docs_dir(tmp_path_chdir, capture_output):
    """When docs/ is absent, the docs-command bullet line is dropped from AGENT.md."""
    _seed_minimal_project(tmp_path_chdir)
    # No docs/ directory.

    with capture_output():
        try:
            app(["project", "add-skill", "agentic-exploration"])
        except SystemExit as e:
            assert e.code == 0

    agent_text = Path(tmp_path_chdir, "AGENT.md").read_text()
    assert "Docs:" not in agent_text


def test_add_skill_unknown_skill_aborts(tmp_path_chdir, capture_output):
    """Unknown skill names abort with a clear error message."""
    _seed_minimal_project(tmp_path_chdir)

    with capture_output() as output, pytest.raises(SystemExit) as exc_info:
        app(["project", "add-skill", "definitely-not-a-skill"])

    assert exc_info.value.code == 1
    output_text = output.getvalue()
    assert "Unknown skill" in output_text
    assert "agentic-exploration" in output_text
    # And no files were created.
    assert not Path(tmp_path_chdir, "Human.md").exists()
    assert not Path(tmp_path_chdir, "AGENT.md").exists()


def test_add_skill_backs_up_existing_files_without_overwrite(
    tmp_path_chdir, capture_output
):
    """Existing AGENT.md is backed up to AGENT.md.bak when --overwrite is not passed."""
    _seed_minimal_project(tmp_path_chdir)
    existing = tmp_path_chdir / "AGENT.md"
    existing.write_text("pre-existing AGENT contents\n")

    with capture_output():
        try:
            app(["project", "add-skill", "agentic-exploration"])
        except SystemExit as e:
            assert e.code == 0

    # New AGENT.md is the rendered template.
    assert "pre-existing AGENT contents" not in existing.read_text()
    # And the old content is preserved in a .bak file.
    backup = tmp_path_chdir / "AGENT.md.bak"
    assert backup.exists()
    assert backup.read_text() == "pre-existing AGENT contents\n"


def test_add_skill_overwrite_skips_backup(tmp_path_chdir, capture_output):
    """--overwrite replaces existing files in place without creating a backup."""
    _seed_minimal_project(tmp_path_chdir)
    (tmp_path_chdir / "AGENT.md").write_text("pre-existing\n")

    with capture_output():
        try:
            app(["project", "add-skill", "agentic-exploration", "--overwrite"])
        except SystemExit as e:
            assert e.code == 0

    # No backup created.
    assert not (tmp_path_chdir / "AGENT.md.bak").exists()
