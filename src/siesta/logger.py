# Copyright 2025 Entalpic
"""
A module to log messages to the console.

This module provides a class to log messages to the console with different levels of severity,
along with methods to prompt the user for input, confirm messages, abort the program, and clear the
current line.

Example
-------
.. code-block:: python

    from siesta.logger import Logger

    logger = Logger("MyLogger")
    logger.success("This is a success message.")
    c = logger.confirm("Do you want to continue?")
    if not c:
        logger.abort("Aborting.")
    logger.success("Continuing...")


"""

import sys
from datetime import datetime

from rich import print
from rich.console import Console
from rich.panel import Panel


class BaseLogger:
    """A **dummy** class for documentation purposes."""

    def dummy(self, arg1, arg2):
        r"""
        Summary line: this function is not used anywhere, it's just an example.

        Extended description of function from the docstrings tutorial :ref:`write
        docstrings-extended`.

        Refer to:

        * functions with :func:`siesta.utils.safe_dump`
        * classes with :class:`siesta.logger.Logger`
        * methods with :meth:`siesta.logger.Logger.prompt`
        * constants with :const:`siesta.cli.app`

        Prepend with ``~`` to refer to the name of the object only instead of the full
        path -> :func:`~siesta.utils.safe_dump` will display as ``safe_dump``
        instead of the full path ``siesta.utils.safe_dump``.

        Great maths:

        .. math::

            \int_0^1 x^2 dx = \frac{1}{3}

        .. important::

            A docstring with **math** MUST be a raw Python string (a string prepended with
            an ``r``: ``r"raw"``) to avoid backslashes being treated as escape characters.

            Alternatively, you can use double backslashes.

        .. warning::

            Display a warning. See :ref:`learn by example`. (<-- this is a cross reference,
            learn about it `here
            <https://www.sphinx-doc.org/en/master/usage/referencing.html#ref-rolel>`_)


        Examples
        --------
        >>> function(1, "a")
        True
        >>> function(1, 2)
        True

        >>> function(1, 1)
        Traceback (most recent call last):
            ...

        Or

        .. code-block:: python

            function(1, "a")
            function(1, 2)
            print("Done.")

        Notes
        -----
        This block uses ``$ ... $`` for inline maths -> $e^{\frac{x}{2}}$.

        Or ``$$ ... $$`` for block math instead of the ``.. math:`` directive above.

        $$
        \sum_{i=1}^{+\infty} \frac{1}{i^2} = \frac{\pi^2}{6}
        $$


        Parameters
        ----------
        arg1 : int
            Description of arg1
        arg2 : str
            Description of arg2

        Returns
        -------
        bool
            Description of return value

        Raises
        ------
        ValueError
            If arg1 is equal to arg2.
        """
        if arg1 == arg2:
            raise ValueError("arg1 must not be equal to arg2")
        return True


