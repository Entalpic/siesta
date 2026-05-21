# ADR 0002: CLI Package Modularization

## Status
Accepted

## Context
The CLI lived in a single large module (`siesta.cli`), which made command
ownership, testing, and maintenance harder as command groups grew.

Issue #43 required splitting command groups into a `cli/` package with domain
modules. During planning review, we also clarified that Python import
compatibility is not a long-term requirement; only the CLI executable contract
must remain stable.

## Decision
Split the CLI into domain modules with explicit ownership:

- `main_app` — root app wiring and `main()` entrypoint
- `docs_app` — documentation commands
- `project_app` — project commands
- `self_app` — self-management and tab-completion commands
- `_shared` — cross-domain helpers (for example shell resolution)

Keep `siesta.cli` package exports minimal (`app`, `main`) and point the script
entrypoint to `siesta.cli.main_app:main`.

Breaking change: callers must import command implementations from domain
modules instead of relying on flat `siesta.cli` symbols.

## Consequences
Positive:
- Command ownership is explicit and easier to navigate.
- Tests can patch domain modules directly.
- Root package exports no longer shadow domain submodules.

Trade-offs:
- External Python imports from `siesta.cli` are no longer supported beyond
  `app` and `main`.
- Cross-domain calls must import from the owning domain module.

## Alternatives Considered
- Keep a compatibility shim re-exporting all legacy symbols from
  `siesta.cli.__init__`.
  Rejected because it preserved a misleading flat API and caused submodule name
  shadowing (`siesta.cli.docs_app` referred to the App object, not the module).
- Structural package split without moving implementations.
  Rejected because it did not reduce maintenance burden or improve ownership.
