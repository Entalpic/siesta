# `notes.md`: discoveries and hard-won lessons

`notes.md` is the **discovery layer**. It grows continuously — every session that diagnoses something, hits a library quirk, runs a failed experiment, or learns a data oddity adds an entry. This is the file that pays the highest cross-session continuity dividend: a fresh agent that reads `notes.md` first avoids relearning every lesson the previous session paid for.

The trap is unbounded growth. A `notes.md` over ~400 lines stops getting read — by you and by every agent session. **Curation is your job.** Agents can (and should) append diagnoses; you decide what gets *promoted* into `AGENT.md` / `research_plan.md` and what gets *pruned*. Build a weekly compaction pass into your rhythm **before** it becomes overwhelming.

The rule of thumb: every diagnostic an agent performs should be logged here. Every stable rule that emerges should be promoted out of here. The file is a *processing queue*, not an archive.

## How to use this template

1. Copy the fenced block below into your project root as `notes.md`.
2. **Append new entries to the top of the relevant section**, with a date. Newest first — old entries scroll off the working set first that way.
3. Each week, compact:
   - Promote stable rules into `AGENT.md` (the agent gets it without needing to read this file).
   - Promote stable findings into `research_plan.md` (the project's anchor reflects what we actually learned).
   - Prune entries that are no longer load-bearing (a quirk that's been fixed at the source can go).
4. **When you promote something, leave a one-line breadcrumb** in the *Promoted* section so the trail survives.

## What does *not* go in `notes.md`

- Today's plan or task (→ `TODO.md`).
- The research question or approach (→ `research_plan.md`).
- Stable, repo-wide conventions (→ `AGENT.md`, once they've stabilized — promote them out of here).
- Session-end pickup context (→ `handoff.md`).
- Long-form prose you'd put in a paper draft. Notes are *scratch* — if it's worth prose, it's worth promoting.

---

```markdown
# [🙋 Project name] — notes

**Last compacted:** [🙋 YYYY-MM-DD — update at each weekly compaction]
**Length budget:** ~400 lines. If we're over, schedule a compaction pass before the next TODO.

> Append entries to the **top** of each section. Each entry: date, what surprised you, the symptom, the fix or workaround, and a commit SHA or TODO ID if applicable. When an entry stabilizes into a repo-wide rule, promote it into `AGENT.md` and leave a one-line breadcrumb under **Promoted** below.

## Library / framework quirks

[🙋 Append a dated entry per quirk. Include: library + version, the surprising behavior, the symptom (how you noticed), the fix or workaround, a commit SHA if applicable.]

## Environment / cluster / tooling gotchas

[🙋 Append a dated entry per gotcha. Include: the environment (machine, container, cluster, OS, GPU model), the surprising behavior, the symptom, the fix or workaround.]

## Data oddities

[🙋 Append a dated entry per oddity. Include: which dataset / file / column, what's weird, when it was discovered, how the code handles it now (and why we don't silently 'clean' it).]

## Failed experiments / attempts

Things that didn't work, and *why*. Keep these even after pivoting — they prevent re-trying the same dead end.

[🙋 Append a dated entry per failed attempt. Include: what was tried, what the result was, the hypothesis for why it failed, whether it's worth revisiting and under what conditions.]

## Diagnostics

When a test fails or an analysis surprises you, the *diagnosis* goes here — not just the fix. Future-you (and any agent) needs the reasoning, not the patch.

[🙋 Append a dated entry per diagnosis. Include: the symptom, the chain of reasoning, the root cause, the fix, and any pattern worth watching for. If the same pattern recurs, that's a candidate for promotion into `AGENT.md`.]

## Promoted (breadcrumbs)

One-line records of entries promoted out of this file. Keeps the trail visible without keeping the bulk.

- [🙋 YYYY-MM-DD — short summary — promoted to `AGENT.md` §section]
- [🙋 YYYY-MM-DD — short summary — promoted to `research_plan.md` §section]
```
