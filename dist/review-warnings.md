# Code Review Warnings

Branch reviewed: `feat-refactor-cli-py` @ `93202bf` vs `origin/main`  
PR: https://github.com/Entalpic/siesta/pull/54 (merged as `9c6022d`)

## Critical

- **Undocumented user-facing breaking change in a “refactor” commit.** Commit `93202bf` changes `siesta self show-github-pat --full` from one-step plaintext output to an interactive gate via `logger.confirm()` → `input()` in `src/siesta/cli/self_app.py` (lines 292–303) and `src/siesta/logger.py` (lines 196–211). On main, `--full` printed immediately. In CI/non-TTY or closed stdin this can hang or raise `EOFError`; there is no `--yes`/env bypass (explicitly rejected in `docs/adr/0003-pat-full-display-confirmation.md`). This is a behavior change, not a move-only refactor.

- **Breaking Python import surface with no semver or release notes.** `src/siesta/cli.py` is deleted; `src/siesta/cli/__init__.py` exports only `app` and `main`. ADR 0002 documents that `from siesta.cli import init_docs` (etc.) is intentionally broken and the compatibility shim was rejected. `pyproject.toml` still has `version = "1.2.0"` and there is no CHANGELOG. That is at least a minor (likely major) semver event with zero consumer migration artifact.

- **Script entrypoint changed without compatibility layer.** `pyproject.toml` changes `[project.scripts]` from `siesta.cli:main` to `siesta.cli.main_app:main`. Anything pinning the old entrypoint string (packaging wrappers, docs, tooling) breaks on upgrade even though `from siesta.cli import main` still works.

- **`--full` non-interactive path is untested in production shape.** `tests/test_cli/test_show_github_pat.py` mocks `siesta.cli.self_app.logger.confirm` for both full-display tests (lines 24, 38). There is no test exercising real `input()`/TTY behavior, so the regression risk for automation users is unverified.

- **Cross-domain import coupling is now a module-boundary footgun.** `src/siesta/cli/project_app.py` line 12 imports `init_docs` from `docs_app` at import time; `main_app.py` eagerly loads all three domain apps. No circular import today (`self_app.py` lazy-imports `main_app` at lines 213–217), but any future `docs_app` → `project_app` import creates a hard cycle that did not exist in the monolithic `cli.py`.

## Suggestions

- **Command-registration guard is too shallow.** `tests/test_cli/test_cli_package.py` only asserts three root subapps, `tab-completions`, and five callables. It does not enumerate leaf commands (`docs`×5, `project`×3, `self`×6 incl. `upgrade` alias, `tab-completions`×4). Drift from `origin/main` would not be caught by this suite alone.

- **Split mixed concerns.** Move ADR 0003 / PAT confirmation (`src/siesta/cli/self_app.py`, `tests/test_cli/test_show_github_pat.py`) into its own PR so the 1.4k-line package split stays reviewable and bisectable.

- **Patch-site proliferation in tests.** `tests/conftest.py` now patches `get_user_pat` in both `siesta.cli.self_app` and `siesta.cli.docs_app` (lines 28–35); other tests patch per-domain `logger.confirm` paths. Consider a single patch target (e.g. always `siesta.utils.github.get_user_pat`) to reduce missed-patch regressions when adding commands.

- **Published API docs will reshuffle.** AutoAPI scans `src/siesta` (`docs/source/conf.py` line 111); symbols move from `siesta.cli.*` to `siesta.cli.docs_app.*` / `project_app.*` / `self_app.*`. In-repo references like `docs/source/guide/example.rst` (`siesta.cli.app()`) still work via `__init__.py`, but external deep links to old autoapi anchors will rot unless redirected.

- **Dual public entrypoints.** `siesta.cli.main_app:main` (pyproject) vs `from siesta.cli import main` (`__init__.py`) are redundant public surfaces; pick one canonical path and document it to avoid drift.
