# Copyright 2025 Entalpic
"""Tests for CLI package module layout and entrypoint contract."""

import importlib
import tomllib
from pathlib import Path

import pytest
from cyclopts import App

import siesta.cli.main_app as main_app
from siesta.cli import main
from siesta.cli.agents_app import (
    add_constitution,
    add_rule,
    add_skill,
    agents_app,
    quickstart,
)
from siesta.cli.docs_app import build_docs, docs_app, init_docs
from siesta.cli.main_app import app
from siesta.cli.project_app import project_app, quickstart_project, setup_tests
from siesta.cli.self_app import self_app, show_github_pat, tab_completions_app

CANONICAL_SCRIPT_ENTRYPOINT = "siesta.cli.main_app:main"


def test_project_scripts_entrypoint_matches_canonical_contract():
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert data["project"]["scripts"]["siesta"] == CANONICAL_SCRIPT_ENTRYPOINT


def test_canonical_script_entrypoint_is_callable():
    module_path, _, attr = CANONICAL_SCRIPT_ENTRYPOINT.partition(":")
    module = importlib.import_module(module_path)
    assert callable(getattr(module, attr))


def test_entrypoint_main_is_callable():
    assert callable(main)


def test_entrypoint_main_translates_cancellation_to_exit_130(
    monkeypatch, capture_output
):
    """The console-script wrapper owns Cancellation exit semantics."""
    monkeypatch.setattr(main_app, "_set_completion_hint", lambda: None)
    monkeypatch.setattr(main_app.metadata, "version", lambda _package: "0.0.0")
    monkeypatch.setattr(
        main_app, "start_background_update_check", lambda _version: object()
    )
    monkeypatch.setattr(
        main_app,
        "app",
        lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    with capture_output() as output:
        with pytest.raises(SystemExit) as exc_info:
            main_app.main()

    assert exc_info.value.code == 130
    assert "Aborted." in output.getvalue()


def _subapp_names(root_app: App) -> set[str]:
    names: set[str] = set()
    for subapp in root_app.subapps:
        if not subapp.name:
            continue
        name = subapp.name[0] if isinstance(subapp.name, tuple) else subapp.name
        names.add(name)
    return names


def _command_names(root_app: App) -> set[str]:
    """Return user-facing command names registered on a Cyclopts app."""
    return {name for name in root_app._commands if not name.startswith("-")}


def test_root_app_registers_domain_apps():
    assert isinstance(app, App)
    assert _command_names(app) == {"agents", "docs", "project", "self"}


def test_docs_app_registers_leaf_commands():
    assert _command_names(docs_app) == {"init", "update", "build", "watch", "open"}


def test_project_app_registers_leaf_commands():
    assert _command_names(project_app) == {
        "quickstart",
        "setup-tests",
        "add-skill",
        "tree",
    }


def test_self_app_registers_leaf_commands():
    assert _command_names(self_app) == {
        "tab-completions",
        "set-github-pat",
        "show-github-pat",
        "show-deps",
        "version",
        "update",
        "upgrade",
    }


def test_tab_completions_app_registers_leaf_commands():
    assert _command_names(tab_completions_app) == {
        "install",
        "show",
        "where",
        "uninstall",
    }


def test_agents_app_registers_commands():
    assert _command_names(agents_app) == {
        "add-skill",
        "add-rule",
        "add-constitution",
        "quickstart",
    }


def test_agents_app_exposes_command_callables():
    assert callable(add_skill)
    assert callable(add_rule)
    assert callable(add_constitution)
    assert callable(quickstart)


def test_domain_modules_expose_command_callables():
    assert callable(init_docs)
    assert callable(build_docs)
    assert callable(quickstart_project)
    assert callable(setup_tests)
    assert callable(show_github_pat)


def test_self_app_registers_tab_completions():
    assert "tab-completions" in _subapp_names(self_app)


def test_cli_domain_modules_import_without_cycles():
    """Domain modules must import cleanly without circular dependencies."""
    import importlib

    for module_name in (
        "siesta.cli.main_app",
        "siesta.cli.agents_app",
        "siesta.cli.docs_app",
        "siesta.cli.project_app",
        "siesta.cli.self_app",
    ):
        importlib.reload(importlib.import_module(module_name))
