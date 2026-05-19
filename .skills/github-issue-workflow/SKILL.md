---
name: github-issue-workflow
description: "`gh` mechanics for the `agent:todo` issue lifecycle defined in this repo's AGENTS.md: identify TODO issues via the `agent:todo` label, claim with mutually-exclusive status labels, maintain a single managed plan comment per issue, and transition state atomically. Use whenever the user asks to claim, scout, plan, build, sync, publish, or close agent-actionable GitHub issues."
---

# GitHub Issue Workflow

Implements the lifecycle defined in [`AGENTS.md`](../../AGENTS.md) using GitHub Issues + the `gh` CLI. **This file is the playbook (how); AGENTS.md is the rulebook (what and why).** If they disagree, AGENTS.md wins.

## Pre-flight: `gh`

The user must have the `gh` CLI installed and authenticated.

1. Installation (if missing) -> test with `which gh`, if not found, install with https://github.com/cli/cli#installation
2. Authentication -> test with `gh auth status`, tell the user to run `gh auth login` if user isn't logged-in. 

## Label vocabulary

Two orthogonal axes.

### Type label (persistent)

| Label        | Meaning                                                                                                              |
| ------------ | -------------------------------------------------------------------------------------------------------------------- |
| `agent:todo` | Issue is agent-actionable. Required for the workflow to apply. Persists across the lifecycle, including after close. |

Issues without `agent:todo` are out of scope (bugs, human discussions, feature requests).

**Create agent TODOs** with the [Agent TODO](.github/ISSUE_TEMPLATE/agent-todo.yml) issue template (template chooser → *Agent TODO*). It applies `agent:todo` automatically and requires branch intent.

### Status labels (mutually exclusive, one at a time)

No status label means the issue is **unclaimed**.

| Label             | Meaning                                                             |
| ----------------- | ------------------------------------------------------------------- |
| `agent:scouting`  | A scout is preparing the plan; read-only except the plan comment    |
| `agent:building`  | A builder is implementing; one per session                          |
| `agent:blocked`   | Paused awaiting user input or external dependency                   |
| `agent:reviewing` | Implementation done, awaiting critique/feedback before commit       |
| `agent:done`      | Committed and ready to close (or already closed)                    |

### Bootstrap (one-time per repo)

```bash
gh label create "agent:todo"      --color 0e8a16 --description "Agent: TODO (agent-actionable)"
gh label create "agent:scouting"  --color a2eeef --description "Agent status: scouting (plan in progress)"
gh label create "agent:building"  --color fbca04 --description "Agent status: building (implementation in progress)"
gh label create "agent:blocked"   --color d73a4a --description "Agent status: blocked (awaiting user or external)"
gh label create "agent:reviewing" --color 0075ca --description "Agent status: reviewing (critique pending)"
gh label create "agent:done"      --color cfd3d7 --description "Agent status: done (committed, ready to close)"
```

## Branch (required on every agent TODO)

Every `agent:todo` issue must declare where work happens. Issues filed via the Agent TODO template include form fields **`Branch`** (`branch_mode`) and **`Existing branch name`** (`branch_name`). For issues created another way, the body must state the same information explicitly.

