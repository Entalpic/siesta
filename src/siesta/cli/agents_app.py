# Copyright 2025 Entalpic
"""Agent asset CLI commands (``siesta agents``)."""

import sys
from pathlib import Path
from textwrap import dedent
from typing import Annotated

from cyclopts import App, Parameter

from siesta.utils.agents import (
    DEFAULT_CONSTITUTION,
    _display_path,
    available_constitutions,
    available_rules,
    available_skills,
    collect_confirmed_removals,
    constitution_paths,
    detect_installed_rules,
    detect_installed_skills,
    install_constitution,
    install_quickstart,
    install_rule,
    install_skill,
    print_removal_summary,
    print_summary,
    remove_constitution,
    remove_rule,
    remove_skill,
    resolve_providers,
    resolve_remove_selection,
    resolve_scope,
    resolve_selection,
    rule_target,
    skill_target,
)
from siesta.utils.common import logger

agents_app = App(
    name="agents",
    help=dedent(
        """
        Install and remove agent assets (Skills, Rules, Constitution) in a
        repository or user home, for Cursor and/or Claude.

        Upgrade with ``$ siesta self update``.
        """.strip()
    ),
)
""":py:class:`cyclopts.App`: The app for the ``siesta agents`` sub-command."""

add_app = App(
    name="add",
    help="Install bundled Agent Assets (Skills, Rules, or Constitution).",
)
remove_app = App(
    name="remove",
    help="Remove detected Agent Assets (Skills, Rules, or Constitution).",
)
agents_app.command(add_app)
agents_app.command(remove_app)


def _merge_summaries(
    combined: dict[str, list[str]], result: dict[str, list[str]]
) -> None:
    """Merge one install summary into *combined*."""
    for key in combined:
        combined[key].extend(result.get(key, []))


# ---------------------------------------------------------------------------
# add skill / rule / constitution
# ---------------------------------------------------------------------------


@add_app.command(name="skill")
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
    directly to skip the prompt (``siesta agents add skill grill-with-docs``),
    or use ``--all`` to install every available Skill.

    Examples
    --------
    .. code-block:: bash

        # Interactive selection
        $ siesta agents add skill -i

        # Install a specific skill for Cursor only
        $ siesta agents add skill grill-with-docs --cursor --local

        # Install all skills globally for Claude
        $ siesta agents add skill --all --claude --global

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
        list(names), all_, available, interactive, kind="skill", scope=scope
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
        _merge_summaries(combined, result)

    print_summary(combined)


@add_app.command(name="rule")
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
        $ siesta agents add rule -i

        # Install a specific rule for both providers
        $ siesta agents add rule python-docstrings --both --local

        # Install all rules globally
        $ siesta agents add rule --all --global

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
    selected = resolve_selection(
        list(names), all_, available, interactive, kind="rule", scope=scope
    )
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
        _merge_summaries(combined, result)

    print_summary(combined)


@add_app.command(name="constitution")
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
        $ siesta agents add constitution

        # Install into the user home for Claude only
        $ siesta agents add constitution --claude --global

        # List available constitutions
        $ siesta agents add constitution --help

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
# remove skill / rule / constitution
# ---------------------------------------------------------------------------


