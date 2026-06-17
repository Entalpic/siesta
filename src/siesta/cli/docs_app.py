# Copyright 2025 Entalpic
"""Documentation CLI commands."""

import os
import platform
import subprocess
import time
from pathlib import Path
from subprocess import CompletedProcess
from textwrap import dedent
from typing import Annotated, cast

from cyclopts import App, Parameter
from watchdog.observers import Observer

from siesta.utils import github
from siesta.utils.common import (
    logger,
    resolve_path,
    run_command,
    write_or_update_pre_commit_file,
)
from siesta.utils.config import CLI_DEFAULTS
from siesta.utils.conflicts import (
    OperationSummary,
    apply_backup,
    render_summary,
    run_mutations,
)
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
from siesta.utils.project import InitDocsMutation

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
    as_main_deps: bool | None = None,
    overwrite: bool | None = None,
    backup: bool = False,
    deps: bool | None = None,
    uv: bool | None = None,
    interactive: Annotated[bool, Parameter(name=["-i", "--interactive"])] = False,
    branch: str = "main",
    contents: str = "src/siesta/boilerplate",
    remote_assets: bool = False,
    project_name: str | None = None,
):
    """Initialize a Sphinx documentation project with Entalpic's standard configuration.

    Also called automatically by ``siesta project quickstart``.

    Scaffolds a ``docs/`` folder using the bundled boilerplate: split source/build
    layout, standard ``conf.py`` and ``index.rst`` with good defaults. Optionally
    installs recommended dependencies (run ``siesta self show-deps`` to list them).

    If you skip dependency installation, install them manually before running
    ``siesta docs build`` or ``siesta docs watch``.

    After init, update the ``$FILL_HERE`` placeholders in the generated ``conf.py``
    before building.

    Parameters
    ----------
    path : str, optional
        Path for the docs folder, by default ``./docs``.
    as_main_deps : bool | None, optional
        Install docs dependencies as main (not dev) dependencies. Unspecified: defaults
        to ``False`` in non-interactive mode; prompts when ``-i`` is active and deps
        are enabled.
    overwrite : bool | None, optional
        How to handle an existing docs folder. ``True`` = overwrite, ``False`` = skip,
        ``None`` (default) = prompt in TTY or abort in non-TTY.
    backup : bool, optional
        Back up existing docs before overwriting (applies when overwriting).
    deps : bool | None, optional
        Install recommended docs dependencies. Unspecified: defaults to ``True`` in
        non-interactive mode; prompts when ``-i`` is active.
    uv : bool | None, optional
        Use ``uv add`` to install dependencies. Unspecified: defaults to ``True`` when
        ``uv.lock`` exists (non-interactive); prompts when ``-i`` is active.
    interactive : bool, optional
        Prompt for each unspecified option before any Mutation (``-i``). When ``False``
        (default), unspecified options use CLI defaults; explicit flags always win.
    branch : str, optional
        Branch to fetch static files from when using ``--remote-assets``.
    contents : str, optional
        Path to static files in the repository when using ``--remote-assets``.
    remote_assets : bool, optional
        Fetch boilerplate docs assets from the remote GitHub repository instead of
        using the local bundled files. Requires a GitHub Personal Access Token (PAT).
        Run ``siesta self set-github-pat`` to configure one.
    project_name : str, optional
        The project's name. If not provided, it will be prompted.

    Raises
    ------
    SystemExit
        If the path already exists and ``overwrite`` is unset in a non-TTY
        environment, or if the user selects Abort during Conflict Resolution.
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
    resolved_path = resolve_path(path)
    logger.info(f"Initializing docs at path: [r]{resolved_path}[/r]")

    # Prompt collection phase: resolve all feature decisions before any Mutation.
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

    # Execution phase: the docs-folder Conflict is detected, resolved, and applied
    # through the unified mutation driver — exactly like the other write commands.
    summary = run_mutations(
        [
            InitDocsMutation(
                path,
                bool(as_main_deps),
                deps,
                with_uv,
                interactive,
                branch,
                contents,
                remote_assets,
                project_name,
            )
        ],
        overwrite=overwrite,
        backup=backup,
    )
    render_summary(summary)


def _execute_docs_init(
    *,
    path: str,
    as_main_deps: bool,
    deps: bool,
    with_uv: bool,
    interactive: bool,
    branch: str,
    contents: str,
    remote_assets: bool,
    project_name: str | None,
) -> None:
    """Scaffold the docs folder for :class:`~siesta.utils.project.InitDocsMutation`.

    Runs only after the docs-folder Conflict has been resolved and applied by
    ``run_mutations``; it owns no conflict handling and assumes the destination is
    ready to be written.

    Parameters
    ----------
    path : str
        Path for the docs folder.
    as_main_deps : bool
        Install docs dependencies as main (not dev) dependencies.
    deps : bool
        Install recommended docs dependencies.
    with_uv : bool
        Use ``uv add`` to install dependencies.
    interactive : bool
        Prompt for unspecified placeholders while writing ``conf.py``.
    branch : str
        Branch to fetch static files from when using ``remote_assets``.
    contents : str
        Path to the static files in the repository when using ``remote_assets``.
    remote_assets : bool
        Fetch boilerplate docs assets from the remote GitHub repository.
    project_name : str | None
        The project's name; prompted by ``overwrite_docs_files`` when unset.
    """
    resolved_path = resolve_path(path)
    resolved_path.mkdir(parents=True, exist_ok=True)
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
        resolved_path,
        branch=branch,
        content_path=contents,
        overwrite=True,
        local=not remote_assets,
    )
    # Make empty dirs (_build and _static) in target directory
    make_empty_folders(resolved_path)
    # Update defaults from user config
    overwrite_docs_files(resolved_path, interactive, project_name)

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

    build_docs(str(resolved_path))


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
    resolved_path = resolve_path(path)
    if not resolved_path.exists():
        logger.abort(f"Path not found: {resolved_path}", exit=1)

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

    summary = OperationSummary()

    if update_static:
        static = resolved_path / "source" / "_static"
        if not static.exists():
            logger.abort(f"Static folder not found: {static}", exit=1)
        copy_boilerplate(
            dest=resolved_path,
            branch=branch,
            content_path=contents,
            overwrite=False,
            include_files_regex="_static",
            local=not remote_assets,
        )
        summary.written.append(str(static))

    if update_conf:
        conf_path = resolved_path / "source" / "conf.py"
        if conf_path.exists():
            apply_backup(conf_path)
            summary.backed_up.append(str(conf_path))
        update_conf_py(resolved_path, branch=branch, local=not remote_assets)
        summary.written.append(str(conf_path))

    if update_precommit:
        write_or_update_pre_commit_file()
        has_uv = Path("uv.lock").exists()
        if has_uv:
            run_command(["uv", "add", "--dev", "pre-commit"])
            run_command(["uv", "run", "pre-commit", "install"])
        else:
            run_command(["pre-commit", "install"])
        summary.written.append(".pre-commit-config.yaml")

    render_summary(summary)
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
    resolved_path = resolve_path(path)
    if not resolved_path.exists():
        logger.abort(f"Path not found: {resolved_path}", exit=1)
    make = resolved_path / "Makefile"
    if not make.exists():
        logger.abort(f"Makefile not found in {resolved_path}.", exit=1)
    commands = [
        ["make", "clean"],
        ["make", "html"],
    ]
    with_uv = Path("uv.lock").exists()
    if with_uv:
        commands = [["uv", "run"] + command for command in commands]
    for c, command in enumerate(commands):
        with logger.loading(f"Running {' '.join(command)}..."):
            result = run_command(command, cwd=str(resolved_path), check=False)
        if result is False:
            logger.abort("Failed to build the docs.")
        result = cast(CompletedProcess[str], result)
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
    docs_path = (resolved_path / "build/html/index.html").relative_to(Path.cwd())
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
    pattern_list = [p.strip() for p in patterns.split(";")]

    # Watch for changes
    abd = AutoBuildDocs(pattern_list, build_docs, path=path)
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
    resolved_path = resolve_path(path)
    index = resolved_path / "build/html/index.html"
    if not index.exists():
        logger.abort(f"Index file not found: {index}", exit=1)

    logger.info(f"Opening {index} in the default browser.")
    if platform.system() == "Darwin":  # macOS
        subprocess.call(("open", str(index)))
    elif platform.system() == "Windows":  # Windows
        startfile = getattr(os, "startfile", None)
        if callable(startfile):
            startfile(str(index))
        else:
            logger.abort("Opening docs is not supported on this platform.", exit=1)
    else:  # Linux variants
        subprocess.call(("xdg-open", str(index)))
