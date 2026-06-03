# Copyright 2025 Entalpic
"""Utilities for the ``siesta agents`` commands.

Covers catalog discovery, destination-path resolution, ``.mdc`` → Claude ``.md``
rule translation, conflict-aware file writing, and the constitution install
algorithm.
"""

import json
import shutil
import sys
from importlib.resources import files
from pathlib import Path

from ruamel.yaml import YAML

from siesta.logger import Logger

logger = Logger("siesta")
"""A logger to log messages to the console."""

# ---------------------------------------------------------------------------
# Catalog root
# ---------------------------------------------------------------------------

ASSETS = files("siesta") / "agents_assets"
"""Root of the bundled Agent Asset Catalog."""
SKILLS_DIR = ASSETS / "skills"
RULES_DIR = ASSETS / "rules"
CONSTITUTIONS_DIR = ASSETS / "constitutions"
DEFAULT_CONSTITUTION = "entalpic-default"
IMPORT_LINE = "@AGENTS.md"
QUICKSTART_FILE = ASSETS / "quickstart.yaml"
"""Path to the bundled Quickstart Config (curated default Agent Assets)."""


# ---------------------------------------------------------------------------
# Catalog discovery
# ---------------------------------------------------------------------------


def available_skills() -> list[str]:
    """Return the names of all bundled skills.

    Returns
    -------
    list[str]
        Sorted list of skill names (directory names under ``skills/``).
    """
    return sorted(p.name for p in SKILLS_DIR.iterdir() if p.is_dir())


def available_rules() -> list[str]:
    """Return the names of all bundled rules (without the ``.mdc`` extension).

    Returns
    -------
    list[str]
        Sorted list of rule names.
    """
    return sorted(p.name[:-4] for p in RULES_DIR.iterdir() if p.name.endswith(".mdc"))


def available_constitutions() -> list[str]:
    """Return the names of all bundled constitution templates.

    Returns
    -------
    list[str]
        Sorted list of constitution names (directory names under ``constitutions/``).
    """
    return sorted(p.name for p in CONSTITUTIONS_DIR.iterdir() if p.is_dir())


# ---------------------------------------------------------------------------
# Provider + scope resolution
# ---------------------------------------------------------------------------


def resolve_providers(cursor: bool, claude: bool, both: bool) -> list[str]:
    """Resolve the target Providers from CLI flags.

    Parameters
    ----------
    cursor : bool
        ``--cursor`` flag value.
    claude : bool
        ``--claude`` flag value.
    both : bool
        ``--both`` flag value (or default when none given).

    Returns
    -------
    list[str]
        One or both of ``"cursor"`` and ``"claude"``.
    """
    if both or (not cursor and not claude):
        return ["cursor", "claude"]
    return [p for p, on in (("cursor", cursor), ("claude", claude)) if on]


def resolve_scope(local: bool, global_: bool) -> str:
    """Resolve the Asset Scope from CLI flags.

    Parameters
    ----------
    local : bool
        ``--local`` flag value.
    global_ : bool
        ``--global`` flag value.

    Returns
    -------
    str
        ``"local"`` or ``"global"``.
    """
    if local and global_:
        logger.abort("Cannot use both --local and --global.")
    return "global" if global_ else "local"


def base_dir(provider: str, scope: str) -> Path:
    """Return the Provider root directory for a given scope.

    Parameters
    ----------
    provider : str
        ``"cursor"`` or ``"claude"``.
    scope : str
        ``"local"`` or ``"global"``.

    Returns
    -------
    Path
        ``.cursor/`` or ``.claude/`` under cwd (local) or home (global).
    """
    root = Path.home() if scope == "global" else Path.cwd()
    return root / (".cursor" if provider == "cursor" else ".claude")


# ---------------------------------------------------------------------------
# Target paths
# ---------------------------------------------------------------------------


def skill_target(provider: str, scope: str, name: str) -> Path:
    """Return the destination directory for a skill.

    Parameters
    ----------
    provider : str
        ``"cursor"`` or ``"claude"``.
    scope : str
        ``"local"`` or ``"global"``.
    name : str
        Skill name (must match a directory under ``skills/``).

    Returns
    -------
    Path
        Destination directory path (not yet guaranteed to exist).
    """
    return base_dir(provider, scope) / "skills" / name


