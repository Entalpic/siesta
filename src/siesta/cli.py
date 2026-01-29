# Copyright 2025 Entalpic
"""
Source code for the ``siesta`` Command-Line Interface (CLI).

Learn how to use with:

.. code-block:: bash

    # Top-level commands, add --help to any of them
    # to understand what they do and their options their options.

    $ siesta # shows help

    $ siesta docs # shows help
    $ siesta docs init
    $ siesta docs open
    $ siesta docs build
    $ siesta docs update
    $ siesta docs watch

    $ siesta project # shows help
    $ siesta project quickstart
    $ siesta project tree

    $ siesta self # shows help
    $ siesta self version
    $ siesta self update  # or: siesta self upgrade

    $ siesta set-github-pat
    $ siesta show-deps

You can also refer to the :ref:`siesta-cli-tutorial` for more information.
"""

import getpass
import os
import platform
import subprocess
import time
from importlib import metadata
from pathlib import Path
from shutil import get_terminal_size, rmtree
from textwrap import dedent
from typing import Optional

from cyclopts import App
from gitignore_parser import parse_gitignore
from watchdog.observers import Observer

from siesta.utils.common import (
    get_project_name,
    load_deps,
    logger,
    resolve_path,
    run_command,
    write_or_update_pre_commit_file,
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
from siesta.utils.github import get_user_pat
from siesta.utils.project import (
    add_ipdb_as_debugger,
    write_gitignore,
    write_test_actions_config,
    write_tests_infra,
)
from siesta.utils.self import (
    compare_versions,
    get_installation_method,
    get_latest_version,
    get_update_command,
    get_update_message,
    start_background_update_check,
    update_siesta,
)
from siesta.utils.tree import make_labeled_tree

# Main app
app = App(
    help=dedent(
        f"""
    Siesta Is Entalpic'S Terminal Assistant ({metadata.version("siesta")})
    
    A set of CLI tools to help you with good practices in Python development at Entalpic.

    Upgrade with ``$ uv tool upgrade siesta``.

    See Usage instructions in the online docs: https://entalpic-siesta.readthedocs-hosted.com/en/latest/autoapi/siesta/.
    """.strip()
    ),
)
""":py:class:`cyclopts.App`: The main CLI application."""

docs_app = App(
    name="docs",
    help=dedent(
        """
        Initialize, build and watch a Sphinx documentation project with standard Entalpic config.

        Upgrade with ``$ uv tool upgrade siesta``.

        See Usage instructions in the online docs: https://entalpic-siesta.readthedocs-hosted.com/en/latest/autoapi/siesta.

        """.strip(),
    ),
)
""":py:class:`cyclopts.App`: The app for the ``siesta docs`` sub-command."""

project_app = App(
    name="project",
    help=dedent(
        """
        Initialize a Python project with standard Entalpic config.

        Upgrade with ``$ uv tool upgrade siesta``.

        See Usage instructions in the online docs: https://entalpic-siesta.readthedocs-hosted.com/en/latest/autoapi/siesta.

        """.strip(),
    ),
)
""":py:class:`cyclopts.App`: The app for the ``siesta project`` sub-command."""

self_app = App(
    name="self",
    help=dedent(
        """
        Manage siesta itself: check version, update to the latest release.

        """.strip(),
    ),
)
""":py:class:`cyclopts.App`: The app for the ``siesta self`` sub-command."""

app.command(docs_app)
app.command(project_app)
app.command(self_app)


def main():
    """Run the CLI, gracefully handling ``KeyboardInterrupt``."""
    # Start background update check (non-blocking)
    update_future = start_background_update_check(metadata.version("siesta"))

    try:
        app()
    except KeyboardInterrupt:
        logger.abort("\nAborted.", exit=1)
    finally:
        # Show update message at the end (if available)
        update_msg = get_update_message(update_future)
        if update_msg:
            logger.print(update_msg)


@app.command(name="set-github-pat")
def set_github_pat(pat: Optional[str] = ""):
    """
    Store a GitHub Personal Access Token (PAT) in your keyring.

    A Github PAT is required to fetch the latest version of the documentation's static
    files etc. from the repository.

    `About GitHub PAT <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#about-personal-access-tokens>`_

    `Creating Github a PAT <https://github.com/settings/personal-access-tokens>`_


    1. Go to ``Settings > Developer settings > Personal access tokens (fine-grained) >
       Generate new token``.
    2. Name it ``siesta``.
    3. Set ``Entalpic`` as resource owner
    4. Expire it in 1 year.
    5. Only select the ``siesta`` repository
    6. Set *Repository Permissions* to *Contents: Read* and *Metadata: Read*.
    7. Click on *Generate token*.


    Parameters
    ----------
    pat : str, optional
        The GitHub Personal Access Token.
    """
    from keyring import set_password

    assert isinstance(pat, str), "PAT must be a string."

    logger.warning(
        "Run [r]$ siesta set-github-pat --help[/r]"
        + " if you're not sure how to generate a PAT."
    )
    if not pat:
        pat = getpass.getpass("Enter your GitHub PAT (hidden): ")
    logger.confirm(
        f"Are you sure you want to set the GitHub PAT to {pat[:5]}...{pat[-5:]}?"
    )
    set_password("siesta", "github_pat", pat)
    logger.success("GitHub PAT set. You can now use `siesta docs init`.")


@app.command(name="show-deps")
def show_deps(as_pip: bool = False):
    """Show the recommended dependencies for the documentation that would be installed with `siesta docs init`.

    Parameters
    ----------
    as_pip : bool, optional
        Show as pip install command.
    """
    deps = load_deps()
    if as_pip:
        logger.print(" ".join([d for k in deps for d in deps[k]]))
    else:
        logger.print("Dependencies:")
        for scope in deps:
            logger.print("  • " + scope + ": " + " ".join(deps[scope]))


@docs_app.command(name="init")
def init_docs(
    path: str = "./docs",
    as_main_deps: bool = None,
    overwrite: bool = False,
    deps: bool = None,
    uv: bool = None,
    with_defaults: bool = True,
    branch: str = "main",
    contents: str = "src/siesta/boilerplate",
    local: bool = False,
    project_name: str = None,
):
    """Initialize a Sphinx documentation project with Entalpic's standard configuration (also called within ``siesta project quickstart``).

    In particular:

    - Initializes a new Sphinx project at the specified path.

    - Optionally installs recommended dependencies (run `siesta show-deps` to see
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
    with_defaults: bool, optional
        Whether to trust the defaults and skip all prompts.
    branch : str, optional
        The branch to fetch the static files from.
    contents : str, optional
        The path to the static files in the repository.
    local : bool, optional
        Use local boilerplate docs assets instead of fetching from the repository.
        May update to outdated contents so avoid using this option.
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

    # Check for GitHub Personal Access Token
    pat = get_user_pat()
    if not pat and not local:
        logger.warning(
            "You need to set a GitHub Personal Access Token"
            + " to fetch the latest static files."
        )
        logger.warning("Run [r]$ siesta set-github-pat --help[/r] to learn how to.")
        logger.abort("Aborting.", exit=1)

    # Setting defaults
    if with_defaults:
        if deps is not None:
            logger.warning(
                "Ignoring deps argument because you are using --with-defaults."
            )
        deps = True
        if as_main_deps is not None:
            logger.warning(
                "Ignoring as_main_deps argument because you are using --with-defaults."
            )
        as_main_deps = False

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
        # user wants to overwrite -> remove the folder and warn
        logger.warning("🚧 Overwriting path.")
        rmtree(path)

    # Create the docs folder
    path.mkdir(parents=True)
    logger.success("Docs initialized 📄")

    # Whether to install dependencies
    should_install = deps is not None or logger.confirm(
        "Would you like to install recommended dependencies?"
    )
    with_uv = False
    if should_install:
        # Check if uv.lock exists in order to decide whether to use uv or not
        if resolve_path("./uv.lock").exists():
            with_uv = (
                uv
                or with_defaults  # if using defaults, assume uv since uv.lock exists
                or logger.confirm(
                    "It looks like you are using uv. Use `uv add` to add dependencies?"
                )
            )
        else:
            if uv:
                logger.warning(
                    "uv.lock not found. Skipping uv dependencies, installing with pip."
                )
        logger.info(f"Installing docs dependencies{' with uv.' if with_uv else '.'}..")
        # Execute the command to install dependencies
        install_dependencies(with_uv, with_uv and not as_main_deps)
        logger.info("Docs dependencies installed.")
    else:
        logger.warning("Skipping dependency installation.")

    # Download and copy siesta pre-filled folder structure to the target directory
    copy_boilerplate(
        path, branch=branch, content_path=contents, overwrite=True, local=local
    )
    # Make empty dirs (_build and _static) in target directory
    make_empty_folders(path)
    # Update defaults from user config
    overwrite_docs_files(path, with_defaults, project_name)

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
    local: bool = False,
):
    """
    Update the static files in the docs folder like CSS, JS and images.

    Basically will download the remote repository's static files into a local temporary
    folder, then will copy them in your docs ``source/_static`` folder.

    .. important::

        ``$ siesta update`` requires a GitHub Personal Access Token (PAT) to fetch
        the latest version of the documentation's static files etc. from the repository.
        Run ``$ siesta set-github-pat`` to do so.

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
    local : bool, optional
        Use local boilerplate docs assets instead of fetching from the repository.
        May update to outdated contents so avoid using this option.
    """
    # Check if the path exists
    path = resolve_path(path)
    if not path.exists():
        logger.abort(f"Path not found: {path}", exit=1)

    # Confirm to overwrite the documentation's HTML static files
    if logger.confirm("Overwrite the documentation's HTML static files. Continue?"):
        static = path / "source" / "_static"
        if not static.exists():
            logger.abort(f"Static folder not found: {static}", exit=1)
        copy_boilerplate(
            dest=path,
            branch=branch,
            content_path=contents,
            overwrite=False,
            include_files_regex="_static",
            local=local,
        )
        logger.success("Static files updated.")

    # Update the conf.py file
    if logger.confirm("Would you like to update the conf.py file?"):
        update_conf_py(path, branch=branch)
        logger.success("[r]conf.py[/r] updated.")

    # Update the pre-commit hooks
    if logger.confirm("Would you like to update the pre-commit hooks?"):
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


@project_app.command(name="quickstart")
def quickstart_project(
    as_app: bool = False,
    as_pkg: bool = False,
    precommit: bool | None = None,
    docs: bool | None = None,
    deps: bool | None = None,
    docs_path: str = "./docs",
    as_main_deps: bool | None = None,
    overwrite: bool = False,
    with_defaults: bool = True,
    branch: str = "main",
    contents: str = "src/siesta/boilerplate",
    local: bool = False,
    ipdb: bool | None = None,
    tests: bool | None = None,
    actions: bool | None = None,
    gitignore: bool | None = None,
):
    """Start a ``uv``-based Python project from scratch, with initial project structure and docs.

    Overall:

    * Initializes a new ``uv`` project with ``$ uv init``.
    * Installs recommended dependencies with ``$ uv add --dev [...]``.
    * Initializes a new Sphinx project at the specified path as per ``$ siesta
      docs init``.
    * Initializes pre-commit hooks with ``$ uv run pre-commit install``.

    .. note::

        The default behavior is to initialize the project as a library (with a package
        structure within a ``src/`` folder). Use the ``--as-app`` flag to initialize the
        project as an app (just a script file to start with) or ``--as-pkg`` to initialize
        as a package (with a package structure in the root directory).

    .. important::

        Using ``--with-defaults`` will trust the defaults and skip all prompts:

        - Install recommended dependencies.
        - Initialize pre-commit hooks.
        - Initialize the docs.

    .. important::

        If you generate the docs, (with ``--docs`` or ``--with-defaults``) parameters
        like ``--deps`` and ``--as_main_deps`` will passed to the ``siesta docs init``
        command so it may be worth checking ``$ siesta docs init --help``.

    Parameters
    ----------
    as_app : bool, optional
        Whether to initialize the project as an app (just a script file to start with).
    as_pkg : bool, optional
        Whether to initialize the project as a package (with a package structure in the root directory).
    precommit : bool, optional
        Whether to install pre-commit hooks, by default ``None`` (i.e. prompt the user).
    docs : bool, optional
        Whether to initialize the docs, by default ``None`` (i.e. prompt the user).
    deps : bool, optional
        Whether to install dependencies (dev &? docs), by default ``None`` (i.e. prompt the user).
    docs_path : str, optional
        Where to build the docs, by default ``./docs``.
    as_main_deps : bool, optional
        Whether to include docs dependencies in the main dependencies, by default
        ``None`` (i.e. prompt the user).
    overwrite : bool, optional
        Whether to overwrite existing files (if any). Will be passed to ``siesta
        docs init``.
    with_defaults : bool, optional
        Whether to trust the defaults and skip all prompts.
    branch : str, optional
        The branch to fetch the static files from.
    contents : str, optional
        The path to the static files in the repository.
    local : bool, optional
        Use local boilerplate docs assets instead of fetching from the repository.
        May update to outdated contents so avoid using this option.
    ipdb: bool, optional
        Whether to add ipdb as debugger, by default ``None`` (i.e. prompt the user).
    tests: bool, optional
        Whether to initialize (pytest) tests infra, by default ``None`` (i.e. prompt the user).
    actions: bool, optional
        Whether to initialize GitHub Actions, by default ``None`` (i.e. prompt the user).
    gitignore: bool, optional
        Whether to initialize the ``.gitignore`` file, by default ``None`` (i.e. prompt the user).
    """
    if as_app and as_pkg:
        logger.abort("Cannot use both --as-app and --as-pkg flags.")

    # uv is required
    has_uv = bool(run_command(["uv", "--version"]))
    if not has_uv:
        logger.abort(
            "uv not found. Please install it first -> https://docs.astral.sh/uv/getting-started/installation/"
        )

    # Get the project name
    project_name = get_project_name(with_defaults)

    # Setting defaults
    if with_defaults:
        if precommit is not None:
            logger.warning("Ignoring precommit argument because of --with-defaults.")
        precommit = True
        if docs is not None:
            logger.warning("Ignoring docs argument because of --with-defaults.")
        docs = True
        if deps is not None:
            logger.warning("Ignoring deps argument because of --with-defaults.")
        deps = True
        if as_main_deps is not None:
            logger.warning("Ignoring as_main_deps argument because of --with-defaults.")
        as_main_deps = False
        if ipdb is not None:
            logger.warning("Ignoring ipdb argument because of --with-defaults.")
        ipdb = True
        if tests is not None:
            logger.warning("Ignoring tests argument because of --with-defaults.")
        tests = True
        if actions is not None:
            logger.warning("Ignoring actions argument because of --with-defaults.")
        actions = True
        if gitignore is not None:
            logger.warning("Ignoring gitignore argument because of --with-defaults.")
        gitignore = True

    # Check if the project is already initialized
    has_uv_lock = Path("uv.lock").exists()
    if not has_uv_lock:
        cmd = ["uv", "init"]
        cmd.append(f"--name={project_name}")
        if as_app:
            # Initialize as app (no src/ directory)
            pass
        elif as_pkg:
            # Initialize as package (package structure in root directory)
            cmd.append("--package")
        else:
            # Initialize as library (package structure in src/ directory)
            cmd.append("--lib")

        initialized = run_command(cmd)
        if initialized is False:
            logger.abort("Failed to initialize the project.")
        logger.info("Project initialized with uv.")
    else:
        logger.info("Project already initialized with uv.")

    # Install dependencies
    if deps is None:
        deps = logger.confirm("Would you like to install recommended dependencies?")
    if deps:
        dev_deps = load_deps()["dev"]
        installed = run_command(["uv", "add", "--dev"] + dev_deps)
        if installed is False:
            logger.abort("Failed to install the dev dependencies.")
        logger.info("Dev dependencies installed.")

    # Install pre-commit hooks
    if precommit is None:
        precommit = logger.confirm(
            "Would you like to update & install pre-commit hooks?"
        )
    if precommit:
        write_or_update_pre_commit_file()
        pre_commit_installed = run_command(["uv", "run", "pre-commit", "install"])
        if pre_commit_installed is False:
            logger.abort("Failed to install pre-commit hooks.")
        logger.info("Pre-commit hooks installed.")

    if ipdb is None:
        ipdb = logger.confirm("Would you like to add ipdb as debugger?")
    if ipdb:
        add_ipdb_as_debugger()
        logger.info("[r]ipdb[/r] added as debugger.")
    if tests is None:
        tests = logger.confirm("Would you like to initialize (pytest) tests infra?")
    if tests:
        write_tests_infra(project_name)
        logger.info("Tests infra written.")
    if actions is None:
        actions = logger.confirm("Would you like to initialize GitHub Actions?")
    if actions:
        write_test_actions_config()
        logger.info("Test actions config written.")
    if gitignore is None:
        gitignore = logger.confirm(
            "Would you like to initialize the ``.gitignore`` file?"
        )
    if gitignore:
        write_gitignore()
        logger.info("Gitignore written.")

    if docs is None:
        docs = logger.confirm("Would you like to initialize the docs?")
    if docs:
        init_docs(
            path=docs_path,
            as_main_deps=as_main_deps,
            overwrite=overwrite,
            deps=deps,
            with_defaults=with_defaults,
            branch=branch,
            contents=contents,
            local=local,
        )

    tree_project(".")
    logger.info("Project initialized.")
    logger.success("🔥 Happy coding! 👋")


@project_app.command(name="tree")
def tree_project(path: str = ".", ignore_from_gitignore: bool = True):
    """Show a project's tree, i.e. its directory structure.

    Additionally displays labels to explain the purpose of useful files / directories.

    Parameters
    ----------
    path : str, optional
        The path to the project.
    ignore_from_gitignore : bool, optional
        Whether to ignore files from the ``.gitignore`` file in ``path``.
        Only useful if ``path`` is a git repository.
    """
    path = resolve_path(path)
    if not path.exists():
        logger.abort(f"Path not found: {path}", exit=1)
    gitignore_path = path / ".gitignore"
    if ignore_from_gitignore and gitignore_path.exists():
        ignore = parse_gitignore(gitignore_path)
    else:
        ignore = None
    term_cols = get_terminal_size().columns
    logger.info(
        ".\n"
        + make_labeled_tree(
            path,
            ignore,
            max_line_length=term_cols - 4,  # account for panel borders
        ),
        as_panel=True,
        title="Your project's directory structure",
    )


# ============================================================================
# Self commands
# ============================================================================


@self_app.command(name="version")
def self_version():
    """Show the current siesta version and check for updates.

    Displays the installed version, installation method, and whether
    a newer version is available on PyPI.
    """
    from siesta import __version__

    # Get installation method
    method = get_installation_method()
    method_display = {
        "uv": "uv tool",
        "pipx": "pipx",
        "pip": "pip",
        "editable": "editable (development)",
    }.get(method, method)

    logger.info(f"siesta version: [r]{__version__}[/r]")
    logger.info(f"Installation method: [r]{method_display}[/r]")

    # Check for updates
    with logger.loading("Checking for updates..."):
        latest = get_latest_version()

    if latest is None:
        logger.warning("Could not check for updates (network error).")
        return

    comparison = compare_versions(__version__, latest)
    if comparison < 0:
        logger.warning(f"A newer version is available: [r]{latest}[/r]")
        logger.info("Run [r]siesta self update[/r] to upgrade.")
    elif comparison > 0:
        logger.info("You are running a pre-release or development version.")
        logger.info(f"Latest stable release: [r]{latest}[/r]")
    else:
        logger.success("You are running the latest version.")


@self_app.command(name="update")
def self_update(force: bool = False, dry: bool = False):
    """Update siesta to the latest version.

    Automatically detects how siesta was installed (uv tool, pipx, pip, or editable)
    and uses the appropriate update command (uv tool, pipx, pip), except for editable
    installations (i.e. when siesta is installed from source) in which case it
    shows a warning and suggests manual steps.

    Parameters
    ----------
    force : bool, optional
        Force update even if already on the latest version.
    dry : bool, optional
        Show what would be done without actually updating.
    """
    from siesta import __version__

    # Get installation method
    method = get_installation_method()
    method_display = {"uv": "uv tool", "pipx": "pipx", "pip": "pip"}.get(method, method)

    # Handle editable installations
    if method == "editable":
        logger.warning("siesta is installed in editable (development) mode.")
        logger.info("To update, navigate to the source directory and run:")
        logger.info("  [r]git pull[/r]")
        logger.info("  [r]uv pip install -e .[/r]  (or pip install -e .)")
        return

    # Dry run: just show what would be done
    if dry:
        cmd = get_update_command(method)
        logger.info(f"Installation method: [r]{method_display}[/r]")
        logger.info(f"Would run: [r]{' '.join(cmd)}[/r]")
        return

    # Check current vs latest version
    with logger.loading("Checking for updates..."):
        latest = get_latest_version()

    if latest is None:
        logger.warning("Could not check for latest version (network error).")
        if not force:
            logger.info("Use [r]--force[/r] to update anyway.")
            return

    if latest and not force:
        comparison = compare_versions(__version__, latest)
        if comparison >= 0:
            logger.success(f"Already up to date (version {__version__}).")
            return

    # Perform the update
    logger.info(f"Updating siesta via {method_display}...")

    success = update_siesta(method)
    if success:
        logger.success("siesta has been updated successfully.")
        logger.info(
            "Restart your terminal or run [r]siesta self version[/r] to verify."
        )
    else:
        logger.error("Update failed.")
        logger.info("Try updating manually:")
        if method == "uv":
            logger.info("  [r]uv tool upgrade siesta[/r]")
        elif method == "pipx":
            logger.info("  [r]pipx upgrade siesta[/r]")
        else:
            logger.info("  [r]pip install --upgrade siesta[/r]")


# Register 'upgrade' as an alias for 'update'
self_app.command(self_update, name="upgrade")
