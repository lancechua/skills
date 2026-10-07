---
name: git-workflow
description: Lance's git workflow rules (rebase over merge, one commit per PR comment, no push until told). Use when committing, syncing/rebasing, resolving conflicts, pushing, or addressing PR review comments.
---

# Git workflow

## Rules

- **Rebase, never merge.** Resolve conflicts and sync with the remote by rebasing. No merge commits.
- **One commit per PR review comment.** Each commit applies cleanly on its own to the base branch: independently cherry-pickable, no dependence on later fixes.
- **Fold follow-ups into the right commit.** `git commit --fixup <sha>`, then autosquash. No standalone "fix the fix" commits.
- **Do not push until the user explicitly says so.** This covers force-push (including after a rebase), `--force-with-lease`, tags, and `gh pr create`. Finish locally, report, then stop and ask.
- **Verify before describing.** Run `git show <sha>` (or `--stat`) before saying what a commit changed. Never describe a diff from memory.
- **Be pragmatic.** These are defaults, not dogma. Project conventions (CONTRIBUTING, CLAUDE.md, squash-merge policy, commit-message format) win over them. If a rule can't be met sensibly, say why and ask rather than contort the history.

## Autosquash

The agent shell has no interactive editor, so run non-interactively:

```bash
GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash <base>
```

`<base>` is the PR's base branch: `gh pr view --json baseRefName -q .baseRefName` (use `origin/<name>`).

## Addressing PR review comments

`<PR>` defaults to the current branch's PR.

1. **Fetch unresolved comments.** `gh pr view <PR> --comments` doesn't show resolved state. Use GraphQL and keep threads where `isResolved` is false:
   ```bash
   gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){reviewThreads(first:100){nodes{isResolved path line comments(first:10){nodes{body author{login}}}}}}}}' -F o={owner} -F r={repo} -F n=<PR>
   ```
   List them in a table.
2. **One commit per comment.**
3. **Overlapping comments.** If comment B builds on A's changes, B can't be cherry-picked alone. Flag it and ask: merge into one commit, or accept the dependency?
4. **Draft a PR body:** table of comment → commit SHA → summary (SHAs from `git show`, not memory).
5. **Stop and ask before pushing.**