@remove_app.command(name="skill")
def remove_skill_cmd(
    names: list[str] = [],
    *,
    cursor: bool = False,
    claude: bool = False,
    both: bool = False,
    local: bool = False,
    global_: Annotated[bool, Parameter(name=["--global"])] = False,
    backup: bool = False,
    interactive: Annotated[bool, Parameter(name=["-i", "--interactive"])] = False,
) -> None:
    """Remove detected Skills from the repository or user home.

    Without arguments, an interactive checklist of detected Skills is shown.
    Pass skill names directly to skip the prompt
    (``siesta agents remove skill grill-with-docs``).

    Each proposed removal path is confirmed individually before any file is
    deleted.

    Examples
    --------
    .. code-block:: bash

        # Interactive selection
        $ siesta agents remove skill -i

        $ siesta agents remove skill grill-with-docs --cursor

    Parameters
    ----------
    names : list[str], optional
        Skill names to remove.
    cursor : bool, optional
        Target the Cursor provider.
    claude : bool, optional
        Target the Claude provider.
    both : bool, optional
        Target both providers (default when no provider flag is given).
    local : bool, optional
        Remove from the current repository (default).
    global_ : bool, optional
        Remove from the user home.
    backup : bool, optional
        Back up targets before removing.
    interactive : bool, optional
        Enable interactive prompts (``-i``).
    """
    # --- Validation phase ---
    scope = resolve_scope(local, global_)
    providers = resolve_providers(cursor, claude, both)
    detected = detect_installed_skills(providers, scope)
    selected = resolve_remove_selection(
        list(names), detected, interactive, kind="skill", providers=providers, scope=scope
    )
    if not selected:
        if detected:
            logger.info("No skills selected; nothing to do.")
        sys.exit(0)

    candidates = _build_removal_candidates(
        selected, providers, scope, skill_target, "skill"
    )

    # --- Prompt collection phase ---
    confirmed, skipped = _confirm_removal_candidates(candidates)

    # --- Execution phase ---
    combined: dict[str, list[str]] = {"removed": [], "skipped": [], "backed_up": []}
    combined["skipped"].extend(skipped)

    confirmed_by_name = _group_confirmed_providers(confirmed)
    for skill_name, confirmed_providers in confirmed_by_name.items():
        result = remove_skill(skill_name, confirmed_providers, scope, backup=backup)
        _merge_removal_summaries(combined, result)

    print_removal_summary(combined)


@remove_app.command(name="rule")
def remove_rule_cmd(
    names: list[str] = [],
    *,
    cursor: bool = False,
    claude: bool = False,
    both: bool = False,
    local: bool = False,
    global_: Annotated[bool, Parameter(name=["--global"])] = False,
    backup: bool = False,
    interactive: Annotated[bool, Parameter(name=["-i", "--interactive"])] = False,
) -> None:
    """Remove detected Rules from the repository or user home.

    Without arguments, an interactive checklist of detected Rules is shown.
    Pass rule names directly to skip the prompt
    (``siesta agents remove rule python-docstrings``).

    Each proposed removal path is confirmed individually before any file is
    deleted.

    Examples
    --------
    .. code-block:: bash

        # Interactive selection
        $ siesta agents remove rule -i

        $ siesta agents remove rule python-docstrings --claude

    Parameters
    ----------
    names : list[str], optional
        Rule names to remove (without extension).
    cursor : bool, optional
        Target the Cursor provider.
    claude : bool, optional
        Target the Claude provider.
    both : bool, optional
        Target both providers (default when no provider flag is given).
    local : bool, optional
        Remove from the current repository (default).
    global_ : bool, optional
        Remove from the user home.
    backup : bool, optional
        Back up targets before removing.
    interactive : bool, optional
        Enable interactive prompts (``-i``).
    """
    # --- Validation phase ---
    scope = resolve_scope(local, global_)
    providers = resolve_providers(cursor, claude, both)
    detected = detect_installed_rules(providers, scope)
    selected = resolve_remove_selection(
        list(names), detected, interactive, kind="rule", providers=providers, scope=scope
    )
    if not selected:
        if detected:
            logger.info("No rules selected; nothing to do.")
        sys.exit(0)

    candidates = _build_removal_candidates(
        selected, providers, scope, rule_target, "rule"
    )

    # --- Prompt collection phase ---
    confirmed, skipped = _confirm_removal_candidates(candidates)

    # --- Execution phase ---
    combined: dict[str, list[str]] = {"removed": [], "skipped": [], "backed_up": []}
    combined["skipped"].extend(skipped)

    confirmed_by_name = _group_confirmed_providers(confirmed)
    for rule_name, confirmed_providers in confirmed_by_name.items():
        result = remove_rule(rule_name, confirmed_providers, scope, backup=backup)
        _merge_removal_summaries(combined, result)

    print_removal_summary(combined)


