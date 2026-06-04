# Copyright 2025 Entalpic
"""Root CLI application wiring and entrypoint."""

from importlib import metadata
from textwrap import dedent

from cyclopts import App

from siesta.cli.agents_app import agents_app
from siesta.cli.docs_app import docs_app
from siesta.cli.project_app import project_app
from siesta.cli.self_app import self_app
from siesta.completions import detect_current_shell, is_completion_installed
from siesta.utils.common import logger
from siesta.utils.self import get_update_message, start_background_update_check

app = App(
    help=dedent(
        f"""
    Siesta Is Entalpic'S Terminal Assistant ({metadata.version("siesta")})
    
    A set of CLI tools to help you with good practices in Python development at Entalpic.

    Upgrade with ``$ siesta self update``.

    See Usage instructions in the online docs: https://entalpic-siesta.readthedocs-hosted.com/en/latest/autoapi/siesta/.
    """.strip()
    ),
)
""":py:class:`cyclopts.App`: The main CLI application."""

app.command(agents_app)
app.command(docs_app)
app.command(project_app)
app.command(self_app)


def _set_completion_hint() -> None:
    """Show a tab-completion install tip in ``--help`` when not already installed."""
    current_shell = detect_current_shell()
    if current_shell is None or not is_completion_installed(current_shell):
        shell_flag = " --shell <bash|zsh>" if current_shell is None else ""
        app.help_epilogue = (
            f"Tip: enable tab completions with "
            f"`siesta self tab-completions install{shell_flag}`"
        )


def main():
    """Run the CLI, gracefully handling ``KeyboardInterrupt``."""
    _set_completion_hint()

    # Start background update check (non-blocking)
    update_future = start_background_update_check(metadata.version("siesta"))
    interrupted = False

    try:
        app()
    except KeyboardInterrupt:
        interrupted = True
        logger.abort("\nAborted.", exit=130)
    finally:
        # Show update message at the end (if available)
        if not interrupted:
            update_msg = get_update_message(update_future)
            if update_msg:
                logger.print(update_msg)


__all__ = ["app", "agents_app", "docs_app", "project_app", "self_app", "main"]
