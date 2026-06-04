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


def test_quickstart_test_scaffold_uses_normalized_import(tmp_path_chdir):
    """Generated import tests use the Python package name created by uv."""
    cli.write_tests_infra("Siesta-Quickstart.3qwVCd")

    test_file = tmp_path_chdir / "tests" / "test_import.py"
    content = test_file.read_text()

    assert content.startswith("# Copyright 2025 Entalpic")
    assert "from pathlib import Path\n\nimport pytest" in content
    assert "import siesta_quickstart_3qwvcd  # noqa: F401" in content


def test_quickstart_collects_decisions_before_mutations(tmp_path_chdir, monkeypatch):
    """Test quickstart collects prompts before any mutating command runs."""
    events: list[str] = []
    prompts = iter([True, True, True, True, True, True, True, True, False])

    def fake_confirm(message: str, default: bool = True) -> bool:
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
    monkeypatch.setattr(
        "siesta.cli.project_app.logger.select",
        lambda *_args, **_kwargs: (
            events.append("select:layout") or "Library with src/ layout (recommended)"
        ),
    )
    monkeypatch.setattr(
        "siesta.cli.project_app.logger.prompt",
        lambda message, default=None: events.append(f"prompt:{message}") or default,
    )
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
    monkeypatch.setattr(
        "siesta.cli.docs_app.init_docs",
        lambda **_kwargs: events.append("init_docs"),
    )
    monkeypatch.setattr(
        cli, "tree_project", lambda *_args, **_kwargs: events.append("tree")
    )
    monkeypatch.setattr(
        cli, "install_quickstart", lambda *a, **k: (events.append("agents"), {})[1]
    )
    monkeypatch.setattr(cli, "print_summary", lambda *a, **k: None)

    try:
        app(["project", "quickstart", "-i"])
    except SystemExit as e:
        assert e.code == 0

    first_mutation = next(
        i
        for i, event in enumerate(events)
        if event != "check_uv"
        and not event.startswith(("confirm:", "select:", "prompt:"))
    )
    prompt_indices = [
        i
        for i, event in enumerate(events)
        if event.startswith(("confirm:", "select:", "prompt:"))
    ]
    assert prompt_indices
    assert max(prompt_indices) < first_mutation


