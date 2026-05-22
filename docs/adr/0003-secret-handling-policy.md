# ADR 0003: Secret Handling Policy

## Status
Accepted

## Context
GitHub Personal Access Tokens (PATs) are stored in the system keyring and used
only when remote asset fetching requires authenticated access. Two exposure
channels were identified during issue #43 review:

1. **Output:** `siesta self show-github-pat --full` could print a stored PAT in
   plaintext after a warning only, exposing secrets in terminal history, shell
   logs, and CI artifacts.
2. **Input:** `siesta self set-github-pat` accepted the token as a command-line
   positional argument, making it visible in shell history, process listings,
   and audit logs.

## Decision
Apply a unified **Secret Handling Policy** for PAT commands:

### Output (secret display)
- Keep masked display as the default for `show-github-pat`.
- When `--full` is requested:
  1. Show an explicit risk warning about plaintext capture surfaces.
  2. Require interactive confirmation with fail-closed semantics (explicit
     yes only; deny on empty input, EOF, and non-interactive stdin).
  3. If confirmation is declined, cancel full display and return the masked
     token.

### Input (secret capture)
- Do not accept PAT values via command-line arguments.
- Require hidden interactive entry via `getpass`.
- Require confirmation before persisting the token.

## Consequences
Positive:
- Accidental secret disclosure requires deliberate, interactive steps.
- Default behavior remains safe for routine token identification and setup.
- PAT values are not left in shell history or process listings via argv.

Trade-offs:
- Non-interactive `--full` usage has no bypass by design; operators must use
  masked output or interactive sessions.
- Scripts can no longer pass a PAT on the command line to `set-github-pat`;
  interactive entry is required.
- Users who previously relied on one-step `--full` or argv PAT must adapt.

## Alternatives Considered
- Remove `--full` entirely.
  Rejected because operators still need a supported path to inspect stored
  tokens during troubleshooting.
- Gate `--full` behind an environment variable only.
  Rejected because env-gated bypasses are easy to set accidentally in shared
  shells and do not provide interactive intent confirmation.
- Keep argv PAT with documentation warnings only.
  Rejected because warnings do not remove the exposure channel.
