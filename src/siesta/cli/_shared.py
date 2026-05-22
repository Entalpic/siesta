# Copyright 2025 Entalpic
"""Shared CLI helpers."""

import sys

from rich import print as rprint

from siesta.completions import Shell, detect_current_shell


def resolve_shell(shell: Shell | None) -> Shell:
    """Return ``shell`` if given, otherwise detect and return the current shell.

    Parameters
    ----------
    shell : Shell | None
        Explicitly provided shell value, or ``None`` to auto-detect.

    Returns
    -------
    Shell
        The resolved shell (``"bash"`` or ``"zsh"``).
    """
    if shell is not None:
        return shell
    detected = detect_current_shell()
    if detected is None:
        rprint(
            "[red]Cannot detect current shell. "
            "Please specify --shell bash or --shell zsh.[/red]"
        )
        sys.exit(1)
    return detected
