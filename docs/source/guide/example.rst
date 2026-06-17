.. Copyright 2025 Entalpic
.. _example-docs:

##########################
Example documentation file
##########################

This is an example documentation file that illustrates how to use ``.rst`` syntax to write documentation, including **tutorials**.

---

Include code to illustrate how to use the package / module / class / method / function etc.

Remember, this works in docstrings *and* in stand-alone ``.rst`` files.

.. code-block:: python

    from siesta.cli.main_app import app

    app()

.. note::

    This is a note. You can use it to add notes to your documentation.

.. warning::

    This is a warning. You can use it to add warnings to your documentation.

Cool features:

Reference code docs of:

- A class: :class:`siesta.logger.BaseLogger` (long format)
- Another class :class:`~siesta.logger.Logger` (short format, by prepending ``~``)
- A method :meth:`~siesta.logger.Logger.prompt`
- Or even an external library :class:`github.MainClass.Github`

.. note::

    External content should be listed in ``docs/source/conf.py`` under ``intersphinx_mapping``.
    More info in the `Read The Docs documentation <https://docs.readthedocs.io/en/stable/guides/intersphinx.html>`_.

An actual tutorial on ``.rst``:
`ReStructured Text for those who know Markdown <https://docs.open-mpi.org/en/v5.0.x/developers/rst-for-markdown-expats.html#hyperlinks-to-urls>`_

.. important::

    Check out this documentation for more on the specific so-called *admonitions* like
    the "note", "warning", "important", etc. coloured boxes in this document:
    `Shibuya theme documentation <https://shibuya.lepture.com/writing/admonition/>`_

.. attention::

    ReStructured Text is a bit more complicated than Markdown, but it's worth it.
    **One common mistake** is to forget that spaces and new lines matter in ``.rst``.
    For example, the following will not work:

    .. code-block::

        .. note::
        This is NOT a note.

    But this will

    .. code-block::

        .. note::

            This is a note.

    Same goes for whitespaces: ``.. code-block::`` ✅ ``..code-block::`` ❌.


.. todo::

    Improving the documentation: `Recommendations for Sphinx plugins <https://shibuya.lepture.com/extensions/sphinx-copybutton/>`_.

.. dropdown::  :octicon:`megaphone` Want to learn more?

    You can use icons :octicon:`project` and badges :bdg-primary:`primary`,
    :bdg-primary-line:`primary-line`.

    This is all documented in `Sphinx-Design <https://shibuya.lepture.com/extensions/sphinx-design/>`_.
