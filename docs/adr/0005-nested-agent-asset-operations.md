---
status: accepted
---

# Nested Agent Asset Operations

The `siesta agents` command group now separates operations from Agent Asset kinds:
`siesta agents add skill`, `add rule`, and `add constitution` install bundled assets;
`siesta agents remove skill`, `remove rule`, and `remove constitution` remove
detected local or global assets. The previous flat commands (`add-skill`, `add-rule`,
`add-constitution`) were removed without compatibility aliases.

## Considered Options

- Keep flat `add-*` commands and add parallel `remove-*` commands — rejected: the
  grammar duplicates the operation in every command name and does not scale if more
  operations are added later.
- Add nested commands while keeping deprecated flat aliases — rejected: the CLI is
  still early enough to prefer a clean public surface over compatibility shims.
- Allow non-interactive removal sweeps over detected assets — rejected: removal is
  destructive; every candidate must be confirmed individually before mutation.

## Decision

- Nest Agent Asset kinds under `add` and `remove` subcommands.
- Break the old flat command names intentionally.
- Gate every removal candidate with an explicit questionary confirmation; `--force`
  on Constitution removal permits user-authored content but never bypasses confirmation.
- Default removal scope to local, matching add defaults.

## Consequences

- Scripts and docs must use the nested command paths.
- Removal is safer but always requires interactive confirmation (or explicit names
  plus per-path confirmation).
- `quickstart` remains a top-level `agents` command because it installs the
  Quickstart Config subset, not a single Agent Asset kind.
