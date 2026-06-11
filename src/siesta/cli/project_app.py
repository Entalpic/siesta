# Copyright 2025 Entalpic
"""Project CLI commands."""

import sys
from pathlib import Path
from shutil import get_terminal_size
from textwrap import dedent
from typing import Annotated

from cyclopts import App, Parameter
from gitignore_parser import parse_gitignore

from siesta.utils.agents import install_quickstart, print_summary
from siesta.utils.common import (
    get_project_name,
    load_deps,
    logger,
    resolve_path,
    run_command,
    write_or_update_pre_commit_file,
)
from siesta.utils.config import CLI_DEFAULTS
from siesta.utils.project import (
    add_ipdb_as_debugger,
    write_gitignore,
    write_test_actions_config,
    write_tests_infra,
)
from siesta.utils.tree import make_labeled_tree

project_app = App(
    name="project",
    help=dedent(
        """
        Initialize and manage Python projects with standard Entalpic config.

        Upgrade with ``$ siesta self update``.

        See Usage instructions in the online docs: https://entalpic-siesta.readthedocs-hosted.com/en/latest/autoapi/siesta.

        """.strip(),
    ),
)
""":py:class:`cyclopts.App`: The app for the ``siesta project`` sub-command."""


def _confirm_quickstart_decision(message: str, default_key: str) -> bool:
    """Prompt for a quickstart decision using the non-interactive CLI default.

    Parameters
    ----------
    message : str
        The decision prompt shown to the user.
    default_key : str
        The key in :data:`siesta.utils.config.CLI_DEFAULTS` that owns the recommendation.

    Returns
    -------
    bool
        Whether the user confirmed the decision.
    """
    return logger.confirm(message, default=CLI_DEFAULTS[default_key])


def _resolve_conflict(
    name: str,
    overwrite: bool | None,
    allow_overwrite: bool = True,
) -> bool:
    """Resolve a Conflict between a planned Mutation and an existing artifact.

    Must be called during the Prompt Collection Phase, before any Mutation.

    Parameters
    ----------
    name : str
        Human-readable description of the conflicting artifact (shown in prompts).
    overwrite : bool | None
        The global ``--overwrite`` flag. ``True`` = proceed, ``False`` = skip,
        ``None`` = resolve at runtime.
    allow_overwrite : bool, optional
        Whether "overwrite" is a valid choice for this step. ``False`` for steps
        where overwriting is not supported (e.g. ``uv init``).

    Returns
    -------
    bool
        ``True`` = proceed with the Mutation (overwrite). ``False`` = skip this step.
        Never returns when the user chooses Abort — calls ``logger.abort()`` instead.
    """
    if overwrite is True:
        if not allow_overwrite:
            logger.warning(
                f"{name} already exists. Overwrite not supported for this step — skipping."
            )
            return False
        return True
    if overwrite is False:
        logger.warning(f"{name} already exists. Skipping.")
        return False
    # overwrite is None: resolve at runtime
    if not sys.stdin.isatty():
        logger.abort(
            f"{name} already exists. "
            "Pass --overwrite to overwrite or the matching --no-<feature> flag to skip."
        )
    if allow_overwrite:
        choice = logger.select(
            f"{name} already exists — what do you want to do?",
            ["Skip (keep existing)", "Overwrite", "Abort"],
        )
    else:
        choice = logger.select(
            f"{name} already exists — what do you want to do?",
            ["Skip (keep existing)", "Abort"],
        )
    if choice == "Abort":
        logger.abort("Aborted.")
    return choice == "Overwrite"


