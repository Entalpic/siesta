# ADR 0001: Prompt-First Command Execution

## Status
Accepted

## Context
Write-oriented CLI commands currently interleave user prompting and state mutations.
If the user interrupts during a late prompt, the repository may be left in a
partially modified state.

The same risk appears across multiple commands, not just one entrypoint.

## Decision
Adopt a two-phase command model for write-oriented commands:

1. Run non-mutating validation checks.
2. Collect all user decisions (prompt collection phase).
3. Execute mutations only after decision collection is complete.

Mutation includes both filesystem writes and external side effects.

For commands that support non-interactive defaults, no prompts are shown in
non-interactive mode. Decisions are resolved from explicit flags first, then
CLI defaults.

## Consequences
Positive:
- Interruptions during decision collection cannot leave partially applied changes.
- Command behavior becomes more predictable and testable via an ordering contract.
- Top-level commands can own decision collection and pass explicit choices to
  nested command calls.

Trade-offs:
- Commands need explicit separation between decision logic and mutation logic.
- Some prompt flows become less conversational and more up-front.

## Alternatives Considered
- Keep current interleaved prompt/write flow and rely on best effort cleanup.
  Rejected because it cannot guarantee zero mutation on cancellation.
- Implement rollback after each mutation.
  Rejected for complexity and incomplete rollback guarantees across side effects.
