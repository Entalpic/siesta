# Copyright 2025 Entalpic
"""Generalist utility functions."""

import importlib
import json
import re
from os.path import expandvars
from pathlib import Path
from shutil import copy2
from subprocess import CalledProcessError, run

from ruamel.yaml import YAML

from siesta.logger import Logger

logger = Logger("siesta")
"""A logger to log messages to the console."""
ROOT = importlib.resources.files("siesta")
"""The root directory of the ``siesta`` package."""


def safe_dump(data, file, **kwargs):
    """Dump some data to a file using ``ruamel.yaml``.

    Parameters
    ----------
    data : dict
        The data to dump to the file.
    file : str | Path | IO
        The file to dump the data to.
    """
    handle = file
    if isinstance(file, str):
        handle = open(file, "w")
    else:
        handle = file

    yaml = YAML(typ="rt", pure=True)
    yaml.default_flow_style = False
    yaml.dump(data, handle, **kwargs)
    if isinstance(file, str):
        handle.close()


def safe_load(file):
    """Load data from a file using ``ruamel.yaml``.

    Parameters
    ----------
    file : str | Path | IO
        The file to load the data from.
    """
    handle = file
    if isinstance(file, str):
        handle = open(file, "r")
    yaml = YAML(typ="safe", pure=True)
    return yaml.load(handle)


def run_command(
    cmd: list[str], check: bool = True, cwd: str | Path | None = None
) -> str | bool:
    """Run a command in the shell.

    Parameters
    ----------
    cmd : list[str]
        The command to run.
    check : bool, optional
        Whether to raise an error if the command fails, by default ``True``.
    cwd : str | Path | None, optional
        The working directory to run the command in, by default ``None``.

    Returns
    -------
    str | bool
        The result of the command.
    """
    try:
        return run(
            cmd,
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=cwd,
        )
    except CalledProcessError as e:
        logger.error(e.stderr)
        return False


def resolve_path(path: str | Path) -> Path:
    """Resolve a path and expand environment variables.

    Parameters
    ----------
    path : str | Path
        The path to resolve.

    Returns
    -------
    Path
        The resolved path.
    """
    return Path(expandvars(path)).expanduser().resolve()


def load_deps() -> list[str]:
    """Load dependencies from the |dependenciesjson|_ file.

    Returns
    -------
    list[str]
        The dependencies to load.

    .. |dependenciesjson| replace:: ``dependencies.json``
    .. _dependenciesjson: ../../../dependencies.json
    .. include 3x "../" because we need to reach /dependencies.json from /autoapi/siesta/utils/index.html
    """
    path = ROOT / "dependencies.json"
    return json.loads(path.read_text())


def write_or_update_pre_commit_file() -> None:
    """Write the pre-commit file to the current directory."""
    pre_commit = Path(".pre-commit-config.yaml")
    ref = ROOT / "precommits.yaml"
    if pre_commit.exists():
        # Load existing config
        with open(pre_commit, "r") as f:
            current = safe_load(f)

        # Load reference config
        with open(ref, "r") as f:
            reference = safe_load(f)

        # Update existing config with reference repos
        if not isinstance(current, dict):
            current = {}
        if not isinstance(reference, dict):
            reference = {}
        if "repos" not in current:
            current["repos"] = []
        if "repos" not in reference:
            reference["repos"] = []
        current_repos = {repo["repo"]: repo for repo in current["repos"]}
        for repo in reference["repos"]:
            current_repos[repo["repo"]] = repo

        current["repos"] = list(current_repos.values())

        # Write updated config
        safe_dump(current, pre_commit)
        logger.info("Pre-commit file updated.")
        return

    # Copy reference file if no existing config
    copy2(ref, pre_commit)
    logger.info("Pre-commit file written.")


def get_pyver():
    """Get the Python version from the user.

    Returns
    -------
    str
        The Python version.
    """
    python_version_file = Path(".python-version")
    if python_version_file.exists():
        return python_version_file.read_text().strip()
    if run_command(["which", "uv"]):
        # e.g. "Python 3.12.1"
        full_version = run_command(["uv", "run", "python", "--version"]).stdout.strip()
        version = full_version.split()[1]
        major, minor, _ = version.split(".")
        return f"{major}.{minor}"
    return "3.12"


def get_project_name(interactive: bool = False, snake_case: bool = False) -> str:
    """Get the current project's name from the pyproject.toml or user.

    Prompts the user for the project name, with the default being the name in the pyproject.toml
    if it exists or the current directory's name.

    Parameters
    ----------
    interactive : bool, optional
        Whether to prompt the user. Defaults to ``False`` (use defaults).
    snake_case : bool, optional
        Whether to convert the project name to snake case, by default ``False``.

    Returns
    -------
    str
        The project name.
    """
    pyproject_toml = Path("pyproject.toml")
    pyproject_name = None
    if pyproject_toml.exists():
        txt = pyproject_toml.read_text()
        pyproject_name = re.search(r"name\s*=\s*['\"](.*)['\"]", txt).group(1)
    default = pyproject_name or resolve_path(".").name
    name = logger.prompt("Project name", default=default) if interactive else default
    if snake_case:
        name = name.lower().replace(" ", "_").replace("-", "_")
    return name
