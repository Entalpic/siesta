# Copyright 2025 Entalpic
"""Utility functions for the ``siesta docs`` subcommand."""

import json
import re
from filecmp import cmp as compare_files
from os.path import relpath
from pathlib import Path
from shutil import copy2, copytree
from tempfile import TemporaryDirectory

from watchdog.events import FileSystemEvent, RegexMatchingEventHandler

from siesta.utils.common import (
    get_project_name,
    get_pyver,
    load_deps,
    logger,
    resolve_path,
    run_command,
    safe_dump,
)
from siesta.utils.config import ROOT
from siesta.utils.github import fetch_github_files


def backup(path: Path) -> Path:
    """Backup a file by copying it to the same directory with a .bak extension.

    If the file already exists, it will be copied with a .bak.1, .bak.2, etc. extension.

    Parameters
    ----------
    path : Path
        The path to backup the target files to.
    overwrite : bool
        Whether to overwrite the files if they already exist.

    Returns
    -------
    Path
        The path to the backup file.
    """
    src = resolve_path(path)
    dest = src.parent / f"{src.name}.bak"
    if dest.exists():
        b = 1
        while (dest := src.parent / f"{src.name}.bak.{b}").exists():
            b += 1
    copy2(src, dest)
    return dest


def _copy_not_overwrite(src: str | Path, dest: str | Path):
    """Private function to copy a file, backing up the destination if it exists.

    To be used by :func:`copy_defaults_folder` and :func:`~shutil.copytree` to update files recursively
    without overwriting existing files.

    Inspiration: `Stackoverflow <https://stackoverflow.com/a/78638812/3867406>`_

    Parameters
    ----------
    src : str | Path
        The path to the src file.
    dest : str | Path
        The path to copy the target file to.
    """
    if Path(dest).exists() and not compare_files(src, dest, shallow=False):
        backed_up = backup(dest)
        logger.warning(f"Backing up {dest} to {backed_up}")
    copy2(src, dest)


def copy_boilerplate(
    dest: Path,
    overwrite: bool,
    branch: str = "main",
    content_path: str = "src/siesta/boilerplate",
    include_files_regex: str = ".*",
    local: bool = True,
):
    """Copy the target files to the specified path.

    By default, uses the local bundled boilerplate files. Set ``local=False`` to
    fetch from the remote GitHub repository instead.

    You can specify specific files to include using a regex pattern,
    used (approximately) as follows:

    .. code-block:: python

        with TemporaryDirectory() as tmpdir:
            keep_file = re.findall(regex, str(file.relative_to(tmpdir)))

    Parameters
    ----------
    dest : Path
        The path to copy the target files to.
    overwrite : bool
        Whether to overwrite the files if they already exist.
    branch: str
        The branch to fetch the files from, by default ``"main"``.
    content_path: str
        The directory or file to fetch from the repository
    include_files_regex: str
        A regex pattern to include only files that match the pattern with :func:`re.findall`.
    local : bool, optional
        Use the local bundled boilerplate files. Defaults to ``True``. Set to ``False``
        to fetch from the remote GitHub repository (requires a GitHub PAT).
    """
    with TemporaryDirectory() as tmpdir:
        if local:
            # use local boilerplate:
            # copy the boilerplate folder to the tmpdir
            copytree(
                ROOT / content_path.replace("src/siesta/", ""),
                Path(tmpdir),
                dirs_exist_ok=True,
            )
        else:
            fetch_github_files(branch=branch, content_path=content_path, dir=tmpdir)
        tmpdir = Path(tmpdir)
        if include_files_regex:
            for f in tmpdir.rglob("*"):
                fn = str(f.relative_to(tmpdir))
                if f.is_file() and not re.match(include_files_regex, fn):
                    f.unlink()

        dest = resolve_path(dest)

        assert dest.exists(), f"Destination folder not found: {dest}"
        copytree(
            tmpdir,
            dest,
            dirs_exist_ok=True,
            copy_function=copy2 if overwrite else _copy_not_overwrite,
        )


def write_rtd_config() -> None:
    """Write the ReadTheDocs configuration file to the current directory."""
    rtd = Path(".readthedocs.yaml")
    if rtd.exists():
        logger.warning("ReadTheDocs file already exists. Skipping.")
        return
    pyver = get_pyver()
    config = {
        "version": 2,
        "build": {
            "os": "ubuntu-22.04",
            "tools": {"python": pyver},
            "commands": [
                "asdf plugin add uv",
                "asdf install uv latest",
                "asdf global uv latest",
                "uv sync",
                "uv run sphinx-build -M html docs/source $READTHEDOCS_OUTPUT",
            ],
        },
    }

    safe_dump(config, rtd)


