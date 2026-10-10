---
name: pr-review-primer
description: Primer for starting a review of someone else's pull request: summary, key sections, key decisions, likely confusions, a digest of existing discussion and post-open changes, and a suggested reading order. Use when asked to get up to speed on, onboard to, or prep for reviewing a PR, before running pr-review.
---

# PR review primer

Orient the reviewer before they read the diff. Don't hunt for bugs here; that's `pr-review`.

## Input

The user says how to reach the PR: number, URL, branch, or a local checkout/patch. If missing, ask once. Resolve with `gh pr view <PR>` (or `git diff <base>...<branch>` when local).

## Steps

1. **Ask familiarity**, unless the user already said. One question: how well do they know the changed files/area (new / skimmed / know well)? Calibrate depth: *new* gets more background and glossary; *know well* gets only the deltas and decisions.
2. **Gather.** Run in parallel:
   - `gh pr view <PR> --json title,body,author,baseRefName,headRefName,state,isDraft,createdAt,commits,files,statusCheckRollup,closingIssuesReferences`
   - `gh pr diff <PR>` (use `--name-only` first if huge, then read the central files)
   - Linked issues and design docs named in the body.
   - Review threads: the GraphQL query in `git-workflow` ("Fetch unresolved comments"), plus `gh pr view <PR> --comments` for top-level comments.
3. **Write the primer** (format below).
4. **Digest discussion and changes**, only if the PR is accessible (below).
5. **Close** with a suggested reading order and one concrete first action.

## Primer format

- **Summary.** 2-4 sentences: what and why, and the intended behavior change. Quote the PR's stated goal; flag if the diff does more or less than it says.
- **Shape.** Size (files, +/-), split into code / tests / docs / config / generated. Mark generated or mechanical files as skippable.
- **Key sections.** Table: file or symbol, role in the change, review priority (core / supporting / skim). Core first.
- **Key decisions.** Each non-obvious choice the author made: the choice, the alternative, and where the PR (or a comment) justifies it. Mark "inferred" when the author didn't say.
- **Likely confusions.** Pre-empt: misleading names, code that looks wrong but is intentional, behavior that depends on config or ordering, old code the PR touches but doesn't change, and terms of art. Scale to familiarity.
- **Claims to check.** The PR's "exactly / always / never / no behavior change" statements, listed for `pr-review` to attack.
- **Not in this PR.** Explicit non-goals, deferred work, TODOs added.

## Discussion and change digest

- **Timeline.** Opened date, commits and force-pushes since, current CI status.
- **Threads.** Table: thread (path:line + url), raised by, point in one line, status (open / resolved / outdated), and whether a later commit addressed it (check `git show <sha>`, not the reply).
- **Consensus vs. disputes.** What's settled, what's still contested, who is waiting on whom.
- **Since opened.** What changed in the diff after the first review or since the user's last look. Use `git range-diff` when force-pushed; otherwise list commits after the first review.
- If inaccessible (no `gh` auth, private repo, local patch only), say so and skip this section. Don't guess.

## Also useful

- **Risk map.** Hot spots: public API, migrations, concurrency, numerics, security boundary, deleted tests.
- **Test coverage map.** Which changed behaviors have tests and which don't.
- **How to run it.** Checkout command (`gh pr checkout <PR>`), test command, and any setup the PR needs.
- **Related prior art.** Existing helpers in the repo the PR duplicates or ignores.
- **Questions for the author.** Things the primer couldn't resolve.

## Output

- Lead with the primer, then the digest. Mark what you read vs. what you inferred.
- Keep it skimmable: tables and short bullets, no diff retelling.
- End with a **reading order** (3-6 files, in order) and a **first action**, e.g. "Read `src/x.py` lines 40-120, then run `pr-review`."
