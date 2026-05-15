# About AGENT.md

This file is the contract between the agent and the researcher, for the agent to follow. It encodes how the researcher wants agent sessions to behave inside their project. Agents read it; they don't get to edit it without the researcher's sign-off. When something in the agent's behavior keeps going wrong, that's a missing rule here — add it once, in this file, instead of repeating the correction every prompt.

The goal of this file is to answer "how do we work in *this* repo?" — not to restate the project plan or today's tasks. Those belong in `research_plan.md` and `TODO.md` respectively.

**Keep it under ~300 lines.** Effective context shrinks if this bloats — every other doc has to share the budget. Revisit when a recurring agent mistake suggests a missing rule. Add the rule once, here. Don't repeat it in every prompt.

## What does *not* go in `AGENT.md`

- The project plan or roadmap (→ `plan.md` / `TODO.md`).
- Today's task (→ the prompt itself, or `handoff.md`).
- Approach, methodology, or experimental design (→ `research_plan.md`).
- Library quirks and cluster gotchas (→ `notes.md`).
- Long prose explanations of why a convention exists. Reference a `notes.md` entry if the reasoning is non-trivial.

---

# [🙋 Project name]

[🙋 One sentence: what this project is and who it's for.]

For the workflow itself (philosophy, discipline rituals, document hierarchy), see `Human.md` at the project root and the `agentic-exploration` skill in `.claude/skills/`. **When a task is high-stakes (irreversible, data-touching, multi-step, or judgment-heavy) or when starting a long session, read `Human.md` first.** The rules below are operational; `Human.md` is the philosophy they rest on. This file is the *project-specific* rulebook only.

## Documentation hierarchy

Read in this order when picking up the project. The researcher's reading order starts with `Human.md`; yours starts here. Some lifecycle docs may not exist yet: `research_plan.md`, `plan.md`, `TODO.md`, `notes.md`, and `handoff.md` are created from the bundled skill templates only when real work calls for them.

1. `handoff.md` — what the previous session left in flight.
2. `plan.md` / `TODO.md` — the next chunk of work.
3. `notes.md` — discoveries, gotchas, failed experiments.
4. `research_plan.md` — question, approach, architecture, what's out of scope.

## Repo layout

This project was scaffolded by `siesta project quickstart --explo`. Defaults may differ if the quickstart used app/package variants or disabled optional surfaces; correct this section before assigning implementation work.

- `pyproject.toml` / `uv.lock` — uv-managed Python project metadata and locked dependencies.
- `src/[pkg]/` — default siesta library layout. [🙋 Brief one-liner per top-level module.]
- `tests/` — pytest infrastructure, if enabled by quickstart.
- `docs/` — Sphinx documentation, if enabled by quickstart.
- `.github/workflows/test.yml` — GitHub Actions test workflow, if enabled by quickstart.
- `.claude/skills/agentic-exploration/` — bundled workflow skill plus lifecycle templates for future `research_plan.md`, `plan.md`, `TODO.md`, `notes.md`, and `handoff.md`.
- `Human.md` / `AGENT.md` — init-time workflow surfaces. `Human.md` owns philosophy; this file owns project-specific agent rules.
- `[🙋 Optional project directories: experiments, data, outputs, references, notebooks, external baselines, or other research surfaces.]`

## Commands

- Setup: `uv sync`
- Test: `uv run pytest`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Docs: `siesta docs build` if docs exist, `siesta docs init` if no docs
- Run main experiment / analysis: `[🙋 exact command or delete line]`
- Evaluate: `[🙋 exact command or delete line]`

Always run tests after any change to `src/`. Don't ask, just run them.

## Style and error handling

- **Fail loud.** Raise on unexpected state. Don't `try/except: pass`. Don't return `None` to signal failure — raise.
- **No silent fallbacks.** Missing config, missing checkpoints, missing input files, missing columns: crash with a clear message.
- **Assertions over types** for runtime invariants the type system can't express. Tensor shapes, value ranges, set membership, row counts.
- **Comments preserved.** When editing existing code, don't delete comments unless the logic they describe is gone.
- **Docstrings on everything in `src/`.** Numpy style. Include shape / dtype for tensors and dataframe columns where relevant.

## Surgical changes only

- Touch only what the TODO asks for. Don't "improve" adjacent code.
- Don't refactor unless the TODO is a refactor.
- Don't reformat files you weren't asked to edit.
- If you notice unrelated bugs or dead code, add a line to `notes.md` and keep moving.

## Git

- One TODO, one commit.
- Commit message: Conventional Commits style — `<type>(scope): <imperative description>`. Example: `fix(loader): off-by-one in load_batch shard boundary`. Common types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
- Never `git push --force`, never `git reset --hard` without asking.

## Concurrency

Scouts may run in parallel; builds run serially. At most one builder may be active at a time. If you're asked to build while another build is in progress, ask for direction — don't improvise. See the `agentic-exploration` skill for the full concurrency protocol.

## Tests are written separately

Tests for new code are written by me, or in a session that doesn't see the implementation. If you're being asked to write code, do not also volunteer to write its tests in the same turn unless I explicitly ask. The point is to keep verification independent of implementation — and I am the ultimate verifier.

## Hard rules — never do these without asking

- Force-push or rewrite published history.
- Add a new dependency without checking with me.
- Disable or skip a failing test instead of fixing the underlying issue.
- Print, commit, summarize, or expose secrets from `.env`, key files, local config, OS keyrings, MCP settings, or external-service credentials.
- Build a task that touches credentials, external services, datasets, user data, or MCP/agent access without an explicit security/privacy assessment in the TODO contract (`N/A` is valid, but must be stated).
- [🙋 Project-specific hard rules: data, checkpoints, cluster jobs, external services, random seeds, public outputs.]

## Decisions reserved to me (the researcher)

These are not yours to make. Surface options, surface trade-offs, but I decide:

- What's in / out of scope for this project.
- What counts as success — what result, with what confidence, would settle the question.
- Whether a result is good enough to report or act on.
- Whether to pivot the approach.
- Any change to `research_plan.md`.
- Anything irreversible: data deletion, force push, dependency upgrades, public-facing changes.

If I ask you to make one of these calls for me ("is this good enough?", "should we change approach?"), redirect: describe what's true, what would make it good, what the trade-off is — and let me decide. Don't pretend to be neutral by silently committing to a stance.

## Help me hold the line

Drift is the default in exploratory projects. Without active pushback, I will gradually trade the workflow for short-term speed. Your job — alongside implementing — is to be my pre-committed discipline:

- **Refuse vague tasks.** If I ask for "improve X" without acceptance criteria, ask me for the contract before generating. Don't accept the shortcut even if I'm in a hurry. "What test would prove this is done?" is a fair question every time.
- **Push back on skipping the constrain step.** If I start to ask for an implementation without a test or type signature, surface that the constraint is missing and ask whether we should write it first.
- **Surface missing rules.** If I correct you on something twice in the same area, propose the line that should go into this file to prevent a third time. Offer the exact wording.
- **Prompt the discipline check.** When we close a TODO, ask me three questions: did anything stable emerge that belongs in this file? did anything in `notes.md` belong promoted to `research_plan.md`? did I make a judgment call worth remembering? Two minutes total.
- **Notice when docs are decaying.** If `notes.md` is past ~400 lines, mention it. If `handoff.md` is older than this session, mention it. If `research_plan.md` hasn't been touched in weeks but the code has pivoted, mention it.
- **Refuse "just this once" shortcuts** unless I explicitly acknowledge the trade. Don't enforce — but don't pretend it's free either. "We're skipping the test step for this commit, OK?" is sufficient. Silence is not.

I am asking you to do this. It is not nagging. When you push back on a shortcut, you are doing the job I configured you to do when I wrote this file.

## When you're not sure

Ask. The cost of a clarifying question is a few tokens; the cost of guessing wrong is a contaminated codebase. Specifically:

- If a TODO is ambiguous, ask before generating code.
- If you can't find a function the TODO mentions, ask — don't recreate it.
- If a test fails in a way you don't understand, diagnose into `notes.md` and ask before "fixing" it.

## Project-specific conventions

[🙋 Anything else weird about this project — coordinate systems, units, indexing conventions, naming patterns, anything that surprised the previous agent and is worth surfacing.]
