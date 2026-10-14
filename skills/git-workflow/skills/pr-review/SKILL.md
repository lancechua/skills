---
name: pr-review
description: A checklist for reviewing someone else's pull request: a design/contract pass, an adversarial pass that probes claims, config, boundary inputs, gates and a realistic scenario, and an over-engineering pass via ponytail-review when installed. Use when asked to review a PR, re-review after updates, or catch up on a PR's review threads. For responding to review comments on your own PR, use git-workflow.
---

# PR review

Three passes. They find different bugs, so do all of them.

1. **Design and contract.** API shape, abstractions, docstrings vs. behavior, what can be simplified or deleted.
2. **Break it.** Run the code against inputs and configs the author didn't test. Write each probe as a small script in a scratch directory, not the repo.
3. **Over-engineering.** If the `ponytail:ponytail-review` skill is installed (check the available-skills list), invoke it on the PR diff. Fold its findings into **simplify / judgment call**. Skip this pass if it isn't installed.

## Pass 2 probes

1. **Attack every "exactly", "always", "never" and "equivalent".** Build the smallest counterexample: two periods, two channels, one varying input. A claim that survives is fine. One that doesn't gets qualified or fixed.
2. **Run under non-default config.** Precision (`floatX=float32`), alternate backends (JAX, numba), the other OS or platform when the code touches a solver.
3. **Feed boundary inputs.** Zero and negative values, empty and 0-d arrays, a single dimension, integer vs. string labels, partial dicts, mixed zero/non-zero parameters. Check values and gradients (NaN, inf).
4. **For every validation or gate, name what it can't see.** What does the check actually prove? Matching labels, shapes or names can pass on the wrong object. Construct the input that slips through.
5. **Run one realistic scenario.** Real-looking data, not the test fixture: trending or growing inputs, flighted/sparse ones, short windows. Read the numbers the feature produces and ask whether a user would act on them.

## Notes

Keep running notes in `pr-<N>-review.md` in the working repo, created at the first finding.
Sections: **Open**, **Tentative**, **Optional**, **Verified**.
Log an item when the user asks ("log it"), with its tag.
Write each item concisely, using sub-items instead of long prose.
Add explainers (e.g. a table of which quantity is which) when the user asks for one.
If `sembr:sembr-reformat` is installed, apply it to the notes and any drafted comment.

## Output

- Number findings so the author can reference them (`#1`, `#2`, …).
- Split into **should fix before merge** and **simplify / judgment call**.
- Each finding: location, the failing input or quote, the expected vs. actual result.
- Mark what you verified by running code vs. what you read.

## Re-reviewing after updates

1. List threads and replies since your last review. Use the GraphQL query in git-workflow and filter by date. Digest each reply: the point, whether it changes your finding, and what is still open. Update the notes.
2. For each of your findings, check the fixing commit with `git show <sha>`, not the reply text.
3. Re-run pass 2 on the new diff only. Fixes introduce their own boundary cases.

When the review is ready to publish, use `finalize-review`.
