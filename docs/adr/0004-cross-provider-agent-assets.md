---
status: accepted
---

# Cross-Provider Agent Asset Installation

The `siesta agents` commands install Agent Assets from a single bundled Agent Asset Catalog: each Rule is authored once as a Cursor `.mdc` and translated to a Claude `.md` (`globs` -> `paths`, drop `description`, omit `paths` when always-applied), and a Constitution is stored as an `AGENTS.md` source of truth plus a `CLAUDE.md` `@AGENTS.md` import stub — so `AGENTS.md` is always written (for Cursor compatibility) even when only the Claude Provider is targeted. We chose one canonical source plus vendor translation so a single edit to an asset stays consistent across Providers (Provider Mirroring).

## Considered Options

- Pre-built per-Provider variants stored in the catalog — rejected: two copies of each asset drift over time.
- A tool-neutral source format compiled to both Providers — rejected: needless indirection, since `.mdc` already carries the metadata (`globs`, `alwaysApply`) the translation needs.
- Mirroring the user's existing global `~/.cursor` / `~/.claude` installs — rejected: not reproducible and not shippable inside the package.
