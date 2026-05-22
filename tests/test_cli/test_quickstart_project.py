# Copyright 2025 Entalpic
from pathlib import Path

import siesta.cli.project_app as cli
from siesta.cli.main_app import app


def test_quickstart_project(tmp_path_chdir, capture_output):
    """Test project quickstart command creates expected project structure."""

    with capture_output() as output:
        try:
            app(["project", "quickstart"])
        except SystemExit as e:
            assert e.code == 0

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
        try:
            app(["project", "quickstart", "--as-app"])
        except SystemExit as e:
            assert e.code == 0

    assert "Failed to build the docs" not in output.getvalue()
    # Should not have src directory for app
    assert not Path(tmp_path_chdir, "src").exists()
    # But should still have docs
    assert Path(tmp_path_chdir, "docs").exists()


def test_quickstart_project_as_pkg(tmp_path_chdir, capture_output):
    """Test project quickstart --as-pkg creates package structure in root directory."""

    with capture_output() as output:
        try:
            app(["project", "quickstart", "--as-pkg"])
        except SystemExit as e:
            assert e.code == 0

    assert "Failed to build the docs" not in output.getvalue()
    assert (tmp_path_chdir / "src").exists()
    assert (tmp_path_chdir / "src" / tmp_path_chdir.name).exists()


def test_quickstart_respects_no_tests(tmp_path_chdir, capture_output):
    """Test that user flags take precedence (--no-tests)."""

    with capture_output() as output:
        # User specifies --no-tests, defaults should not override it
        try:
            app(["project", "quickstart", "--no-tests"])
        except SystemExit as e:
            assert e.code == 0

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
        try:
            app(["project", "quickstart", "--no-actions"])
        except SystemExit as e:
            assert e.code == 0

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
        try:
            app(
                [
                    "project",
                    "quickstart",
                    "--no-tests",
                    "--no-actions",
                ]
            )
        except SystemExit as e:
            assert e.code == 0

    assert "Failed to build the docs" not in output.getvalue()

    # Check project structure - docs should exist (default)
    assert Path(tmp_path_chdir, "docs").exists()
    assert Path(tmp_path_chdir, "uv.lock").exists()

    # Check tests directory does NOT exist (user specified --no-tests)
    assert not Path(tmp_path_chdir, "tests").exists()

    # Check GitHub Actions does NOT exist (user specified --no-actions)
    assert not Path(tmp_path_chdir, ".github").exists()


def test_quickstart_collects_decisions_before_mutations(tmp_path_chdir, monkeypatch):
    """Test quickstart collects prompts before any mutating command runs."""
    events: list[str] = []
    prompts = iter([True, True, True, True, True, True, True])

    def fake_confirm(message: str) -> bool:
        events.append(f"confirm:{message}")
        return next(prompts)

    def fake_run_command(cmd, check=True, cwd=None):
        cmd_str = " ".join(cmd)
        if cmd == ["uv", "--version"]:
            events.append("check_uv")
        else:
            events.append(f"run:{cmd_str}")

        class Result:
            stdout = "ok"
            returncode = 0

        return Result()

    monkeypatch.setattr("siesta.cli.project_app.logger.confirm", fake_confirm)
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr(cli, "run_command", fake_run_command)
    monkeypatch.setattr(cli, "load_deps", lambda: {"dev": []})
    monkeypatch.setattr(
        cli, "write_or_update_pre_commit_file", lambda: events.append("precommit_file")
    )
    monkeypatch.setattr(cli, "add_ipdb_as_debugger", lambda: events.append("ipdb"))
    monkeypatch.setattr(
        cli, "setup_tests", lambda **_kwargs: events.append("setup_tests")
    )
    monkeypatch.setattr(cli, "write_gitignore", lambda: events.append("gitignore"))
    monkeypatch.setattr(cli, "init_docs", lambda **_kwargs: events.append("init_docs"))
    monkeypatch.setattr(
        cli, "tree_project", lambda *_args, **_kwargs: events.append("tree")
    )

    try:
        app(["project", "quickstart", "-i"])
    except SystemExit as e:
        assert e.code == 0

    first_mutation = next(
        i
        for i, event in enumerate(events)
        if event != "check_uv" and not event.startswith("confirm:")
    )
    prompt_indices = [
        i for i, event in enumerate(events) if event.startswith("confirm:")
    ]
    assert prompt_indices
    assert max(prompt_indices) < first_mutation