class Logger(BaseLogger):
    """A class to log messages to the console."""

    def __init__(self, name: str, with_time: bool = True):
        """Initialize the Logger.

        Parameters
        ----------
        name : str
            The name of the logger.
        with_time : bool, optional
            Whether to include the time in the log messages, by default True.
        """
        self.name = name
        self.with_time = with_time
        self.console = Console()

    def now(self):
        """Get the current time.

        Returns
        -------
        str
            The current time.
        """
        return datetime.now().strftime("%H:%M:%S")

    @property
    def prefix(self):
        """Get the prefix for the log messages.

        The prefix includes the name of the logger and the current time.

        Returns
        -------
        str
            The prefix.
        """
        prefix = ""
        if self.name:
            prefix += f"{self.name}"
            if self.with_time:
                prefix += f" | {self.now()}"
        else:
            prefix += self.now()
        if prefix:
            return rf"[grey50 bold]\[{prefix}][/grey50 bold] "
        return prefix

    def prompt(self, message: str, default: str = None) -> str:
        """Prompt the user for a value.

        Parameters
        ----------
        message : str
            The message to prompt the user with.
        default : str, optional
            The default value, by default None.

        Returns
        -------
        str
            The value entered by the user.
        """
        text = (
            f"{self.prefix}{message} \\[default: {default}]"
            if default
            else f"{self.prefix}{message}"
        )
        print(text, end="")
        return input(":").strip() or default

    def confirm(self, message: str) -> bool:
        """Confirm a message with the user.

        Parameters
        ----------
        message : str
            The message to confirm.

        Returns
        -------
        bool
            Whether the user confirmed the message.
        """
        return self.prompt(f"{message} (Y/n)", "y").lower() == "y"

    def abort(self, message: str, exit=1):
        """Abort the program with a message.

        Parameters
        ----------
        message : str
            The message to print before aborting.
        """
        print(f"{self.prefix}[red]{message}[/red]")
        sys.exit(exit)

    def success(self, message: str, title: str = "Success", as_panel: bool = False):
        """Print a success message.

        Parameters
        ----------
        message : str
            The message to print.
        title : str, optional
            The title of the panel, by default ``"Success"``.
        as_panel : bool, optional
            Whether to print the message in a panel, by default ``False``.
        """
        if as_panel:
            content = Panel(
                message, subtitle=self.prefix, title=title, border_style="green"
            )
        else:
            content = f"{self.prefix}[green]{message}[/green]"
        self.console.print(content)

    def warning(self, message: str, title: str = "Warning", as_panel: bool = False):
        """Print a warning message.

        Parameters
        ----------
        message : str
            The message to print.
        title : str, optional
            The title of the panel, by default ``"Warning"``.
        as_panel : bool, optional
            Whether to print the message in a panel, by default ``False``.
        """
        if as_panel:
            content = Panel(
                message, subtitle=self.prefix, title=title, border_style="yellow"
            )
        else:
            content = f"{self.prefix}[yellow]{message}[/yellow]"
        self.console.print(content)

    def error(self, message: str, title: str = "Error", as_panel: bool = False):
        """Print an error message.

        Parameters
        ----------
        message : str
            The message to print.
        title : str, optional
            The title of the panel, by default ``"Error"``.
        as_panel : bool, optional
            Whether to print the message in a panel, by default False.
        """
        if as_panel:
            content = Panel(
                message, subtitle=self.prefix, title=title, border_style="red"
            )
        else:
            content = f"{self.prefix}[red]{message}[/red]"
        self.console.print(content)

    def info(self, message: str, title: str = "Info", as_panel: bool = False):
        """Print an info message.

        Parameters
        ----------
        message : str
            The message to print.
        title : str, optional
            The title of the panel, by default ``"Info"``.
        as_panel : bool, optional
            Whether to print the message in a panel, by default ``False``.
        """
        if as_panel:
            content = Panel(
                message, subtitle=self.prefix, title=title, border_style="blue"
            )
        else:
            content = f"{self.prefix}[blue]{message}[/blue]"
        self.console.print(content)

    def clear_line(self):
        """Clear the current line."""
        import shutil

        cols = shutil.get_terminal_size().columns
        print(" " * cols, end="\r")
        print(" " * cols, end="\r")

    def loading(self, message: str):
        """Print a loading message.

        Parameters
        ----------
        message : str
            The message to print.
        """
        return self.console.status(message)

    def print(self, *args, title: str = None, as_panel: bool = False, **kwargs) -> None:
        """Print a message.

        Parameters
        ----------
        *args :
            The arguments to print.
        title : str, optional
            The title of the panel, by default None.
        as_panel : bool, optional
            Whether to print the message in a panel, by default False.
        **kwargs :
            The keyword arguments to print.
        """
        if as_panel:
            self.console.print(
                Panel(*args, **kwargs, subtitle=self.prefix, title=title)
            )
        else:
            self.console.print(self.prefix, *args, **kwargs)
