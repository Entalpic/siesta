# Copyright 2025 Entalpic
import importlib

# Package name for PyPI
PACKAGE_NAME = "siesta"
"""Name of the PyPI package for the ``siesta`` package."""

PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
"""URL of the PyPI package for the ``siesta`` package."""

GITHUB_OWNER = "entalpic"
"""Name of the GitHub owner for the ``siesta`` repository."""
GITHUB_REPO = "siesta"
"""Name of the GitHub repository for the ``siesta`` package."""

UPDATE_CHECK_ENV_VAR = "SIESTA_UPDATE_CHECK_HOURS"
"""Name of the environment variable for update check frequency."""
DEFAULT_UPDATE_CHECK_HOURS = 24
"""Default update check frequency (in hours). Default is ``24`` (once per day).
Set to ``"false"`` or ``"-1"`` to disable automatic checks.
"""

ROOT = importlib.resources.files(PACKAGE_NAME)
"""Root directory of the ``siesta`` package."""

CLI_DEFAULTS = {
    "deps": True,
    "as_main_deps": False,
    "precommit": True,
    "ipdb": True,
    "tests": True,
    "actions": True,
    "gitignore": True,
}
"""Default values for the CLI when not in ``interactive`` mode.

- ``deps``: Whether to install dependencies (dev &? docs), by default ``True``.
- ``as_main_deps``: Whether to include docs dependencies in the main dependencies, by default ``False``.
- ``precommit``: Whether to install pre-commit hooks, by default ``True``.
- ``ipdb``: Whether to add ipdb as debugger, by default ``True``.
- ``tests``: Whether to initialize (pytest) tests infra, by default ``True``.
- ``actions``: Whether to initialize GitHub Actions, by default ``True``.
- ``gitignore``: Whether to initialize the ``.gitignore`` file, by default ``True``.
"""
