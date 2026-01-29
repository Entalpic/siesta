# Copyright 2025 Entalpic
"""Utility functions for siesta self-management (version, update).

This module provides functionality for:

- Detecting how siesta was installed (uv tool, pipx, pip, or editable)
- Checking PyPI for the latest version
- Updating siesta using the appropriate package manager
- Background update checks with caching

Environment Variables
---------------------
SIESTA_UPDATE_CHECK_HOURS : str
    Controls how often siesta checks for updates in the background.
    Default is ``"24"`` (once per day). Set to ``"false"`` or ``"-1"``
    to disable automatic update checks entirely.
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.request import urlopen

from github import Github, GithubException
from github.Auth import Token
from packaging.version import Version
from platformdirs import user_cache_dir

from siesta.utils.common import logger, run_command
from siesta.utils.github import get_user_pat

if TYPE_CHECKING:
    from typing import TypedDict

    class CacheData(TypedDict):
        last_check: float
        latest_version: str | None


# Package name for PyPI
PACKAGE_NAME = "siesta"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"

# GitHub repo info
GITHUB_OWNER = "entalpic"
GITHUB_REPO = "siesta"

# Environment variable for update check frequency (in hours)
# Set to "false", "False", or "-1" to disable
UPDATE_CHECK_ENV_VAR = "SIESTA_UPDATE_CHECK_HOURS"
DEFAULT_UPDATE_CHECK_HOURS = 24

# Cache file location (uses platform-appropriate directory)
# - macOS: ~/Library/Caches/siesta
# - Linux: ~/.cache/siesta (or $XDG_CACHE_HOME/siesta)
# - Windows: C:\Users\<user>\AppData\Local\siesta\Cache
_CACHE_DIR = Path(user_cache_dir(PACKAGE_NAME))
_CACHE_FILE = _CACHE_DIR / "update_check.json"


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


def get_installation_source() -> str:
    """Detect the source from which siesta was installed.

    Returns
    -------
    str
        One of: ``"github"`` or ``"pypi"``.

    Notes
    -----
    Detection is based on the ``direct_url.json`` metadata:

    - If ``vcs_info`` is present with ``vcs: "git"`` → GitHub installation
    - Otherwise → PyPI installation
    """
    try:
        dist = metadata.distribution(PACKAGE_NAME)
        try:
            direct_url_text = dist.read_text("direct_url.json")
            if direct_url_text:
                direct_url = json.loads(direct_url_text)
                # Check for VCS (git) installation
                vcs_info = direct_url.get("vcs_info", {})
                if vcs_info.get("vcs") == "git":
                    return "github"
        except FileNotFoundError:
            pass
    except metadata.PackageNotFoundError:
        pass

    return "pypi"


def _get_latest_version_github(timeout: float = 5.0) -> str | None:
    """Query GitHub for the latest siesta version.

    First tries without authentication (public repo), then falls back to
    PAT authentication if rate-limited or if access is denied.

    Parameters
    ----------
    timeout : float, optional
        Timeout for the HTTP request in seconds, by default 5.0.
        Note: PyGithub uses its own timeout handling.

    Returns
    -------
    str | None
        The latest version string, or ``None`` if the query failed.
    """

    def try_get_version(g: Github) -> str | None:
        """Try to get version from releases, then tags."""
        try:
            repo = g.get_repo(f"{GITHUB_OWNER}/{GITHUB_REPO}")

            # Try releases first
            try:
                release = repo.get_latest_release()
                tag_name = release.tag_name
                return tag_name.lstrip("v") if tag_name else None
            except GithubException as e:
                # 404 means no releases, try tags
                if e.status == 404:
                    pass
                else:
                    raise

            # Fall back to tags
            tags = repo.get_tags()
            if tags.totalCount > 0:
                tag_name = tags[0].name
                return tag_name.lstrip("v") if tag_name else None

        except GithubException:
            raise

        return None

    # Try unauthenticated first (public repo)
    try:
        g = Github(timeout=int(timeout))
        result = try_get_version(g)
        if result:
            return result
    except GithubException as e:
        # 403 often means rate limited, will try with auth
        if e.status != 403:
            logger.warning(f"Failed to fetch latest version from GitHub: {e}")
            return None

    # Fall back to PAT authentication (for rate limiting)
    pat = get_user_pat()
    if pat:
        try:
            g = Github(auth=Token(pat), timeout=int(timeout))
            result = try_get_version(g)
            if result:
                return result
        except GithubException as e:
            logger.warning(f"Failed to fetch latest version from GitHub: {e}")

    return None


def _get_latest_version_pypi(timeout: float = 5.0) -> str | None:
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


def get_latest_version(timeout: float = 5.0, source: str | None = None) -> str | None:
    """Query the appropriate source for the latest siesta version.

    The source is determined by how siesta was installed:

    - If installed from GitHub (via git URL), queries GitHub releases/tags
    - If installed from PyPI, queries PyPI

    Parameters
    ----------
    timeout : float, optional
        Timeout for the HTTP request in seconds, by default 5.0.
    source : str | None, optional
        The source to query (``"github"`` or ``"pypi"``).
        If ``None``, it will be auto-detected based on installation method.

    Returns
    -------
    str | None
        The latest version string, or ``None`` if the query failed.
    """
    if source is None:
        source = get_installation_source()

    if source == "github":
        return _get_latest_version_github(timeout=timeout)
    else:
        return _get_latest_version_pypi(timeout=timeout)


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


# =============================================================================
# Background update check functionality
# =============================================================================


def _get_update_check_hours() -> float | None:
    """Get the update check frequency from environment variable.

    Returns
    -------
    float | None
        The number of hours between checks, or ``None`` if checks are disabled.
    """
    value = os.environ.get(UPDATE_CHECK_ENV_VAR, str(DEFAULT_UPDATE_CHECK_HOURS))
    value_lower = value.lower().strip()

    # Check for disabled values
    if value_lower in ("false", "-1"):
        return None

    try:
        hours = float(value)
        if hours < 0:
            return None
        return hours
    except ValueError:
        # Invalid value, use default
        return DEFAULT_UPDATE_CHECK_HOURS


def _read_cache() -> CacheData | None:
    """Read the update check cache file.

    Returns
    -------
    CacheData | None
        The cached data, or ``None`` if the cache doesn't exist or is invalid.
    """
    if not _CACHE_FILE.exists():
        return None

    try:
        with _CACHE_FILE.open() as f:
            data = json.load(f)
            # Validate structure
            if "last_check" in data:
                return data
    except (json.JSONDecodeError, OSError):
        pass

    return None


def _write_cache(latest_version: str | None) -> None:
    """Write the update check cache file.

    Parameters
    ----------
    latest_version : str | None
        The latest version found, or ``None`` if the check failed.
    """
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with _CACHE_FILE.open("w") as f:
            json.dump(
                {
                    "last_check": time.time(),
                    "latest_version": latest_version,
                },
                f,
            )
    except OSError:
        # Silently ignore cache write failures
        pass


def _should_check_for_updates() -> bool:
    """Determine if we should check for updates.

    Takes into account:
    - Environment variable settings
    - Editable installations (skip)
    - Cache freshness

    Returns
    -------
    bool
        ``True`` if we should check for updates, ``False`` otherwise.
    """
    # Check if disabled via environment variable
    check_hours = _get_update_check_hours()
    if check_hours is None:
        return False

    # Skip for editable installations
    if get_installation_method() == "editable":
        return False

    # Check cache freshness
    cache = _read_cache()
    if cache is not None:
        last_check = cache.get("last_check", 0)
        age_hours = (time.time() - last_check) / 3600
        if age_hours < check_hours:
            return False

    return True


def _check_for_updates_sync(current_version: str) -> tuple[str, str] | None:
    """Synchronously check for updates (called in background thread).

    Parameters
    ----------
    current_version : str
        The current installed version.

    Returns
    -------
    tuple[str, str] | None
        A tuple of (current_version, latest_version) if an update is available,
        or ``None`` if up to date or check failed.
    """
    latest = get_latest_version(timeout=3.0)
    _write_cache(latest)

    if latest is None:
        return None

    if compare_versions(current_version, latest) < 0:
        return (current_version, latest)

    return None


# Global executor for background checks
_executor: ThreadPoolExecutor | None = None


def start_background_update_check(current_version: str) -> Future | None:
    """Start a background check for updates.

    This function returns immediately. Use ``get_update_message()`` to get
    the result after the command has finished.

    Parameters
    ----------
    current_version : str
        The current installed version.

    Returns
    -------
    Future | None
        A Future that will contain the update info, or ``None`` if the check
        was skipped (disabled, cached, or editable install).
    """
    if not _should_check_for_updates():
        return None

    global _executor
    if _executor is None:
        # Use a single-thread executor that won't block shutdown
        _executor = ThreadPoolExecutor(max_workers=1)

    return _executor.submit(_check_for_updates_sync, current_version)


def get_update_message(future: Future | None, timeout: float = 0.5) -> str | None:
    """Get the update message from a background check.

    Parameters
    ----------
    future : Future | None
        The Future returned by ``start_background_update_check()``.
    timeout : float, optional
        Maximum time to wait for the result, by default 0.5 seconds.

    Returns
    -------
    str | None
        The update message to display, or ``None`` if no update is available
        or the check timed out/failed.
    """
    if future is None:
        return None

    try:
        result = future.result(timeout=timeout)
        if result is not None:
            current, latest = result
            return (
                f"\n[yellow]A new version of siesta is available: "
                f"[bold]{latest}[/bold] (you have {current})[/yellow]\n"
                f"[dim]Run [bold]siesta self update[/bold] to upgrade.[/dim]"
            )
    except Exception:
        # Timeout or other error - silently ignore
        pass

    return None
