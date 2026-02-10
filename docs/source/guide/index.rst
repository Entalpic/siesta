.. Copyright 2025 Entalpic
Documentation At Entalpic
=========================

*Documentation* refers to the content that you produce to help others understand your code. 

It includes both the code's *docstrings* and the *manual documentation files* like the current one you are reading.

.. admonition:: Docstrings TL-DR
    :class: tip

    Use `Numpy-style <https://numpydoc.readthedocs.io/en/latest/format.html>`_ docstrings as illustrated in this :ref:`write docstrings-extended`.

    :doc:`write-docstrings` contains a guide on how to write docstrings in particular (which requires basic understanding of reStructuredText).

.. admonition:: Manual documentation files TL-DR
    :class: hint
    
    Use `reStructuredText <https://shibuya.lepture.com/writing/>`_ to write your manual documentation files.
        
    :doc:`write-docstrings` contains a guide on how to write docstrings in particular (which requires basic understanding of reStructuredText).

.. admonition:: ``siesta``
    :class: hint
    
    Siesta is Entalpic'S Terminal Assistant. It is a CLI tool that helps you with good practices in Python development at Entalpic, especially with boilerplate setup for projects and documentation.

    .. code-block:: bash

        # Start a new project from scratch
        siesta project quickstart

        # Add testing infrastructure to an existing project
        siesta project setup-tests

        # Add documentation to an existing project
        siesta docs init

    See :ref:`siesta-cli-tutorial` for more information.

.. toctree::
    :maxdepth: 1

    /guide/write-documentation
    /guide/write-docstrings
    /guide/example

    .. /guide/github
    .. /guide/ruff
