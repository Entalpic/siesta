# Agentic quickstart — Phase 2 complete

Phase 2 (`siesta project quickstart --explo`) is implemented. Subsequent phases — `--prod`, `setup-agentic-workflow`, `project add-skill agentic-exploration` — remain deferred.

## What ships now

Running `siesta project quickstart --explo` scaffolds, in addition to the normal quickstart output:

- `Human.md` at the project root (rendered from the bundled `references/human.md`).
- `AGENT.md` at the project root (rendered from the bundled `references/agent.md`).
- The full bundled skill at `.claude/skills/agentic-exploration/` in the target project, including `SKILL.md`, `doc-hierarchy.md`, `references/`, and `templates/`.

Lifecycle documents (`research_plan.md`, `plan.md`, `TODO.md`, `notes.md`, `handoff.md`) are intentionally **not** materialized at init. The agent reaches for `templates/` only when the researcher's real work first calls for the corresponding artifact.

## Where the assets live now

Single source of truth in siesta: [`src/siesta/skills/agentic-exploration/`](src/siesta/skills/agentic-exploration/), flat (no `.claude/` hierarchy in siesta's source tree — that hierarchy is a downstream tool concern, materialized at scaffold time in the target project). The previous repo-local copy at `.claude/skills/agentic-exploration/` was removed in the same commit so there is no drift surface. The bundled skill was relocated out of `boilerplate/` (which stays for *docs* boilerplate only) into its own `skills/` subpackage to surface skills as a first-class concept.

Siesta itself is production-style and no longer consumes the agentic-exploration skill in-repo. Use the user-scope skill at `~/.claude/skills/agentic-exploration/` if you want the workflow available across siesta sessions.

## Placeholders siesta fills at scaffold time

Siesta substitutes only the `[🙋 …]` slots that it can derive without inventing research-domain content. All other `🙋` placeholders round-trip unchanged so `grep '🙋'` in a scaffolded project still surfaces every researcher-input spot.

| Placeholder | Source |
|---|---|
| `[🙋 Project name]` | `--name` / `pyproject.toml` |
| `[🙋 package name]` | normalized project name (hyphens → underscores) |
| `[🙋 test command]` | `uv run pytest` when tests enabled; bullet line dropped otherwise |
| `[🙋 docs command]` | `siesta docs build` / `siesta docs init` line when docs enabled; bullet line dropped otherwise |

## Three-surface model (preserved)

| Surface | Lives at | Audience | Role |
|---|---|---|---|
| `SKILL.md` | `src/siesta/skills/agentic-exploration/SKILL.md` (and at `.claude/skills/agentic-exploration/SKILL.md` in scaffolded projects) | Agent | Canonical operational protocol. |
| `Human.md` | Scaffolded at project root by `--explo` | Researcher | Canonical researcher philosophy. |
| `AGENT.md` | Scaffolded at project root by `--explo` | Agent | Project-specific rules. References `Human.md` and the skill. |

## Implementation entry points

- [`src/siesta/utils/agentic.py`](src/siesta/utils/agentic.py) — `setup_agentic_exploration(...)`, `render_reference_template(...)`, `copy_agentic_skill(...)`.
- [`src/siesta/cli.py`](src/siesta/cli.py) — `quickstart_project()` exposes the `--explo` flag. When neither `--explo` nor `--no-explo` is passed the user is always prompted with an explanation of what gets scaffolded (no silent default, even in non-interactive mode).
- [`src/siesta/utils/config.py`](src/siesta/utils/config.py) — `CLI_DEFAULTS` intentionally does **not** carry an `"explo"` entry: the flag is prompt-or-pass, never silently defaulted.
- [`tests/test_utils/test_agentic_utils.py`](tests/test_utils/test_agentic_utils.py) and [`tests/test_cli/test_quickstart_project.py`](tests/test_cli/test_quickstart_project.py) — coverage.

## Retrofit command

`siesta project add-skill agentic-exploration` retrofits the workflow into an existing project. It detects `tests/` and `docs/` from the filesystem so the rendered `AGENT.md` only documents commands that actually exist, then calls the same [`setup_agentic_exploration()`](src/siesta/utils/agentic.py) as `--explo`. See [`src/siesta/cli.py`](src/siesta/cli.py) and [`tests/test_cli/test_add_skill.py`](tests/test_cli/test_add_skill.py).

Today only `agentic-exploration` is a supported skill; the validation lives in `SUPPORTED_SKILLS` in [`src/siesta/cli.py`](src/siesta/cli.py) — adding a new skill is a one-line change.

## Deferred follow-ups

- `siesta project quickstart --prod` — production-style quickstart preset.
- `siesta project setup-agentic-workflow` — retrofit-the-whole-workflow command (broader scope than `add-skill`).
- The `pyproject.toml` sdist include line (`src/boilerplate/*`) looks stale relative to actual layout (`src/siesta/boilerplate/`). Wheels are unaffected and ship correctly. Worth a separate fix.