def update_conf_py(dest: Path, branch: str = "main", local: bool = True):
    """Update the ``conf.py`` file with the latest content from the boilerplate.

    Parameters
    ----------
    dest : Path
        The path to the ``conf.py`` file.
    branch : str, optional
        Which remote branch to get ``conf.py`` from, by default ``"main"``
    local : bool, optional
        Use the local bundled ``conf.py`` instead of fetching from the repository.
        Defaults to ``True``.
    """
    with TemporaryDirectory() as tmpdir:
        if local:
            # Copy the local bundled conf.py to the tmpdir
            local_conf = ROOT / "boilerplate" / "source" / "conf.py"
            tmpdir = Path(tmpdir)
            copy2(local_conf, tmpdir / "conf.py")
        else:
            fetch_github_files(
                branch=branch,
                content_path="src/siesta/boilerplate/source/conf.py",
                dir=tmpdir,
            )
            tmpdir = Path(tmpdir)
        src = tmpdir / "conf.py"
        dest = resolve_path(dest / "source/conf.py")
        assert dest.exists(), f"Destination file (conf.py) not found: {dest}"
        start_pattern = "# :siesta: <update>"
        end_pattern = "# :siesta: </update>"

        # load the source and destination files contents
        src_content = src.read_text()
        dest_content = dest.read_text()
        # get the content between the start and end patterns in the source file
        pattern = f"{start_pattern}(.+){end_pattern}"
        incoming = re.search(pattern, src_content, flags=re.DOTALL)
        if not incoming:
            return
        incoming = incoming.group(1)

        # replace the content between the start and end patterns in the destination file
        replacement = f"{start_pattern}{incoming}{end_pattern}"
        if re.search(pattern, dest_content, flags=re.DOTALL):
            # pattern exists, replace it
            dest_content = re.sub(pattern, replacement, dest_content, flags=re.DOTALL)
        else:
            # pattern does not exist, add it
            dest_content += f"\n{replacement}\n"

        if not dest_content.endswith("\n"):
            dest_content += "\n"

        # write the updated content to the destination file
        dest.write_text(dest_content)


def install_dependencies(uv: bool, dev: bool):
    """Install dependencies for the docs.

    Parameters
    ----------
    uv : bool
        Whether to install using ``uv`` or ``pip install``.
    dev : bool
        If using ``uv``, whether to install as dev dependencies.
    """
    cmd = ["uv", "add"] if uv else ["python", "-m", "pip", "install"]
    if dev:
        cmd.append("--dev")
    cmd.extend(load_deps()["docs"])
    # capture error and output
    output = run_command(cmd)
    if output is not False and (out := output.stdout.strip()):
        logger.print(out)


def make_empty_folders(dest: Path):
    """Make the static and build folders in the target folder.

    Parameters
    ----------
    dest : Path
        The path to make the empty folders in.
    """
    dest = resolve_path(dest)

    assert dest.exists(), f"Destination folder not found: {dest}"

    (dest / "build").mkdir(parents=True, exist_ok=True)
    (dest / "source/_static").mkdir(parents=True, exist_ok=True)
    (dest / "source/_templates").mkdir(parents=True, exist_ok=True)


def discover_packages(dest: Path, interactive: bool = False) -> str:
    """Discover packages in the current directory.

    Directories will be returned relatively to the conf.py file in the documentation
    folder as a list of strings in order to document them with autoapi.

    Parameters
    ----------
    dest : Path
        The path to the documentation folder
    interactive : bool, optional
        Whether to prompt the user. Defaults to ``False`` (use defaults).

    Returns
    -------
    str:
        The discovered packages as a JSON-dumped list of strings.
    """
    start = "."
    if (resolve_path(start) / "src").exists():
        start = "src"
    packages = [
        p for p in Path(start).iterdir() if p.is_dir() and (p / "__init__.py").exists()
    ]
    if not packages and interactive:
        user_packages = logger.prompt(
            "No packages found. Enter relative package paths separated by commas"
        )
        packages = [resolve_path(p.strip()) for p in user_packages.split(",")]
    if not packages:
        packages = [Path(".")]
    for p in packages:
        if not p.exists():
            logger.abort(f"Package not found: {p}", exit=1)

    ref = dest / "source"
    packages = [relpath(p, ref) for p in packages]

    return json.dumps([str(p) for p in packages])


