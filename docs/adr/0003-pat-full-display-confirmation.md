# ADR 0003: PAT Full-Display Confirmation Friction

## Status
Accepted

## Context
`siesta self show-github-pat --full` could print a stored GitHub PAT in
plaintext. Even with a warning message, a single flag was enough to expose
secrets in terminal history, shell logs, and CI artifacts.

This behavior predates the CLI package refactor and was identified as a
high-risk security concern during issue #43 review.

## Decision
Keep masked display as the default for `show-github-pat`.

When `--full` is requested:

1. Show an explicit risk warning about plaintext capture surfaces.
2. Require interactive confirmation before printing the full token.
3. If confirmation is declined, cancel full display and return the masked token.

## Consequences
Positive:
- Accidental secret disclosure requires two deliberate steps (`--full` plus
  confirmation).
- Default behavior remains safe for routine token identification.

Trade-offs:
- Non-interactive `--full` usage now requires mocking or alternate operational
  workflows; there is no bypass flag by design.
- Users who previously relied on one-step `--full` must confirm explicitly.

## Alternatives Considered
- Remove `--full` entirely.
  Rejected because operators still need a supported path to inspect stored
  tokens during troubleshooting.
- Gate `--full` behind an environment variable only.
  Rejected because env-gated bypasses are easy to set accidentally in shared
  shells and do not provide interactive intent confirmation.