def rule_target(provider: str, scope: str, name: str) -> Path:
    """Return the destination file path for a rule.

    Parameters
    ----------
    provider : str
        ``"cursor"`` or ``"claude"``.
    scope : str
        ``"local"`` or ``"global"``.
    name : str
        Rule name (without extension).

    Returns
    -------
    Path
        Destination file path (``.mdc`` for Cursor, ``.md`` for Claude).
    """
    ext = "mdc" if provider == "cursor" else "md"
    return base_dir(provider, scope) / "rules" / f"{name}.{ext}"


# ---------------------------------------------------------------------------
# .mdc → Claude .md translation
# ---------------------------------------------------------------------------


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Split a Markdown file into its YAML frontmatter dict and body text.

    Parameters
    ----------
    text : str
        Raw file content.

    Returns
    -------
    tuple[dict, str]
        ``(frontmatter_dict, body)`` where ``frontmatter_dict`` is empty when
        the file has no frontmatter block.
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    _, fm_block, body = parts
    fm = YAML(typ="safe", pure=True).load(fm_block) or {}
    return fm, body.lstrip("\n")


def _split_globs(value: str) -> list[str]:
    """Split a Cursor ``globs`` string into individual patterns.

    Cursor uses commas to separate multiple globs, but a single brace-expansion
    glob (e.g. ``**/*.{py,js}``) also contains commas. Split only on commas at
    brace-nesting depth 0 so brace groups stay intact.

    Parameters
    ----------
    value : str
        Raw comma-separated ``globs`` value.

    Returns
    -------
    list[str]
        Individual glob patterns, stripped of surrounding whitespace.
    """
    patterns: list[str] = []
    depth = 0
    current = ""
    for char in value:
        if char == "{":
            depth += 1
        elif char == "}":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            if current.strip():
                patterns.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        patterns.append(current.strip())
    return patterns


def mdc_to_claude(text: str) -> str:
    """Translate a Cursor ``.mdc`` rule to Claude ``.md`` format.

    Translation rules:

    - ``globs`` → ``paths`` as a YAML list (comma-separated strings are split).
    - ``alwaysApply: true`` or absent ``globs`` → no ``paths`` field (loads every
      session).
    - ``alwaysApply: false`` + ``globs`` → ``paths`` derived from ``globs``.
    - ``description`` is dropped (Claude rule frontmatter only documents ``paths``).
    - Body markdown is copied verbatim.

    Parameters
    ----------
    text : str
        Raw ``.mdc`` file content.

    Returns
    -------
    str
        Translated ``.md`` content for Claude.
    """
    fm, body = _split_frontmatter(text)
    globs = fm.get("globs")
    always = bool(fm.get("alwaysApply"))
    paths: list[str] | None = None
    if not always and globs:
        if isinstance(globs, str):
            paths = _split_globs(globs)
        elif isinstance(globs, list):
            paths = [str(g) for g in globs]
    if paths:
        # json.dumps produces a valid double-quoted YAML scalar, escaping any
        # quotes/backslashes a glob might contain.
        front = (
            "---\npaths:\n"
            + "".join(f"  - {json.dumps(p)}\n" for p in paths)
            + "---\n\n"
        )
        return front + body
    return body


# ---------------------------------------------------------------------------
# Selection resolution
# ---------------------------------------------------------------------------


