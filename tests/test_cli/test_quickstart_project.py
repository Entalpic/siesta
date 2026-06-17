# Copyright 2025 Entalpic
import sys
from pathlib import Path

import pytest

import siesta.cli.project_app as cli
from siesta.cli.main_app import app

# Steps to disable so a quickstart run exercises only the uv-init decision.
_NO_FEATURE_FLAGS = [
    "--no-deps",
    "--no-precommit",
    "--no-tests",
    "--no-actions",
    "--no-gitignore",
    "--no-docs",
    "--no-agents",
]


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
    from siesta.utils.project import write_tests_infra

    write_tests_infra("Siesta-Quickstart.3qwVCd")

    test_file = tmp_path_chdir / "tests" / "test_import.py"
    content = test_file.read_text()

    assert content.startswith("# Copyright ") and "Entalpic" in content.splitlines()[0]
    assert "import importlib\nfrom pathlib import Path" in content
    assert "importlib.import_module('siesta_quickstart_3qwvcd')" in content


def test_quickstart_collects_decisions_before_mutations(tmp_path_chdir, monkeypatch):
    """Test quickstart collects prompts before any mutating command runs."""
    events: list[str] = []
    prompts = iter([True, True, True, True, True, True, True, True, True, False])

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
    monkeypatch.setattr("siesta.utils.common.run_command", fake_run_command)
    monkeypatch.setattr(cli, "load_deps", lambda: {"dev": []})
    monkeypatch.setattr(
        "siesta.cli.project_app.run_mutations",
        lambda *_a, **_k: (
            events.append("run_mutations"),
            __import__(
                "siesta.utils.conflicts", fromlist=["OperationSummary"]
            ).OperationSummary(),
        )[1],
    )
    monkeypatch.setattr(
        "siesta.cli.project_app.run_mutations",
        lambda *_a, **_k: (
            events.append("run_mutations"),
            __import__(
                "siesta.utils.conflicts", fromlist=["OperationSummary"]
            ).OperationSummary(),
        )[1],
    )
    monkeypatch.setattr("siesta.cli.project_app.render_summary", lambda *_a, **_k: None)
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
    monkeypatch.setattr(
        "siesta.utils.common.run_command", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(cli, "load_deps", lambda: {"dev": []})
    monkeypatch.setattr(
        "siesta.cli.project_app.run_mutations",
        lambda *_a, **_k: __import__(
            "siesta.utils.conflicts", fromlist=["OperationSummary"]
        ).OperationSummary(),
    )
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
    monkeypatch.setattr(
        "siesta.utils.common.run_command", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(cli, "load_deps", lambda: {"dev": []})
    monkeypatch.setattr(
        "siesta.cli.project_app.run_mutations",
        lambda *_a, **_k: __import__(
            "siesta.utils.conflicts", fromlist=["OperationSummary"]
        ).OperationSummary(),
    )
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
    monkeypatch.setattr("siesta.utils.project.run_command", fake_run_command)
    monkeypatch.setattr("siesta.utils.common.run_command", fake_run_command)
    monkeypatch.setattr(cli, "tree_project", lambda *_args, **_kwargs: None)

    try:
        app(["project", "quickstart", "-i", "--as-app", "--uv-init"])
    except SystemExit as e:
        assert e.code == 0

    assert selected is False
    assert ["uv", "init", "--name=test_siesta"] in commands


def test_quickstart_interactive_respects_explicit_docs_path(
    tmp_path_chdir, monkeypatch
):
    """Explicit docs path skips the interactive docs path prompt."""
    prompted = False
    exec_kwargs = {}

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
    monkeypatch.setattr(
        "siesta.utils.common.run_command", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(
        "siesta.cli.docs_app._execute_docs_init",
        lambda **kwargs: exec_kwargs.update(kwargs),
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
    assert exec_kwargs["path"] == "custom-docs"


def test_quickstart_fresh_project_docs_uv_prompt_collection(
    tmp_path_chdir, monkeypatch
):
    """docs_with_uv is resolved in prompt collection (before uv init runs)."""
    exec_kwargs = {}

    class _Result:
        stdout = "Python 3.12.1\n"
        returncode = 0

    monkeypatch.setattr("siesta.cli.project_app.logger.confirm", lambda *_a, **_k: True)
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr("siesta.utils.common.run_command", lambda *_a, **_k: _Result())
    monkeypatch.setattr("siesta.utils.project.run_command", lambda *_a, **_k: _Result())
    monkeypatch.setattr(cli, "load_deps", lambda: {"dev": []})
    monkeypatch.setattr(
        "siesta.cli.docs_app._execute_docs_init",
        lambda **kwargs: exec_kwargs.update(kwargs),
    )
    monkeypatch.setattr(cli, "tree_project", lambda *_args, **_kwargs: None)

    try:
        app(
            [
                "project",
                "quickstart",
                "--no-agents",
                "--no-ipdb",
                "--no-tests",
                "--no-actions",
            ]
        )
    except SystemExit as e:
        assert e.code == 0

    # uv.lock does not exist at prompt-collection time (fresh project), so docs falls
    # back to pip — resolved before the uv-init mutation could create a uv.lock.
    assert exec_kwargs["with_uv"] is False


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


def test_quickstart_existing_uv_project_aborts_without_no_uv_init(
    tmp_path_chdir, monkeypatch, capture_output
):
    """Non-TTY quickstart on an already-initialized project aborts unless opted out."""
    (tmp_path_chdir / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    # Force a non-TTY environment so the uv-init conflict resolves to abort.
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr(
        "siesta.utils.common.run_command", lambda *_args, **_kwargs: True
    )

    code = None
    with capture_output() as output:
        try:
            app(["project", "quickstart"])
        except SystemExit as e:
            code = e.code

    assert code != 0
    assert "uv project" in output.getvalue()


def test_quickstart_existing_uv_project_skips_with_no_uv_init(
    tmp_path_chdir, monkeypatch, capture_output
):
    """--no-uv-init lets a non-TTY quickstart proceed on an existing project."""
    (tmp_path_chdir / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    commands: list[list[str]] = []
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr(
        "siesta.utils.common.run_command",
        lambda cmd, *_a, **_k: commands.append(cmd) or True,
    )
    monkeypatch.setattr(cli, "tree_project", lambda *_args, **_kwargs: None)

    code = None
    with capture_output() as output:
        try:
            app(["project", "quickstart", "--no-uv-init", *_NO_FEATURE_FLAGS])
        except SystemExit as e:
            code = e.code

    assert code == 0
    # uv init must not run, and no fresh-directory warning (the project already exists).
    assert not any(cmd[:2] == ["uv", "init"] for cmd in commands)
    assert "Skipping uv init on a fresh directory" not in output.getvalue()


def test_quickstart_no_uv_init_on_fresh_project_warns(
    tmp_path_chdir, monkeypatch, capture_output
):
    """--no-uv-init on a fresh directory warns that later steps may fail."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr(
        "siesta.utils.common.run_command", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(cli, "tree_project", lambda *_args, **_kwargs: None)

    code = None
    with capture_output() as output:
        try:
            app(["project", "quickstart", "--no-uv-init", *_NO_FEATURE_FLAGS])
        except SystemExit as e:
            code = e.code

    assert code == 0
    assert "Skipping uv init on a fresh directory" in output.getvalue()


def test_quickstart_gitignore_takes_precedence_over_uv_init(
    tmp_path_chdir,
    monkeypatch,
):
    """A fresh quickstart writes siesta's .gitignore after uv init."""
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr(
        "siesta.utils.common.run_command", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(cli, "tree_project", lambda *_args, **_kwargs: None)

    try:
        app(
            [
                "project",
                "quickstart",
                "--no-deps",
                "--no-precommit",
                "--no-tests",
                "--no-actions",
                "--no-docs",
                "--no-agents",
            ]
        )
    except SystemExit as e:
        assert e.code == 0

    content = (tmp_path_chdir / ".gitignore").read_text()
    assert ".vscode/" in content


def test_quickstart_preexisting_gitignore_is_a_conflict(
    tmp_path_chdir, monkeypatch, capture_output
):
    """A .gitignore present before the run is a Conflict; --no-overwrite skips it."""
    (tmp_path_chdir / ".gitignore").write_text("# user's own\n")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr(
        "siesta.utils.common.run_command", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(cli, "tree_project", lambda *_args, **_kwargs: None)

    with capture_output():
        try:
            app(
                [
                    "project",
                    "quickstart",
                    "--no-overwrite",
                    "--no-deps",
                    "--no-precommit",
                    "--no-tests",
                    "--no-actions",
                    "--no-docs",
                    "--no-agents",
                ]
            )
        except SystemExit as e:
            assert e.code == 0

    assert (tmp_path_chdir / ".gitignore").read_text() == "# user's own\n"


def test_abort_zero_state_change(tmp_path_chdir, monkeypatch):
    """Abort on gitignore conflict leaves the project unchanged."""
    from siesta.utils.common import logger

    (tmp_path_chdir / ".gitignore").write_text("# pre-existing\n")
    before = {p.relative_to(tmp_path_chdir) for p in tmp_path_chdir.rglob("*")}

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(logger, "select", lambda _msg, _labels: "Abort")
    monkeypatch.setattr(cli, "get_project_name", lambda _interactive: "test_siesta")
    monkeypatch.setattr(
        "siesta.utils.common.run_command", lambda *_args, **_kwargs: True
    )

    with pytest.raises(SystemExit):
        app(
            [
                "project",
                "quickstart",
                "--no-deps",
                "--no-precommit",
                "--no-tests",
                "--no-actions",
                "--no-docs",
                "--no-agents",
            ]
        )

    after = {p.relative_to(tmp_path_chdir) for p in tmp_path_chdir.rglob("*")}
    assert after == before
    assert not (tmp_path_chdir / "pyproject.toml").exists()


def test_quickstart_single_pipeline_non_interactive(tmp_path_chdir, capture_output):
    """Full non-interactive quickstart runs one pipeline including agents."""
    with capture_output() as output:
        try:
            app(
                [
                    "project",
                    "quickstart",
                    "--no-docs",
                ]
            )
        except SystemExit as e:
            assert e.code == 0

    assert (tmp_path_chdir / ".gitignore").exists()
    assert (tmp_path_chdir / "tests" / "test_import.py").exists()
    assert (tmp_path_chdir / ".github" / "workflows" / "test.yml").exists()
    assert (tmp_path_chdir / "AGENTS.md").exists()
    assert "setup_tests" not in output.getvalue()


def test_quickstart_respects_no_agents(tmp_path_chdir, capture_output):
    """--no-agents skips the agent assets step."""
    with capture_output():
        try:
            app(["project", "quickstart", "--no-agents"])
        except SystemExit as e:
            assert e.code == 0

    assert not (tmp_path_chdir / "AGENTS.md").exists()
    assert not (tmp_path_chdir / ".cursor" / "skills").exists()
