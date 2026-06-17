---
status: accepted
---

# Unified conflict-resolution seam

All filesystem conflicts in `project`, `docs`, and `agents` commands share one `detect → resolve → apply` substrate: a `Mutation` Protocol, a `Conflict` dataclass with per-artifact allowed `Resolution` subsets (`skip`, `overwrite`, `backup`, `abort`, `merge`), and a `run_mutations` driver that collects every conflict before any write.

## Considered Options

- **Per-command bespoke resolvers** (`_resolve_conflict`, `_decide_action`, inline guards) — rejected: duplicated detection, divergent flag vocabulary (`--force` vs `--overwrite`), and the `quickstart → setup_tests` delegation trap breaking the Ordering Contract.
- **Paired `pre_X()` / `X()` hooks** — rejected in favor of an operation-owned seam (see issue #63 grill).

## Consequences

- The Ordering Contract is structural: `apply()` cannot run until all conflicts are resolved.
- CLI conflict vocabulary is `--overwrite` (tri-state) and `--backup`; add/overwrite `--force` is removed. `agents remove ... --force` remains a distinct authorization flag for user-authored Constitution files.
- `agents add` is prompt-first like `project quickstart` (extends ADR 0001/0006).
- Non-TTY with `overwrite=None` aborts before any mutation.
- `docs init` runs through `run_mutations` like `quickstart` / `setup_tests` / `agents add`: it owns no bespoke conflict handling, so its docs-folder Conflict is resolved before any scaffolding. `InitDocsMutation.apply()` performs the scaffolding (via `_execute_docs_init`); the CLI command only collects the deps/uv decisions up front.
- Removal and `docs update` reporting reuse `OperationSummary` / `render_summary` without participating in the Conflict framework.

Supersedes the add/overwrite flag surface described in ADR 0004.
