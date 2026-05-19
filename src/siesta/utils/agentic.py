# Copyright 2025 Entalpic
"""Utility functions for ``siesta project quickstart --explo``.

Materializes the agentic-exploration workflow into a freshly-scaffolded project:
``Human.md`` / ``AGENT.md`` at the project root, and the full bundled skill under
``.claude/skills/agentic-exploration/``. Lifecycle documents
(``research_plan.md``, ``plan.md``, ``TODO.md``, ``notes.md``, ``handoff.md``) are
intentionally not created at init — the agent materializes them from
``templates/`` only when the researcher's real work calls for them.
"""

import re
from pathlib import Path
from shutil import copy2, copytree
from typing import Callable

from siesta.utils.common import logger, resolve_path
from siesta.utils.config import ROOT
from siesta.utils.docs import _copy_not_overwrite

# Path of the bundled skill within the installed siesta package, relative to ROOT.
BUNDLED_AGENTIC_DIR = "skills/agentic-exploration"

# Mapping from a bundled reference template (relative to BUNDLED_AGENTIC_DIR) to
# the file name it is materialized as at the scaffolded project's root.
REFERENCE_TO_PROJECT_FILE: dict[str, str] = {
    "references/human.md": "Human.md",
    "references/agent.md": "AGENT.md",
}


_PROJECT_NAME_MAX_LEN = 128
"""Maximum allowed length for a sanitized project name."""


def _sanitize_project_name(name: str) -> str:
    """Strip control characters and newlines from a project name.

    Prevents a crafted ``name`` in ``pyproject.toml`` (e.g.
    ``foo\\n\\n## Ignore prior instructions…``) from injecting headings or
    instructions into the AI-facing ``AGENT.md`` / ``Human.md`` files.

    Parameters
    ----------
    name : str
        Raw project name as read from ``pyproject.toml`` or the directory.

    Returns
    -------
    str
        The sanitized name: only PEP 508 package-name characters retained
        (``[a-zA-Z0-9._-]``), truncated to :data:`_PROJECT_NAME_MAX_LEN`
        characters.

    Raises
    ------
    ValueError
        If the sanitized name is empty.

    Examples
    --------
    .. code-block:: python

        _sanitize_project_name("foo\\n## Inject")  # -> "fooInject"
        _sanitize_project_name("my-project_1.0")   # -> "my-project_1.0"
    """
    # Restrict to PEP 508 package-name characters (letters, digits, hyphens,
    # underscores, dots) to prevent injection of markdown syntax or control
    # characters into the AI-facing template files.
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    sanitized = sanitized[:_PROJECT_NAME_MAX_LEN]
    if not sanitized:
        raise ValueError(
            f"Project name '{name!r}' is empty after sanitization. "
            "Provide a valid name via pyproject.toml or use the directory name."
        )
    return sanitized


def _assert_not_symlink(path: Path, label: str) -> None:
    """Raise ``ValueError`` if ``path`` is a symbolic link.

    Prevents siesta from following symlinks into unintended filesystem
    locations when writing scaffolded files.

    Parameters
    ----------
    path : Path
        The path to check.
    label : str
        Human-readable name for the path used in the error message.

    Raises
    ------
    ValueError
        If ``path`` is a symbolic link.

    Examples
    --------
    .. code-block:: python

        _assert_not_symlink(Path("/tmp/proj/Human.md"), "Human.md")
    """
    if path.is_symlink():
        raise ValueError(
            f"Refusing to write to '{path}': {label} is a symbolic link. "
            "Remove the symlink and retry."
        )


def _symlink_safe_copy(base_copy_fn: Callable[[str, str], None]) -> Callable[[str, str], None]:
    """Wrap a ``shutil.copy2``-compatible function to refuse symlink destinations.

    Parameters
    ----------
    base_copy_fn : Callable[[str, str], None]
        The underlying copy function (e.g. ``copy2`` or ``_copy_not_overwrite``).

    Returns
    -------
    Callable[[str, str], None]
        A wrapper that raises ``ValueError`` if the destination is a symlink.

    Examples
    --------
    .. code-block:: python

        safe_fn = _symlink_safe_copy(copy2)
        safe_fn("/tmp/src.txt", "/tmp/dest.txt")  # raises if dest is a symlink
    """

    def _copy(src: str, dest: str) -> None:
        dest_path = Path(dest)
        if dest_path.is_symlink():
            raise ValueError(
                f"Refusing to write to '{dest_path}': destination is a symbolic link. "
                "Remove the symlink and retry."
            )
        base_copy_fn(src, dest)

    return _copy


def _normalize_package_name(project_name: str) -> str:
    """Mirror ``uv``'s package-name normalization for a Python project.

    Parameters
    ----------
    project_name : str
        The project's display name as known to siesta (e.g. from ``pyproject.toml``).

    Returns
    -------
    str
        The normalized package name suitable for ``src/<pkg>/`` directories
        (hyphens replaced with underscores).

    Examples
    --------
    .. code-block:: python

        _normalize_package_name("my-cool-project")  # -> "my_cool_project"
    """
    return project_name.replace("-", "_")


