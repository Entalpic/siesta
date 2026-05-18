# Copyright 2025 Entalpic
"""Utility functions for ``siesta project quickstart --explo``.

Materializes the agentic-exploration workflow into a freshly-scaffolded project:
``Human.md`` / ``AGENT.md`` at the project root, and the full bundled skill under
``.claude/skills/agentic-exploration/``. Lifecycle documents
(``research_plan.md``, ``plan.md``, ``TODO.md``, ``notes.md``, ``handoff.md``) are
intentionally not created at init — the agent materializes them from
``templates/`` only when the researcher's real work calls for them.
"""

from pathlib import Path
from shutil import copy2, copytree

from siesta.utils.common import logger, resolve_path
from siesta.utils.config import ROOT
from siesta.utils.docs import _copy_not_overwrite

# Path of the bundled skill within the installed siesta package, relative to ROOT.
BUNDLED_AGENTIC_DIR = "boilerplate/agentic-exploration"

# Mapping from a bundled reference template (relative to BUNDLED_AGENTIC_DIR) to
# the file name it is materialized as at the scaffolded project's root.
REFERENCE_TO_PROJECT_FILE: dict[str, str] = {
    "references/human.md": "Human.md",
    "references/agent.md": "AGENT.md",
}


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

    Returns
    -------
    dict[str, str | None]
        Mapping of placeholder string to substitution value (or ``None`` to drop
        the containing line).

    Examples
    --------
    .. code-block:: python

        _build_substitutions("my-proj", tests=True, docs=False)
        # {"[🙋 Project name]": "my-proj", "[🙋 package name]": "my_proj", ...}
    """
    return {
        "[🙋 Project name]": project_name,
        "[🙋 package name]": _normalize_package_name(project_name),
        "[🙋 test command]": "uv run pytest" if tests else None,
        "[🙋 docs command]": (
            "`siesta docs build` if docs exist, `siesta docs init` if no docs"
            if docs
            else None
        ),
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
        if dest.exists() and not overwrite:
            backed_up = backup(dest)
            logger.warning(f"Backing up {dest} to {backed_up}")
        dest.write_text(rendered, encoding="utf-8")


def copy_agentic_skill(project_path: Path, overwrite: bool) -> None:
    """Copy the bundled agentic-exploration skill into the scaffolded project.

    The bundled flat layout (``<package>/boilerplate/agentic-exploration/``) is
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
    dest_root.parent.mkdir(parents=True, exist_ok=True)
    copytree(
        src_root,
        dest_root,
        dirs_exist_ok=True,
        copy_function=copy2 if overwrite else _copy_not_overwrite,
    )


def setup_agentic_exploration(
    project_path: Path | str,
    project_name: str,
    *,
    tests: bool,
    docs: bool,
    overwrite: bool = False,
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
        )
    """
    project_path = resolve_path(project_path)
    substitutions = _build_substitutions(project_name, tests=tests, docs=docs)
    write_agentic_reference_files(project_path, substitutions, overwrite)
    copy_agentic_skill(project_path, overwrite)
    logger.info(
        "Agentic exploration workflow scaffolded "
        "([r]Human.md[/r], [r]AGENT.md[/r], "
        "[r].claude/skills/agentic-exploration/[/r])."
    )
