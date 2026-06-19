# Copyright 2025 Entalpic
"""Unified conflict detection, resolution, and mutation driver for filesystem writes."""

from __future__ import annotations

import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from siesta.utils.common import logger


class Resolution(StrEnum):
    """How a single Conflict is resolved before any write.

    ``SKIP`` keeps the existing artifact, ``OVERWRITE`` replaces it, ``BACKUP``
    renames it to ``.bak`` then writes, ``MERGE`` prepends new content while
    preserving the existing file (the ``CLAUDE.md`` import-stub case), and
    ``ABORT`` stops the run before any Mutation (intercepted in ``run_mutations``).
    """

    SKIP = "skip"
    OVERWRITE = "overwrite"
    BACKUP = "backup"
    ABORT = "abort"
    MERGE = "merge"


@dataclass(frozen=True)
class Conflict:
    """A pre-existing artifact a Mutation would overwrite, with its allowed Resolutions.

    ``key`` MUST be unique across every Mutation in a single ``run_mutations`` call:
    resolutions are stored in one shared dict keyed by ``key``, and each
    :meth:`Mutation.apply` reads its decision back by the same key. Two Conflicts
    sharing a key would clobber each other's resolution. Callers namespace keys
    accordingly (for example ``skill:<name>:<provider>``, ``constitution:agents``).
    ``options`` is the subset of :class:`Resolution` offered for this Conflict.
    """

    key: str
    name: str
    options: frozenset[Resolution]


@dataclass
class OperationSummary:
    """Accumulated outcomes of applying Mutations, rendered by :func:`render_summary`."""

    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    backed_up: list[str] = field(default_factory=list)
    merged: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)

    def merge(self, other: OperationSummary) -> None:
        self.written += other.written
        self.skipped += other.skipped
        self.backed_up += other.backed_up
        self.merged += other.merged
        self.removed += other.removed


def is_occupied(path: Path) -> bool:
    """Whether *path* holds an artifact a Mutation would overwrite.

    A missing path is vacant, and so is an empty directory — it is only a container
    with nothing to lose. Any file counts as occupied, even a zero-byte one: an empty
    file can be intentional (a package's ``__init__.py``, a ``py.typed`` marker), so a
    Mutation must treat it as a Conflict rather than clobber it silently.

    Parameters
    ----------
    path : Path
        Destination path a Mutation would write to.

    Returns
    -------
    bool
        ``True`` if *path* is an existing file or a non-empty directory.
    """
    if not path.exists():
        return False
    if path.is_dir():
        return any(path.iterdir())
    return True


def apply_backup(dest: Path) -> None:
    """Rename *dest* to ``dest.bak`` (overwriting any previous backup)."""
    bak = dest.parent / (dest.name + ".bak")
    if bak.exists():
        if bak.is_dir():
            shutil.rmtree(bak)
        else:
            bak.unlink()
    dest.rename(bak)


def write_path(
    src: Path | None,
    dest: Path,
    resolution: Resolution,
    *,
    content_override: str | None = None,
) -> Resolution:
    """Perform the filesystem action for one destination given its resolved action."""
    if resolution is Resolution.SKIP:
        return Resolution.SKIP
    # write_path only owns SKIP/BACKUP/OVERWRITE: MERGE is content-specific and handled
    # by the owning Mutation, ABORT is intercepted in run_mutations before any apply.
    if resolution not in (Resolution.OVERWRITE, Resolution.BACKUP):
        raise ValueError(f"write_path cannot perform resolution {resolution!r}")
    if resolution is Resolution.BACKUP:
        apply_backup(dest)
    elif resolution is Resolution.OVERWRITE and dest.exists() and dest.is_dir():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if content_override is not None:
        dest.write_text(content_override, encoding="utf-8")
    elif src is not None and src.is_dir():
        shutil.copytree(src, dest)
    elif src is not None:
        shutil.copy2(src, dest)
    return (
        Resolution.BACKUP if resolution is Resolution.BACKUP else Resolution.OVERWRITE
    )


def resolve_conflict(
    conflict: Conflict, *, overwrite: bool | None, backup: bool
) -> Resolution:
    """Resolve a single conflict from flags, TTY prompt, or abort."""
    opts = conflict.options
    if overwrite is False:
        logger.warning(f"{conflict.name} already exists. Skipping.")
        return Resolution.SKIP
    if overwrite is True:
        if Resolution.OVERWRITE in opts:
            return (
                Resolution.BACKUP
                if backup and Resolution.BACKUP in opts
                else Resolution.OVERWRITE
            )
        if Resolution.MERGE in opts:
            return Resolution.MERGE
        logger.warning(
            f"{conflict.name} already exists. Overwrite not supported for this step — skipping."
        )
        return Resolution.SKIP
    if not sys.stdin.isatty():
        logger.abort(
            f"{conflict.name} already exists. Pass --overwrite to overwrite, "
            "--no-overwrite to skip, or the matching --no-<feature> flag."
        )
    label_order = [
        ("Skip (keep existing)", Resolution.SKIP),
        ("Overwrite", Resolution.OVERWRITE),
        ("Backup and overwrite", Resolution.BACKUP),
        ("Prepend import (preserve content)", Resolution.MERGE),
        ("Abort", Resolution.ABORT),
    ]
    labels = [label for label, res in label_order if res in opts]
    choice = logger.select(
        f"{conflict.name} already exists — what do you want to do?",
        labels,
    )
    for label, res in label_order:
        if label == choice:
            return res
    return Resolution.ABORT


@runtime_checkable
class Mutation(Protocol):
    """One project-state change driven by :func:`run_mutations`.

    The Ordering Contract is structural: ``run_mutations`` calls every
    :meth:`detect_conflicts` and resolves all Conflicts before invoking any
    :meth:`apply`, so ``apply`` never prompts. ``apply`` receives the full
    ``resolutions`` map (keyed by :attr:`Conflict.key`) and reads back only the
    decisions for the Conflicts it reported.
    """

    def detect_conflicts(self) -> list[Conflict]: ...
    def apply(self, resolutions: Mapping[str, Resolution]) -> OperationSummary: ...


def run_mutations(
    mutations: list[Mutation], *, overwrite: bool | None, backup: bool
) -> OperationSummary:
    """Collect all conflicts, resolve them, then apply mutations in order."""
    resolutions: dict[str, Resolution] = {}
    for m in mutations:
        for c in m.detect_conflicts():
            r = resolve_conflict(c, overwrite=overwrite, backup=backup)
            if r is Resolution.ABORT:
                logger.abort("Aborted.")
            resolutions[c.key] = r
    summary = OperationSummary()
    for m in mutations:
        summary.merge(m.apply(resolutions))
    return summary


def render_summary(summary: OperationSummary) -> None:
    """Print a Rich summary of mutation outcomes."""
    if summary.written:
        for p in summary.written:
            logger.success(f"Written: {p}")
    if summary.backed_up:
        for p in summary.backed_up:
            logger.info(f"Backed up + written: {p}")
    if summary.merged:
        for p in summary.merged:
            logger.info(f"Import prepended: {p}")
    if summary.skipped:
        for p in summary.skipped:
            logger.warning(f"Skipped (already exists): {p}")
    if summary.removed:
        for p in summary.removed:
            logger.info(f"Removed: {p}")
    if (
        not summary.written
        and not summary.backed_up
        and not summary.merged
        and not summary.skipped
        and not summary.removed
    ):
        logger.info("Nothing to do.")
