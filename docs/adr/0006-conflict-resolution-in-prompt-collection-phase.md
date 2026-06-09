---
status: accepted
---

# Conflict Resolution belongs in the Prompt Collection Phase

When `siesta project quickstart` detects that an artifact it would write already exists on disk (a Conflict), the resolution decision — skip, overwrite, or abort — is collected during the Prompt Collection Phase, before the first Mutation. This preserves the Ordering Contract: if the user chooses Abort, the project state is identical to its pre-run state, with nothing to roll back.

## Considered Options

- **Resolve conflicts mid-execution** — prompt the user at the point of each Mutation, with a "retry after manual fix" option. Rejected: Abort mid-execution would require rolling back already-completed Mutations (filesystem writes, `uv add` side effects, pre-commit installs), which is not feasible. The retry option also creates a mid-execution interactive pause that breaks scripted use.
- **Always abort on conflict in non-interactive mode** — skip the prompt, treat any Conflict as a hard failure unless `--overwrite` is explicit. Rejected: too blunt; `--no-X` flags already let users opt out of individual steps.

## Consequences

- The Prompt Collection Phase pre-scans all artifact paths before executing anything.
- The "retry after manual fix" pattern is replaced by: choose Abort (clean exit), fix manually, re-run.
- In non-TTY environments, any unresolved Conflict (`overwrite` not explicitly set) aborts before any Mutation.
