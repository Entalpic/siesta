# Copyright 2025 Entalpic
"""Utilities for the ``siesta agents`` commands.

Covers catalog discovery, destination-path resolution, ``.mdc`` → Claude ``.md``
rule translation, conflict-aware file writing, and the constitution install
algorithm.
"""

import json
import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from ruamel.yaml import YAML

from siesta.utils.common import logger
from siesta.utils.conflicts import (
    Conflict,
    Mutation,
    OperationSummary,
    Resolution,
    apply_backup,
    run_mutations,
    write_path,
)

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


def _display_path(path: Path | str) -> str:
    """Return a filesystem path as a CWD-relative display string.

    Parameters
    ----------
    path : Path | str
        Filesystem path to show in CLI prompts and summaries.

    Returns
    -------
    str
        ``path`` rendered relative to the current working directory.
    """
    cwd = Path.cwd()
    target = Path(path)
    if not target.is_absolute():
        target = cwd / target

    if target.anchor != cwd.anchor:
        return str(target)

    cwd_parts = cwd.parts
    target_parts = target.parts
    common = 0
    for cwd_part, target_part in zip(cwd_parts, target_parts, strict=False):
        if cwd_part != target_part:
            break
        common += 1

    parents = [".."] * (len(cwd_parts) - common)
    return str(Path(*parents, *target_parts[common:]))


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
    global\\_ : bool
        ``--global`` flag value.

    Returns
    -------
    str
        ``"local"`` or ``"global"``.
    """
    if local and global_:
        logger.abort("Cannot use both --local and --global.")
    return "global" if global_ else "local"


def scope_display_label(scope: str) -> str:
    """Return a human-readable Asset Scope label for CLI messages.

    Parameters
    ----------
    scope : str
        ``"local"`` or ``"global"``.

    Returns
    -------
    str
        Scope label including a short parenthetical explanation.
    """
    if scope == "global":
        return "global (user home)"
    return "local (current repository)"


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
    scope: str,
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
    scope : str
        Asset Scope (``"local"`` or ``"global"``) shown in the selection prompt.

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
    if not available:
        return []
    prompt = f"Select {kind}s to add — {scope_display_label(scope)}:"
    return logger.checkbox(prompt, available)


# ---------------------------------------------------------------------------
# Mutation-based install helpers
# ---------------------------------------------------------------------------

_STD_OPTIONS = frozenset(
    {Resolution.SKIP, Resolution.OVERWRITE, Resolution.BACKUP, Resolution.ABORT}
)


def _record_write(summary: OperationSummary, action: Resolution, path: str) -> None:
    if action is Resolution.BACKUP:
        summary.backed_up.append(path)
    elif action is not Resolution.SKIP:
        summary.written.append(path)


@dataclass
class SkillMutation:
    name: str
    providers: list[str]
    scope: str

    def detect_conflicts(self) -> list[Conflict]:
        conflicts: list[Conflict] = []
        for provider in self.providers:
            dest = skill_target(provider, self.scope, self.name)
            if dest.exists():
                conflicts.append(
                    Conflict(
                        key=f"skill:{self.name}:{provider}",
                        name=f"{provider}: {_display_path(dest)}",
                        options=_STD_OPTIONS,
                    )
                )
        return conflicts

    def apply(self, resolutions: Mapping[str, Resolution]) -> OperationSummary:
        summary = OperationSummary()
        src = Path(str(SKILLS_DIR / self.name))
        for provider in self.providers:
            dest = skill_target(provider, self.scope, self.name)
            key = f"skill:{self.name}:{provider}"
            resolution = resolutions.get(key, Resolution.OVERWRITE)
            if resolution is Resolution.SKIP:
                summary.skipped.append(_display_path(dest))
                continue
            action = write_path(src, dest, resolution)
            _record_write(summary, action, _display_path(dest))
        return summary


@dataclass
class RuleMutation:
    name: str
    providers: list[str]
    scope: str

    def detect_conflicts(self) -> list[Conflict]:
        conflicts: list[Conflict] = []
        for provider in self.providers:
            dest = rule_target(provider, self.scope, self.name)
            if dest.exists():
                conflicts.append(
                    Conflict(
                        key=f"rule:{self.name}:{provider}",
                        name=f"{provider}: {_display_path(dest)}",
                        options=_STD_OPTIONS,
                    )
                )
        return conflicts

    def apply(self, resolutions: Mapping[str, Resolution]) -> OperationSummary:
        summary = OperationSummary()
        src = Path(str(RULES_DIR / f"{self.name}.mdc"))
        raw = src.read_text(encoding="utf-8")
        for provider in self.providers:
            dest = rule_target(provider, self.scope, self.name)
            key = f"rule:{self.name}:{provider}"
            resolution = resolutions.get(key, Resolution.OVERWRITE)
            if resolution is Resolution.SKIP:
                summary.skipped.append(_display_path(dest))
                continue
            content = raw if provider == "cursor" else mdc_to_claude(raw)
            action = write_path(src, dest, resolution, content_override=content)
            _record_write(summary, action, _display_path(dest))
        return summary


@dataclass
class ConstitutionMutation:
    name: str
    providers: list[str]
    scope: str

    def _destinations(self) -> tuple[Path, Path]:
        if self.scope == "local":
            return Path.cwd() / "AGENTS.md", Path.cwd() / "CLAUDE.md"
        return (
            Path.home() / ".claude" / "AGENTS.md",
            Path.home() / ".claude" / "CLAUDE.md",
        )

    def detect_conflicts(self) -> list[Conflict]:
        if self.providers == ["cursor"] and self.scope == "global":
            return []
        agents_dest, claude_dest = self._destinations()
        conflicts: list[Conflict] = []
        if agents_dest.exists():
            conflicts.append(
                Conflict(
                    key="constitution:agents",
                    name="AGENTS.md",
                    options=_STD_OPTIONS,
                )
            )
        if "claude" in self.providers and claude_dest.exists():
            existing = claude_dest.read_text(encoding="utf-8")
            if IMPORT_LINE not in existing:
                conflicts.append(
                    Conflict(
                        key="constitution:claude",
                        name=f"CLAUDE.md ({_display_path(claude_dest)})",
                        options=frozenset(
                            {Resolution.SKIP, Resolution.MERGE, Resolution.ABORT}
                        ),
                    )
                )
        return conflicts

    def apply(self, resolutions: Mapping[str, Resolution]) -> OperationSummary:
        summary = OperationSummary()
        if self.providers == ["cursor"] and self.scope == "global":
            logger.warning(
                "Constitution is project-scoped for Cursor; nothing to do globally. "
                "Tip: use --local (default) or --claude to target Claude's global ~/.claude/."
            )
            return summary

        src_dir = Path(str(CONSTITUTIONS_DIR / self.name))
        agents_dest, claude_dest = self._destinations()

        agents_resolution = resolutions.get("constitution:agents", Resolution.OVERWRITE)
        if agents_resolution is not Resolution.SKIP:
            action = write_path(src_dir / "AGENTS.md", agents_dest, agents_resolution)
            _record_write(summary, action, _display_path(agents_dest))
            logger.info(
                "AGENTS.md written (Cursor compatibility; not required by Claude itself)."
            )
        else:
            summary.skipped.append(_display_path(agents_dest))

        if "claude" not in self.providers:
            return summary

        if not claude_dest.exists():
            action = write_path(
                src_dir / "CLAUDE.md", claude_dest, Resolution.OVERWRITE
            )
            _record_write(summary, action, _display_path(claude_dest))
        else:
            existing = claude_dest.read_text(encoding="utf-8")
            if IMPORT_LINE in existing:
                logger.info("CLAUDE.md already imports AGENTS.md; nothing to do.")
            else:
                claude_resolution = resolutions.get("constitution:claude")
                if claude_resolution is Resolution.SKIP:
                    summary.skipped.append(_display_path(claude_dest))
                elif claude_resolution is Resolution.MERGE:
                    claude_dest.write_text(
                        f"{IMPORT_LINE}\n\n{existing}", encoding="utf-8"
                    )
                    summary.merged.append(_display_path(claude_dest))
                else:
                    action = write_path(
                        src_dir / "CLAUDE.md",
                        claude_dest,
                        claude_resolution or Resolution.OVERWRITE,
                    )
                    _record_write(summary, action, _display_path(claude_dest))

        return summary


def quickstart_asset_mutations(
    providers: list[str], scope: str, cfg: Mapping[str, object] | None = None
) -> list[Mutation]:
    """Build mutations for every selected asset from the Quickstart Config."""
    if cfg is None:
        cfg = load_quickstart()

    skills = list(cfg["skills"])
    rules = list(cfg["rules"])
    constitution = cfg["constitution"]

    unknown_skills = [s for s in skills if s not in available_skills()]
    if unknown_skills:
        logger.abort(
            f"Quickstart Config references unknown skill(s): {unknown_skills}. "
            f"Available: {available_skills()}"
        )

    unknown_rules = [r for r in rules if r not in available_rules()]
    if unknown_rules:
        logger.abort(
            f"Quickstart Config references unknown rule(s): {unknown_rules}. "
            f"Available: {available_rules()}"
        )

    if constitution and constitution not in available_constitutions():
        logger.abort(
            f"Quickstart Config references unknown constitution: {constitution!r}. "
            f"Available: {available_constitutions()}"
        )

    mutations: list[Mutation] = []
    for name in skills:
        mutations.append(SkillMutation(name, providers, scope))
    for name in rules:
        mutations.append(RuleMutation(name, providers, scope))
    if constitution:
        mutations.append(ConstitutionMutation(str(constitution), providers, scope))
    return mutations


def install_quickstart(
    providers: list[str],
    scope: str,
    *,
    overwrite: bool | None = None,
    backup: bool = False,
    cfg: Mapping[str, object] | None = None,
) -> OperationSummary:
    """Install all Agent Assets declared in the Quickstart Config."""
    mutations = quickstart_asset_mutations(providers, scope, cfg)
    return run_mutations(
        mutations,
        overwrite=overwrite,
        backup=backup,
    )


# ---------------------------------------------------------------------------
# Quickstart Config loader
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


# ---------------------------------------------------------------------------
# Installed asset detection + removal
# ---------------------------------------------------------------------------


def detect_installed_skills(providers: list[str], scope: str) -> list[str]:
    """Return sorted names of installed Skills for the given Providers and scope.

    Parameters
    ----------
    providers : list[str]
        Target Providers (``"cursor"`` and/or ``"claude"``).
    scope : str
        ``"local"`` or ``"global"``.

    Returns
    -------
    list[str]
        Sorted skill names found under any selected Provider.
    """
    names: set[str] = set()
    for provider in providers:
        skills_dir = base_dir(provider, scope) / "skills"
        if not skills_dir.is_dir():
            continue
        for child in skills_dir.iterdir():
            if child.is_dir():
                names.add(child.name)
    return sorted(names)


def asset_search_paths(providers: list[str], scope: str, kind: str) -> list[str]:
    """Return display paths scanned when detecting installed assets.

    Parameters
    ----------
    providers : list[str]
        Target Providers (``"cursor"`` and/or ``"claude"``).
    scope : str
        ``"local"`` or ``"global"``.
    kind : str
        Asset kind label (``"skill"`` or ``"rule"``).

    Returns
    -------
    list[str]
        CWD-relative paths to each Provider's skills or rules directory.
    """
    subdir = "skills" if kind == "skill" else "rules"
    return [_display_path(base_dir(provider, scope) / subdir) for provider in providers]


def detect_installed_rules(providers: list[str], scope: str) -> list[str]:
    """Return sorted names of installed Rules for the given Providers and scope.

    Parameters
    ----------
    providers : list[str]
        Target Providers (``"cursor"`` and/or ``"claude"``).
    scope : str
        ``"local"`` or ``"global"``.

    Returns
    -------
    list[str]
        Sorted rule names (without extension) found under any selected Provider.
    """
    names: set[str] = set()
    for provider in providers:
        rules_dir = base_dir(provider, scope) / "rules"
        if not rules_dir.is_dir():
            continue
        suffix = ".mdc" if provider == "cursor" else ".md"
        for child in rules_dir.iterdir():
            if child.is_file() and child.name.endswith(suffix):
                names.add(child.name[: -len(suffix)])
    return sorted(names)


def constitution_paths(
    providers: list[str], scope: str
) -> tuple[Path | None, Path | None]:
    """Return Constitution file paths for the selected Providers and scope.

    Parameters
    ----------
    providers : list[str]
        Target Providers.
    scope : str
        ``"local"`` or ``"global"``.

    Returns
    -------
    tuple[Path | None, Path | None]
        ``(agents_path, claude_path)`` where either entry may be ``None`` when
        not applicable for the selected Provider/scope combination.
    """
    if providers == ["cursor"] and scope == "global":
        return None, None

    if scope == "local":
        agents_path = Path.cwd() / "AGENTS.md"
        claude_path = Path.cwd() / "CLAUDE.md" if "claude" in providers else None
        return agents_path, claude_path

    agents_path = Path.home() / ".claude" / "AGENTS.md"
    claude_path = (
        Path.home() / ".claude" / "CLAUDE.md" if "claude" in providers else None
    )
    return agents_path, claude_path


def constitution_claude_counterpart_path(scope: str) -> Path:
    """Return the ``CLAUDE.md`` path that may import ``AGENTS.md`` for *scope*.

    Unlike :func:`constitution_paths`, this ignores the selected Providers so
    local ``--cursor`` removals still detect a project-level ``CLAUDE.md``.
    """
    if scope == "local":
        return Path.cwd() / "CLAUDE.md"
    return Path.home() / ".claude" / "CLAUDE.md"


def claude_md_imports_agents(path: Path) -> bool:
    """Return whether *path* exists and contains the ``@AGENTS.md`` import line."""
    if not path.exists():
        return False
    return IMPORT_LINE in path.read_text(encoding="utf-8")


def agents_md_is_removable(path: Path, *, force: bool = False) -> bool:
    """Return whether *path* would be removed by :func:`remove_constitution_file`."""
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    return content in _catalog_agents_md_contents() or force


def agents_removal_would_break_claude_import(
    scope: str,
    agents_path: Path,
    *,
    force: bool = False,
    confirmed_claude: bool = False,
) -> bool:
    """Return whether removing *agents_path* alone would break a ``CLAUDE.md`` import."""
    if confirmed_claude:
        return False
    if not agents_md_is_removable(agents_path, force=force):
        return False
    return claude_md_imports_agents(constitution_claude_counterpart_path(scope))


def resolve_remove_selection(
    names: list[str],
    detected: list[str],
    interactive: bool,
    kind: str,
    providers: list[str],
    scope: str,
) -> list[str]:
    """Resolve which installed asset names to consider for removal.

    Follows the same Input Precedence as :func:`resolve_selection`: explicit
    names win; otherwise an interactive checkbox is shown on a TTY (or the
    command aborts when stdin is not a tty).

    Parameters
    ----------
    names : list[str]
        Explicit names from the CLI.
    detected : list[str]
        Names detected on disk for the selected Providers and scope.
    interactive : bool
        Whether ``-i``/``--interactive`` was passed.
    kind : str
        Human-readable kind label (``"skill"`` or ``"rule"``).
    providers : list[str]
        Target Providers used for search-path disclosure in abort messages.
    scope : str
        Asset Scope (``"local"`` or ``"global"``) for search-path disclosure.

    Returns
    -------
    list[str]
        Asset names to evaluate for removal (may be empty).
    """
    search_paths = asset_search_paths(providers, scope, kind)
    searching = ", ".join(search_paths)
    scope_label = scope_display_label(scope)

    if names:
        missing = [n for n in names if n not in detected]
        if missing:
            logger.abort(
                f"No installed {kind}(s) found: {missing}. "
                f"Scope: {scope_label}. "
                f"Searching: {searching}. "
                f"Detected: {detected or '(none)'}"
            )
        return list(names)

    if not sys.stdin.isatty():
        if interactive:
            logger.abort("Interactive selection requires a terminal (no TTY).")
        logger.abort(
            f"No {kind}s specified. Pass names to remove, or use -i for "
            f"interactive mode.\n"
            f"Scope: {scope_label}\n"
            f"Searching: {searching}\n"
            f"Detected: {detected or '(none)'}"
        )
    if not detected:
        logger.info(
            f"No installed {kind}s found.\nScope: {scope_label}\nSearching: {searching}"
        )
        return []
    prompt = f"Select {kind}s to remove — {scope_label}:"
    return logger.checkbox(prompt, detected)


def collect_confirmed_removals(
    candidates: list[tuple[str, Path]],
) -> tuple[list[Path], list[str]]:
    """Confirm each removal candidate before any Mutation.

    Parameters
    ----------
    candidates : list[tuple[str, Path]]
        ``(display_label, path)`` pairs proposed for removal.

    Returns
    -------
    tuple[list[Path], list[str]]
        Confirmed paths and skipped display labels.
    """
    confirmed: list[Path] = []
    skipped: list[str] = []
    for label, path in candidates:
        if logger.confirm(f"Remove {label}?"):
            confirmed.append(path)
        else:
            skipped.append(label)
    return confirmed, skipped


def _catalog_agents_md_contents() -> set[str]:
    """Return the exact ``AGENTS.md`` contents of every bundled Constitution."""
    contents: set[str] = set()
    for name in available_constitutions():
        src = Path(str(CONSTITUTIONS_DIR / name / "AGENTS.md"))
        contents.add(src.read_text(encoding="utf-8"))
    return contents


def _claude_md_is_import_stub(content: str) -> bool:
    """Return whether *content* is only the ``@AGENTS.md`` import stub."""
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    return lines == [IMPORT_LINE]


def _strip_agents_import(content: str) -> str:
    """Remove ``@AGENTS.md`` import lines from *content*, preserving the rest."""
    kept = [line for line in content.splitlines() if line.strip() != IMPORT_LINE]
    return "\n".join(kept).strip("\n")


def remove_path(path: Path, *, backup: bool = False) -> Resolution:
    """Remove a file or directory, optionally backing it up first."""
    if backup:
        apply_backup(path)
        return Resolution.BACKUP
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return Resolution.OVERWRITE


def _record_removal(
    summary: OperationSummary, action: Resolution | str, path: str
) -> None:
    if action in (Resolution.OVERWRITE, "removed"):
        summary.removed.append(path)
    elif action in (Resolution.BACKUP, "backed_up"):
        summary.backed_up.append(path)
    elif action in (Resolution.SKIP, "skipped"):
        summary.skipped.append(path)
    elif action == "modified":
        summary.written.append(path)


def remove_skill(
    name: str,
    providers: list[str],
    scope: str,
    *,
    backup: bool = False,
) -> OperationSummary:
    """Remove a single skill for every requested Provider (paths pre-confirmed).

    Parameters
    ----------
    name : str
        Skill name.
    providers : list[str]
        Target Providers.
    scope : str
        ``"local"`` or ``"global"``.
    backup : bool, optional
        Back up before removing.

    Returns
    -------
    dict[str, list[str]]
        ``{"removed": [...], "skipped": [...], "backed_up": [...]}``
    """
    summary = OperationSummary()
    for provider in providers:
        dest = skill_target(provider, scope, name)
        if not dest.exists():
            continue
        action = remove_path(dest, backup=backup)
        _record_removal(summary, action, _display_path(dest))
    return summary


def remove_rule(
    name: str,
    providers: list[str],
    scope: str,
    *,
    backup: bool = False,
) -> OperationSummary:
    """Remove a single rule for every requested Provider (paths pre-confirmed).

    Parameters
    ----------
    name : str
        Rule name (without extension).
    providers : list[str]
        Target Providers.
    scope : str
        ``"local"`` or ``"global"``.
    backup : bool, optional
        Back up before removing.

    Returns
    -------
    dict[str, list[str]]
        ``{"removed": [...], "skipped": [...], "backed_up": [...]}``
    """
    summary = OperationSummary()
    for provider in providers:
        dest = rule_target(provider, scope, name)
        if not dest.exists():
            continue
        action = remove_path(dest, backup=backup)
        _record_removal(summary, action, _display_path(dest))
    return summary


def remove_constitution_file(
    path: Path,
    *,
    force: bool = False,
    backup: bool = False,
) -> tuple[str, str]:
    """Apply conservative removal logic to a Constitution file.

    Parameters
    ----------
    path : Path
        ``AGENTS.md`` or ``CLAUDE.md`` path (must exist; caller confirms first).
    force : bool, optional
        Allow removing user-authored content after confirmation.
    backup : bool, optional
        Back up before whole-file removal or partial rewrite.

    Returns
    -------
    tuple[str, str]
        ``(action, display_path)`` where *action* is ``"removed"``, ``"backed_up"``,
        ``"modified"``, or ``"skipped"``.
    """
    display = _display_path(path)
    content = path.read_text(encoding="utf-8")

    if path.name == "AGENTS.md":
        if content not in _catalog_agents_md_contents() and not force:
            return "skipped", display + " (user-authored; pass --force to remove)"
        if backup:
            apply_backup(path)
            return "backed_up", display
        path.unlink()
        return "removed", display

    # CLAUDE.md
    if IMPORT_LINE not in content:
        if not force:
            return "skipped", display + " (user-authored; pass --force to remove)"
        if backup:
            apply_backup(path)
            return "backed_up", display
        path.unlink()
        return "removed", display

    if _claude_md_is_import_stub(content):
        if backup:
            apply_backup(path)
            return "backed_up", display
        path.unlink()
        return "removed", display

    new_content = _strip_agents_import(content)
    suffix = " (import removed)"
    if backup:
        apply_backup(path)
        suffix = " (import removed; original backed up)"
    path.write_text(new_content + ("\n" if new_content else ""), encoding="utf-8")
    return "modified", display + suffix


def remove_constitution(
    providers: list[str],
    scope: str,
    *,
    force: bool = False,
    backup: bool = False,
    confirmed_agents: bool = False,
    confirmed_claude: bool = False,
    allow_broken_claude_import: bool = False,
) -> OperationSummary:
    """Remove Constitution files confirmed during the Prompt Collection Phase."""
    summary = OperationSummary()
    agents_path, claude_path = constitution_paths(providers, scope)

    if confirmed_agents and agents_path and agents_path.exists():
        if (
            not allow_broken_claude_import
            and agents_removal_would_break_claude_import(
                scope,
                agents_path,
                force=force,
                confirmed_claude=confirmed_claude,
            )
        ):
            _record_removal(
                summary,
                "skipped",
                _display_path(agents_path)
                + " (would break CLAUDE.md @AGENTS.md import)",
            )
        else:
            action, display = remove_constitution_file(
                agents_path, force=force, backup=backup
            )
            _record_removal(summary, action, display)

    if confirmed_claude and claude_path and claude_path.exists():
        action, display = remove_constitution_file(
            claude_path, force=force, backup=backup
        )
        _record_removal(summary, action, display)

    return summary
