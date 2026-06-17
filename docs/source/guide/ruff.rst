.. Copyright 2025 Entalpic

:orphan:

.. _coding conventions:

########
Ruff 101
########


TL;DR
-----

Use `Ruff <https://docs.astral.sh/ruff/>`_ and associated `Ruff IDE Extension (for VSCode, Cursor, PyCharm, (Neo)Vim, etc.) <https://docs.astral.sh/ruff/editors/setup/>`_ to:

- Format your code (Black-compatible)
- Sort your imports (isort-compatible)
- Lint your code (Flake8-compatible)

.. code-block:: bash

    uv add --dev ruff
    # or
    pip install ruff
    # then:
    ruff check  # lint
    ruff format path/to/file.py  # format
    ruff format path/to/folder/  # format

.. tip::

    `Set your default formatter <https://code.visualstudio.com/docs/python/formatting#_set-a-default-formatter>`_ to ``Ruff`` then enable `Format on save <https://stackoverflow.com/a/54665086/3867406>`_ in VSCode not to think about it.

    You can easily find ways to do the same thing on other IDEs by asking Google 👻

In the following section we'll describe how popular formatters / linters / sorters work, keeping in mind this is all bundled (and extended) in **Ruff**.

Formatting with Ruff (or Black)
-------------------------------

.. note::

    ``black`` is very similar to ``ruff`` as it is also a code formatter and the `foundation for Ruff <https://astral.sh/blog/the-ruff-formatter#2-black-compatible>`_
    While Ruff is gaining more and more traction, Black is still the most popular code formatter and industry standard.

    In the following sections what we write about Ruff will also apply to Black.

Ruff is a code formatter. It ensures we all write code in the same style. Importantly, it will **change your code** if needed, to enforce conventions.

For instance, this is valid Python code:

.. code-block:: python

    a=32000
    b = {
    'a': 1, "b":2,}
    function (a=1,b = [1,2,3],c=3,)

But Ruff will reformat it to:

.. code-block:: python

    a = 32000
    b = {"a": 1, "b": 2}
    function(a=1, b=[1, 2, 3], c=3)

Some choices are optimized for readability (for instance single quotes ``'`` are replaced by double quotes ``"``). Others are just a matter of subjective taste (for instance the number of spaces around the equal sign ``=``).

That being said, what matters is the consistency. Ruff is a tool that ensures **we all write code in the same style**. This will also make PRs clearer, easier to review, and less prone to conflicts. Plus, it will save you time: you don't have to think about formatting anymore, Ruff does it for you.

There are a number of ways to work with Ruff. It can be an extension in your IDE (PyCharm, VSCode, etc.), a pre-commit hook, or a command line tool. The latter is the simplest to set up and use:

.. code-block:: bash

    uv add --dev ruff
    # or
    pip install ruff
    # then:
    ruff format path/to/file.py
    ruff format path/to/folder/

.. tip::

    Ruff can also format your *in-docstring* Python examples!
    Add the following to your ``pyproject.toml``:

    .. code-block:: toml

        [tool.ruff.format]
        docstring-code-format = true

Ruff will reformat the file in place. If you want to see the changes before applying them, use the ``--diff`` flag:

.. code-block:: bash

    ❯ uv run ruff format --diff
    --- docs/source/conf.py
    +++ docs/source/conf.py
    @@ -112,7 +112,7 @@
        "show-module-summary",
        "imported-members",
    ]
    -autoapi_keep_files=False
    +autoapi_keep_files = False
    
    # sphinx_math_dollar
    # Note: CHTML is the only output format that works with \mathcal{}

    1 file would be reformatted, 5 files already formatted

.. caution::

    Your file needs to be valid Python for ``ruff`` to run. If you have a Syntax Error in your code, ``ruff`` will fail and it may look like your IDE extension "is not working". It is trying to, but it cannot. Fix the Syntax Error first, then run ``ruff`` again.

Check out the `Ruff (formatter) documentation <https://docs.astral.sh/ruff/formatter/>`_ for more information.

Linting with Ruff (or Flake8)
-----------------------------

Ruff is also a code linter. It will help you, just like ``ruff format``, with writing good, consistent code. 
It will also help you avoid common pitfalls and mistakes like undefined variables, unused imports, etc.
Linters are most commonly used in one of two ways:

1. Provide feedback as you code in your IDE through extensions to warn you about potential issues.
2. As a Continuous Integration tool to ensure that all code is compliant with the rules.

.. note::

    Understanding ``flake8`` is important because it is also an industry standard.
    Ruff goes a step further by extending Flake8 with additional rules and being more consistent.
    `Goodbye to Flake8 and PyLint: faster linting with Ruff <https://pythonspeed.com/articles/pylint-flake8-ruff/>`_


E.g.:

.. code-block:: python

    # example1.py
    def f(myvar):
        return myva * 2

.. code-block:: bash

    ❯ ruff check        

    example.py:2:12: F821 Undefined name `myva`
      |
    1 | def f(myvar):
    2 |     return myva * 2
      |            ^^^^ F821
      |

    Found 1 error.

.. hint::

    Some errors are more severe than others. Some errors are actually safe to fix automatically. This is why Ruff has a ``--fix`` flag. For instance:

    .. code-block:: python

        f"Hello, world!"
        # ❯ ruff check --fix
        "Hello, world!"

        "Hello, {name}".format(greeting="Hello", name="World")
        # ❯ ruff check --fix
        "Hello, {name}".format(name="World")

See `Rules <https://docs.astral.sh/ruff/rules/>`_ for more information (look for the 🛠️ symbol).

Most IDEs will also let you use Ruff as an extension to have feedback as you code. Ask Google about your particular IDE, you're very likely not the first one.

Check out the `Ruff (linter) documentation <https://docs.astral.sh/ruff/linter/>`_ for more information.

.. tip::

    You can `disable specific rules locally <https://docs.astral.sh/ruff/linter/#error-suppression>`_.

    .. code-block:: python

        # Ignore F841.
        x = 1  # noqa: F841

        # Ignore E741 and F841.
        i = 1  # noqa: E741, F841

        # Ignore _all_ violations.
        x = 1  # noqa

Sorting imports with Ruff (or isort)
-------------------------------------

Sorting imports is a common task in Python projects. It is a good practice to sort your imports to make your code more readable and easier to maintain.

Ruff can do this for you. It will sort your imports to make sure that:

-   standard library imports are on top
-   third-party imports are in the middle
-   local imports are at the bottom

It will also sort the imports alphabetically, and group them by package.

.. note::

    ``isort`` is another tool that can do this, and is a popular tool in the Python community.
    Basically, Ruff is a more modern and opinionated version of the ``black`` + ``flake8`` + ``isort`` trio.


.. code-block:: python

    from os.path import expandvars
    from os.path import relpath
    from siesta.logger import Logger
    from pathlib import Path
    import json
    from rich import print
    from subprocess import run
    from shutil import copytree

Becomes:

.. code-block:: python

    import json
    from os.path import expandvars, relpath
    from pathlib import Path
    from shutil import copytree
    from subprocess import run

    from rich import print

    from siesta.logger import Logger

This will be done automatically when using IDE extensions (if not, ask Google about your particular IDE and case). 

If you want to do it manually, you can use Ruff from the command line:

.. code-block:: bash

    ruff check --select I --fix


.. note::

    Yes, it should be more of a ``format`` action than a ``check`` action, `but that's the way it is <https://github.com/astral-sh/ruff/issues/8926>`_.