def test_quickstart_interactive_recommends_cli_defaults(tmp_path_chdir, monkeypatch):
    """Interactive quickstart prompts use CLI defaults as recommendations."""
    defaults: dict[str, bool] = {}

    def fake_confirm(message: str, default: bool = True) -> bool:
        defaults[message] = default
        return default

    monkeypatch.setattr("siesta.cli.project_app.logger.confirm", fake_confirm)
    monkeypatch.setattr(
        "siesta.cli.project_app.logger.select",
        lambda *_args, **_kwargs: "Library with src/ layout (recommended)",
    )
    monkeypatch.setattr(
        "siesta.cli.project_app.logger.prompt",
        lambda _message, default=None: default,
    )
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr(cli, "run_command", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(cli, "load_deps", lambda: {"dev": []})
    monkeypatch.setattr(cli, "write_or_update_pre_commit_file", lambda: None)
    monkeypatch.setattr(cli, "add_ipdb_as_debugger", lambda: None)
    monkeypatch.setattr(cli, "setup_tests", lambda **_kwargs: None)
    monkeypatch.setattr(cli, "write_gitignore", lambda: None)
    monkeypatch.setattr(cli, "tree_project", lambda *_args, **_kwargs: None)

    try:
        app(["project", "quickstart", "-i", "--no-docs", "--no-agents"])
    except SystemExit as e:
        assert e.code == 0

    assert defaults["Would you like to install recommended dependencies?"] is True
    assert defaults["Would you like to add ipdb as debugger?"] is True


def test_quickstart_interactive_recommends_dev_docs_deps(tmp_path_chdir, monkeypatch):
    """Docs dependency placement prompt recommends the non-interactive default."""
    defaults: dict[str, bool] = {}

    def fake_confirm(message: str, default: bool = True) -> bool:
        defaults[message] = default
        return default

    monkeypatch.setattr("siesta.cli.project_app.logger.confirm", fake_confirm)
    monkeypatch.setattr(
        "siesta.cli.project_app.logger.select",
        lambda *_args, **_kwargs: "Library with src/ layout (recommended)",
    )
    monkeypatch.setattr(
        "siesta.cli.project_app.logger.prompt",
        lambda _message, default=None: default,
    )
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr(cli, "run_command", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(cli, "load_deps", lambda: {"dev": []})
    monkeypatch.setattr(cli, "write_or_update_pre_commit_file", lambda: None)
    monkeypatch.setattr(cli, "add_ipdb_as_debugger", lambda: None)
    monkeypatch.setattr(cli, "setup_tests", lambda **_kwargs: None)
    monkeypatch.setattr(cli, "write_gitignore", lambda: None)
    monkeypatch.setattr(
        "siesta.cli.docs_app.init_docs",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(cli, "tree_project", lambda *_args, **_kwargs: None)

    try:
        app(["project", "quickstart", "-i", "--no-agents"])
    except SystemExit as e:
        assert e.code == 0

    message = (
        "Would you like to install documentation dependencies as main dependencies?"
    )
    assert defaults[message] is False


def test_quickstart_interactive_respects_explicit_layout(tmp_path_chdir, monkeypatch):
    """Explicit layout flags skip the interactive layout prompt."""
    selected = False
    commands: list[list[str]] = []

    def fake_select(*_args, **_kwargs):
        nonlocal selected
        selected = True
        return "Library with src/ layout (recommended)"

    def fake_run_command(cmd, check=True, cwd=None):
        commands.append(cmd)
        return True

    monkeypatch.setattr(
        "siesta.cli.project_app.logger.confirm", lambda *_a, **_k: False
    )
    monkeypatch.setattr("siesta.cli.project_app.logger.select", fake_select)
    monkeypatch.setattr(
        "siesta.cli.project_app.logger.prompt",
        lambda _message, default=None: default,
    )
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr(cli, "run_command", fake_run_command)
    monkeypatch.setattr(cli, "tree_project", lambda *_args, **_kwargs: None)

    try:
        app(["project", "quickstart", "-i", "--as-app"])
    except SystemExit as e:
        assert e.code == 0

    assert selected is False
    assert ["uv", "init", "--name=test_siesta"] in commands


def test_quickstart_interactive_respects_explicit_docs_path(
    tmp_path_chdir, monkeypatch
):
    """Explicit docs path skips the interactive docs path prompt."""
    prompted = False
    init_docs_kwargs = {}

    def fake_prompt(_message, default=None):
        nonlocal prompted
        prompted = True
        return default

    monkeypatch.setattr(
        "siesta.cli.project_app.logger.confirm", lambda *_a, **_k: False
    )
    monkeypatch.setattr(
        "siesta.cli.project_app.logger.select",
        lambda *_args, **_kwargs: "Library with src/ layout (recommended)",
    )
    monkeypatch.setattr("siesta.cli.project_app.logger.prompt", fake_prompt)
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr(cli, "run_command", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        "siesta.cli.docs_app.init_docs",
        lambda **kwargs: init_docs_kwargs.update(kwargs),
    )
    monkeypatch.setattr(cli, "tree_project", lambda *_args, **_kwargs: None)

    try:
        app(
            [
                "project",
                "quickstart",
                "-i",
                "--docs",
                "--docs-path=custom-docs",
                "--no-deps",
                "--no-agents",
            ]
        )
    except SystemExit as e:
        assert e.code == 0

    assert prompted is False
    assert init_docs_kwargs["path"] == "custom-docs"


def test_quickstart_installs_agents(tmp_path_chdir, capture_output):
    """Agent assets are written by default during project quickstart."""
    with capture_output():
        try:
            app(["project", "quickstart"])
        except SystemExit as e:
            assert e.code == 0

    assert (tmp_path_chdir / "AGENTS.md").exists()
    assert (tmp_path_chdir / ".cursor" / "skills" / "grill-with-docs").is_dir()
    assert (tmp_path_chdir / ".cursor" / "rules" / "python-docstrings.mdc").exists()


def test_quickstart_respects_no_agents(tmp_path_chdir, capture_output):
    """--no-agents skips the agent assets step."""
    with capture_output():
        try:
            app(["project", "quickstart", "--no-agents"])
        except SystemExit as e:
            assert e.code == 0

    assert not (tmp_path_chdir / "AGENTS.md").exists()
    assert not (tmp_path_chdir / ".cursor" / "skills").exists()
