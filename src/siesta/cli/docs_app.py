# Copyright 2025 Entalpic
"""Documentation CLI commands."""

import os
import platform
import subprocess
import time
from pathlib import Path
from shutil import rmtree
from textwrap import dedent
from typing import Annotated

from cyclopts import App, Parameter
from watchdog.observers import Observer

from siesta.utils.common import (
    logger,
    resolve_path,
    run_command,
    write_or_update_pre_commit_file,
)
from siesta.utils.config import CLI_DEFAULTS
from siesta.utils.docs import (
    AutoBuildDocs,
    copy_boilerplate,
    has_python_files,
    install_dependencies,
    make_empty_folders,
    overwrite_docs_files,
    update_conf_py,
    write_rtd_config,
)
from siesta.utils import github

docs_app = App(
    name="docs",
    help=dedent(
        """
        Initialize, build and watch a Sphinx documentation project with standard Entalpic config.

        Upgrade with ``$ siesta self update``.

        See Usage instructions in the online docs: https://entalpic-siesta.readthedocs-hosted.com/en/latest/autoapi/siesta.

        """.strip(),
    ),
)
""":py:class:`cyclopts.App`: The app for the ``siesta docs`` sub-command."""


@docs_app.command(name="init")
def init_docs(
    path: str = "./docs",
    as_main_deps: bool = None,
    overwrite: bool = False,
    deps: bool = None,
    uv: bool = None,
    interactive: Annotated[bool, Parameter(name=["-i", "--interactive"])] = False,
    branch: str = "main",
    contents: str = "src/siesta/boilerplate",
    remote_assets: bool = False,
    project_name: str = None,
):
    """Initialize a Sphinx documentation project with Entalpic's standard configuration (also called within ``siesta project quickstart``).

    In particular:

    - Initializes a new Sphinx project at the specified path.

    - Optionally installs recommended dependencies (run ``siesta self show-deps`` to see
      them).

    - Uses the split source / build folder structure.

    - Includes standard `conf.py` and `index.rst` files with good defaults.

    .. warning::

        If you don't install the dependencies here, you will need to install them
        manually.

    .. important::

        Update the placeholders (``$FILL_HERE``) in the generated files with the
        appropriate values before you build the documentation.

    .. tip::

        Build the local HTML docs by running ``$ siesta docs build`` or ``$ siesta docs watch``.

    Parameters
    ----------
    path : str, optional
        Where to store the docs.
    as_main_deps : bool, optional
        Whether docs dependencies should be included in the main or dev dependencies.
    overwrite : bool, optional
        Whether to overwrite existing docs (if any).
    deps : bool, optional
        Prevent dependencies prompt by forcing its value to ``True`` or ``False``.
    uv : bool, optional
        Prevent uv prompt by forcing its value to ``True`` or ``False``.
    interactive : bool, optional
        Enable interactive mode with prompts for all options (``-i``). By default,
        sensible defaults are used. User-specified flags always take precedence.
    branch : str, optional
        The branch to fetch the static files from.
    contents : str, optional
        The path to the static files in the repository.
    remote_assets : bool, optional
        Fetch boilerplate docs assets from the remote GitHub repository instead of
        using the local bundled files. Requires a GitHub Personal Access Token (PAT).
        Run ``$ siesta self set-github-pat`` to configure one.
    project_name : str, optional
        The project's name. If not provided, it will be prompted.
    Raises
    ------
    sys.exit(1)
        If the path already exists and ``--overwrite`` is not provided.
    """
    # Check for Python files before proceeding
    if not has_python_files():
        logger.abort(
            "No Python files found in project. Documentation requires Python files to document.",
            exit=1,
        )

    # Check for GitHub Personal Access Token (only needed for remote assets)
    if remote_assets:
        pat = github.get_user_pat()
        if not pat:
            logger.warning(
                "You need to set a GitHub Personal Access Token"
                + " to fetch the latest static files."
            )
            logger.warning(
                "Run [r]$ siesta self set-github-pat --help[/r] to learn how to."
            )
            logger.abort("Aborting.", exit=1)

    # Setting defaults: only fill in values that weren't explicitly provided
    if not interactive:
        if deps is None:
            deps = CLI_DEFAULTS["deps"]
        if as_main_deps is None:
            as_main_deps = CLI_DEFAULTS["as_main_deps"]

    # Where the docs will be stored, typically `$CWD/docs`
    path = resolve_path(path)
    logger.info(f"Initializing docs at path: [r]{path}[/r]")
    if path.exists():
        # docs folder already exists
        if not overwrite:
            # user doesn't want to overwrite -> abort
            logger.warning(f"Path already exists: {path}")
            logger.warning("Use --overwrite to overwrite.")
            logger.abort("Aborting.", exit=1)

    # Prompt collection phase: gather decisions before any mutation.
    if deps is None:
        deps = logger.confirm("Would you like to install recommended dependencies?")

    with_uv = False
    if deps:
        # Check if uv.lock exists in order to decide whether to use uv or not
        if resolve_path("./uv.lock").exists():
            if uv is not None:
                with_uv = uv
            elif not interactive:  # if not interactive, assume uv since uv.lock exists
                with_uv = True
            else:
                with_uv = logger.confirm(
                    "It looks like you are using uv. Use `uv add` to add dependencies?"
                )
        else:
            if uv:
                logger.warning(
                    "uv.lock not found. Skipping uv dependencies, installing with pip."
                )

    # Execution phase: perform mutations only after all decisions are collected.
    if path.exists():
        logger.warning("🚧 Overwriting path.")
        rmtree(path)

    path.mkdir(parents=True)
    logger.success("Docs initialized 📄")

    # Install dependencies if requested.
    if deps:
        logger.info(f"Installing docs dependencies{' with uv.' if with_uv else '.'}..")
        # Execute the command to install dependencies
        install_dependencies(with_uv, with_uv and not as_main_deps)
        logger.info("Docs dependencies installed.")
    else:
        logger.warning("Skipping dependency installation.")

    # Download and copy siesta pre-filled folder structure to the target directory
    copy_boilerplate(
        path,
        branch=branch,
        content_path=contents,
        overwrite=True,
        local=not remote_assets,
    )
    # Make empty dirs (_build and _static) in target directory
    make_empty_folders(path)
    # Update defaults from user config
    overwrite_docs_files(path, interactive, project_name)

    # Check if the ReadTheDocs YAML config exists
    has_rtd = Path(".readthedocs.yaml").exists()
    if not has_rtd:
        write_rtd_config()
        logger.info("ReadTheDocs config written.")
    else:
        logger.info("ReadTheDocs config already exists.")

    logger.info(
        "Now go to your newly created docs folder and update placeholders in"
        + " [r]conf.py[/r] with the appropriate values.",
    )

    build_docs(path)


