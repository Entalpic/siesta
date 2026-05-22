# Copyright 2025 Entalpic
"""Tests for CLI package module layout and entrypoint contract."""

from cyclopts import App

from siesta.cli import main
from siesta.cli.docs_app import build_docs, docs_app, init_docs
from siesta.cli.main_app import app
from siesta.cli.project_app import project_app, quickstart_project, setup_tests
from siesta.cli.self_app import self_app, show_github_pat, tab_completions_app


def test_entrypoint_main_is_callable():
    assert callable(main)


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
    return {
        name
        for name in root_app._commands
        if not name.startswith("-")
    }


def test_root_app_registers_domain_apps():
    assert isinstance(app, App)
    assert _command_names(app) == {"docs", "project", "self"}


def test_docs_app_registers_leaf_commands():
    assert _command_names(docs_app) == {"init", "update", "build", "watch", "open"}


def test_project_app_registers_leaf_commands():
    assert _command_names(project_app) == {"quickstart", "setup-tests", "tree"}


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


def test_domain_modules_expose_command_callables():
    assert callable(init_docs)
    assert callable(build_docs)
    assert callable(quickstart_project)
    assert callable(setup_tests)
    assert callable(show_github_pat)


def test_self_app_registers_tab_completions():
    assert "tab-completions" in _subapp_names(self_app)
