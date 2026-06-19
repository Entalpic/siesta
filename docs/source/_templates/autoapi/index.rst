.. Copyright 2025 Entalpic

Siesta User Guide
=================

This page contains leads to the documentation of the ``siesta`` package.

The API reference was auto-generated with ``autoapi`` [#f1]_.

You can see the source code on `GitHub <https://github.com/Entalpic/siesta>`_ and explore the rendered documentation here ⬇️

Installation
------------

Using siesta:

.. code-block:: bash

   $ uv tool install git+ssh://git@github.com/entalpic/siesta.git
   # update:
   $ uvx siesta self update

TL;DR
-----

.. code-block:: bash

   # Start a new project (uv init + deps + tests + docs + Agent Assets)
   $ siesta project quickstart

   # Add docs to an existing project
   $ siesta docs init

   # Install curated Agent Assets (Skills, Rules, Constitution)
   $ siesta agents quickstart

   # Build docs
   $ siesta docs build

   # Open docs in browser
   $ siesta docs open

   # Enable tab completions (bash / zsh)
   $ siesta self tab-completions install


Contributing
------------

.. code-block:: bash

   # 1️⃣ Clone the repository
   git clone git@github.com:Entalpic/siesta.git
   # or
   gh repo clone Entalpic/siesta

   # 2️⃣ Install the package
   uv tool install -e ./siesta
   # or
   pip install -e ./siesta


.. toctree::
   :titlesonly:

   {% for page in pages|selectattr("is_top_level_object") %}
   {{ page.include_path }}
   {% endfor %}


.. [#f1] Created with `sphinx-autoapi <https://github.com/readthedocs/sphinx-autoapi>`_