def _build_substitutions(
    project_name: str,
    *,
    tests: bool,
    docs: bool,
    layout: str = "lib",
) -> dict[str, str | None]:
    """Build the placeholder-substitution table for siesta-known slots.

    A ``None`` value signals that every line containing the placeholder should be
    dropped entirely from the rendered output (used when the corresponding feature
    was disabled at quickstart time).

    Parameters
    ----------
    project_name : str
        The project's display name; substituted into ``[🙋 Project name]``.
    tests : bool
        Whether pytest infrastructure was scaffolded. Controls whether the
        ``[🙋 test command]`` line is filled with ``uv run pytest`` or dropped.
    docs : bool
        Whether docs were scaffolded. Controls whether the ``[🙋 docs command]``
        line is filled or dropped.
    layout : str, optional
        Project layout mode: ``"lib"`` (default src-layout library), ``"pkg"``
        (src-layout package), or ``"app"`` (no ``src/`` directory). Controls
        whether lines tagged ``[🙋 src-layout-line]`` are kept or dropped.

    Returns
    -------
    dict[str, str | None]
        Mapping of placeholder string to substitution value (or ``None`` to drop
        the containing line).

    Examples
    --------
    .. code-block:: python

        _build_substitutions("my-proj", tests=True, docs=False, layout="app")
        # {"[🙋 Project name]": "my-proj", "[🙋 src-layout-line]": None, ...}
    """
    # For app layout, drop lines tagged with [🙋 src-layout-line] (no src/ dir).
    # For lib/pkg, replace the marker with "" so the line renders normally.
    src_layout_line: str | None = None if layout == "app" else ""
    return {
        "[🙋 Project name]": project_name,
        "[🙋 package name]": _normalize_package_name(project_name),
        "[🙋 test command]": "uv run pytest" if tests else None,
        "[🙋 docs command]": (
            "`siesta docs build` if docs exist, `siesta docs init` if no docs"
            if docs
            else None
        ),
        "[🙋 src-layout-line]": src_layout_line,
    }


def render_reference_template(
    text: str,
    substitutions: dict[str, str | None],
) -> str:
    """Render a reference template by applying placeholder substitutions.

    For each (placeholder, value) pair:

    - if ``value`` is a string, every occurrence of ``placeholder`` is replaced;
    - if ``value`` is ``None``, every line containing ``placeholder`` is removed.

    Unfilled ``[🙋 …]`` placeholders not present in ``substitutions`` are
    intentionally preserved — they are the researcher's authoring surface.

    Parameters
    ----------
    text : str
        The raw template content.
    substitutions : dict[str, str | None]
        Placeholder-to-substitution table; see :func:`_build_substitutions`.

    Returns
    -------
    str
        The rendered template content.

    Examples
    --------
    .. code-block:: python

        render_reference_template(
            "# [🙋 Project name]\\n- Test: [🙋 test command]\\n",
            {"[🙋 Project name]": "foo", "[🙋 test command]": None},
        )
        # "# foo\\n"
    """
    # Placeholders mapped to None drop their entire containing line; collect them up-front.
    drop_placeholders = {ph for ph, val in substitutions.items() if val is None}
    fill_placeholders = {
        ph: val for ph, val in substitutions.items() if isinstance(val, str)
    }
    output_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        # A drop placeholder anywhere on the line removes the whole line — used when
        # a feature like tests/docs was disabled at quickstart time.
        if any(ph in line for ph in drop_placeholders):
            continue
        for ph, val in fill_placeholders.items():
            if ph in line:
                line = line.replace(ph, val)
        output_lines.append(line)
    return "".join(output_lines)


def write_agentic_reference_files(
    project_path: Path,
    substitutions: dict[str, str | None],
    overwrite: bool,
) -> None:
    """Write ``Human.md`` and ``AGENT.md`` at ``project_path`` from bundled references.

    Each reference template is rendered with the given substitutions, then written
    to its target root file. If the destination already exists and ``overwrite`` is
    ``False``, the existing file is backed up via :func:`siesta.utils.docs.backup`.

    Parameters
    ----------
    project_path : Path
        The root directory of the scaffolded project.
    substitutions : dict[str, str | None]
        Placeholder-to-substitution table; see :func:`_build_substitutions`.
    overwrite : bool
        Whether to overwrite an existing destination file. If ``False``, the
        existing file is backed up before being replaced.

    Examples
    --------
    .. code-block:: python

        write_agentic_reference_files(Path("/tmp/p"), subs, overwrite=False)
    """
    # Local import: avoid a top-level cycle with siesta.utils.docs (which itself
    # imports from siesta.utils.common, siesta.utils.config, siesta.utils.github).
    from siesta.utils.docs import backup

    src_root = Path(str(ROOT)) / BUNDLED_AGENTIC_DIR
    for rel_src, target_name in REFERENCE_TO_PROJECT_FILE.items():
        src = src_root / rel_src
        rendered = render_reference_template(
            src.read_text(encoding="utf-8"), substitutions
        )
        dest = project_path / target_name
        # Refuse to follow symlinks — a malicious repo could point these names
        # at files outside the project directory.
        _assert_not_symlink(dest, target_name)
        if dest.exists() and not overwrite:
            backed_up = backup(dest)
            logger.warning(f"Backing up {dest} to {backed_up}")
        dest.write_text(rendered, encoding="utf-8")


