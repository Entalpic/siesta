# Handoff — Phase 2: siesta `project quickstart --explo` implementation

You are picking up where the previous agent left off. **Phase 1 (skill assessment) and Phase 1.5 (skill restructure) are done.** Your job is **Phase 2**: wiring the skill into siesta so that `siesta project quickstart --explo` materializes the workflow into a new project.

This is the handoff doc the previous agent wrote at the user's request. Read it end to end before touching code.

---

## Why we're doing this

**The user** is `victor.schmidt@entalpic.ai`. Their objective: **encourage SOTA agentic workflows for exploratory research projects**. They are the founder/principal researcher; treat them as the protagonist of every session, not as a customer asking for a feature.

**The product context**: siesta is Entalpic's CLI for scaffolding Python projects with their conventions. Today it handles production-style scaffolding (Sphinx docs, pytest infra, CI, pre-commits). It does **not** yet support exploratory/research projects, which have different document conventions and require workflow discipline that production code does not.

**The bigger picture**: research projects (ML experiments, scientific simulation, data analysis) work best when augmented by agents — but only if the project is structured to keep the researcher in ownership of the *what* and *why* while agents handle the *how*. Without active discipline, projects drift to ad-hoc within weeks, and agent-augmented becomes "agent-replaced", with all the contamination that implies. The `agentic-exploration` skill encodes the protocol for keeping that discipline alive. Phase 2 is making it one CLI command away for any new repo.

The relevant background reading is [`system-architecture.md`](system-architecture.md) for siesta itself, and the contents of [`.claude/skills/agentic-exploration/`](.claude/skills/agentic-exploration/) for the skill (`SKILL.md`, `doc-hierarchy.md`, `references/`, `templates/`).

---

## The mental model you must preserve

The skill enforces a **three-surface model**. Do not collapse, duplicate, or rename these — they are load-bearing.

| Surface | Lives at | Audience | Role |
|---|---|---|---|
| `SKILL.md` | `.claude/skills/agentic-exploration/SKILL.md` | Agent (loaded on invocation; reread for high-stakes work) | Canonical **operational protocol** — what the agent does, step by step. The 8-step inner-loop checklist is its core. |
| `Human.md` | Project root (scaffolded by siesta) | Researcher (read at project start, re-read at phase boundaries / weekly) — also the agent in high-stakes situations | Canonical **researcher philosophy** — division of labour, principles, doc hierarchy, anti-patterns. |
| `AGENT.md` | Project root (scaffolded by siesta) | Agent (every session) | **Project-specific rules** — commands, conventions, hard rules. References `Human.md` and the skill. |

The split is intentional. Each file is single-purpose. **If you find yourself duplicating content across them, you have lost the split — re-read the skill and re-do the work.** This is the single biggest mistake to avoid in Phase 2.

The rest of the skill folder splits cleanly by purpose — keep the split intact:

- [`.claude/skills/agentic-exploration/doc-hierarchy.md`](.claude/skills/agentic-exploration/doc-hierarchy.md) — per-layer content and maintenance rhythms appendix. Lives at skill root; read on demand from inside the bundled skill; **never** copied to project root.
- [`.claude/skills/agentic-exploration/references/`](.claude/skills/agentic-exploration/references/) — **init-time** materials. Copied verbatim (with substitutions) into the project root by `--explo`. Two files: [`references/agent.md`](.claude/skills/agentic-exploration/references/agent.md) → `AGENT.md`, [`references/human.md`](.claude/skills/agentic-exploration/references/human.md) → `Human.md`.
- [`.claude/skills/agentic-exploration/templates/`](.claude/skills/agentic-exploration/templates/) — **lifecycle** materials. **Not** copied at init. Stay inside the bundled skill. The agent reaches for one of these only when the researcher's real work calls for the corresponding artifact for the first time (`research_plan.md`, `plan.md`, `TODO.md`, `notes.md`, `handoff.md`) and scaffolds it then — not before.

---

## What is already done (Phase 1 + Phase 1.5)

1. The skill was assessed and restructured under the **Option A** (audience-split) model — previously `SKILL.md` was a dual-audience manifesto + agent protocol; now `SKILL.md` is purely the agent protocol and `Human.md` (templated) is the canonical philosophy.
2. The skill folder `.claude/skills/agentic-exploration/` is in its final layout:
   - `SKILL.md` — agent-facing operational protocol.
   - `doc-hierarchy.md` — deep-dive appendix (skill-internal; not copied to project root).
   - `references/human.md` — canonical researcher manifesto template (becomes `Human.md` at init).
   - `references/agent.md` — project-specific agent rulebook template (becomes `AGENT.md` at init; with the escalation pointer to `Human.md`).
   - `templates/{research-plan,plan,todo,notes,handoff}-template.md` — lifecycle scaffolds the agent uses on demand during the project, **not** materialized at init.