def resolve_selection(
    names: list[str],
    all_flag: bool,
    available: list[str],
    interactive: bool,
    kind: str,
) -> list[str]:
    """Resolve the final list of catalog items to install.

    Follows Input Precedence: explicit names win; ``--all`` uses the full catalog;
    otherwise an interactive checkbox is shown (or the command aborts when stdin
    is not a tty).

    Parameters
    ----------
    names : list[str]
        Explicit names provided on the CLI.
    all_flag : bool
        Whether ``--all`` was passed.
    available : list[str]
        All catalog item names of this kind.
    interactive : bool
        Whether ``-i``/``--interactive`` was passed.
    kind : str
        Human-readable kind label used in messages (``"skill"`` or ``"rule"``).

    Returns
    -------
    list[str]
        Resolved list of item names to install (may be empty → No-Op).
    """
    if names and all_flag:
        logger.abort(f"--all and explicit {kind} names are mutually exclusive.")
    if all_flag:
        return list(available)
    if names:
        unknown = [n for n in names if n not in available]
        if unknown:
            logger.abort(f"Unknown {kind}(s): {unknown}. Available: {available}")
        return list(names)
    # Interactive selection needs a real terminal, regardless of how it was
    # requested. An explicit -i with no TTY is a broken invocation worth
    # surfacing rather than letting questionary hang or crash.
    if not sys.stdin.isatty():
        if interactive:
            logger.abort("Interactive selection requires a terminal (no TTY).")
        logger.abort(
            f"No {kind}s specified. Pass names, --all, or use -i for interactive mode."
        )
    return logger.checkbox(f"Select {kind}s to add:", available)


# ---------------------------------------------------------------------------
# Conflict-aware writer
# ---------------------------------------------------------------------------

_Action = str  # "write" | "overwrite" | "backup_write" | "skip"


def _decide_action(
    dest: Path,
    force: bool,
    backup: bool,
    interactive: bool,
    label: str,
) -> _Action:
    """Decide how to handle a potential conflict at *dest*.

    Parameters
    ----------
    dest : Path
        Destination path (file or directory).
    force : bool
        Whether ``--force`` was passed.
    backup : bool
        Whether ``--backup`` was passed.
    interactive : bool
        Whether ``-i``/``--interactive`` was passed.
    label : str
        Human-readable label for prompts (e.g. the relative destination path).

    Returns
    -------
    str
        One of ``"write"``, ``"overwrite"``, ``"backup_write"``, or ``"skip"``.
    """
    if not dest.exists():
        return "write"
    if force:
        return "backup_write" if backup else "overwrite"
    if interactive:
        choice = logger.select(
            f"{label} already exists. What to do?",
            ["skip", "overwrite", "backup and overwrite"],
        )
        if choice == "backup and overwrite":
            return "backup_write"
        return choice  # "skip" or "overwrite"
    return "skip"


def _apply_backup(dest: Path) -> None:
    """Rename *dest* to ``dest.bak`` (overwriting any previous backup).

    Parameters
    ----------
    dest : Path
        Path to back up.
    """
    bak = dest.parent / (dest.name + ".bak")
    if bak.exists():
        if bak.is_dir():
            shutil.rmtree(bak)
        else:
            bak.unlink()
    dest.rename(bak)


def write_file(
    src: Path,
    dest: Path,
    *,
    content_override: str | None = None,
    force: bool = False,
    backup: bool = False,
    interactive: bool = False,
    label: str | None = None,
) -> _Action:
    """Write a single file from *src* to *dest*, respecting the conflict policy.

    Parameters
    ----------
    src : Path
        Source file (unused when *content_override* is given).
    dest : Path
        Destination file path.
    content_override : str, optional
        When given, write this string instead of reading *src*.
    force : bool, optional
        Overwrite without prompting.
    backup : bool, optional
        Back up the existing file before overwriting.
    interactive : bool, optional
        Prompt the user when a conflict exists.
    label : str, optional
        Display label for conflict prompts; defaults to the dest filename.

    Returns
    -------
    str
        The action taken (``"write"``, ``"overwrite"``, ``"backup_write"``, or
        ``"skip"``).
    """
    display = label or dest.name
    action = _decide_action(dest, force, backup, interactive, display)
    if action == "skip":
        return "skip"
    if action == "backup_write":
        _apply_backup(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if content_override is not None:
        dest.write_text(content_override, encoding="utf-8")
    else:
        shutil.copy2(str(src), str(dest))
    return action


def write_dir(
    src: Path,
    dest: Path,
    *,
    force: bool = False,
    backup: bool = False,
    interactive: bool = False,
    label: str | None = None,
) -> _Action:
    """Copy a directory from *src* to *dest*, respecting the conflict policy.

    Parameters
    ----------
    src : Path
        Source directory.
    dest : Path
        Destination directory.
    force : bool, optional
        Overwrite without prompting.
    backup : bool, optional
        Back up the existing directory before overwriting.
    interactive : bool, optional
        Prompt the user when a conflict exists.
    label : str, optional
        Display label for conflict prompts.

    Returns
    -------
    str
        The action taken.
    """
    display = label or dest.name
    action = _decide_action(dest, force, backup, interactive, display)
    if action == "skip":
        return "skip"
    if action == "backup_write" and dest.exists():
        _apply_backup(dest)
    elif action == "overwrite" and dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(src), str(dest))
    return action


