# `research_plan.md`: project anchor

`research_plan.md` is the **anchor layer** of the doc hierarchy. It changes rarely (weeks-to-months between meaningful edits) and answers: *what question are we trying to answer? what's the approach? what's the architecture? what does success look like? what are we explicitly not doing?*

Every line should be something you can defend in a meeting. If you can't justify a line, delete it. If an agent drafted a line you can't justify, definitely delete it. This file is **yours** — agents may draft sections you sign off on, but they don't make scoping or success decisions silently.

The fact that this file changes rarely is exactly what lets every other doc (`plan.md`, `TODO.md`, `notes.md`, the code itself) mutate fast — the anchor keeps the project from forgetting its own question.

Equivalently: `design_doc.md`, `proposal.md`, `investigation.md`. Pick one name, stick with it across the project.

## How to use this template

1. Copy the fenced block below into your project root as `research_plan.md`.
2. Fill in every `[🙋 …]` placeholder. **Don't let an agent fill these in for you.**
3. Re-read end-to-end at every phase boundary; edit any drift *before* the next TODO starts.
4. Update the **Change log** section when the approach genuinely shifts — not every edit, only the ones that change what the project *is*.

## What does *not* go in `research_plan.md`

- TODO-level work items (→ `plan.md` / `TODO.md`).
- Library quirks, debugging notes, failed experiments (→ `notes.md`).
- Repo conventions, commands, hard rules (→ `AGENT.md`).
- The philosophy of agent collaboration (→ `Human.md`).
- Final write-up prose. This is a *living plan*, not a paper draft. The moment it reads like a paper introduction you can't edit, it has stopped being load-bearing.

---

```markdown
# [🙋 Project name] — research plan

**Status:** [🙋 active / paused / wrapping up / archived]
**Current phase:** [🙋 phase name from roadmap below]
**Last full re-read:** [🙋 YYYY-MM-DD — update at every phase boundary]

## Question

[🙋 The actual research question or hypothesis, framed for the intended audience (a teammate, a reviewer, your future self, a decision-maker). One paragraph. If you need more than a paragraph, the question isn't sharp enough yet — sharpen before scoping any TODOs.]

**Intended audience for the deliverable:** [🙋 e.g. "internal modeling team", "ICLR reviewers", "a launch decision by Q3". This shapes how everything below is framed.]

**Why now:** [🙋 What changed that makes this worth doing now? Optional but useful for future-you.]

## Success criteria

[🙋 What result, with what confidence, would answer the question? Be concrete. "Lower validation MSE than baseline by ≥5% on the held-out test set of dataset X" is a criterion. "Better than the baseline" is not.]

**What would falsify the hypothesis:** [🙋 The version of the criterion that points the other way. If you can't state this, the question may not be falsifiable — surface that before deepening the project.]

## Comparison / baseline

[🙋 Name the specific point of comparison: an existing model, a prior method, a published baseline, a null hypothesis, a "do nothing" option. Where does it live — a paper, a repo, a checkpoint, a previous internal run?]

## Approach

[🙋 The actual idea, written for someone with relevant background. A few paragraphs. What's the proposed method / model / analysis pipeline? Why should it work? What's the load-bearing assumption?

If you can't write this clearly, the project isn't ready to start. Stop here and think more before scoping TODOs.]

## Architecture sketch

[🙋 At a level above code: modules, data flow, training loop, analysis pipeline, evaluation harness. A diagram or short bulleted breakdown is fine. The point is a mental map before reading the code.

Suggested skeleton — delete or rewrite to match your project:
- **Data layer**: how raw inputs become tensors / dataframes / fixtures.
- **Model / method layer**: the core thing being studied.
- **Training / fitting / inference loop**: optimizer, schedule, checkpointing.
- **Evaluation**: metrics, splits, plots.
- **Glue**: experiment runner, config system, output organization.]

## Roadmap

Milestone-level only, not TODO-level. Each phase produces something you can stop and reflect on. The mapping to actual commits lives in `plan.md` / `TODO.md`.

- **Phase 1 — [🙋 short name]:** [🙋 what gets built / answered. What's the deliverable at the end? What's the stopping condition?]
- **Phase 2 — [🙋 short name]:** [🙋 ...]
- **Phase 3 — [🙋 short name]:** [🙋 ...]

[🙋 Mark the current phase. Cross off completed phases but leave them in for context.]

## Out of scope

What this project is explicitly *not* doing. Being explicit here prevents scope creep and gives the agent a clear "no" to point to when asked.

- [🙋 Item — and *why* it's out of scope. e.g. "Hyperparameter search at scale — fixed compute budget."]
- [🙋 Item — and why.]

## External references

Code, papers, datasets, internal docs the project depends on or builds against.

- [🙋 Paper / link — what we use from it]
- [🙋 Codebase / link — what we use from it]
- [🙋 Dataset / path / version — license, notes]
- [🙋 Internal doc / link — relationship to this project]

## Open questions

Real uncertainties that block or shape the work. Resolved questions get *deleted*, not crossed out — the change log records the resolution.

- [🙋 Open question — what would resolve it]
- [🙋 Open question — what would resolve it]

## Change log

Major pivots and approach changes only. Not every edit — just the ones that change what the project *is*.

- [🙋 YYYY-MM-DD — what changed, why, and where the previous approach is documented (commit SHA, prior version of this file)]
```