@project_app.command(name="quickstart")
def quickstart_project(
    as_app: bool = False,
    as_pkg: bool = False,
    uv_init: bool | None = None,
    precommit: bool | None = None,
    docs: bool | None = None,
    deps: bool | None = None,
    docs_path: str = "./docs",
    as_main_deps: bool | None = None,
    overwrite: bool | None = None,
    interactive: Annotated[bool, Parameter(name=["-i", "--interactive"])] = False,
    branch: str = "main",
    contents: str = "src/siesta/boilerplate",
    remote_assets: bool = False,
    ipdb: bool | None = None,
    tests: bool | None = None,
    actions: bool | None = None,
    gitignore: bool | None = None,
    agents: bool | None = None,
):
    """Start a ``uv``-based Python project from scratch, with initial project structure and docs.

    Overall:

    * Initializes a new ``uv`` project with ``$ uv init``.
    * Installs recommended dependencies with ``$ uv add --dev [...]``.
    * Sets up pytest testing infrastructure (via ``siesta project setup-tests``).
    * Sets up GitHub Actions for CI.
    * Initializes a new Sphinx project at the specified path as per ``$ siesta
      docs init``.
    * Initializes pre-commit hooks with ``$ uv run pre-commit install``.

    .. tip::

        If you only need to add testing infrastructure to an existing project,
        use ``siesta project setup-tests`` instead.

    .. note::

        The default behavior is to initialize the project as a library (with a package
        structure within a ``src/`` folder). Use the ``--as-app`` flag to initialize the
        project as an app (just a script file to start with) or ``--as-pkg`` to initialize
        as a package (with a package structure in the root directory).

    .. important::

        By default, sensible defaults are used for unspecified options:

        - Install recommended dependencies.
        - Initialize pre-commit hooks.
        - Initialize pytest testing infrastructure and GitHub Actions.
        - Initialize the docs.

        User-specified flags always take precedence. For example,
        ``--no-tests`` will skip test initialization.

        Use ``-i`` or ``--interactive`` to be prompted for each option instead.

    .. important::

        If you generate the docs (with ``--docs`` or by default) parameters
        like ``--deps`` and ``--as_main_deps`` will passed to the ``siesta docs init``
        command so it may be worth checking ``$ siesta docs init --help``.

    Parameters
    ----------
    as_app : bool, optional
        Whether to initialize the project as an app (just a script file to start with).
    as_pkg : bool, optional
        Whether to initialize the project as a package (with a package structure in the root directory).
    uv_init : bool, optional
        Whether to initialize a ``uv`` project (``$ uv init``), by default ``None`` (i.e.
        prompt the user). Use ``--no-uv-init`` to skip — note the other steps (``--deps``,
        ``--precommit``) need a ``uv`` project to exist, so skipping it on a fresh directory
        will make them fail.
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
    overwrite : bool | None, optional
        How to handle existing artifacts. ``True`` = overwrite all, ``False`` = skip all,
        ``None`` (default) = prompt in TTY or abort in non-TTY.
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
    ipdb: bool, optional
        Whether to add ipdb as debugger, by default ``None`` (i.e. prompt the user).
    tests: bool, optional
        Whether to initialize (pytest) tests infra, by default ``None`` (i.e. prompt the user).
    actions: bool, optional
        Whether to initialize GitHub Actions, by default ``None`` (i.e. prompt the user).
    gitignore: bool, optional
        Whether to initialize the ``.gitignore`` file, by default ``None`` (i.e. prompt the user).
    agents : bool, optional
        Whether to install recommended agent assets (skills/rules/constitution), by default
        ``None`` (i.e. prompt the user).
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
    project_name = get_project_name(interactive)

    # Setting defaults: only fill in values that weren't explicitly provided
    if not interactive:
        if uv_init is None:
            uv_init = CLI_DEFAULTS["uv_init"]
        if precommit is None:
            precommit = CLI_DEFAULTS["precommit"]
        if docs is None:
            docs = CLI_DEFAULTS["docs"]
        if deps is None:
            deps = CLI_DEFAULTS["deps"]
        if as_main_deps is None:
            as_main_deps = CLI_DEFAULTS["as_main_deps"]
        if ipdb is None:
            ipdb = CLI_DEFAULTS["ipdb"]
        if tests is None:
            tests = CLI_DEFAULTS["tests"]
        if actions is None:
            actions = CLI_DEFAULTS["actions"]
        if gitignore is None:
            gitignore = CLI_DEFAULTS["gitignore"]
        if agents is None:
            agents = CLI_DEFAULTS["agents"]

    # Prompt collection phase: gather all unresolved decisions before mutations.
    if interactive and not as_app and not as_pkg:
        layout = logger.select(
            "How should the project be initialized?",
            [
                "Library with src/ layout (recommended)",
                "Application script",
                "Package without src/ layout",
            ],
        )
        as_app = layout == "Application script"
        as_pkg = layout == "Package without src/ layout"

    if uv_init is None:
        uv_init = _confirm_quickstart_decision(
            "Would you like to initialize a uv project?", "uv_init"
        )

    if deps is None:
        deps = _confirm_quickstart_decision(
            "Would you like to install recommended dependencies?", "deps"
        )

    if precommit is None:
        precommit = _confirm_quickstart_decision(
            "Would you like to update & install pre-commit hooks?", "precommit"
        )

    if ipdb is None:
        ipdb = _confirm_quickstart_decision(
            "Would you like to add ipdb as debugger?", "ipdb"
        )
    ipdb_overwrite = False
    if ipdb:
        _inits = list(Path("src/").glob("**/__init__.py"))
        if _inits:
            _first_init = sorted(
                [(_i, len(str(_i).split("/"))) for _i in _inits], key=lambda x: x[1]
            )[0][0]
            if "PYTHONBREAKPOINT" in _first_init.read_text():
                result = _resolve_conflict(
                    "ipdb debugger (PYTHONBREAKPOINT already present)", overwrite
                )
                if not result:
                    ipdb = False
                else:
                    ipdb_overwrite = True

    if tests is None:
        tests = _confirm_quickstart_decision(
            "Would you like to initialize (pytest) tests infra?", "tests"
        )

    if actions is None:
        actions = _confirm_quickstart_decision(
            "Would you like to initialize GitHub Actions?", "actions"
        )

    if gitignore is None:
        gitignore = _confirm_quickstart_decision(
            "Would you like to initialize the ``.gitignore`` file?", "gitignore"
        )
    gitignore_overwrite = False
    # Capture pre-run existence: only a .gitignore present before any Mutation is a
    # Conflict. The one `uv init` writes during the Execution Phase is a pipeline
    # byproduct, so siesta's gitignore takes precedence over it (see CONTEXT.md).
    gitignore_preexisted = Path(".gitignore").exists()
    if gitignore and gitignore_preexisted:
        result = _resolve_conflict(".gitignore", overwrite)
        if not result:
            gitignore = False
        else:
            gitignore_overwrite = True

    if docs is None:
        docs = _confirm_quickstart_decision(
            "Would you like to initialize the docs?", "docs"
        )

    if docs and interactive and docs_path == "./docs":
        docs_path = logger.prompt("Documentation path", default=docs_path)

    docs_overwrite = False
    if docs and resolve_path(docs_path).exists():
        result = _resolve_conflict(f"docs at {docs_path}", overwrite)
        if not result:
            docs = False
        else:
            docs_overwrite = True

    if agents is None:
        agents = _confirm_quickstart_decision(
            "Would you like to install recommended agent assets?", "agents"
        )

    if docs and deps and as_main_deps is None:
        as_main_deps = _confirm_quickstart_decision(
            "Would you like to install documentation dependencies as main dependencies?",
            "as_main_deps",
        )

    docs_with_uv: bool | None = None
    if docs and deps:
        if Path("uv.lock").exists():
            if interactive:
                docs_with_uv = logger.confirm(
                    "It looks like you are using uv. Use `uv add` to add dependencies?"
                )
            else:
                docs_with_uv = True

    # Conflict Resolution: uv init. Overwriting uv init is not supported by uv
    # itself, so this conflict is skip-only and resolved here, just before execution.
    already_initialized = Path("uv.lock").exists() or Path("pyproject.toml").exists()
    if uv_init is False:
        # Explicit opt-out. Warn when there is no uv project yet, since the remaining
        # steps (deps, pre-commit, ...) need one to exist.
        if not already_initialized:
            logger.warning(
                "Skipping uv init on a fresh directory — dependency and pre-commit "
                "steps may fail without a uv project."
            )
        run_uv_init = False
    elif already_initialized:
        run_uv_init = False
        _resolve_conflict(
            "uv project (pyproject.toml or uv.lock already exists — safe to skip if already set up with uv)",
            overwrite,
            allow_overwrite=False,
        )
        logger.info("Skipping uv init — project already initialized.")
    else:
        run_uv_init = True

    # Execution phase: perform mutations after all decisions are collected.
    if run_uv_init:
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

    if deps:
        dev_deps = load_deps()["dev"]
        installed = run_command(["uv", "add", "--dev"] + dev_deps)
        if installed is False:
            logger.abort("Failed to install the dev dependencies.")
        logger.info("Dev dependencies installed.")

    if precommit:
        write_or_update_pre_commit_file()
        pre_commit_installed = run_command(["uv", "run", "pre-commit", "install"])
        if pre_commit_installed is False:
            logger.abort("Failed to install pre-commit hooks.")
        logger.info("Pre-commit hooks installed.")

    if ipdb:
        add_ipdb_as_debugger(overwrite=ipdb_overwrite)
        logger.info("[r]ipdb[/r] added as debugger.")

    if tests:
        # Decision ownership stays in quickstart; setup-tests receives explicit values.
        setup_tests(
            project_name=project_name,
            actions=actions,
            deps=False,  # deps already handled by quickstart
            interactive=False,
        )
    elif actions:
        # Warn if user wants CI but has no tests
        if not Path("tests").exists():
            logger.warning(
                "You're setting up GitHub Actions CI without tests. "
                "Either add tests later or update [r].github/workflows/test.yml[/r] "
                "to match your project's needs."
            )
        write_test_actions_config()
        logger.info("Test actions config written.")

    if gitignore:
        # Overwrite when the file was not a pre-run Conflict: any .gitignore on disk
        # now was written by `uv init` this run, and siesta's takes precedence.
        write_gitignore(overwrite=gitignore_overwrite or not gitignore_preexisted)
        logger.info("Gitignore written.")

    if docs:
        from siesta.cli.docs_app import init_docs

        init_docs(
            path=docs_path,
            as_main_deps=bool(as_main_deps),
            overwrite=docs_overwrite,
            deps=deps,
            uv=docs_with_uv,
            interactive=False,
            branch=branch,
            contents=contents,
            remote_assets=remote_assets,
            project_name=project_name,
        )

    if agents:
        # Back up existing agent files when overwriting so a user-authored
        # CLAUDE.md/AGENTS.md is recoverable from a .bak.
        _overwrite = overwrite is True
        summary = install_quickstart(
            ["cursor", "claude"], "local", force=_overwrite, backup=_overwrite
        )
        print_summary(summary)
        logger.info("Agent assets installed.")

    tree_project(".")
    logger.info("Project initialized.")
    logger.success("🔥 Happy coding! 👋")


@project_app.command(name="setup-tests")
def setup_tests(
    project_name: str | None = None,
    actions: bool | None = None,
    deps: bool | None = None,
    interactive: Annotated[bool, Parameter(name=["-i", "--interactive"])] = False,
):
    """Set up pytest testing infrastructure for an existing project.

    This command adds testing infrastructure to an existing Python project:

    - Installs ``pytest`` and ``pytest-cov`` as dev dependencies.
    - Creates a ``tests/`` directory with an example test file.
    - Optionally sets up GitHub Actions for CI (runs tests on PRs and pushes to main).

    .. tip::

        This is useful when you have an existing project that doesn't have tests yet,
        or when you want to add Entalpic's standard testing setup to a project.

    .. note::

        This command assumes a ``uv``-based project (``uv.lock`` exists).
        If ``uv.lock`` is not found, dependencies will be installed with ``pip``.

    Example
    -------
    .. code-block:: bash

        # Set up tests with all defaults (installs deps + GitHub Actions)
        $ siesta project setup-tests

        # Set up tests interactively (prompts for each option)
        $ siesta project setup-tests -i

        # Set up tests without GitHub Actions (user flag takes precedence)
        $ siesta project setup-tests --no-actions

        # Set up tests for a specific project name
        $ siesta project setup-tests --project-name=myproject

    Parameters
    ----------
    project_name : str, optional
        The project's name. If not provided, it will be detected from ``pyproject.toml``
        or prompted.
    actions : bool, optional
        Whether to initialize GitHub Actions, by default ``None`` (i.e. prompt the user
        in interactive mode, defaults to ``True`` otherwise).
    deps : bool, optional
        Whether to install test dependencies (``pytest``, ``pytest-cov``), by default
        ``None`` (i.e. prompt the user in interactive mode, defaults to ``True`` otherwise).
    interactive : bool, optional
        Enable interactive mode with prompts for all options (``-i``). By default,
        sensible defaults are used. User-specified flags always take precedence.
    """
    # Get the project name
    if project_name is None:
        project_name = get_project_name(interactive)

    # Setting defaults: only fill in values that weren't explicitly provided
    if not interactive:
        if actions is None:
            actions = CLI_DEFAULTS["actions"]
        if deps is None:
            deps = CLI_DEFAULTS["deps"]

    # Check if uv is available and uv.lock exists
    has_uv = Path("uv.lock").exists()

    # Prompt collection phase: gather decisions before mutations.
    if deps is None:
        deps = logger.confirm("Would you like to install test dependencies?")

    if actions is None:
        actions = logger.confirm("Would you like to initialize GitHub Actions?")

    # Execution phase: apply selected mutations.
    if deps:
        test_deps = ["pytest", "pytest-cov"]
        if has_uv:
            installed = run_command(["uv", "add", "--dev"] + test_deps)
            if installed is False:
                logger.abort("Failed to install test dependencies.")
            logger.info("Test dependencies installed with uv.")
        else:
            installed = run_command(["pip", "install"] + test_deps)
            if installed is False:
                logger.abort("Failed to install test dependencies.")
            logger.info("Test dependencies installed with pip.")

    # Write the tests infrastructure
    write_tests_infra(project_name)
    logger.info("Tests infra written.")

    if actions:
        write_test_actions_config()
        logger.info("Test actions config written.")

    logger.success("Testing infrastructure set up successfully.")


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
    resolved_path = resolve_path(path)
    if not resolved_path.exists():
        logger.abort(f"Path not found: {resolved_path}", exit=1)
    gitignore_path = resolved_path / ".gitignore"
    if ignore_from_gitignore and gitignore_path.exists():
        ignore = parse_gitignore(gitignore_path)
    else:
        ignore = None
    term_cols = get_terminal_size().columns
    logger.info(
        ".\n"
        + make_labeled_tree(
            resolved_path,
            ignore,
            max_line_length=term_cols - 4,  # account for panel borders
        ),
        as_panel=True,
        title="Your project's directory structure",
    )
