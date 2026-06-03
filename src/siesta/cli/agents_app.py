# Copyright 2025 Entalpic
"""Agent asset CLI commands (``siesta agents``)."""

import sys
from textwrap import dedent
from typing import Annotated

from cyclopts import App, Parameter

from siesta.utils.agents import (
    DEFAULT_CONSTITUTION,
    available_constitutions,
    available_rules,
    available_skills,
    install_constitution,
    install_quickstart,
    install_rule,
    install_skill,
    print_summary,
    resolve_providers,
    resolve_scope,
    resolve_selection,
)
from siesta.utils.common import logger

agents_app = App(
    name="agents",
    help=dedent(
        """
        Install agent assets (Skills, Rules, Constitution) into a repository or
        user home, for Cursor and/or Claude.

        Upgrade with ``$ siesta self update``.
        """.strip()
    ),
)
""":py:class:`cyclopts.App`: The app for the ``siesta agents`` sub-command."""


# ---------------------------------------------------------------------------
# add-skill
# ---------------------------------------------------------------------------


@agents_app.command(name="add-skill")
def add_skill(
    names: list[str] = [],
    *,
    all_: Annotated[bool, Parameter(name=["--all"])] = False,
    cursor: bool = False,
    claude: bool = False,
    both: bool = False,
    local: bool = False,
    global_: Annotated[bool, Parameter(name=["--global"])] = False,
    force: bool = False,
    backup: bool = False,
    interactive: Annotated[bool, Parameter(name=["-i", "--interactive"])] = False,
) -> None:
    """Install one or more bundled Skills into the repository or user home.

    Without arguments, an interactive checklist is shown. Pass skill names
    directly to skip the prompt (``siesta agents add-skill grill-with-docs``),
    or use ``--all`` to install every available Skill.

    Examples
    --------
    .. code-block:: bash

        # Interactive selection
        $ siesta agents add-skill -i

        # Install a specific skill for Cursor only
        $ siesta agents add-skill grill-with-docs --cursor --local

        # Install all skills globally for Claude
        $ siesta agents add-skill --all --claude --global

    Parameters
    ----------
    names : list[str], optional
        Skill names to install. Mutually exclusive with ``--all``.
    all_ : bool, optional
        Install all available Skills.
    cursor : bool, optional
        Target the Cursor provider.
    claude : bool, optional
        Target the Claude provider.
    both : bool, optional
        Target both providers (default when no provider flag is given).
    local : bool, optional
        Install into the current repository (default).
    global_ : bool, optional
        Install into the user home (``~/.cursor/skills/``, ``~/.claude/skills/``).
    force : bool, optional
        Overwrite existing targets without prompting.
    backup : bool, optional
        Back up existing targets before overwriting.
    interactive : bool, optional
        Enable interactive prompts for each conflict (``-i``).
    """
    # --- Validation phase ---
    scope = resolve_scope(local, global_)
    providers = resolve_providers(cursor, claude, both)

    available = available_skills()
    selected = resolve_selection(
        list(names), all_, available, interactive, kind="skill"
    )
    if not selected:
        logger.info("No skills selected; nothing to do.")
        sys.exit(0)

    # --- Execution phase ---
    combined: dict[str, list[str]] = {"written": [], "skipped": [], "backed_up": []}
    for name in selected:
        result = install_skill(
            name,
            providers,
            scope,
            force=force,
            backup=backup,
            interactive=interactive,
        )
        for key in combined:
            combined[key].extend(result.get(key, []))

    print_summary(combined)


# ---------------------------------------------------------------------------
# add-rule
# ---------------------------------------------------------------------------


@agents_app.command(name="add-rule")
def add_rule(
    names: list[str] = [],
    *,
    all_: Annotated[bool, Parameter(name=["--all"])] = False,
    cursor: bool = False,
    claude: bool = False,
    both: bool = False,
    local: bool = False,
    global_: Annotated[bool, Parameter(name=["--global"])] = False,
    force: bool = False,
    backup: bool = False,
    interactive: Annotated[bool, Parameter(name=["-i", "--interactive"])] = False,
) -> None:
    """Install one or more bundled Rules into the repository or user home.

    Cursor receives the canonical ``.mdc`` file verbatim. Claude receives a
    translated ``.md`` file (``globs`` → ``paths``; ``alwaysApply`` controls
    whether the ``paths`` block is emitted at all).

    Examples
    --------
    .. code-block:: bash

        # Interactive selection
        $ siesta agents add-rule -i

        # Install a specific rule for both providers
        $ siesta agents add-rule python-docstrings --both --local

        # Install all rules globally
        $ siesta agents add-rule --all --global

    Parameters
    ----------
    names : list[str], optional
        Rule names to install (without extension). Mutually exclusive with ``--all``.
    all_ : bool, optional
        Install all available Rules.
    cursor : bool, optional
        Target the Cursor provider.
    claude : bool, optional
        Target the Claude provider.
    both : bool, optional
        Target both providers (default when no provider flag is given).
    local : bool, optional
        Install into the current repository (default).
    global_ : bool, optional
        Install into the user home (``~/.cursor/rules/``, ``~/.claude/rules/``).
    force : bool, optional
        Overwrite existing targets without prompting.
    backup : bool, optional
        Back up existing targets before overwriting.
    interactive : bool, optional
        Enable interactive prompts for each conflict (``-i``).
    """
    # --- Validation phase ---
    scope = resolve_scope(local, global_)
    providers = resolve_providers(cursor, claude, both)

    available = available_rules()
    selected = resolve_selection(list(names), all_, available, interactive, kind="rule")
    if not selected:
        logger.info("No rules selected; nothing to do.")
        sys.exit(0)

    # --- Execution phase ---
    combined: dict[str, list[str]] = {"written": [], "skipped": [], "backed_up": []}
    for name in selected:
        result = install_rule(
            name,
            providers,
            scope,
            force=force,
            backup=backup,
            interactive=interactive,
        )
        for key in combined:
            combined[key].extend(result.get(key, []))

    print_summary(combined)


