# Copyright 2025 Entalpic
"""Utility functions related to the ``siesta project`` subcommand."""

from pathlib import Path
from textwrap import dedent

import requests

from siesta.utils.common import get_pyver, logger, safe_dump


def write_test_actions_config() -> None:
    """
    Write the test actions config to the ``.github/workflows/test.yml`` file.

    Basically this will allow you to run tests automatically on Github on any PR or push to the main branch.
    """
    github_dir = Path(".github")
    workflows_dir = github_dir / "workflows"
    if workflows_dir.exists():
        logger.warning("Workflows directory already exists. Skipping.")
        return
    workflows_dir.mkdir(parents=True, exist_ok=True)
    test_config = {
        "name": "Tests",
        "on": {
            "pull_request": None,
            "push": {
                "branches": ["main"],
            },
        },
        "jobs": {
            "test-install": {
                "runs-on": "ubuntu-latest",
                "strategy": {"matrix": {"python-version": [get_pyver()]}},
                "steps": [
                    {
                        "uses": "actions/checkout@v4",
                    },
                    {
                        "name": "Set up Python ${{ matrix.python-version }}",
                        "uses": "actions/setup-python@v5",
                        "with": {"python-version": "${{ matrix.python-version }}"},
                    },
                    {
                        "name": "Install uv",
                        "run": "curl -LsSf https://astral.sh/uv/install.sh | sh",
                    },
                    {
                        "name": "Install dependencies",
                        "run": "uv sync",
                    },
                ],
            },
            "test-pytest": {
                "runs-on": "ubuntu-latest",
                "strategy": {"matrix": {"python-version": [get_pyver()]}},
                "steps": [
                    {
                        "uses": "actions/checkout@v4",
                    },
                    {
                        "name": "Set up Python ${{ matrix.python-version }}",
                        "uses": "actions/setup-python@v5",
                        "with": {"python-version": "${{ matrix.python-version }}"},
                    },
                    {
                        "name": "Install uv",
                        "run": "curl -LsSf https://astral.sh/uv/install.sh | sh",
                    },
                    {
                        "name": "Install dependencies",
                        "run": "uv sync",
                    },
                    {
                        "name": "Run tests",
                        "run": "uv run pytest",
                    },
                ],
            },
        },
    }
    safe_dump(test_config, workflows_dir / "test.yml")


def write_tests_infra(project_name: str):
    """Write the tests infrastructure to the ``tests/`` directory.

    This will create a ``test_import.py`` file that will test that the project can be imported.

    Parameters
    ----------
    project_name : str
        The name of the project.
    """
    tests_dir = Path("tests")
    project_name = project_name.replace("-", "_")
    if tests_dir.exists():
        logger.warning("Tests directory already exists. Skipping.")
        return
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_example = dedent(rf'''
    # Copyright 2025 Entalpic
    import pytest
    from pathlib import Path


    @pytest.fixture(autouse=True)
    def mock_variable():
        """Mock some variable."""
        yield 42

    def test_variable(mock_variable):
        """Test the variable."""
        assert mock_variable == 42

    def test_import():
        """Test the project's import."""
        import {project_name}  # noqa: F401

    def test_copyrights():
        src = Path(__file__).resolve().parent.parent
        no_copyrights = []
        for file in (
            list(src.rglob("*.py"))
            + list(src.rglob("*.rst"))
            + list(src.rglob("*.yaml"))
            + list(src.rglob("*.yml"))
        ):
            if ".venv" in str(file):
                continue
            first_line = file.read_text().split("\n")[0]
            if "Copyright" not in first_line or "Entalpic" not in first_line:
                no_copyrights.append(
                    f"Copyright not found in {{file}} ; first line: {{first_line}}"
                )
        assert len(no_copyrights) == 0, "\n".join(no_copyrights)
    ''')
    (tests_dir / "test_import.py").write_text(test_example)


def add_ipdb_as_debugger():
    """Set ``ipdb`` as default debugger to the project.

    This will set ``ipdb`` as default debugger when calling ``breakpoint()`` by setting the
    ``PYTHONBREAKPOINT`` environment variable to ``ipdb.set_trace``.
    """
    inits = list(Path("src/").glob("**/__init__.py"))
    if not inits:
        logger.warning("No __init__.py files found. Skipping ipdb debugger.")
        return

    first_init = sorted(
        [(i, len(str(i).split("/"))) for i in inits], key=lambda x: x[1]
    )[0][0]

    first_init.write_text(
        first_init.read_text()
        + dedent(
            """

            try:
                import os

                import ipdb  # noqa: F401

                # set ipdb as default debugger when calling `breakpoint()`
                os.environ["PYTHONBREAKPOINT"] = "ipdb.set_trace"
            except ImportError:
                print(
                    "`ipdb` not available.",
                    "Consider adding it to your dev stack for a smoother debugging experience.",
                )
            """
        )
    )


def download_python_gitignore() -> str:
    """Download the gitignore file from the ``.gitignore`` file."""
    gitignore_url = (
        "https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore"
    )
    response = requests.get(gitignore_url)
    return response.text


def write_gitignore() -> None:
    """Write the gitignore file to the ``.gitignore`` file."""
    gitignore_path = Path(".gitignore")
    python_gitignore = download_python_gitignore()
    gitignore = dedent("""
    # Custom
    .vscode/
    .DS_Store
    """)
    gitignore_path.write_text(gitignore + python_gitignore)
