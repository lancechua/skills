# grocery-pantry-manager

A skill for managing a grocery/shopping list and a linked pantry inventory. Handles fuzzy item matching between list and pantry ("tissue" added, "toilet paper" bought later still matches), tracks purchase/expiry dates, proactively flags expiring items, and nudges on staples that haven't been repurchased in a while.

## Contents

```
grocery-pantry-manager/
├── SKILL.md                       # the skill instructions
├── assets/
│   └── checklist_template.html    # starting point for the visual checklist artifact
└── evals/
    └── evals.json                 # test prompts + assertions for verifying the skill
```

## Requirements

None beyond basic file read/write and JSON parsing — no database engine, no external packages. Works with any harness that lets the agent read/write local files and set environment variables.

## Installing

1. Copy the `grocery-pantry-manager/` directory into wherever your harness looks for skills (e.g. a `skills/` directory it scans on startup — check your harness's docs for the exact path).
2. Optionally set `GROCERY_PANTRY_DIR` to choose where the data files live. If unset, the skill defaults to `~/.grocery-pantry`.

```bash
export GROCERY_PANTRY_DIR="$HOME/.grocery-pantry"   # optional, this is the default
```

3. No further setup — the skill creates `grocery-list.jsonl` and `pantry.jsonl` in that directory the first time it's used.

## Data files

Two plain JSONL files (one JSON object per line), created on first use:

- `$GROCERY_PANTRY_DIR/grocery-list.jsonl`
- `$GROCERY_PANTRY_DIR/pantry.jsonl`

They're plain text and portable — back them up, sync them, or inspect them with `cat`/`jq` like any other file. See `SKILL.md` for the exact schema.

## Testing

`evals/evals.json` has 5 test prompts with expected behavior and assertions, covering: adding items, fuzzy-matched removal into the pantry, correcting an existing pantry record without duplicating it, proactive expiry surfacing, and low-stock nudging. Run these against your harness with the skill installed to sanity-check behavior after any edits.
