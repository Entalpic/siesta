# `plan.md`: medium-grained roadmap

`plan.md` is the **medium-grained roadmap** — the next 5-20 things that need to happen, grouped by theme or phase. It changes weekly-ish. This is where you reason about *ordering, dependencies, and risk* before linearizing items into one-commit-sized contracts in `TODO.md`.

If `research_plan.md` says *"phase 2: ablations"*, `plan.md` says *"in phase 2 we need these 6 ablations, in roughly this order, and the GP-vs-NN comparison probably has to wait on the data layout fix"*.

You can keep `plan.md` and `TODO.md` as separate files (this template) or fold both into one file with two sections — the skill says both are fine. Pick once and stick with it.

## How to use this template

1. Copy the fenced block below into your project root as `plan.md`.
2. Group items by phase (from `research_plan.md`'s roadmap) or by theme if phases are too coarse.
3. Give each item a stable identifier (e.g. `P2-A3` for phase 2 / theme A / item 3) so TODOs can reference them. The identifier doesn't need to be formal — just unique enough that a TODO's `Source plan item` field can point back unambiguously.
4. Re-scope at every phase boundary; archive completed phases.
5. When an item is ready to be done, move it into `TODO.md` with a full contract — *don't* execute items directly from `plan.md`. The contract step is non-negotiable.

## What does *not* go in `plan.md`

- The research question or success criteria (→ `research_plan.md`).
- One-commit-sized, agent-runnable tasks with contracts (→ `TODO.md`).
- Per-item debugging notes or diagnoses (→ `notes.md`).
- Session-level pickup context (→ `handoff.md`).

---

```markdown
# [🙋 Project name] — plan

**Current phase:** [🙋 Phase N — name from `research_plan.md`]
**Last re-scoped:** [🙋 YYYY-MM-DD]

## Phase [🙋 N] — [🙋 short name]

**Goal of this phase:** [🙋 one sentence — what stopping condition tells us this phase is done?]

**Stopping condition / deliverable:** [🙋 specific thing that ends the phase. e.g. "a notebook reproducing the baseline within ±2% of the published number", "a written ablation table with N rows".]

### [🙋 Theme A — e.g. "data plumbing"]

- [🙋 `P{N}-A1` Item — one line. Why it's needed. Any upstream dependency.]
- [🙋 `P{N}-A2` Item — ...]
- [🙋 `P{N}-A3` Item — ...]

**Risks / unknowns for this theme:** [🙋 what could go sideways; what would block progress; what's the cheap probe that would resolve the risk?]

**Security / privacy considerations:** [🙋 does this theme touch credentials, external services, datasets, user data, or MCP/agent access? `None identified` is valid but must be explicit.]

### [🙋 Theme B — e.g. "baseline reproduction"]

- [🙋 `P{N}-B1` Item — depends on `P{N}-A1`]
- [🙋 `P{N}-B2` Item — ...]

**Risks / unknowns:** [🙋 ...]

### [🙋 Theme C — e.g. "the new method"]

- [🙋 `P{N}-C1` Item — ...]
- [🙋 `P{N}-C2` Item — ...]

**Risks / unknowns:** [🙋 ...]

## Cross-cutting / parking lot

Items that don't fit a theme yet, or are tempting tangents being deferred on purpose. Capturing them here prevents them from sneaking into TODOs by accident.

- [🙋 Item — why it's parked, what would re-activate it]

## Next 1-3 items to linearize

When you next sit down to write TODOs, pull from here:

1. [🙋 Item from above, ready to scope into a contract in `TODO.md`]
2. [🙋 ...]
3. [🙋 ...]

## Archive — completed phases

Brief records of completed phases. Useful for `git bisect` orientation and for the eventual write-up.

### Phase [🙋 N-1] — [🙋 name] — done [🙋 YYYY-MM-DD]

[🙋 One paragraph: what got done, what surprised us, what got promoted into `research_plan.md` or `AGENT.md` as a result, key commit SHAs if useful.]
```
