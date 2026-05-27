# Agents

This repository coordinates agent work through **GitHub Issues as the shared source of truth**. Read this file at the start of every session.

For the `gh` mechanics that implement this discipline (labels, managed-comment markers, command syntax), follow [`.skills/github-issue-workflow/SKILL.md`](.skills/github-issue-workflow/SKILL.md).

## Lifecycle

Only issues tagged `agent:todo` are agent-actionable; other issues (bugs, human discussions, feature requests) are out of scope. Lifecycle status across the cycle is tracked via mutually-exclusive `agent:*` status labels — see [the skill](.skills/github-issue-workflow/SKILL.md) for the vocabulary.

Every work item follows the same cycle:

1. **Pick** an open issue tagged `agent:todo` with no `agent:*` status label set. Prefer issues filed with the **Agent TODO** template (`.github/ISSUE_TEMPLATE/agent-todo.yml`), which require branch intent: `new` (agent creates a conventional branch + worktree) or `existing` (named branch).
2. **Claim** by setting the appropriate `agent:*` label *before* substantive reading or writing.
3. **Optional clarification** with the user.
4. **Optional scout** — produce a plan in the issue's managed comment without implementation changes.
5. **Plan approval** — get explicit user go-ahead before implementing.
6. **Build** — implement.
7. **Critique & feedback** — summarize what changed, what was verified, residual risks.
8. **Adversarial review** - Spawn a sub-agent whose explicit task is to adversarially review the implementation and assess security risks
9. **Commit** — one issue = one commit, conventional message, `Refs #<num>` in the footer.
10. **Wrap-up** — when implementation is done, run the `/wrap-up-branch` skill through PR merge. Keep `agent:building` during PR/CI/wrap-up.
11. **Close (post-merge)** — after merge succeeds, update the issue status with the merge commit hash, switch label to `agent:done`, and close the issue.

## Always-on rules

1. **Claim before reading.** Set an `agent:*` label on an issue before any substantive reading, searching, or writing related to it.
2. **One build at a time.** At most one issue may have `agent:building` per session. If the user asks for a second concurrent build, stop and ask what to do.
3. **Don't steal claims.** If `agent:scouting` or `agent:building` is already set by another agent, stop and ask the user.
4. **One issue = one commit** with a clear conventional commit message. Reference the issue (`Refs #<num>`) in the commit footer.
5. **Plans live in the issue's managed comment.** Local drafts in `plans/` are allowed for noisy iteration but must be published to the comment at four checkpoints: end of scouting, start of build, before commit, after commit. For merged PRs, publish a final post-merge status update before closing.
6. **GitHub state wins.** When the issue and any local artifact (e.g. `plans/`) disagree, the issue is correct.
7. **Never publish secrets** into issue bodies or comments — tokens, `.env` contents, `gh auth token` output, credentials, PII, customer data. Treat issues as world-readable until proven otherwise.
8. **Use wrap-up skill before close.** Follow lifecycle order: run `/wrap-up-branch` after commit/critique and before closing the issue. Wrap-up is not complete until the linked issue is transitioned to `agent:done` and closed.

## Worktrees

Issues with **`Branch: new`** (Agent TODO template) require a new branch and a **separate worktree** — see [`.skills/github-issue-workflow/SKILL.md`](.skills/github-issue-workflow/SKILL.md) for naming and `git worktree add` steps. For **`existing`**, use the named branch (worktree if one already exists). If the user's local clone does not use worktrees, ask how they want to handle it.

## Scouting

A scout prepares the ground for a builder. This is how we have partial parallel work with still a single builder to mitigate conflicts. Triggered when the user asks to draft, audit, pre-review, or scout an issue.

- Claim with `agent:scouting`.
- **Read-only outside** the issue's managed comment and a local scouting draft at `plans/scouting-<slug>.md`. Do **not** edit implementation, docs, or test files.
- Produce in the managed comment: context/background, constraints, proposed plan, likely files touched, risks/conflicts, acceptance criteria, security assessment, open questions for user alignment.
- When the plan is ready, switch the label to `agent:blocked` ("awaiting user review of plan").
- Scouts **do not commit**.
- Multiple scouts may run in parallel; each writes a distinct local draft and updates its own issue's managed comment.

### Parallel scouting interview workflow

When multiple scout sub-agents run in parallel, each scout must follow this interaction contract:

- **Branch baseline first.** Scout from the branch declared in the issue body. If no valid branch is declared, default to `main` and explicitly note that fallback in the managed comment.
- **Worktree when not on main.** If the effective scouting branch is not `main`, use a dedicated worktree for that scout.
- **Mandatory grilling.** Use the `/grill-with-docs` skill during scouting.
- **One question at a time.** Ask exactly one clarifying question, include a recommended answer, then stop and wait for the user before continuing.
- **Track Q&A in GitHub.** Every question/answer turn must be appended to the issue's managed comment so the issue remains the source of truth.
- **Stay read-only.** Question loops are scouting only: no implementation, docs, or test edits.

## Post-scouting

If the next pickup is a scouted issue:

- Start from the managed plan comment.
- **Do not run to build.** The scout did not verify against the live repo; iterate the plan with the user first.
- If another scout is currently running (`agent:scouting`) on the issue you want, ask the user: wait, take a different issue, or stop.

## Skills index

- [`.skills/github-issue-workflow/SKILL.md`](.skills/github-issue-workflow/SKILL.md) — `gh` mechanics for the `agent:todo` issue lifecycle: claiming, managed plan comments, label transitions, and post-merge close-out.
- `/wrap-up-branch` — required end-of-task branch finalization workflow once implementation is complete.

## Local artifacts

- `plans/` — local drafts only. Never the source of truth.
