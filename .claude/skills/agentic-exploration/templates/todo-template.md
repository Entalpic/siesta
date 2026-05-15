# `TODO.md`: linearized, agent-runnable tasks

`TODO.md` is the **linearized roadmap** — each item scoped to be completable in a single commit. It changes weekly-ish. This is the file an agent reads at the start of a session and walks down. Items here have already been triaged in `plan.md`; this file is where they get a *contract*.

The discipline: **one TODO = one commit.** If a TODO produces multiple commits, it was too big — split it. If a commit can't be traced to a TODO line, the workflow has leaked.

Every TODO is a **contract**. Before an agent generates code, the contract must be complete: landmarks, constraints written first, acceptance criteria. A bare wish ("improve the loader") is not a TODO — the agent should refuse to execute it until you write the contract. That refusal is the point.

## How to use this template

1. Copy the fenced block below into your project root as `TODO.md`.
2. For each item, fill in **every** section before handing it to an agent. **If a contract is incomplete, the agent should ask before starting.**
3. Move items from `plan.md` into here as you scope them. Move items out (into **Done** or **Archive**) as you complete them.
4. The one-line summary at the top of each item is what the commit message will be — write it in Conventional Commits style (`feat(scope): …`, `fix(scope): …`, etc.) so the agent can use it verbatim.

## What does *not* go in `TODO.md`

- Phase / theme / dependency reasoning (→ `plan.md`).
- The research question or success criteria (→ `research_plan.md`).
- Diagnostic notes from while a TODO was in progress (→ `notes.md`).
- Why something failed last session, or in-flight state (→ `handoff.md`).

---

```markdown
# [🙋 Project name] — TODO

**Current phase:** [🙋 Phase N from `plan.md`]

> One TODO = one commit. If a contract below is incomplete, the agent should ask before starting — not fill it in.

## Active

### [🙋 TODO-0001] [🙋 `feat(scope): imperative one-liner` — this becomes the commit message]

**Why:** [🙋 one sentence — which `plan.md` item or `research_plan.md` phase does this serve?]

**Landmarks:**
- [🙋 `path/to/file.py:42` — function `name` that needs extending / replacing / creating]
- [🙋 `path/to/test_file.py` — where the test will live]
- [🙋 ...]

**Contract — written *before* implementation:**
- *Test that must pass:* [🙋 e.g. `tests/test_loader.py::test_new_shard_layout` — describe the case it covers and the assertion]
- *Type signature / interface:* [🙋 e.g. `def load_batch(shard_id: int, layout: Layout) -> Batch:`]
- *Docstring expectations:* [🙋 e.g. numpy-style, include shape / dtype where relevant]
- *Explicit DO-NOTs:* [🙋 e.g. "do not touch the old `load_batch_v1` path; it's still in use elsewhere". "do not introduce a new dependency."]

**Acceptance criteria:**
- [🙋 The specific, verifiable thing that proves this is done. A passing test, a generated figure matching a reference, a numerical match against a baseline within a tolerance, a CLI output. Not "looks good to me".]

**Estimate / who:** [🙋 e.g. "agent, ~20 min" or "researcher — requires judgment on edge case X"]

**Notes:** [🙋 optional — anything the agent needs to know upfront. Links to `notes.md` entries, prior failed attempts, references.]

---

### [🙋 TODO-0002] [🙋 next item, same structure]

[🙋 same structure as above]

---

## Blocked / waiting

Items that can't be picked up until something else happens. Link to the blocker.

- [🙋 TODO-XXXX] [🙋 one-liner] — **blocked on:** [🙋 what / who / when]

## Done — current phase

Atomic record of what's been completed this phase. Useful for handoff and for the phase post-mortem.

- [🙋 TODO-XXXX] [🙋 one-liner] — commit [🙋 short SHA] — [🙋 YYYY-MM-DD]
- [🙋 ...]

## Archive

Older completed TODOs from previous phases. **Trim aggressively** — the commit log is the canonical record. Keep an entry here only if it points to a non-obvious decision worth surfacing in the eventual write-up.

- [🙋 Phase N-1: short summary line if worth preserving — commit SHA]
```