3. The **escalation pointer** — telling the agent to read `Human.md` first when the task is high-stakes (irreversible, data-touching, multi-step, judgment-heavy) or when starting a long session — is present in both `SKILL.md` (top of file) and `references/agent.md` (top of the templated `AGENT.md`).
4. The skill's `description` frontmatter has been updated to include `Human.md` in its trigger surface so the skill matches user requests about drafting/auditing `Human.md`.
5. The skill now enforces the lifecycle hierarchy before implementation work: missing `research_plan.md` blocks `plan.md` / `TODO.md` / code work, missing `plan.md` blocks TODO execution, incomplete TODO contracts block generation, and missing `notes.md` blocks build / diagnosis work that would produce learnings. The same top-down rule is summarized in `doc-hierarchy.md`.
6. `references/agent.md` now reflects the siesta-generated exploratory-project surface: uv defaults, optional tests/docs/actions, bundled `.claude/skills/agentic-exploration/`, lifecycle docs created on demand, and project-specific placeholders for research surfaces and hard rules.

There is no Python code change yet. Siesta is at parity with `main` apart from the skill folder.

---

## What Phase 2 must build

### Command surface

- **`siesta project quickstart --explo`** — scaffold a new exploratory project with the agentic workflow ready. **This is your job.**
- `siesta project quickstart --prod` — placeholder; defer to a future PR. Don't implement.
- `siesta project setup-agentic-workflow` — retrofit an existing project. Defer to a future PR. Don't implement.

