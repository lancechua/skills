---
name: finalize-review
description: A workflow for finishing a review of someone else's pull request: re-check the PR for updates, run a final pass, draft the verbatim comments with their locations as a plan, revise, and post only on "post it". Use when asked to finalize, wrap up, draft, or publish a PR review. Run after pr-review.
---

# Finalize review

Turn the running notes into a posted review. Nothing is posted until the user says "post it".

## Steps

1. **Check for updates.** `gh pr view <PR> --json commits,state,reviews,comments` against the date in the notes. List new commits and replies. Check fixes with `git show <sha>`, not the reply text. If the PR is merged, the review becomes a follow-up comment.
2. **Final pass.** Run `pr-review` pass 2 on the new diff only, and read the notes against any linked discussion. Add findings to the notes.
3. **Draft as a plan.** Use plan mode if available. The plan is the review, verbatim, so the user can comment on the exact text. For each comment, give its location: PR summary, inline (`path:line`), issue, or follow-up.
4. **Revise.** Apply the user's edits and print the full text again. Repeat until approved.
5. **Post** only on "post it". Summary review plus inline comments via `gh api` or `gh pr review`, and use event `COMMENT` unless told otherwise.
6. **Record.** Add the review URL and date to the top of `pr-<N>-review.md`.

## Comment style

- Short and direct. One-line intro that says what is good or what the review covers, then numbered items.
- Don't list what was checked, unless the user explicitly asked for a check to be included, or the check gave an interesting result (e.g. a failure). Then include it, even if an agent ran it.
- Tag each item: blocking is the default, otherwise mark **Optional** or **Tentative**.
- Each item: location, the issue, the fix or the question. Nits get a sentence.
- If an item needs detail, keep the comment short and offer detail if the author asks.
- Be transparent about who did what: say which work (prototypes, checks, analysis) was done by an agent and which by the user.
- Use `sembr:sembr-reformat` on the draft if the skill is installed. Skip it if not.
