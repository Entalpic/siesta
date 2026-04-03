# Copyright 2025 Entalpic
"""Utility functions related to GitHub."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from github import (
    BadCredentialsException,
    Github,
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)
from github.Auth import Token
from github.Repository import Repository
from keyring import get_password

from siesta.utils.common import logger, resolve_path
from siesta.utils.config import GITHUB_OWNER, GITHUB_REPO


class CommitInfo(TypedDict):
    hash: str
    author: str
    time: datetime


def get_user_pat():
    """Get the GitHub Personal Access Token (PAT) from the user.

    Returns
    -------
    str
        The GitHub Personal Access Token (PAT).
    """
    return get_password("siesta", "github_pat")


def search_contents(
    repo: Repository, branch: str = "main", content_path: str = "boilerplate"
) -> list[tuple[str, str]]:
    """Get the (deep) contents of a directory.

    Parameters
    ----------
    repo : Repository
        The repository to get the contents from.
    content_path : str
        The path to the directory to get the contents of (with respect to the repository root).
    branch : str, optional
        The branch to fetch the files from, by default ``"main"``.

    Returns
    -------
    list[tuple[str, bytes]]
        The list of tuples containing the file path and content as
        ``(path, bytes content)``.

    """
    contents = repo.get_contents(content_path, ref=branch)
    if not isinstance(contents, list):
        contents = [contents]

    # If we don't adjust the content path, fetching a folder will include the full content
    # path and the files will be copied to the wrong location:
    # eg: if we fetch boilerplate/ and the content is boilerplate/docs/source/conf.py
    #     the file will be copied to "boilerplate/docs/source/conf.py" instead of
    #     "docs/source/conf.py"
    # so we'll remove the hierarchy of the folder from the path
    # trying to download a file
    extra_path = content_path
    if re.match(r".+\.\w+", extra_path.split("/")[-1]):
        # we'll just keep the file name
        extra_path = "/".join(extra_path.split("/")[:-1])
    else:
        # trying to download a folder
        if not extra_path.endswith("/"):
            # we'll remove the hierarchy of the folder from the path
            extra_path = extra_path + "/"

    data = []
    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path, ref=branch))
        else:
            logger.clear_line()
            logger.info(f"Downloading contents of '{file_content.path}'", end="\r")
            # adjust file path
            new_relative_path = file_content.path.replace(extra_path, "")
            if new_relative_path.startswith("/"):
                new_relative_path = new_relative_path[1:]
            data.append(
                (
                    new_relative_path,
                    file_content.decoded_content,
                )
            )
    logger.clear_line()
    logger.info(f"Downloaded contents of '{repo.html_url}/{content_path}'")
    return data


def fetch_github_files(
    branch: str = "main",
    content_path: str = "src/siesta/boilerplate",
    dir: str = ".",
) -> Path:
    """Download a file or directory from a GitHub repository and write it to ``dir``.

    Parameters
    ----------
    branch : str, optional
        The branch to fetch the files from, by default ``"main"``.
    content_path : str
        The directory or file to fetch from the repository
    dir : str, optional
        The directory to save the files to, by default ``"."``.

    Returns
    -------
    Path
        The path to the temporary folder containing the files.
    """
    pat = get_user_pat()
    if not pat:
        logger.abort(
            "GitHub Personal Access Token (PAT) not found. Run 'siesta self set-github-pat' to set it.",
            exit=1,
        )
    auth = Token(pat)
    g = Github(auth=auth)
    repo = g.get_repo("entalpic/siesta")
    try:
        contents = search_contents(repo, branch=branch, content_path=content_path)
    except UnknownObjectException:
        branches = repo.get_branches()
        has_branch = any(b.name == branch for b in branches)
        if not has_branch:
            logger.abort(f"Branch not found: {branch}", exit=1)
        else:
            logger.abort(
                f"Could not find repository contents: {content_path} on branch {branch}",
                exit=1,
            )

    base_dir = resolve_path(dir)
    for name, content in contents:
        path = Path(base_dir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def format_github_access_error(exc: BaseException) -> str:
    """Summarize a PyGithub or transport error for user-facing messages.

    Parameters
    ----------
    exc : BaseException
        The exception raised when calling the GitHub API.

    Returns
    -------
    str
        A short, human-readable description.
    """
    if isinstance(exc, BadCredentialsException):
        return (
            "GitHub rejected the token (invalid or expired). "
            "Run `siesta self set-github-pat` with a valid PAT."
        )
    if isinstance(exc, RateLimitExceededException):
        return "GitHub API rate limit exceeded. Try again later or set a PAT."
    if isinstance(exc, GithubException):
        data = exc.data if isinstance(exc.data, dict) else {}
        msg = data.get("message") or str(exc)
        return f"GitHub API {exc.status}: {msg}"
    return str(exc) or type(exc).__name__


def _get_github_client(timeout: float = 5.0) -> Github:
    """Get a GitHub client, trying unauthenticated first then falling back to PAT.

    Parameters
    ----------
    timeout : float, optional
        Timeout for GitHub API requests in seconds, by default 5.0.

    Returns
    -------
    Github
        A PyGithub client instance.
    """
    pat = get_user_pat()
    if pat:
        return Github(auth=Token(pat), timeout=int(timeout))
    return Github(timeout=int(timeout))


def _get_latest_version_github(timeout: float = 5.0) -> tuple[str | None, str | None]:
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
    tuple[str | None, str | None]
        ``(version, None)`` on success, ``(None, None)`` if no release/tag was found,
        or ``(None, err)`` on failure.
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

    unauth_forbidden: GithubException | None = None

    # Try unauthenticated first (public repo)
    try:
        g = Github(timeout=int(timeout))
        result = try_get_version(g)
        if result:
            return (result, None)
    except GithubException as e:
        # 403 often means rate limited, will try with auth
        if e.status == 403:
            unauth_forbidden = e
        else:
            logger.warning(f"Failed to fetch latest version from GitHub: {e}")
            return (None, format_github_access_error(e))

    # Fall back to PAT authentication (for rate limiting)
    pat = get_user_pat()
    if pat:
        try:
            g = Github(auth=Token(pat), timeout=int(timeout))
            result = try_get_version(g)
            if result:
                return (result, None)
        except GithubException as e:
            logger.warning(f"Failed to fetch latest version from GitHub: {e}")
            return (None, format_github_access_error(e))
    elif unauth_forbidden is not None:
        return (None, format_github_access_error(unauth_forbidden))

    return (None, None)


def get_latest_github_release_version(
    timeout: float = 5.0,
) -> tuple[str | None, str | None]:
    """Get the latest release version from GitHub.

    Parameters
    ----------
    timeout : float, optional
        Timeout for the HTTP request in seconds, by default 5.0.

    Returns
    -------
    tuple[str | None, str | None]
        ``(version, None)`` on success, ``(None, None)`` if no release or tag was found,
        or ``(None, error_message)`` if the query failed.
    """
    return _get_latest_version_github(timeout=timeout)


def get_latest_commit_info(
    timeout: float = 5.0, branch: str = "main"
) -> tuple[CommitInfo | None, str | None]:
    """Get info about the latest commit on a branch from GitHub.

    Parameters
    ----------
    timeout : float, optional
        Timeout for the HTTP request in seconds, by default 5.0.
    branch : str, optional
        The branch to get the latest commit from, by default ``"main"``.

    Returns
    -------
    tuple[CommitInfo | None, str | None]
        ``(info, None)`` on success, ``(None, None)`` if the branch has no commits,
        or ``(None, error_message)`` if the query failed.
    """
    try:
        g = _get_github_client(timeout=timeout)
        repo = g.get_repo(f"{GITHUB_OWNER}/{GITHUB_REPO}")
        commits = repo.get_commits(sha=branch)
        commit = commits[0]
        return (
            {
                "hash": commit.sha[:7],
                "author": commit.commit.author.name,
                "time": commit.commit.author.date,
            },
            None,
        )
    except GithubException as e:
        return (None, format_github_access_error(e))
    except IndexError:
        return (None, None)
    except Exception as e:
        return (None, format_github_access_error(e))