The default behavior of `siesta project quickstart` (no `--explo`, no `--prod`) should remain unchanged from today. `--explo` is purely additive. (User has confirmed this implicitly; flag if you'd argue otherwise.)

### Files `--explo` scaffolds under the target project

**Placeholder convention.** Both templates use `[🙋 …]` brackets to mark every spot the researcher must contribute to. The 🙋 emoji is the single signal — `grep '🙋'` in any scaffolded project surfaces every researcher-input spot. Siesta's role: substitute the values it knows (project name from `--name` or detected from `pyproject.toml`, tooling commands it can infer, etc.) and **leave the rest intact**. In interactive mode (`-i`), siesta may prompt the user for any `[🙋 …]` it can sensibly populate from the prompt; in non-interactive mode, leave everything not already known. **Never plausibly fill a `[🙋 …]` placeholder with invented content** — that's the contamination the skill is designed to prevent. The 🙋 marker must round-trip: it lives in the template, it lives in the scaffolded output (for unfilled spots), and the verification step below greps for it.

Under `--explo`, siesta should produce **only** the init-time surface. The lifecycle docs (`research_plan.md`, `plan.md`, `TODO.md`, `notes.md`, `handoff.md`) are **not** pre-created — the agent materializes each one from `templates/` when the researcher's real work first calls for it. Pre-scaffolding empty lifecycle files would be cargo-culting the workflow; the discipline is that each file appears when it has something to hold.

1. `Human.md` — materialized from [`.claude/skills/agentic-exploration/references/human.md`](.claude/skills/agentic-exploration/references/human.md), extracting only the fenced template block (between the two `---` separators inside the file). The `[🙋 …]` placeholders **must be preserved** — do not plausibly fill them. Project name in the template's `# [🙋 Project name] — researcher guide` heading gets substituted (siesta knows the project name).
2. `AGENT.md` — materialized from [`.claude/skills/agentic-exploration/references/agent.md`](.claude/skills/agentic-exploration/references/agent.md), same extraction logic. The `[🙋 …]` sections (`[🙋 Project name]`, `[🙋 One sentence: …]`, `[🙋 exact command]`, etc.) become interactive prompts in `-i` mode or remain as placeholders otherwise.
3. `.claude/skills/agentic-exploration/` — **bundled** copy of the entire skill folder (incl. `SKILL.md`, `doc-hierarchy.md`, `references/`, `templates/`). Locked decision: the project must be self-contained, so a collaborator cloning the repo without the skill installed globally still gets the workflow protocol *and* the lifecycle templates the agent will reach for later.

### Architectural patterns to reuse (do not invent new patterns)

Read the existing siesta code carefully before writing anything new. The patterns to reuse:

- **Command shape**: see [`quickstart_project()` in `src/siesta/cli.py:850`](src/siesta/cli.py#L850). It uses `Annotated[bool, Parameter(name=["-i", "--interactive"])] = False` for the existing interactive flag — follow the same idiom for `--explo`. Composition of commands via direct function calls (not shelling out) is the convention.
- **Asset bundling**: see [`copy_boilerplate()` in `src/siesta/utils/docs.py`](src/siesta/utils/docs.py). The pattern: stage via `TemporaryDirectory`, copy from `importlib.resources.files("siesta") / "boilerplate"`, optional backup-on-overwrite via `_copy_not_overwrite()`. **Reuse this pattern verbatim** — don't write a new copy loop.
- **Bundled assets directory**: under `src/siesta/boilerplate/`. For Phase 2, add `src/siesta/boilerplate/agentic/` containing the skill folder and the doc skeletons. At build/install time, the skill from `.claude/skills/agentic-exploration/` (the repo's authoritative source) must be copied into `src/siesta/boilerplate/agentic/.claude/skills/agentic-exploration/`. Decide: do this via a build hook in `pyproject.toml`, a `Makefile` target, or a CI step. The user hasn't specified — bring them the choice.
- **Config / interactive defaults**: see `CLI_DEFAULTS` in [`src/siesta/utils/config.py`](src/siesta/utils/config.py). Add `--explo`-related defaults there.
- **Logger**: see [`src/siesta/logger.py`](src/siesta/logger.py) — Rich-formatted console output via the module-level singleton. Use `logger.success/info/warning/error/prompt/confirm`.

### New module(s) to add

You will likely need:

- `src/siesta/utils/agentic.py` — new module for the agentic-scaffolding logic. Function shape mirrors the existing `setup_tests()` and `init_docs()` — takes path, interactive flag, project_name, plus an `--remote-assets`-style option if you support that path.
- `src/siesta/boilerplate/agentic/` — bundled assets.

Resist the urge to extend `utils/project.py`. Agentic scaffolding is a distinct concern from production scaffolding; keep them separate so the code paths don't bleed.

---

## Decisions already locked in (do not re-litigate)

| Decision | Choice | Why |
|---|---|---|
| Human-facing file name | `Human.md` (not `RESEARCHER.md`, not `EXPLORE.md`) | User picked this in Phase 1. Obvious counterpart to `AGENT.md`. |
| Skill packaging in scaffolded project | **Bundle** into project's `.claude/skills/` | User locked in Phase 1. Self-contained projects work for collaborators without the skill installed. |
| SKILL.md content model | Agent operational protocol only (not dual-audience) | Phase 1.5 redistribution. Don't move philosophy back into it. |
| `Human.md` content model | Canonical researcher philosophy (not thin pointer) | Phase 1.5. Inverted polarity: `Human.md` is canonical philosophy; the skill is canonical operational. |
| `--prod` flag | Deferred; out of scope for this PR | User direction. |
| `setup-agentic-workflow` retrofit command | Deferred; out of scope for this PR | User direction. |

---

## Open decisions for you to bring to the user

Do **not** make these unilaterally. Surface them, present the trade-off, let the user decide.

1. **Build-time sync of the skill into bundled assets.** Options: (a) `pyproject.toml` build hook copying `.claude/skills/agentic-exploration/` → `src/siesta/boilerplate/agentic/.claude/skills/`; (b) a `Makefile` / `scripts/` target run before release; (c) keep two copies in git and add a CI check that they're identical. Each has trade-offs (build complexity vs. drift risk vs. PR noise).
2. **Interactive mode behavior.** In `-i` mode, should the command prompt to fill any `[🙋 …]` slots in `AGENT.md` / `Human.md` that siesta can sensibly seed (e.g. project name already known, lint/test commands inferable), or always leave them untouched? Recommend: prompt only in `-i` for the spots siesta has evidence for; placeholders otherwise. Confirm with user.
3. **`--remote-assets` parity.** Today `siesta docs init` supports `--remote-assets` to fetch the latest boilerplate from GitHub. Should `--explo` support the same? (Adds complexity. Recommend: not in this PR; the bundled skill is enough for v1.)

---

## Verification plan

Before declaring Phase 2 done:

1. End-to-end smoke: in a temp directory, run `siesta project quickstart --explo --name test-explo`. Confirm exactly `Human.md`, `AGENT.md`, and the bundled `.claude/skills/agentic-exploration/` land — **and nothing else**. Confirm the bundled skill's files are byte-identical to the repo's authoritative source (incl. `templates/`).
2. Skill discoverability: `cd test-explo` and verify the agent can invoke the skill (e.g. via `/agentic-exploration` or by triggering its description). The skill should activate exactly as it does in this repo.
3. Placeholder preservation: grep the scaffolded `Human.md` and `AGENT.md` for `🙋` — every bracketed researcher-input spot must be intact, not plausibly filled.
4. Existing tests still pass: `uv run pytest` (or whatever siesta uses). No regression in `docs init`, `setup-tests`, or `quickstart_project` defaults.
5. Cross-references in scaffolded docs resolve: the `Human.md`-to-skill link, the `AGENT.md`-to-skill link, the `AGENT.md`-to-`Human.md` link, and `Human.md`-to-`doc-hierarchy.md` (`.claude/skills/agentic-exploration/doc-hierarchy.md`).
6. No premature lifecycle files: confirm `research_plan.md`, `plan.md`, `TODO.md`, `notes.md`, `handoff.md` are **absent** from the scaffolded project. They should appear later only when the agent materializes them from `templates/` in response to real work.

---

## How to work with this user (style and discipline)

The user has been collaborating under the `agentic-exploration` skill's protocol throughout Phase 1 and 1.5. They expect the same in Phase 2.

- **Per-step justification.** They prefer "justify what you're about to do; wait for go; act; move on" over batched edits. Hold this rhythm even for small changes. The user explicitly asked for it.
- **Pushback is welcomed.** When you think a decision is wrong, say so. They will not punish disagreement; they will punish quiet compliance. The Phase 1.5 redistribution (Option A) was the result of the user pushing back on the prior agent's "shared mental model is a feature" framing — the prior agent conceded, and the redistribution was the right call.
- **Plan mode for design choices.** For non-trivial decisions (where new files go, how the build sync works, how the interactive prompts compose), enter plan mode and walk them through the options before writing code.
- **Don't fill `[🙋 …]` placeholders.** Ever. They are the user's authoring surface; you do not plausibly fill them.
- **Refuse vague tasks.** If the user gives you a task without a contract (test, type, acceptance criterion), ask before generating. This is the protocol the skill itself prescribes; modeling it during the implementation reinforces the pattern.

---

## Reference reading order for you, the next agent

1. **This document.** You are here.
2. [`.claude/skills/agentic-exploration/SKILL.md`](.claude/skills/agentic-exploration/SKILL.md) — the protocol you will follow while building, *and* the artifact you are about to bundle into projects.
3. [`.claude/skills/agentic-exploration/references/human.md`](.claude/skills/agentic-exploration/references/human.md) — the template you will materialize. Read end-to-end so you know what goes into scaffolded projects.
4. [`.claude/skills/agentic-exploration/references/agent.md`](.claude/skills/agentic-exploration/references/agent.md) — same.
5. [`system-architecture.md`](system-architecture.md) — siesta's overall architecture. Skim the "Component Deep-Dive" and "Design Decisions" sections.
6. [`src/siesta/cli.py:850-1086`](src/siesta/cli.py#L850-L1086) — the `quickstart_project` function and the surrounding `setup_tests` / `init_docs` calls that demonstrate the composition pattern.
7. [`src/siesta/utils/docs.py`](src/siesta/utils/docs.py) — `copy_boilerplate()` and `_copy_not_overwrite()`. The patterns to reuse.
8. [`src/siesta/utils/project.py`](src/siesta/utils/project.py) — the closest existing analogue to what you're building. Read for shape, not content.

---

## Open questions you may face

- The skill mentions `siesta project quickstart --explo` at multiple points (top of `SKILL.md`, in the behavior-when-active section, in `Human.md` template). If you decide during implementation that the flag should be named differently (`--exploration`, `--research`, etc.), update the skill in the same PR so the references don't go stale. The user picked `--explo` originally as a short form parallel to a future `--prod`; that decision can be revisited but should be revisited deliberately, not by accident.
- The `agentic-exploration` skill description in `SKILL.md` frontmatter is long (~1700 chars). It's intentionally rich for trigger matching. Don't trim it without discussion.

---

Good luck. Hold the line.