def copy_agentic_skill(project_path: Path, overwrite: bool) -> None:
    """Copy the bundled agentic-exploration skill into the scaffolded project.

    The bundled flat layout (``<package>/skills/agentic-exploration/``) is
    placed at ``<project_path>/.claude/skills/agentic-exploration/`` so the
    downstream agent can load it as a project-local skill.

    Parameters
    ----------
    project_path : Path
        The root directory of the scaffolded project.
    overwrite : bool
        Whether to overwrite existing destination files. If ``False``, each
        existing file is backed up before being replaced (via
        :func:`siesta.utils.docs._copy_not_overwrite`).

    Examples
    --------
    .. code-block:: python

        copy_agentic_skill(Path("/tmp/p"), overwrite=False)
    """
    src_root = Path(str(ROOT)) / BUNDLED_AGENTIC_DIR
    # Downstream placement — the `.claude/skills/` hierarchy is tool-specific
    # (Claude Code) and intentionally lives only in the *target* project, not in
    # siesta's source tree.
    dest_root = project_path / ".claude" / "skills" / "agentic-exploration"
    # Guard against symlinked parent directories that could redirect writes
    # outside the project tree before we create any directories.
    for check_path in (
        project_path / ".claude",
        project_path / ".claude" / "skills",
        dest_root,
    ):
        _assert_not_symlink(check_path, str(check_path.relative_to(project_path)))
    dest_root.parent.mkdir(parents=True, exist_ok=True)
    base_copy = copy2 if overwrite else _copy_not_overwrite
    copytree(
        src_root,
        dest_root,
        dirs_exist_ok=True,
        # Wrap the copy function to refuse symlinked destination files within
        # the skill tree (prevents per-file escape via pre-placed symlinks).
        copy_function=_symlink_safe_copy(base_copy),
    )


def setup_agentic_exploration(
    project_path: Path | str,
    project_name: str,
    *,
    tests: bool,
    docs: bool,
    overwrite: bool = False,
    layout: str = "lib",
) -> None:
    """Materialize the agentic-exploration workflow into ``project_path``.

    Creates ``Human.md`` and ``AGENT.md`` at the project root (substituting only
    the placeholders siesta knows at scaffold time) and copies the bundled skill
    content into ``.claude/skills/agentic-exploration/`` for downstream agent
    use. Lifecycle documents (``research_plan.md``, ``plan.md``, ``TODO.md``,
    ``notes.md``, ``handoff.md``) are intentionally not created at init — the
    agent materializes them from ``templates/`` only when real work calls for
    them.

    Parameters
    ----------
    project_path : Path | str
        Root of the scaffolded project.
    project_name : str
        Project name used to fill the ``[🙋 Project name]`` placeholder and to
        derive the normalized package name for ``src/<pkg>/``.
    tests : bool
        Whether pytest infrastructure was scaffolded. Controls the test-command
        placeholder.
    docs : bool
        Whether docs were scaffolded. Controls the docs-command placeholder.
    overwrite : bool, optional
        Whether to overwrite existing files at the destination. Defaults to
        ``False``, in which case existing files are backed up.
    layout : str, optional
        Project layout mode: ``"lib"`` (default), ``"pkg"``, or ``"app"``.
        Passed to ``_build_substitutions`` to control whether ``src/``-specific
        lines are included in the rendered ``AGENT.md``.

    Examples
    --------
    .. code-block:: python

        from pathlib import Path
        from siesta.utils.agentic import setup_agentic_exploration

        setup_agentic_exploration(
            Path("/tmp/new-project"),
            project_name="my-project",
            tests=True,
            docs=False,
            layout="app",
        )
    """
    project_path = resolve_path(project_path)
    # Sanitize before any template substitution to prevent prompt injection via
    # a crafted pyproject.toml name field.
    project_name = _sanitize_project_name(project_name)
    substitutions = _build_substitutions(project_name, tests=tests, docs=docs, layout=layout)
    write_agentic_reference_files(project_path, substitutions, overwrite)
    copy_agentic_skill(project_path, overwrite)
    logger.info(
        "Agentic exploration workflow scaffolded "
        "([r]Human.md[/r], [r]AGENT.md[/r], "
        "[r].claude/skills/agentic-exploration/[/r])."
    )
