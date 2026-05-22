# Copyright 2025 Entalpic
"""Tests for CLI package module layout and entrypoint contract."""

from cyclopts import App

from siesta.cli import main
from siesta.cli.docs_app import build_docs, init_docs
from siesta.cli.main_app import app
from siesta.cli.project_app import quickstart_project, setup_tests
from siesta.cli.self_app import self_app, show_github_pat


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


def test_root_app_registers_domain_apps():
    assert isinstance(app, App)
    assert {"docs", "project", "self"}.issubset(_subapp_names(app))


def test_domain_modules_expose_command_callables():
    assert callable(init_docs)
    assert callable(build_docs)
    assert callable(quickstart_project)
    assert callable(setup_tests)
    assert callable(show_github_pat)


def test_self_app_registers_tab_completions():
    assert "tab-completions" in _subapp_names(self_app)
