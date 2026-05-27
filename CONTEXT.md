# Context

## Glossary

### Mutation
An operation that changes project state, including filesystem writes and external side effects.

### Prompt Collection Phase
The initial command phase where all user decisions are gathered before any mutation is allowed.

### Execution Phase
The phase that starts after prompt collection and performs only the mutations selected by the user.

### Non-Interactive Resolution
Mode where no prompts are shown; command decisions are resolved from explicit flags first, then CLI defaults.

### Cancellation
User interruption during prompt collection that exits with code 130 at the CLI
entrypoint and must occur before any mutation.

### Validation Phase
Fail-fast, non-mutating checks that run before prompt collection to reject invalid command contexts.

### No-Op Selection
A valid outcome where the user selects no actions; command exits successfully without mutation.

### Decision Ownership
The top-level invoked command owns prompt collection for all downstream actions and passes explicit decisions to helper or nested command calls.

### Ordering Contract
Behavioral guarantee that decision collection completes before the first mutating operation starts.

### Input Precedence
Explicit CLI flags are authoritative; prompts are used only to resolve unspecified decisions.

### CLI Domain Module
A module that owns one command group and its command implementations (for example documentation, project, or self-management commands).

### CLI Executable Contract
The stable public surface for running `siesta` as a command. Behavior and command names must remain compatible; Python import paths are not part of this contract.

### Secret Handling Policy
The rules governing how credential material may enter and leave the CLI: secrets are not accepted via command-line arguments, and plaintext secret output requires explicit interactive confirmation.

### Wrap-Up Phase
The post-commit, pre-close phase where branch work is finalized through PR validation and merge while the issue remains in an active building state.

### Post-Merge Finalization
The mandatory issue-close sequence that occurs only after merge succeeds: publish final issue status, transition to `agent:done`, and close the issue.

### Issue Reference Convention
The rule that branch commits and PR context use `Refs #<num>` for linkage; issue closure remains an explicit workflow step rather than auto-close keywords.
