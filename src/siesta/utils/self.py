# Copyright 2025 Entalpic
"""Utility functions for siesta self-management (version, update)."""

import json
import sys
from importlib import metadata
from urllib.error import URLError
from urllib.request import urlopen

from packaging.version import Version

from siesta.utils.common import logger, run_command

# Package name for PyPI
PACKAGE_NAME = "siesta"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"


def get_installation_method() -> str:
    """Detect how siesta was installed.

    Returns
    -------
    str
        One of: ``"uv"``, ``"pipx"``, ``"pip"``, or ``"editable"``.

    Notes
    -----
    Detection is based on:

    - **uv tool**: ``sys.executable`` contains ``/uv/tools/siesta/``
    - **pipx**: ``sys.executable`` contains ``/pipx/venvs/siesta/``
    - **editable**: Package metadata contains ``direct_url.json`` with ``"editable": true``
    - **pip**: Fallback if none of the above match
    """
    executable = sys.executable.lower()

    # Check for uv tool installation
    # Paths like: ~/.local/share/uv/tools/siesta/...
    if "/uv/tools/siesta/" in executable or "\\uv\\tools\\siesta\\" in executable:
        return "uv"

    # Check for pipx installation
    # Paths like: ~/.local/pipx/venvs/siesta/...
    if "/pipx/venvs/siesta/" in executable or "\\pipx\\venvs\\siesta\\" in executable:
        return "pipx"

    # Check for editable (development) installation
    try:
        dist = metadata.distribution(PACKAGE_NAME)
        # Try to read direct_url.json which indicates how the package was installed
        try:
            direct_url_text = dist.read_text("direct_url.json")
            if direct_url_text:
                direct_url = json.loads(direct_url_text)
                if direct_url.get("dir_info", {}).get("editable", False):
                    return "editable"
        except FileNotFoundError:
            pass
    except metadata.PackageNotFoundError:
        pass

    # Default to pip
    return "pip"


def get_latest_version(timeout: float = 5.0) -> str | None:
    """Query PyPI for the latest siesta version.

    Parameters
    ----------
    timeout : float, optional
        Timeout for the HTTP request in seconds, by default 5.0.

    Returns
    -------
    str | None
        The latest version string, or ``None`` if the query failed.
    """
    try:
        with urlopen(PYPI_URL, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("info", {}).get("version")
    except (URLError, json.JSONDecodeError, TimeoutError) as e:
        logger.warning(f"Failed to fetch latest version from PyPI: {e}")
        return None


def compare_versions(current: str, latest: str) -> int:
    """Compare two version strings.

    Parameters
    ----------
    current : str
        The current version string.
    latest : str
        The latest version string.

    Returns
    -------
    int
        - ``-1`` if current < latest (update available)
        - ``0`` if current == latest (up to date)
        - ``1`` if current > latest (ahead, e.g., dev version)
    """
    current_v = Version(current)
    latest_v = Version(latest)

    if current_v < latest_v:
        return -1
    elif current_v > latest_v:
        return 1
    return 0


def get_update_command(method: str) -> list[str]:
    """Get the update command for the given installation method.

    Parameters
    ----------
    method : str
        The installation method (``"uv"``, ``"pipx"``, ``"pip"``, or ``"editable"``).

    Returns
    -------
    list[str]
        The command to run as a list of arguments.

    Raises
    ------
    ValueError
        If the method is ``"editable"`` (cannot be auto-updated).
    """
    if method == "uv":
        return ["uv", "tool", "upgrade", PACKAGE_NAME]
    elif method == "pipx":
        return ["pipx", "upgrade", PACKAGE_NAME]
    elif method == "pip":
        return [sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE_NAME]
    elif method == "editable":
        raise ValueError(
            "Editable installations cannot be auto-updated. "
            "Please run 'git pull' in the source directory and reinstall."
        )
    else:
        # Unknown method, try pip
        logger.warning(f"Unknown installation method '{method}', falling back to pip.")
        return [sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE_NAME]


def update_siesta(method: str | None = None) -> bool:
    """Update siesta using the appropriate method.

    Parameters
    ----------
    method : str | None, optional
        The installation method. If ``None``, it will be auto-detected.

    Returns
    -------
    bool
        ``True`` if the update succeeded, ``False`` otherwise.

    Raises
    ------
    ValueError
        If the installation method is ``"editable"``.
    """
    if method is None:
        method = get_installation_method()

    cmd = get_update_command(method)
    logger.info(f"Running: [r]{' '.join(cmd)}[/r]")

    result = run_command(cmd, check=False)
    if result is False or result.returncode != 0:
        if result and result.stderr:
            logger.error(result.stderr)
        return False

    return True