@docs_app.command(name="update")
def update(
    path: str = "./docs",
    branch: str = "main",
    contents: str = "src/siesta/boilerplate",
    remote_assets: bool = False,
):
    """
    Update the static files in the docs folder like CSS, JS and images.

    By default, uses the local bundled boilerplate files. Use ``--remote-assets`` to
    fetch the latest version from the remote GitHub repository (requires a GitHub PAT;
    run ``$ siesta self set-github-pat`` to configure one).

    .. note::

        Existing files will be backed up to ``{filename}.bak`` before new files are
        copied.

    Parameters
    ----------
    path : str, optional
        The path to your documentation folder.
    branch : str, optional
        The branch to fetch the static files from.
    contents : str, optional
        The path to the static files in the repository.
    remote_assets : bool, optional
        Fetch boilerplate docs assets from the remote GitHub repository instead of
        using the local bundled files. Requires a GitHub Personal Access Token (PAT).
        Run ``$ siesta self set-github-pat`` to configure one.
    """
    # Check if the path exists
    path = resolve_path(path)
    if not path.exists():
        logger.abort(f"Path not found: {path}", exit=1)

    # Prompt collection phase: gather all confirmations up front.
    update_static = logger.confirm(
        "Overwrite the documentation's HTML static files. Continue?"
    )
    update_conf = logger.confirm("Would you like to update the conf.py file?")
    update_precommit = logger.confirm("Would you like to update the pre-commit hooks?")

    if not any([update_static, update_conf, update_precommit]):
        logger.info("No updates selected. Nothing to do.")
        logger.success("Done.")
        return

    # Execution phase: run only the selected mutating actions.
    if update_static:
        static = path / "source" / "_static"
        if not static.exists():
            logger.abort(f"Static folder not found: {static}", exit=1)
        copy_boilerplate(
            dest=path,
            branch=branch,
            content_path=contents,
            overwrite=False,
            include_files_regex="_static",
            local=not remote_assets,
        )
        logger.success("Static files updated.")

    if update_conf:
        update_conf_py(path, branch=branch, local=not remote_assets)
        logger.success("[r]conf.py[/r] updated.")

    if update_precommit:
        write_or_update_pre_commit_file()
        has_uv = Path("uv.lock").exists()
        if has_uv:
            run_command(["uv", "add", "--dev", "pre-commit"])
            run_command(["uv", "run", "pre-commit", "install"])
        else:
            run_command(["pre-commit", "install"])
        logger.success("Pre-commit hooks updated.")
    logger.success("Done.")