# ---------------------------------------------------------------------------
# add-constitution
# ---------------------------------------------------------------------------


@agents_app.command(name="add-constitution")
def add_constitution(
    name: str = DEFAULT_CONSTITUTION,
    *,
    cursor: bool = False,
    claude: bool = False,
    both: bool = False,
    local: bool = False,
    global_: Annotated[bool, Parameter(name=["--global"])] = False,
    force: bool = False,
    backup: bool = False,
    interactive: Annotated[bool, Parameter(name=["-i", "--interactive"])] = False,
) -> None:
    """Install a Constitution (AGENTS.md + optional CLAUDE.md stub).

    ``AGENTS.md`` is always written as the source of truth for Cursor
    compatibility; it is harmless but not required by Claude itself.
    When the Claude provider is targeted, a ``CLAUDE.md`` containing
    ``@AGENTS.md`` is also written (or the import line is prepended to
    an existing ``CLAUDE.md``).

    Examples
    --------
    .. code-block:: bash

        # Install the default constitution for both providers (local)
        $ siesta agents add-constitution

        # Install into the user home for Claude only
        $ siesta agents add-constitution --claude --global

        # List available constitutions
        $ siesta agents add-constitution --help

    Parameters
    ----------
    name : str, optional
        Constitution template name. Defaults to ``entalpic-default``.
        Available templates: entalpic-default.
    cursor : bool, optional
        Target the Cursor provider.
    claude : bool, optional
        Target the Claude provider.
    both : bool, optional
        Target both providers (default when no provider flag is given).
    local : bool, optional
        Install into the current repository (default).
    global_ : bool, optional
        Install into the user home. Note: Cursor has no global constitution
        concept; the Cursor side is skipped with a warning.
    force : bool, optional
        Overwrite existing targets without prompting.
    backup : bool, optional
        Back up existing targets before overwriting.
    interactive : bool, optional
        Enable interactive prompts for each conflict (``-i``).
    """
    # --- Validation phase ---
    scope = resolve_scope(local, global_)
    providers = resolve_providers(cursor, claude, both)

    available = available_constitutions()
    if name not in available:
        logger.abort(f"Unknown constitution: {name!r}. Available: {available}")

    # --- Execution phase ---
    summary = install_constitution(
        name,
        providers,
        scope,
        force=force,
        backup=backup,
        interactive=interactive,
    )
    print_summary(summary)


# ---------------------------------------------------------------------------
# quickstart
# ---------------------------------------------------------------------------


@agents_app.command(name="quickstart")
def quickstart(
    *,
    cursor: bool = False,
    claude: bool = False,
    both: bool = False,
    local: bool = False,
    global_: Annotated[bool, Parameter(name=["--global"])] = False,
    force: bool = False,
    backup: bool = False,
    interactive: Annotated[bool, Parameter(name=["-i", "--interactive"])] = False,
) -> None:
    """Install the curated default Agent Assets in one step.

    Reads the bundled Quickstart Config and installs the declared Skills,
    Rules, and Constitution.  Equivalent to running ``add-skill``,
    ``add-rule``, and ``add-constitution`` for each listed asset.

    Defaults to ``--local`` and both Providers when no flags are given.

    Examples
    --------
    .. code-block:: bash

        # Install all curated assets locally for both providers (default)
        $ siesta agents quickstart

        # Install globally for Claude only
        $ siesta agents quickstart --global --claude

        # Force-overwrite any existing assets
        $ siesta agents quickstart --force

    Parameters
    ----------
    cursor : bool, optional
        Target the Cursor provider.
    claude : bool, optional
        Target the Claude provider.
    both : bool, optional
        Target both providers (default when no provider flag is given).
    local : bool, optional
        Install into the current repository (default).
    global_ : bool, optional
        Install into the user home (``~/.cursor/skills/``, ``~/.claude/skills/``).
    force : bool, optional
        Overwrite existing targets without prompting.
    backup : bool, optional
        Back up existing targets before overwriting.
    interactive : bool, optional
        Enable interactive prompts for each conflict (``-i``).
    """
    # --- Validation phase ---
    scope = resolve_scope(local, global_)
    providers = resolve_providers(cursor, claude, both)

    # --- Execution phase ---
    summary = install_quickstart(
        providers, scope, force=force, backup=backup, interactive=interactive
    )
    print_summary(summary)