def get_repo_url(interactive: bool = False) -> str:
    """Get the repository URL from the user.

    Prompts the user for the repository URL.

    Parameters
    ----------
    interactive : bool, optional
        Whether to prompt the user. Defaults to ``False`` (use defaults).

    Returns
    -------
    str
        The repository URL.
    """
    url = ""
    try:
        ssh_url = (
            run_command(["git", "config", "--get", "remote.origin.url"])
            .stdout.strip()
            .replace("https://github.com/", "")
        )
        html_url = "https://github.com/" + ssh_url.split(":")[-1].replace(".git", "")
        url = (
            logger.prompt("Repository URL", default=html_url)
            if interactive
            else html_url
        )
    except Exception:
        url = logger.prompt("Repository URL", default=url) if interactive else url
    finally:
        return url


def overwrite_docs_files(
    dest: Path, interactive: bool = False, project_name: str = None
):
    """Overwrite the conf.py file with the project name.

    Parameters
    ----------
    dest : Path
        The path to the ``conf.py`` file.
    interactive : bool, optional
        Whether to prompt the user. Defaults to ``False`` (use defaults).
    project_name : str, optional
        The project's name. If not provided, it will be prompted (in interactive mode)
        or discovered from ``pyproject.toml``.
    """
    dest = resolve_path(dest)
    # get the packages to list in autoapi_dirs
    packages = discover_packages(dest, interactive)
    # get project name from $CWD or user prompt
    project = project_name or get_project_name(interactive)
    # get repo URL from git or user prompt
    url = get_repo_url(interactive)

    # setup conf.py based on project name and packages
    conf_py = dest / "source/conf.py"
    assert conf_py.exists(), f"conf.py not found: {dest}"
    conf_text = conf_py.read_text()
    conf_text = conf_text.replace("$PROJECT_NAME", project)
    conf_text = conf_text.replace("autoapi_dirs = []", f"autoapi_dirs = {packages}")
    conf_text = conf_text.replace("$PROJECT_URL", url or " URL TO BE SET ")
    conf_py.write_text(conf_text)

    # setup autoapi index.rst based on project name and repo URL
    index_rst = dest / "source/_templates/autoapi/index.rst"
    assert index_rst.exists(), f"autoapi/index.rst not found: {dest}"
    index_text = index_rst.read_text()
    index_text = index_text.replace("$PROJECT_NAME", project)
    index_text = index_text.replace("$PROJECT_URL", url or " URL TO BE SET ")
    index_rst.write_text(index_text)


def has_python_files(path: Path = Path(".")) -> bool:
    """Check if there are any Python files in the given path or its subdirectories.

    Parameters
    ----------
    path : Path, optional
        The path to check for Python files, by default current directory.

    Returns
    -------
    bool
        True if Python files are found, False otherwise.
    """
    # Look for .py files, excluding common test directories and virtual environments
    exclude_dirs = {".venv", "venv", ".tox", ".eggs", "build", "dist"}
    for p in path.rglob("*.py"):
        # Check if any parent directory is in exclude_dirs
        if not any(x in exclude_dirs for x in p.parts):
            return True
    return False


class AutoBuildDocs(RegexMatchingEventHandler):
    """Automatically build the docs when they are changed.

    Parameters
    ----------
    regexes : list[str]
        The regexes to match against the file paths.
    build_command : list[str]
        The command to run to build the docs.
    path : str
        The path to the docs folder.
    """

    def __init__(self, regexes: list[str], build_command: list[str], path: str):
        super().__init__(regexes=regexes)
        self.build_command = build_command
        self.path = path

    def on_modified(self, event: FileSystemEvent):
        """File modified event handler.

        Runs the build command if the file is a source file that needs to be built.

        Parameters
        ----------
        event : FileSystemEvent
            The event to handle.
        """
        path = event.src_path
        suffix = Path(path).suffix
        is_autoapi_rst = "/source/" in path and "/autoapi/" in path and suffix == ".rst"
        is_docs_py = str(self.path) in path and suffix == ".py"

        dont_run = is_autoapi_rst or is_docs_py

        if not dont_run:
            logger.info(f"Building docs because {path} was modified.")
            self.build_command(self.path)
