# Copyright 2025 Entalpic
"""Utility functions related to GitHub."""

import re
from pathlib import Path

from github import Github, UnknownObjectException
from github.Auth import Token
from github.Repository import Repository
from keyring import get_password

from siesta.utils.common import logger, resolve_path


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
