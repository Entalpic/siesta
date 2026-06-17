# Agents

## Working Principles

**Apply these universally, on every task.**

### 1. Think Before Coding

State your assumptions explicitly. If multiple interpretations exist, present them — don't pick silently. If a simpler approach exists, say so. If something is unclear, stop and ask.

Read `system-architecture.md` first to understand repository structure and boundaries before broad searching. Treat it as the source of truth for architecture; when a task changes components, boundaries, or data flow, update it in the same task.

Before implementing (and whenever a request is vague), use the `grill-with-docs` skill to stress-test the plan against the project's domain language and documented decisions (`CONTEXT.md`, ADRs).

### 2. Simplicity First

Minimum code that solves the problem. Nothing speculative. No features beyond what was asked, no abstractions for single-use code, no error handling for impossible scenarios.

### 3. Surgical Changes

Touch only what you must. Don't "improve" adjacent code, comments, or formatting. Match existing style. Every changed line should trace directly to the user's request. Remove imports/variables/functions that *your* changes made unused; leave pre-existing dead code alone.

### 4. One Artifact Owns Each Piece of Guidance

Three artifacts carry agent guidance, each owning a distinct slice:

- **Constitution** (`AGENTS.md`): always loaded, applies to every task. Owns global principles only. Keep it thin.
- **Rule** (`.cursor/rules/*.mdc`, `.claude/rules/*.md`): loaded by file glob/path. Owns constraints tied to a specific technology or directory.
- **Skill** (`SKILL.md` directory): invoked on demand. Owns multi-step procedures and workflows.

Never duplicate guidance across artifacts. When guidance is a procedure, move it into a Skill and reference it from here.

### 5. Security and Consistency

Treat secrets exposure as critical: API keys, tokens, passwords, credentials, webhook URLs, `.env` contents. Never hardcode secrets in code, tests, docs, examples, commits, or PR text. If you detect a leak or high-risk pattern, stop and warn clearly — even when it is outside the original request.

Before declaring completion: (1) run a secret/leak/security scan, (2) verify every changed line traces to the user's request, (3) check consistency against `CONTEXT.md`, `CONTEXT-MAP.md`, and relevant ADRs.

---

## GitHub Issue Workflow

This repository coordinates agent work through **GitHub Issues as the shared source of truth**.

For the `gh` mechanics that implement this discipline (labels, managed-comment markers, command syntax), follow [`.skills/github-issue-workflow/SKILL.md`](.skills/github-issue-workflow/SKILL.md).

## Lifecycle

Only issues tagged `agent:todo` are agent-actionable; other issues (bugs, human discussions, feature requests) are out of scope. Lifecycle status across the cycle is tracked via mutually-exclusive `agent:*` status labels — see [the skill](.skills/github-issue-workflow/SKILL.md) for the vocabulary.

Every work item follows the same cycle:

1. **Pick** an open issue tagged `agent:todo` with no `agent:*` status label set. Prefer issues filed with the **Agent TODO** template (`.github/ISSUE_TEMPLATE/agent-todo.yml`), which require branch intent: `new` (agent creates a conventional branch + worktree) or `existing` (named branch).
2. **Claim** by setting the appropriate `agent:*` label *before* substantive reading or writing.
3. **Optional clarification** with the user.
4. **Optional scout** — produce a plan in the issue's managed comment without implementation changes.
5. **Plan approval** — get explicit user go-ahead before implementing.
6. **Builder grill gate** — builder runs `/grill-with-docs`, records outcomes/open questions, then explicitly asks permission to proceed. While waiting, keep the issue in `agent:blocked`.
7. **Build** — implement only after explicit user approval to build.
8. **Critique & feedback** — summarize what changed, what was verified, residual risks.
9. **Adversarial review** - Spawn a sub-agent whose explicit task is to adversarially review the implementation and assess security risks
10. **Commit** — one issue = one commit, conventional message, `Refs #<num>` in the footer.
11. **Wrap-up** — when implementation is done, run the `/wrap-up-branch` skill through PR merge. Keep `agent:building` during PR/CI/wrap-up.
12. **Close (post-merge)** — after merge succeeds, update the issue status with the merge commit hash, switch label to `agent:done`, and close the issue.

