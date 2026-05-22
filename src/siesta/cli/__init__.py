# Copyright 2025 Entalpic
"""Siesta CLI package.

Command implementations live in domain modules:

- ``main_app`` — root app wiring and ``main()`` entrypoint
- ``docs_app`` — documentation commands
- ``project_app`` — project commands
- ``self_app`` — self-management and tab-completion commands
"""

from siesta.cli.main_app import app, main

__all__ = ["app", "main"]