# ---------------------------------------------------------------------------
# High-level install helpers (called by CLI commands)
# ---------------------------------------------------------------------------


def install_skill(
    name: str,
    providers: list[str],
    scope: str,
    *,
    force: bool = False,
    backup: bool = False,
    interactive: bool = False,
) -> dict[str, list[str]]:
    """Install a single skill for every requested Provider.

    Parameters
    ----------
    name : str
        Skill name (must exist in the catalog).
    providers : list[str]
        Target Providers (``"cursor"`` and/or ``"claude"``).
    scope : str
        ``"local"`` or ``"global"``.
    force : bool, optional
        Overwrite existing targets without prompting.
    backup : bool, optional
        Back up existing targets before overwriting.
    interactive : bool, optional
        Prompt on conflict.

    Returns
    -------
    dict[str, list[str]]
        ``{"written": [...], "skipped": [...], "backed_up": [...]}``
    """
    src = Path(str(SKILLS_DIR / name))
    summary: dict[str, list[str]] = {"written": [], "skipped": [], "backed_up": []}
    for provider in providers:
        dest = skill_target(provider, scope, name)
        action = write_dir(
            src,
            dest,
            force=force,
            backup=backup,
            interactive=interactive,
            label=f"{provider}: {dest}",
        )
        _record(summary, action, str(dest))
    return summary


def install_rule(
    name: str,
    providers: list[str],
    scope: str,
    *,
    force: bool = False,
    backup: bool = False,
    interactive: bool = False,
) -> dict[str, list[str]]:
    """Install a single rule for every requested Provider.

    Parameters
    ----------
    name : str
        Rule name (without extension).
    providers : list[str]
        Target Providers.
    scope : str
        ``"local"`` or ``"global"``.
    force : bool, optional
        Overwrite without prompting.
    backup : bool, optional
        Back up before overwriting.
    interactive : bool, optional
        Prompt on conflict.

    Returns
    -------
    dict[str, list[str]]
        ``{"written": [...], "skipped": [...], "backed_up": [...]}``
    """
    src = Path(str(RULES_DIR / f"{name}.mdc"))
    raw = src.read_text(encoding="utf-8")
    summary: dict[str, list[str]] = {"written": [], "skipped": [], "backed_up": []}
    for provider in providers:
        dest = rule_target(provider, scope, name)
        content = raw if provider == "cursor" else mdc_to_claude(raw)
        action = write_file(
            src,
            dest,
            content_override=content,
            force=force,
            backup=backup,
            interactive=interactive,
            label=f"{provider}: {dest}",
        )
        _record(summary, action, str(dest))
    return summary