| `branch_mode` | Meaning | Agent action |
| ------------- | ------- | ------------ |
| `new` | New work on a fresh branch | Derive branch name (below), create branch from default branch, work in a **worktree** |
| `existing` | More work on a branch that already exists | Check out that branch (worktree if the user's setup uses them); **do not** create a new branch |

### Pickup gate

Before claiming, read the issue body (or `gh issue view <num> --json body`):

1. If **`Branch`** is missing, **stop** — ask the user to add branch intent or re-file with the Agent TODO template.
2. If **`Branch`** is `existing` and **`Existing branch name`** is empty, **stop** — ask the user to fill the branch name.
3. If **`Branch`** is `existing`, verify the branch exists: `git ls-remote --heads origin <branch_name>` (or ask the user if offline).

Record the resolved branch in the managed plan **Status** block (`Branch: …`).

### New branch naming

When `branch_mode` is `new`, derive the branch **before** substantive work:

1. Start from the issue title: strip a leading `[agent todo]` (case-insensitive), lowercase, replace non-alphanumerics with `-`, collapse repeated hyphens, trim hyphens, truncate slug to **48** characters.
2. Prefix by intent (default **`feat`**):
   - `fix-` — bugfix / regression
   - `docs-` — documentation only
   - `chore-` — tooling, CI, repo hygiene
   - `feat-` — everything else
3. Final form: `<prefix>-<slug>` (e.g. `feat-add-agent-todo-template`). No slashes; match existing repo branches like `feat-agentic-research-workflow`.

Post the chosen branch name in a short issue comment when first claiming (so humans see it before build):

```bash
gh issue comment <num> --body "Branch: \`feat-my-slug\` (new — worktree)"
```

### Worktree for `new`

When `branch_mode` is `new`, implement in a **separate worktree**, not the main checkout (AGENTS.md *Worktrees*):

```bash
# From repo root; adjust default branch if not main
git fetch origin main
SLUG="my-slug"   # from naming steps above, without prefix
BRANCH="feat-${SLUG}"
WT="../$(basename "$PWD")-${SLUG}"
git worktree add -b "$BRANCH" "$WT" origin/main
cd "$WT"
```

If the user does not use worktrees, or worktrees live elsewhere, **ask** before falling back to an in-place branch checkout.

For `existing`, prefer a worktree on that branch when one already exists; otherwise `git worktree add <path> <branch_name>` or checkout per user preference.

## Claim and state transitions

Before claiming, inspect the issue:

```bash
gh issue view <num> --json number,title,labels,assignees,state,body
```

Run the **pickup gate** (branch fields) before setting a status label.

If another agent's `agent:scouting` or `agent:building` is present, **stop and ask the user** (per AGENTS.md rule 3).

Every status change is a single atomic `gh issue edit`:

```bash
gh issue edit <num> \
  --add-label "agent:<new_status>" \
  --remove-label "agent:scouting,agent:building,agent:blocked,agent:reviewing,agent:done"
```

`gh` silently ignores `--remove-label` entries that are not present, so the same remove-list is safe for every transition. **Never include `agent:todo` in the remove list** — the type label is preserved across the lifecycle.

## Managed plan comment

Exactly one agent-owned comment per issue, bracketed by stable markers:

```markdown
<!-- agent-plan:start -->

## Plan

<scouting or building plan>

### Status

- Phase: scouting | building | reviewing | done
- Branch: <name> (`new` | `existing` per issue)
- Last updated: <ISO date>
- Commit: <hash> (when applicable)

<!-- agent-plan:end -->
```

### Find an existing managed comment

```bash
gh issue view <num> --json comments \
  --jq '.comments[] | select(.body | contains("<!-- agent-plan:start -->")) | {id, url}'
```

### Create the first time

```bash
gh issue comment <num> --body-file plan.md
```

### Edit in place

`gh` has no `comment --edit`. Use the REST API:

```bash
gh api --method PATCH \
  /repos/<owner>/<repo>/issues/comments/<comment_id> \
  -f body="$(cat plan.md)"
```

If you cannot reliably find the prior managed comment, **stop and ask** — never post a duplicate plan comment.

## Publication checkpoints

The managed comment **must** be up to date at:

1. End of scouting (plan ready for user review).
2. Start of build (plan confirmed).
3. End of build, before commit (critique + verification summary).
4. After commit (final status + commit hash).

Between checkpoints, prefer local drafts in `plans/scouting-<slug>.md` or `plans/building-<slug>.md` to limit `gh` traffic.

## Closing an issue

After commit:

```bash
gh issue edit <num> \
  --add-label "agent:done" \
  --remove-label "agent:scouting,agent:building,agent:blocked,agent:reviewing"
gh issue close <num> --reason completed
```

Update the managed comment one last time with `Commit: <hash>` in the Status block before closing. The `agent:todo` label remains on the closed issue (useful for `gh issue list --state closed --label agent:todo`).

## Conflict resolution

GitHub state wins (AGENTS.md rule 6). Edge cases:

| Conflict                                       | Resolution                                |
| ---------------------------------------------- | ----------------------------------------- |
| Two managed comments found on one issue        | Stop. Ask user which to keep.             |
| Local `plans/built-*.md` but issue still open  | Sync: close the issue with commit info.   |
| Local `plans/scouted-*.md` but no issue exists | Ask whether to create the issue.          |

## `gh` cheat sheet

| Need                          | Command                                                                                               |
| ----------------------------- | ----------------------------------------------------------------------------------------------------- |
| List open unclaimed           | `gh issue list --state open --label "agent:todo" --search "-label:agent:scouting -label:agent:building -label:agent:blocked -label:agent:reviewing"` |
| Read branch fields            | `gh issue view <num> --json body --jq .body` (look for `### Branch` / `### Existing branch name`) |
| Verify remote branch exists   | `git ls-remote --heads origin <branch_name>`                                                          |
| List all agent-completed work | `gh issue list --state closed --label "agent:todo" --label "agent:done"`                              |
| Show issue + all comments     | `gh issue view <num> --comments`                                                                      |
| Atomic label transition       | `gh issue edit <num> --add-label "<a>" --remove-label "<b>,<c>"`                                      |
| Create plan comment           | `gh issue comment <num> --body-file plan.md`                                                          |
| Edit comment in place         | `gh api --method PATCH /repos/<o>/<r>/issues/comments/<id> -f body="$(cat plan.md)"`                  |
| Close as completed            | `gh issue close <num> --reason completed`                                                             |
| Check repo visibility         | `gh repo view --json visibility`                                                                      |

## Security (gh-specific)

AGENTS.md rule 7 forbids publishing secrets. Concrete gh-specific guardrails:

- **Never paste** `gh auth token` output, `Authorization:` headers, `.env` contents, API keys, signed URLs, or session cookies into issue bodies or comments.
- **Avoid absolute local paths** in comments; use repo-relative paths.
- **Sanitize logs and tracebacks** before pasting — strip credentials, IPs, hostnames, customer/PII data.
- **Check `gh repo view --json visibility`** before pasting implementation detail into a comment you would not put in a public README.
- If you find pre-existing secrets in an issue or comment, **stop and warn the user** instead of silently editing.