@remove_app.command(name="constitution")
def remove_constitution_cmd(
    name: str = "",
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
    """Remove detected Constitution files (AGENTS.md / CLAUDE.md).

    Each file is confirmed individually. ``AGENTS.md`` is removed only when it
    matches a bundled Constitution source unless ``--force`` is passed.
    ``CLAUDE.md`` import stubs may be deleted; mixed content keeps the body and
    drops only the ``@AGENTS.md`` import line.

    Examples
    --------
    .. code-block:: bash

        $ siesta agents remove constitution

        $ siesta agents remove constitution --claude --force

    Parameters
    ----------
    name : str, optional
        Unused catalog name placeholder kept for symmetry with ``add constitution``.
    cursor : bool, optional
        Target the Cursor provider.
    claude : bool, optional
        Target the Claude provider.
    both : bool, optional
        Target both providers (default when no provider flag is given).
    local : bool, optional
        Remove from the current repository (default).
    global_ : bool, optional
        Remove from the user home.
    force : bool, optional
        Allow removing user-authored Constitution files after confirmation.
    backup : bool, optional
        Back up targets before removing or rewriting.
    interactive : bool, optional
        Reserved for future selection flows; confirmations are always required.
    """
    del name, interactive  # constitution removal always confirms each file explicitly

    # --- Validation phase ---
    scope = resolve_scope(local, global_)
    providers = resolve_providers(cursor, claude, both)
    agents_path, claude_path = constitution_paths(providers, scope)

    if providers == ["cursor"] and scope == "global":
        logger.warning(
            "Constitution is project-scoped for Cursor; nothing to do globally. "
            "Tip: use --local (default) or --claude to target Claude's global ~/.claude/."
        )
        print_removal_summary({"removed": [], "skipped": [], "backed_up": []})
        return

    # --- Prompt collection phase ---
    confirmed_agents = False
    confirmed_claude = False

    if agents_path and agents_path.exists():
        label = f"AGENTS.md ({_display_path(agents_path)})"
        confirmed_agents = logger.confirm(f"Remove {label}?")

    if claude_path and claude_path.exists():
        label = f"CLAUDE.md ({_display_path(claude_path)})"
        confirmed_claude = logger.confirm(f"Remove {label}?")

    if not confirmed_agents and not confirmed_claude:
        logger.info("No constitution files confirmed; nothing to do.")
        sys.exit(0)

    # --- Execution phase ---
    summary = remove_constitution(
        providers,
        scope,
        force=force,
        backup=backup,
        confirmed_agents=confirmed_agents,
        confirmed_claude=confirmed_claude,
    )
    print_removal_summary(summary)


def _build_removal_candidates(
    names: list[str],
    providers: list[str],
    scope: str,
    target_fn,
    kind: str,
) -> list[tuple[str, Path, str, str]]:
    """Build ``(label, path, name, provider)`` tuples for existing targets."""
    candidates: list[tuple[str, Path, str, str]] = []
    for name in names:
        for provider in providers:
            dest = target_fn(provider, scope, name)
            if dest.exists():
                label = f"{provider} {kind} {name!r} ({_display_path(dest)})"
                candidates.append((label, dest, name, provider))
    return candidates


def _confirm_removal_candidates(
    candidates: list[tuple[str, Path, str, str]],
) -> tuple[list[tuple[str, Path, str, str]], list[str]]:
    """Confirm each candidate; return confirmed tuples and skipped labels."""
    path_candidates = [(label, path) for label, path, _, _ in candidates]
    confirmed_paths, skipped_labels = collect_confirmed_removals(path_candidates)
    confirmed = [
        (label, path, name, provider)
        for label, path, name, provider in candidates
        if path in confirmed_paths
    ]
    return confirmed, skipped_labels


def _group_confirmed_providers(
    confirmed: list[tuple[str, Path, str, str]],
) -> dict[str, list[str]]:
    """Group confirmed removals by asset name and provider list."""
    grouped: dict[str, list[str]] = {}
    for _, _, name, provider in confirmed:
        grouped.setdefault(name, []).append(provider)
    return grouped


def _merge_removal_summaries(
    combined: dict[str, list[str]], result: dict[str, list[str]]
) -> None:
    """Merge one removal summary into *combined*."""
    for key in combined:
        combined[key].extend(result.get(key, []))


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
    Rules, and Constitution.  Equivalent to running ``add skill``,
    ``add rule``, and ``add constitution`` for each listed asset.

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