def install_constitution(
    name: str,
    providers: list[str],
    scope: str,
    *,
    force: bool = False,
    backup: bool = False,
    interactive: bool = False,
) -> dict[str, list[str]]:
    """Install a constitution for the requested Providers.

    ``AGENTS.md`` is always written (Cursor compatibility; harmless for Claude).
    ``CLAUDE.md`` (an ``@AGENTS.md`` import stub) is written only when ``claude``
    is in *providers*.  If a ``CLAUDE.md`` already exists, the command appends the
    import line rather than overwriting, subject to the usual conflict policy.

    Parameters
    ----------
    name : str
        Constitution template name (directory under ``constitutions/``).
    providers : list[str]
        Target Providers.
    scope : str
        ``"local"`` or ``"global"``.
    force : bool, optional
        Overwrite / force-append without prompting.
    backup : bool, optional
        Back up before overwriting.
    interactive : bool, optional
        Prompt on conflict.

    Returns
    -------
    dict[str, list[str]]
        ``{"written": [...], "skipped": [...], "backed_up": [...]}``
    """
    summary: dict[str, list[str]] = {"written": [], "skipped": [], "backed_up": []}
    src_dir = Path(str(CONSTITUTIONS_DIR / name))

    # Global + cursor-only: Cursor has no global AGENTS.md concept → skip with warning.
    if providers == ["cursor"] and scope == "global":
        logger.warning(
            "Constitution is project-scoped for Cursor; nothing to do globally. "
            "Tip: use --local (default) or --claude to target Claude's global ~/.claude/."
        )
        return summary

    # Determine write roots.
    if scope == "local":
        agents_dest = Path.cwd() / "AGENTS.md"
        claude_dest = Path.cwd() / "CLAUDE.md"
    else:
        # global: only Claude pair lives under ~/.claude/
        agents_dest = Path.home() / ".claude" / "AGENTS.md"
        claude_dest = Path.home() / ".claude" / "CLAUDE.md"

    # 1) AGENTS.md — always written regardless of provider.
    agents_src = src_dir / "AGENTS.md"
    action = write_file(
        agents_src,
        agents_dest,
        force=force,
        backup=backup,
        interactive=interactive,
        label="AGENTS.md",
    )
    _record(summary, action, str(agents_dest))
    if action != "skip":
        logger.info(
            "AGENTS.md written (Cursor compatibility; not required by Claude itself)."
        )

    # 2) CLAUDE.md stub — only when claude is targeted.
    if "claude" not in providers:
        return summary

    if not claude_dest.exists():
        claude_src = src_dir / "CLAUDE.md"
        action = write_file(
            claude_src,
            claude_dest,
            force=False,  # fresh write, no conflict
            backup=False,
            interactive=False,
            label="CLAUDE.md",
        )
        _record(summary, action, str(claude_dest))
    else:
        existing = claude_dest.read_text(encoding="utf-8")
        if IMPORT_LINE in existing:
            logger.info("CLAUDE.md already imports AGENTS.md; nothing to do.")
        else:
            _handle_claude_import(
                claude_dest,
                existing,
                force=force,
                interactive=interactive,
                summary=summary,
            )

    return summary


def _handle_claude_import(
    claude_dest: Path,
    existing: str,
    *,
    force: bool,
    interactive: bool,
    summary: dict[str, list[str]],
) -> None:
    """Prepend the ``@AGENTS.md`` import to an existing ``CLAUDE.md`` if approved.

    Parameters
    ----------
    claude_dest : Path
        Path to the existing CLAUDE.md.
    existing : str
        Current content of CLAUDE.md.
    force : bool
        Prepend without prompting when True.
    interactive : bool
        Prompt the user when True.
    summary : dict[str, list[str]]
        Mutable summary dict to record the outcome.
    """
    do_prepend = False
    if interactive:
        do_prepend = logger.confirm(
            f"CLAUDE.md exists but is missing `{IMPORT_LINE}`. Prepend the import? "
            "(Content will be preserved.)"
        )
    elif force:
        do_prepend = True
    else:
        logger.warning(
            f"CLAUDE.md exists but has no `{IMPORT_LINE}` import. "
            "Skipped. Add `@AGENTS.md` at the top of CLAUDE.md manually to link it."
        )

    if do_prepend:
        claude_dest.write_text(f"{IMPORT_LINE}\n\n{existing}", encoding="utf-8")
        summary["written"].append(str(claude_dest) + " (import prepended)")


# ---------------------------------------------------------------------------
# Quickstart Config loader + installer
# ---------------------------------------------------------------------------


def load_quickstart() -> dict:
    """Load the bundled Quickstart Config from ``agents_assets/quickstart.yaml``.

    Returns a normalized dict with missing or empty categories defaulting to
    an empty list / ``None`` so callers can treat them as No-Ops.

    Returns
    -------
    dict
        ``{"skills": list[str], "rules": list[str], "constitution": str | None}``

    Examples
    --------
    .. code-block:: python

        cfg = load_quickstart()
        # {"skills": ["grill-with-docs"], "rules": [...], "constitution": "entalpic-default"}
    """
    raw = Path(str(QUICKSTART_FILE)).read_text(encoding="utf-8")
    data = YAML(typ="safe", pure=True).load(raw) or {}
    return {
        "skills": list(data.get("skills") or []),
        "rules": list(data.get("rules") or []),
        "constitution": data.get("constitution") or None,
    }