## Always-on rules

1. **Claim before reading.** Set an `agent:*` label on an issue before any substantive reading, searching, or writing related to it.
2. **One build at a time.** At most one issue may have `agent:building` per session. If the user asks for a second concurrent build, stop and ask what to do.
3. **Don't steal claims.** If `agent:scouting` or `agent:building` is already set by another agent, stop and ask the user.
4. **One issue = one commit** with a clear conventional commit message. Reference the issue (`Refs #<num>`) in the commit footer.
5. **Plans live in the issue's managed comment.** Local drafts in `plans/` are allowed for noisy iteration but must be published to the comment at the required lifecycle checkpoints (see the workflow docs). For merged PRs, publish a final post-merge status update before closing.
6. **GitHub state wins.** When the issue and any local artifact (e.g. `plans/`) disagree, the issue is correct.
7. **Never publish secrets** into issue bodies or comments — tokens, `.env` contents, `gh auth token` output, credentials, PII, customer data. Treat issues as world-readable until proven otherwise.
8. **Use wrap-up skill before close.** Follow lifecycle order: run `/wrap-up-branch` after commit/critique and before closing the issue. Wrap-up is not complete until the linked issue is transitioned to `agent:done` and closed.
9. **Refuse guessing under uncertainty.** In the face of uncertainty, refuse the temptation to guess and ask the user.
10. **Mark agent-authored issue content.** Every agent-authored issue comment/reply must end with `🤖` as the final non-whitespace character.
11. **Never track the default branch.** A working branch must never have the default branch (`origin/main`) as its upstream. If detected, stop and warn the user before further work (the workflow skill has detection + remediation). Upstream is set only on the first push.

## Worktrees

Issues with **`Branch: new`** use a new branch in a dedicated worktree. When the agent is **already inside a worktree whose branch is not the default branch**, it first **asks whether to reuse the current worktree or create a new one**. For **`existing`**, use the named branch (worktree if one already exists). If the user's local clone does not use worktrees, ask how they want to handle it. See [`.skills/github-issue-workflow/SKILL.md`](.skills/github-issue-workflow/SKILL.md) for the worktree decision, `git worktree add` steps, and the upstream guard.

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
- **Asynchronous scouting is allowed.** If user attention is unavailable, do not block scouting; publish unresolved items under `Open questions (async scout)` in the managed comment.
- **Structured unresolved items.** Each unresolved scouting question must include: `Question`, `Recommended answer`, `Risk if wrong`, `Needs user confirmation`.
- **One question at a time (live mode).** When actively interviewing the user, ask exactly one clarifying question, include a recommended answer, then wait for the user before continuing.
- **Track Q&A in GitHub.** Every question/answer turn must be appended to the issue's managed comment so the issue remains the source of truth.
- **Stay read-only.** Question loops are scouting only: no implementation, docs, or test edits.

## Post-scouting

If the next pickup is a scouted issue:

- Start from the managed plan comment.
- **Do not run to build.** The scout did not verify against the live repo; iterate the plan with the user first.
- **Builder grill is mandatory.** Before implementation, builder must run `/grill-with-docs`, publish `Grill outcomes`, then explicitly ask for build authorization.
- **Strict approval gate.** If approval wording is ambiguous, do not infer intent; ask again. No implementation starts before explicit approval.
- If another scout is currently running (`agent:scouting`) on the issue you want, ask the user: wait, take a different issue, or stop.

## Skills index

- [`.skills/github-issue-workflow/SKILL.md`](.skills/github-issue-workflow/SKILL.md) — `gh` mechanics for the `agent:todo` issue lifecycle: claiming, managed plan comments, label transitions, and post-merge close-out.
- `/wrap-up-branch` — required end-of-task branch finalization workflow once implementation is complete.

## Local artifacts

- `plans/` — local drafts only. Never the source of truth.
