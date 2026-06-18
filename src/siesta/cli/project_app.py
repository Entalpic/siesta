# Copyright 2025 Entalpic
"""Project CLI commands."""

from pathlib import Path
from shutil import get_terminal_size
from textwrap import dedent
from typing import Annotated

from cyclopts import App, Parameter
from gitignore_parser import parse_gitignore

from siesta.utils.agents import quickstart_asset_mutations
from siesta.utils.common import (
    get_project_name,
    load_deps,
    logger,
    resolve_path,
)
from siesta.utils.config import CLI_DEFAULTS
from siesta.utils.conflicts import Mutation, render_summary, run_mutations
from siesta.utils.project import (
    DepsMutation,
    GitignoreMutation,
    InitDocsMutation,
    IpdbMutation,
    PrecommitMutation,
    TestActionsMutation,
    TestDepsMutation,
    TestsInfraMutation,
    UvInitMutation,
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
    backup: bool = False,
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
    """Start a ``uv``-based Python project from scratch with standard Entalpic configuration.

    Sets up, in order: ``uv init``, dev dependencies (``uv add --dev``), pre-commit
    hooks, ipdb debugger, pytest testing infrastructure, GitHub Actions CI,
    ``.gitignore``, Sphinx documentation (via ``siesta docs init``), and recommended
    local Agent Assets (via ``siesta agents quickstart``).

    Default project layout is a library with a ``src/`` folder. Use ``--as-app`` for a
    single-file script or ``--as-pkg`` for a package without ``src/``.

    By default (non-interactive), each step is enabled using CLI defaults. Explicit
    flags always win — ``--no-tests`` skips tests regardless of defaults. Use ``-i`` /
    ``--interactive`` to be prompted for each unspecified option before any Mutation.

    When docs or tests are initialized, explicit decisions are passed downstream; those
    sub-commands do not re-prompt. Run ``siesta docs init --help`` for docs-specific
    options like ``--deps`` and ``--as-main-deps``.

    For testing on an existing project, use ``siesta project setup-tests``.

    Parameters
    ----------
    as_app : bool, optional
        Initialize the project as a single-file app script instead of a library.
    as_pkg : bool, optional
        Initialize as a package with a package structure in the root directory
        (no ``src/`` layout).
    uv_init : bool | None, optional
        Initialize a new ``uv`` project (``uv init``). Unspecified: defaults to
        ``True`` in non-interactive mode; prompts when ``-i`` is active. Use
        ``--no-uv-init`` to skip — ``--deps`` and ``--precommit`` require a ``uv``
        project, so skipping on a fresh directory will cause those steps to fail.
    precommit : bool | None, optional
        Install pre-commit hooks. Unspecified: defaults to ``True`` in non-interactive
        mode; prompts when ``-i`` is active.
    docs : bool | None, optional
        Initialize Sphinx documentation via ``siesta docs init``. Unspecified: defaults
        to ``True`` in non-interactive mode; prompts when ``-i`` is active.
    deps : bool | None, optional
        Install dev (and optionally docs) dependencies via ``uv add --dev``. Unspecified:
        defaults to ``True`` in non-interactive mode; prompts when ``-i`` is active.
    docs_path : str, optional
        Path for the Sphinx docs folder, by default ``./docs``.
    as_main_deps : bool | None, optional
        Install docs dependencies as main (not dev) dependencies. Unspecified: defaults
        to ``False`` in non-interactive mode; prompts when ``-i`` is active and both
        docs and deps are enabled.
    overwrite : bool | None, optional
        How to handle existing artifacts during Conflict Resolution. ``True`` =
        overwrite, ``False`` = skip, ``None`` (default) = prompt in TTY or abort in
        non-TTY.
    backup : bool, optional
        Back up existing artifacts before overwriting (applies when overwriting).
    interactive : bool, optional
        Prompt for each unspecified option before any Mutation (``-i``). When ``False``
        (default), unspecified options use CLI defaults; explicit flags always win.
    branch : str, optional
        Branch to fetch static files from when using ``--remote-assets``.
    contents : str, optional
        Path to static files in the repository when using ``--remote-assets``.
    remote_assets : bool, optional
        Fetch boilerplate docs assets from the remote GitHub repository instead of using
        the local bundled files. Requires a GitHub Personal Access Token (PAT). Run
        ``siesta self set-github-pat`` to configure one.
    ipdb : bool | None, optional
        Add ipdb as the default debugger (sets ``PYTHONBREAKPOINT=ipdb.set_trace``).
        Unspecified: defaults to ``True`` in non-interactive mode; prompts when ``-i``
        is active.
    tests : bool | None, optional
        Set up pytest testing infrastructure. Unspecified: defaults to ``True`` in
        non-interactive mode; prompts when ``-i`` is active.
    actions : bool | None, optional
        Set up GitHub Actions CI. Unspecified: defaults to ``True`` in non-interactive
        mode; prompts when ``-i`` is active.
    gitignore : bool | None, optional
        Write a ``.gitignore`` file. Unspecified: defaults to ``True`` in
        non-interactive mode; prompts when ``-i`` is active.
    agents : bool | None, optional
        Install recommended local Agent Assets via ``siesta agents quickstart``.
        Unspecified: defaults to ``True`` in non-interactive mode; prompts when ``-i``
        is active.
    """
    from siesta.utils.common import run_command

    if as_app and as_pkg:
        logger.abort("Cannot use both --as-app and --as-pkg flags.")

    has_uv = bool(run_command(["uv", "--version"]))
    if not has_uv:
        logger.abort(
            "uv not found. Please install it first -> https://docs.astral.sh/uv/getting-started/installation/"
        )

    project_name = get_project_name(interactive)

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

    if docs is None:
        docs = _confirm_quickstart_decision(
            "Would you like to initialize the docs?", "docs"
        )

    if docs and interactive and docs_path == "./docs":
        docs_path = logger.prompt("Documentation path", default=docs_path)

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

    already_initialized = Path("uv.lock").exists() or Path("pyproject.toml").exists()
    if uv_init is False and not already_initialized:
        logger.warning(
            "Skipping uv init on a fresh directory — dependency and pre-commit "
            "steps may fail without a uv project."
        )

    mutations: list[Mutation] = []
    if uv_init:
        mutations.append(
            UvInitMutation(project_name, as_app, as_pkg, run_requested=True)
        )
    if deps:
        mutations.append(DepsMutation(load_deps()["dev"]))
    if precommit:
        mutations.append(PrecommitMutation())
    if ipdb:
        mutations.append(IpdbMutation())
    if tests:
        mutations.append(TestsInfraMutation(project_name))
        if actions:
            mutations.append(TestActionsMutation())
    elif actions:
        if not Path("tests").exists():
            logger.warning(
                "You're setting up GitHub Actions CI without tests. "
                "Either add tests later or update [r].github/workflows/test.yml[/r] "
                "to match your project's needs."
            )
        mutations.append(TestActionsMutation())
    if gitignore:
        mutations.append(GitignoreMutation())
    if docs:
        mutations.append(
            InitDocsMutation(
                path=docs_path,
                as_main_deps=bool(as_main_deps),
                deps=deps,
                with_uv=bool(docs_with_uv),
                interactive=False,
                branch=branch,
                contents=contents,
                remote_assets=remote_assets,
                project_name=project_name,
            )
        )
    if agents:
        mutations.extend(quickstart_asset_mutations(["cursor", "claude"], "local"))

    summary = run_mutations(mutations, overwrite=overwrite, backup=backup)
    render_summary(summary)

    tree_project(".")
    logger.info("Project initialized.")
    logger.success("🔥 Happy coding! 👋")


@project_app.command(name="setup-tests")
def setup_tests(
    project_name: str | None = None,
    actions: bool | None = None,
    deps: bool | None = None,
    overwrite: bool | None = None,
    backup: bool = False,
    interactive: Annotated[bool, Parameter(name=["-i", "--interactive"])] = False,
):
    """Set up pytest testing infrastructure for an existing project.

    This command adds testing infrastructure to an existing Python project:

    - Installs ``pytest`` and ``pytest-cov`` as dev dependencies.
    - Creates a ``tests/`` directory with an example test file.
    - Optionally sets up GitHub Actions for CI (runs tests on PRs and pushes to main).

    When ``uv.lock`` is found, dependencies are installed with ``uv add --dev``;
    otherwise ``pip`` is used.

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
    overwrite : bool | None, optional
        How to handle existing test artifacts. ``True`` = overwrite, ``False`` = skip,
        ``None`` (default) = prompt in TTY or abort in non-TTY.
    backup : bool, optional
        Back up existing test artifacts before overwriting when ``--overwrite`` is set.
    interactive : bool, optional
        Enable interactive mode with prompts for all options (``-i``). By default,
        sensible defaults are used. User-specified flags always take precedence.
    """
    if project_name is None:
        project_name = get_project_name(interactive)

    if not interactive:
        if actions is None:
            actions = CLI_DEFAULTS["actions"]
        if deps is None:
            deps = CLI_DEFAULTS["deps"]

    has_uv = Path("uv.lock").exists()

    if deps is None:
        deps = logger.confirm("Would you like to install test dependencies?")

    if actions is None:
        actions = logger.confirm("Would you like to initialize GitHub Actions?")

    mutations: list[Mutation] = []
    if deps:
        mutations.append(TestDepsMutation(["pytest", "pytest-cov"], has_uv))
    mutations.append(TestsInfraMutation(project_name))
    if actions:
        mutations.append(TestActionsMutation())

    summary = run_mutations(mutations, overwrite=overwrite, backup=backup)
    render_summary(summary)

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
            max_line_length=term_cols - 4,
        ),
        as_panel=True,
        title="Your project's directory structure",
    )
