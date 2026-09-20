---
name: grocery-pantry-manager
description: Manage a persistent grocery/shopping list and a linked pantry inventory. Handles adding and removing items even when the wording doesn't match (e.g. "tissue" was added, but the user later says "picked up the toilet paper" — match these as the same item), logs purchase dates and expiry notes for pantry items, proactively flags items about to expire, and checks in when a staple hasn't been repurchased in a while. Use this skill whenever the user mentions a grocery list, shopping list, pantry, fridge/freezer stock, running low on something, "add X to my list", "we're out of X", "I picked up X today", or asks what's expiring soon — even if they don't use the words "grocery list" or "pantry" explicitly.
---

# Grocery & Pantry Manager

Keeps a shopping list and a pantry inventory in sync as the user adds items, buys them, and eventually uses them up — plus a visual checklist the user can glance at.

## Where the data actually lives

Two plain JSONL files (one JSON object per line) on the local filesystem are this skill's database:

- `<GROCERY_PANTRY_DIR>/grocery-list.jsonl` — the shopping list
- `<GROCERY_PANTRY_DIR>/pantry.jsonl` — the pantry inventory

**Configuring the path:** read the `GROCERY_PANTRY_DIR` environment variable. If it's unset, default to `~/.grocery-pantry`. Create the directory (`mkdir -p`) if it doesn't exist before the first read/write of a session. Always resolve this at the start of a turn that touches groceries or pantry — don't cache/hardcode a path across turns, since the user or harness may have changed the environment variable between sessions.

This is deliberately plain files + JSONL rather than a database engine, so the skill works unmodified across different agent harnesses (Claude, Hermes, pi, etc.) with nothing beyond basic file read/write — no SQLite binary, no client library, no schema migration.

Read both files fresh at the start of any turn that touches groceries or pantry — state may have changed since you last looked (another session, another process, manual edits).

### grocery-list.jsonl format

```
{"item": "tissue", "added": "2026-09-10"}
{"item": "eggs", "added": "2026-09-12"}
```

### pantry.jsonl format

```
{"item": "eggs", "bought": "2026-09-05", "quantity": 12, "unit": "eggs", "expires": "2026-09-26", "runs_out": "2026-09-17", "consumption_rate": 1, "notes": "fridge; runs_out and consumption_rate are estimates; rate is eggs/day"}
{"item": "bread", "bought": "2026-09-10", "quantity": 1, "unit": "loaf", "expires": "2026-09-13", "runs_out": "2026-09-15", "consumption_rate": 0.2, "notes": "fridge, day-old when bought; runs_out and consumption_rate are estimates; rate is loaves/day"}
```

Keep one JSON object per line, no trailing commas, no multi-line objects. `quantity` is the amount bought, and `unit` makes that amount interpretable. `expires` is the estimated quality/safety date; `runs_out` is the estimated date the household will consume the recorded quantity. They are different dates and either may be `"unknown"`. `consumption_rate` means the estimated number of `unit`s consumed per day, independent of the recorded quantity. For example, `consumption_rate: 1` with `quantity: 10` and `unit: "eggs"` means the household consumes 1 egg per day, so the eggs should last 10 days. Household size is context held in agent memory or another system prompt, not a pantry field. Preserve unknown values rather than inventing false precision.

When `quantity` is unspecified, bootstrap it with a clearly labeled market/package assumption. Prefer the user's stated package size; otherwise use a common local package size (for example, 10 eggs per tray or 10 toilet-paper rolls per pack), and calibrate it to the user's country, region, retailer, or market when known. If location or market is unknown and package size materially affects the estimate, ask; otherwise use a conservative common-market guess and explicitly tell the user. Never present an assumed quantity as user-provided fact.

When creating or changing an estimate, explicitly tell the user what was assumed (including household size, quantity, storage, and whether a date is about spoilage or consumption), and invite corrections. Never present `expires` or `runs_out` as certain when they are estimates.

## Writing safely

There's no version-token/conflict detection on plain files, so every write follows a write-temp-then-rename pattern to avoid ever leaving a half-written or corrupted file behind:

1. Read the current file's lines (if it exists) into memory.
2. Apply the change (append a line / drop a line / replace a line).
3. Write the full new contents to a temp file in the same directory (e.g. `pantry.jsonl.tmp`).
4. Rename the temp file over the original (atomic on the same filesystem).

Do this for every mutation, including single-line appends — an append that's just "open in append mode and write one line" is fine too since it doesn't risk the rest of the file, but any edit that touches or removes an existing line should go through the full read-modify-write-temp-rename sequence.

## Matching items across list and pantry

The name someone uses when *adding* an item rarely matches the name they use when *removing* it — "tissue" goes on the list, "grabbed the toilet paper" is what closes it out. Match by what the item obviously refers to, not exact string equality. If more than one plausible match exists on the current list, ask which one rather than guessing.

## Core workflow

**Adding to the grocery list**
Append a JSON line to `grocery-list.jsonl` (e.g. `{"item": "milk", "added": "2026-09-13"}`). Don't ask for confirmation for a plain add request — just do it and say so briefly.