def install_quickstart(
    providers: list[str],
    scope: str,
    *,
    force: bool = False,
    backup: bool = False,
    interactive: bool = False,
) -> dict[str, list[str]]:
    """Install all Agent Assets declared in the Quickstart Config.

    Reads the bundled ``agents_assets/quickstart.yaml``, validates every
    listed name against the catalog (fail-fast), then delegates to
    :func:`install_skill`, :func:`install_rule`, and
    :func:`install_constitution`.

    Parameters
    ----------
    providers : list[str]
        Target Providers (``"cursor"`` and/or ``"claude"``).
    scope : str
        ``"local"`` or ``"global"``.
    force : bool, optional
        Overwrite existing targets without prompting.
    backup : bool, optional
        Back up existing targets before overwriting.
    interactive : bool, optional
        Prompt on conflict.

    Returns
    -------
    dict[str, list[str]]
        ``{"written": [...], "skipped": [...], "backed_up": [...]}``
    """
    cfg = load_quickstart()

    # Validation phase: abort before any write if the config references unknown assets.
    unknown_skills = [s for s in cfg["skills"] if s not in available_skills()]
    if unknown_skills:
        logger.abort(
            f"Quickstart Config references unknown skill(s): {unknown_skills}. "
            f"Available: {available_skills()}"
        )

    unknown_rules = [r for r in cfg["rules"] if r not in available_rules()]
    if unknown_rules:
        logger.abort(
            f"Quickstart Config references unknown rule(s): {unknown_rules}. "
            f"Available: {available_rules()}"
        )

    if cfg["constitution"] and cfg["constitution"] not in available_constitutions():
        logger.abort(
            f"Quickstart Config references unknown constitution: {cfg['constitution']!r}. "
            f"Available: {available_constitutions()}"
        )

    # Execution phase: install each category, merging results into one summary.
    combined: dict[str, list[str]] = {"written": [], "skipped": [], "backed_up": []}
    for name in cfg["skills"]:
        result = install_skill(
            name, providers, scope, force=force, backup=backup, interactive=interactive
        )
        for key in combined:
            combined[key].extend(result.get(key, []))

    for name in cfg["rules"]:
        result = install_rule(
            name, providers, scope, force=force, backup=backup, interactive=interactive
        )
        for key in combined:
            combined[key].extend(result.get(key, []))

    if cfg["constitution"]:
        result = install_constitution(
            cfg["constitution"],
            providers,
            scope,
            force=force,
            backup=backup,
            interactive=interactive,
        )
        for key in combined:
            combined[key].extend(result.get(key, []))

    return combined


# ---------------------------------------------------------------------------
# Shared summary helpers
# ---------------------------------------------------------------------------


def _record(summary: dict[str, list[str]], action: str, path: str) -> None:
    """Record an install action in the summary dict.

    Parameters
    ----------
    summary : dict[str, list[str]]
        Mutable summary dict with keys ``"written"``, ``"skipped"``,
        ``"backed_up"``.
    action : str
        One of ``"write"``, ``"overwrite"``, ``"backup_write"``, or ``"skip"``.
    path : str
        The destination path string to record.
    """
    if action in ("write", "overwrite"):
        summary["written"].append(path)
    elif action == "backup_write":
        summary["backed_up"].append(path)
    elif action == "skip":
        summary["skipped"].append(path)


def print_summary(summary: dict[str, list[str]]) -> None:
    """Print a Rich install summary.

    Parameters
    ----------
    summary : dict[str, list[str]]
        ``{"written": [...], "skipped": [...], "backed_up": [...]}``
    """
    written = summary.get("written", [])
    skipped = summary.get("skipped", [])
    backed_up = summary.get("backed_up", [])

    if written:
        for path in written:
            logger.success(f"Written: {path}")
    if backed_up:
        for path in backed_up:
            logger.info(f"Backed up + written: {path}")
    if skipped:
        for path in skipped:
            logger.warning(f"Skipped (already exists): {path}")
    if not written and not backed_up and not skipped:
        logger.info("Nothing to do.")