@docs_app.command(name="build")
def build_docs(path: str = "./docs"):
    """Build your docs.

    Equivalent to running ``$ cd docs && make clean && make html``.

    Parameters
    ----------
    path : str, optional
        The path to your documentation folder.
    """
    path = resolve_path(path)
    if not path.exists():
        logger.abort(f"Path not found: {path}", exit=1)
    make = path / "Makefile"
    if not make.exists():
        logger.abort(f"Makefile not found in {path}.", exit=1)
    commands = [
        ["make", "clean"],
        ["make", "html"],
    ]
    with_uv = Path("uv.lock").exists()
    if with_uv:
        commands = [["uv", "run"] + command for command in commands]
    for c, command in enumerate(commands):
        with logger.loading(f"Running {' '.join(command)}..."):
            result = run_command(command, cwd=str(path), check=False)
        if result.returncode != 0:
            logger.error(result.stderr, title="Build Error", as_panel=True)
            logger.abort("Failed to build the docs.")

        if c == 0:
            continue

        logger.info(result.stdout, title="Build Output", as_panel=True)
        if result.stderr:
            logger.warning(
                result.stderr,
                title=f"Warnings executing [r]{' '.join(command)}[/r]",
                as_panel=True,
            )
    logger.info(
        "Ask Victor if you want to automatically build and deploy the docs to ReadTheDocs."
    )
    docs_path = (path / "build/html/index.html").relative_to(Path.cwd())
    logger.info(f"Local docs built in {docs_path}")
    logger.success("Open locally with [r]siesta docs open[/r]")


@docs_app.command(name="watch")
def watch_docs(
    path: str = "./docs", patterns: str = r".+/src/.+\.py;.+/source/.+\.rst"
):
    """Automatically build the docs when source files matching the given patterns are changed.

    Files must be accessible down the directory you run the command from.

    Files in the ``/autoapi/`` folder are not watched so that the intermediate
    files generated by AutoAPI do not trigger a continuous rebuild.

    Parameters
    ----------
    path : str, optional
        The path to your documentation folder.
    patterns : str, optional
        The patterns to watch for changes, separated by ``;``.
    """
    # Build the docs
    build_docs(path)

    # Patterns to watch
    patterns = [p.strip() for p in patterns.split(";")]

    # Watch for changes
    abd = AutoBuildDocs(patterns, build_docs, path=path)
    observer = Observer()
    observer.schedule(abd, path=".", recursive=True)
    observer.start()
    here = Path().resolve()
    logger.info(f"Watching {here}. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
    logger.print()
    logger.warning("Watching stopped. Bye bye 👋")


@docs_app.command(name="open")
def open_docs(path: str = "./docs"):
    """Open the locally-built docs in the default browser.

    Parameters
    ----------
    path : str, optional
        The path to your documentation folder.
    """
    path = resolve_path(path)
    index = path / "build/html/index.html"
    if not index.exists():
        logger.abort(f"Index file not found: {index}", exit=1)

    logger.info(f"Opening {index} in the default browser.")
    if platform.system() == "Darwin":  # macOS
        subprocess.call(("open", str(index)))
    elif platform.system() == "Windows":  # Windows
        os.startfile(str(index))
    else:  # Linux variants
        subprocess.call(("xdg-open", str(index)))
