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
{"item": "eggs", "bought": "2026-09-05", "expires": "2026-09-26", "notes": "fridge"}
{"item": "bread", "bought": "2026-09-10", "expires": "2026-09-13", "notes": "fridge, day-old when bought"}
```

Keep one JSON object per line, no trailing commas, no multi-line objects. When you don't know an expiry date, use `"expires": "unknown"` rather than guessing — ask the user, or leave it and revisit once they mention it.

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
2. Append a corresponding JSON line to `pantry.jsonl` with today's date as `bought`.
3. Ask for or infer an `expires` date if the item is perishable (see below); use `"expires": "unknown"` if genuinely unclear.
4. Tell the user plainly that it's now tracked in the pantry, and that they should say so explicitly if they want it removed from there (e.g. they didn't actually end up buying it, or it was a mistake).

**Expiry dates**
For common perishables, a reasonable estimate is fine (milk ~1 week refrigerated, bread ~5-7 days at room temp / longer refrigerated, eggs ~3-4 weeks refrigerated, leafy greens ~1 week) — write the estimate in and say it's an estimate. For anything non-perishable or ambiguous, don't invent a date.

**Updating notes**
When the user gives context that changes how long something lasts ("the bread's in the fridge, so it'll keep longer") or corrects an item, replace that pantry item's whole JSON line (read-modify-write-temp-rename) with updated `expires`/`notes`. This is a correction to an existing record, not a new item — never leave a duplicate line behind.

**Proactive expiry check**
Whenever you touch the pantry file for any reason, parse each line and check for items expiring within 3 days (or already past their date), and mention them — don't wait to be asked. Keep it brief: name the item(s) and how soon.

**Low-stock nudge**
If a staple item's last `bought` date in `pantry.jsonl` is old enough that a typical household would plausibly have used it up (use judgment based on the item — e.g. milk after 3 weeks with no repurchase, not after 3 days), ask the user if they're running low and offer to add it back to the grocery list. Don't do this for items with no clear consumption pattern (specialty items, one-offs).

## The visual checklist

After any change to either file, render a simple HTML checklist artifact (grocery items as an unchecked list, pantry items grouped with expiry highlighted if within 3 days or overdue) and present it. See `assets/checklist_template.html` for a starting structure — regenerate it fresh from the current parsed JSONL contents each time rather than trying to incrementally patch a previous version.

Important honesty point for the user: this artifact is a **snapshot rendered from the JSONL files**, not a live database. If the user ticks a box or edits something inside the rendered artifact itself, that doesn't write back to `grocery-list.jsonl` / `pantry.jsonl` — tell them changes need to go through chat (or be confirmed back to you) to actually persist. This is a real constraint, not a design choice to work around silently: don't imply the artifact is self-syncing.
