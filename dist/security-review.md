# Security Review

Branch reviewed: `feat-refactor-cli-py` @ `93202bf` vs `origin/main`  
PR: https://github.com/Entalpic/siesta/pull/54 (merged as `9c6022d`)

**Scope:** PAT handling, secret exposure, command injection, authentication  
**Verdict:** **No Critical or High issues introduced by this branch.** The diff includes a meaningful PAT hardening; remaining findings are mostly inherited behavior in moved code.

## Critical

**None.**

No new critical vulnerabilities in PAT storage, remote asset fetch, subprocess usage, or auth flows.

## High

**None.**

No new high-severity regressions relative to `origin/main`. The primary security change in this branch **reduces** risk (see Improvements below).

## Medium

### 1. PAT can still be passed on the command line (`set-github-pat`)

`set_github_pat(pat: Optional[str] = "")` accepts the token as a Cyclopts positional argument. Values on argv are visible in shell history, `ps`, audit logs, and crash dumps.

Location: `src/siesta/cli/self_app.py` (`set_github_pat`)

**Status:** Pre-existing (same on `origin/main` in monolithic `cli.py`). Not worsened by the refactor; still worth documenting or discouraging (e.g. help text: prefer interactive `getpass` only).

### 2. `logger.confirm()` defaults to “yes” on empty input

`show-github-pat --full` now requires confirmation (good), but `logger.confirm` uses `prompt(..., default="y")`, so **Enter / empty stdin confirms**.

Location: `src/siesta/logger.py` (`confirm`)

**Impact:** Weakens ADR 0003’s “two deliberate steps” if a user runs `--full` and hits Enter without reading the warning. Same pattern affects `set-github-pat` confirmation (pre-existing).

**Recommendation:** For secret-display prompts, default to `n`, require explicit `y`, or refuse non-TTY (`sys.stdin.isatty()`).

### 3. Partial token exposure in logs and prompts

| Surface | Exposure |
|--------|----------|
| `show-github-pat` (default) | First **14** + last **4** chars |
| `set-github-pat` confirm | First **5** + last **5** chars |
| `show-github-pat --full` (after confirm) | Full plaintext via `logger.info` |

Masked output aids identification but leaks non-trivial entropy; full display still lands in Rich/logger output (terminal scrollback, CI logs if captured).

**Status:** Masking and set-confirm behavior unchanged from `main`; `--full` path is **stricter** than before.

## Low

### 4. Keyring-only storage (unchanged, appropriate)

`get_user_pat()` / `set_password("siesta", "github_pat", ...)` via `keyring` — no PAT in repo config or env vars in this diff. `src/siesta/utils/github.py` is **unchanged** vs `main`.

### 5. GitHub auth usage (unchanged)

- Remote assets: `Github(auth=Token(pat))` after keyring read; abort if missing PAT.
- Version/commit checks: unauthenticated first, PAT if configured (`_get_github_client`).
- Errors mapped to user-facing messages without echoing the token (`format_github_access_error`).

No new auth bypass or scope expansion in the diff.

### 6. Command injection posture (unchanged, sound)

- `run_command` uses `subprocess.run` with **argv lists**, no `shell=True` (verified in `src/`).
- `docs open` uses `subprocess.call(("open", ...))` / `xdg-open` with a single path argument.
- Tab-completion hooks use `_shell_quote()` for paths written into shell RC files.

Refactor moves the same patterns into `docs_app` / `project_app`; no new injection vectors identified.

### 7. Test fixture patches fake PAT broadly

`tests/conftest.py` autouse `mock_user_pat` patches `siesta.utils.github`, `siesta.cli.self_app`, and `siesta.cli.docs_app`. Test-only; ensures fake token does not hit real keyring/API. No production impact.

### 8. Reduced Python import surface

`siesta.cli` now exports only `app` and `main`; entrypoint moved to `siesta.cli.main_app:main`. Shrinks accidental programmatic access to commands — minor hardening, not a security boundary.

## Security improvements in this branch

### `show-github-pat --full` confirmation (primary fix)

**Before (`origin/main`):** `--full` printed the full PAT after a warning only.

**After (`93202bf`):** Warning → interactive `logger.confirm` → on decline, masked token + cancel message; documented in ADR 0003.

Location: `src/siesta/cli/self_app.py` (`show_github_pat`)

Tests added: `test_show_github_pat_full` (confirm mocked `True`), `test_show_github_pat_full_cancelled` (`False`).

### Remote-assets PAT gate preserved

`docs_app.init_docs` still requires `get_user_pat()` when `--remote-assets` is set; behavior matches pre-refactor `cli.py`.

## Summary table

| Area | Branch delta | Risk |
|------|----------------|------|
| PAT storage | Unchanged (keyring) | Low |
| PAT display | **Hardened** (`--full` + confirm) | Improved |
| PAT on argv | Unchanged | Medium (pre-existing) |
| Confirm UX | Unchanged default-yes | Medium |
| Subprocess / shell | Moved, same safe patterns | Low |
| GitHub API auth | Unchanged | Low |
| Injection | No `shell=True`; list argv | Low |

## Explicit conclusion

**No Critical or High issues** in `93202bf` vs `origin/main` for PAT handling, secret exposure, injection, or auth.

The branch is a **net security improvement** for PAT display. Residual Medium items are largely **pre-existing**; the most actionable follow-up is tightening `logger.confirm` for secret-related prompts (default **no**, TTY-only) and discouraging PAT-on-argv for `set-github-pat`.