**Marking something bought (removing from the list)**
1. Find the matching JSON line in `grocery-list.jsonl` (fuzzy match, see above) and remove it (read-modify-write-temp-rename, see above).
2. Add or replace the corresponding pantry record with today's date as `bought`, recording `quantity` and `unit` when known. If an existing record for the same item is being purchased again, treat that purchase as evidence that the previous quantity ran out: calculate `consumption_rate = previous_quantity / elapsed_days_since_previous_bought`, then replace the active record rather than leaving duplicate current-stock lines.
3. Ask for quantity and unit when they materially affect the estimate. Otherwise bootstrap them from the user's stated package or a market-aware package-size assumption, explicitly label the assumption, and allow the user to correct it. Use household size from agent memory or system context when estimating usage; do not write it to pantry.jsonl.
4. Ask for or infer an `expires` date if the item is perishable (see below), and estimate `runs_out` from quantity and consumption rate. Use `"unknown"` if genuinely unclear; do not substitute a run-out estimate for a safety/quality expiry date.
5. Tell the user plainly that it's now tracked in the pantry, summarize the assumptions and estimates, and say they should tell you if it was not actually purchased so the record can be removed.

**Expiry dates**
For common perishables, a reasonable estimate is fine (milk ~1 week refrigerated, bread ~5-7 days at room temp / longer refrigerated, eggs ~3-4 weeks refrigerated, leafy greens ~1 week) — write the estimate in and say it's an estimate. For anything non-perishable or ambiguous, don't invent a date.

**Updating notes**
When the user gives context that changes how long something lasts ("the bread's in the fridge, so it'll keep longer"), corrects an item, changes household-size context, or changes usage, replace that pantry item's whole JSON line (read-modify-write-temp-rename) with updated `expires`, `runs_out`, `consumption_rate`, `quantity`, and/or `notes`. This is a correction to an existing record, not a new item — never leave a duplicate line behind. Tell the user about every assumption changed, including the household-size context used.

**Consumption and run-out estimates**
Use the recorded quantity, household size from agent memory or system context, typical use of the item, and any prior purchase interval to estimate `consumption_rate` and `runs_out`. `consumption_rate` is the number of `unit`s consumed per day. If a whole-quantity duration is known, calculate `consumption_rate = quantity / duration_days`. If the item's quantity is measured in packages, keep the rate in packages per day; do not mix units.

Calculate `runs_out` as `bought + (quantity / consumption_rate)` days. Round the run-out date to the nearest whole day and label it an estimate. When partial stock is reported, update `consumption_rate = quantity_consumed / elapsed_days` and calculate remaining days as `remaining_quantity / consumption_rate`; then set `runs_out = report_date + remaining_days`. For example, 10 eggs bought, 5 eggs remaining after 5 days means `consumption_rate = (10 - 5) / 5 = 1 egg/day` and `runs_out` is 5 days after the report date. If there is a prior observed rate, prefer it over a generic default; otherwise use typical use adjusted for the household size in context. The estimate should be a best guess, not a claim that the item is gone on that exact date.

When a staple's estimated `runs_out` date arrives or passes, ask whether the household has run out or is running low before adding it to the grocery list. If the user says they still have some, ask only what is needed to improve the estimate (rough quantity remaining, original quantity if unknown, household size, and whether usage has changed), then replace that pantry line with a revised `quantity`, `runs_out`, and `consumption_rate`. Explain what changed and why.

When a user reports that an item ran out earlier or later than estimated, update the active pantry line's `consumption_rate` and run-out estimate using that observation, preserve the expiry estimate separately, and explicitly state the revised assumption.

**Proactive expiry check**
Whenever you touch the pantry file for any reason, parse each line and check for items expiring within 3 days (or already past their date), and mention them — don't wait to be asked. Keep it brief: name the item(s) and how soon.

**Low-stock nudge**
If a staple item's `runs_out` date has arrived or passed, ask the user if they're running low and offer to add it back to the grocery list. For older records without `runs_out`, use the previous `bought`-date heuristic as a fallback and say that the estimate is being bootstrapped. Don't do this for items with no clear consumption pattern (specialty items, one-offs). A low-stock nudge must ask rather than assume the item is gone.

## The visual checklist

After any change to either file, render a simple HTML checklist artifact (grocery items as an unchecked list, pantry items grouped with expiry highlighted if within 3 days or overdue) and present it. See `assets/checklist_template.html` for a starting structure — regenerate it fresh from the current parsed JSONL contents each time rather than trying to incrementally patch a previous version.

Important honesty point for the user: this artifact is a **snapshot rendered from the JSONL files**, not a live database. If the user ticks a box or edits something inside the rendered artifact itself, that doesn't write back to `grocery-list.jsonl` / `pantry.jsonl` — tell them changes need to go through chat (or be confirmed back to you) to actually persist. This is a real constraint, not a design choice to work around silently: don't imply the artifact is self-syncing.
