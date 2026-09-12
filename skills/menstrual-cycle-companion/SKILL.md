---
name: menstrual-cycle-companion
description: Menstrual cycle tracking, prediction, and advice for a household — logging period/symptom data to a local SQLite database, predicting next period/ovulation/fertile window from personal history (or bootstrap values if no history yet), giving research-grounded self-care advice, and sending proactive notifications ahead of a predicted period or fertile window. Use this whenever the user wants to log a period, symptoms, flow, or pain; asks when their next period or fertile window will be; asks for advice on cramps, PMS, or cycle-related discomfort; wants to set up cycle reminders/notifications; or is a supporting partner asking how to help or what's coming up. Supports multiple linked profiles (e.g. one cycling person and one supporting partner) in the same household.
---

# Menstrual Cycle Companion

Tracks menstrual cycle data for one or more people, predicts upcoming
periods/fertile windows from their own history, gives grounded self-care
advice, and can proactively notify people ahead of a predicted period or
fertile window.

**This skill is not a medical device or a doctor.** Always frame advice and
predictions as general information, not a diagnosis or guaranteed forecast,
and read `references/clinical-basis.md` before giving substantive advice —
it has the research grounding (why predictions work the way they do, and
what's actually evidence-supported for pain/PMS) so advice isn't improvised.

## Setup (first time only)

You (the AI assistant) run the one-time setup on the user's behalf — the
user does **not** need to know about the Python CLI. In conversation, just
do:

```bash
cd scripts
python3 cli.py init
```

This creates a SQLite database and a `config.json` for notifications at
`$MCC_DATA_DIR` (defaults to `~/.menstrual-cycle-companion/`). Set
`MCC_DATA_DIR` as an env var if the user wants the data stored elsewhere.

Then create a profile per person. This household has two roles:
- `cycler` — logs periods/symptoms, gets predictions
- `partner` — doesn't log cycle data, but can be linked to a cycler
  profile to receive supportively-worded notifications and ask "what's
  coming up" / "how can I help" on their behalf

```bash
python3 cli.py add-profile <name> cycler
python3 cli.py add-profile <name> partner
python3 cli.py link <partner_name> <cycler_name>
```

If this is a brand-new user with no logged history yet, **bootstrap
before the first real prediction is needed**: ask for typical cycle length
(days between period starts) and typical period length, and — only if they
happen to know it from prior tracking (BBT/LH strips) — their typical luteal
phase length. Don't ask for luteal length as a default question; most
people don't track it and 14 days is a reasonable default.

```bash
python3 cli.py add-profile <name> cycler --cycle-length 28 --period-length 5
# or update later:
python3 cli.py bootstrap <name> --cycle-length 28 --luteal-length 12
```

> **Important:** You are the user's interface. They express requests in
> natural language ("my period started today," "when's my next period?",
> "set up notifications for me"). You translate those into the appropriate
> `cli.py` calls behind the scenes. **Do not expose the CLI to the user**
> unless they explicitly ask for the raw commands or want to run something
> manually in a terminal.

## Available scripts

All Python scripts in the `scripts/` directory are required for the skill to function:
- `scripts/cli.py` — Main command-line interface for all operations (you call this on the user's behalf)
- `scripts/db.py` — Database schema and data access layer
- `scripts/predict.py` — Prediction algorithms for periods, ovulation, and fertile windows
- `scripts/check_due_notifications.py` — Checks for notifications due today
- `scripts/notify.py` — Sends notifications via configured methods
- `scripts/mark_notified.py` — Marks notifications as sent to prevent duplicates

These scripts are safe to import from each other and can be used to build custom
workflows beyond the CLI commands exposed above.

## You are the natural-language interface

The user talks to **you**, not the CLI. Examples:

| User says… | You do… |
|------------|---------|
| "My period started today" | `python3 cli.py log-period <name> --date today` |
| "Log today: cramps 7/10, headache, mood irritable" | `python3 cli.py log-daily <name> --pain 7 --symptoms cramps,headache --mood irritable` |
| "When's my next period?" | `python3 cli.py predict <name>` and relay the estimate/range |
| "What's coming up for my partner?" | `python3 cli.py predict <cycler_name>` and frame for partner |
| "Set up daily notifications" | Help them configure `config.json` and a cron job |
| "Run the daily check now" | `python3 check_due_notifications.py`, compose messages, `notify.send()`, `mark_notified.py` |

**Never make the user type `cli.py` commands.** They are implementation detail.

## Logging data

```bash
python3 cli.py log-period <name> --date 2026-08-01 --notes "optional"
python3 cli.py log-daily <name> --date 2026-08-01 --flow medium --pain 6 \
    --symptoms cramps,headache,bloating --mood irritable --notes "optional"
```

`--date` defaults to today if omitted. Re-logging the same date updates
that entry rather than duplicating it. When the user casually mentions
something in conversation ("ugh, cramps are bad today", "period started
this morning"), log it — don't make them phrase it as a formal command.

Symptom tags are free text (comma-separated) — don't force a fixed
vocabulary, just keep tags reasonably consistent for the same person over
time so patterns are easy to spot later (e.g. always `headache` not
sometimes `head pain`).

## Predicting

```bash
python3 cli.py predict <name>
```

Returns JSON with the predicted next period (as an estimate **and** a
range), estimated ovulation, fertile window, and a confidence level. Always
relay predictions as ranges/estimates in conversation, not as a single
certain date — see `references/clinical-basis.md` for why. If `status` is
`needs_bootstrap`, ask the missing bootstrap questions rather than guessing.

For a fuller picture (e.g. the user asks "how have my last few periods
been?" or wants to spot patterns), use `history`:

```bash
python3 cli.py history <name> --limit 30
```

This is a good moment to actually analyze the data yourself — look for
things like symptoms clustering in the days before a period, whether pain
is trending up or down over recent cycles, or unusually short/long gaps
worth mentioning. That kind of pattern-spotting across logged history is
something you're well suited to do that a static app isn't — use it.

## Giving advice

Read `references/clinical-basis.md` before answering substantive questions
about pain, PMS, or symptom management — it has what's actually
evidence-supported (NSAIDs, heat, exercise, magnesium, when combining
approaches helps) versus weaker or unsupported claims, plus the "see a
doctor" flags. Ground advice in there rather than general knowledge, and
always:

- Note you're not a doctor and this isn't a diagnosis
- Tailor advice using what's actually logged for that person (e.g. if pain
  is logged at 8/10 every cycle and NSAIDs are mentioned as not helping,
  that's a "consider seeing a doctor" moment, not just another tip)
- For the `partner` role, frame advice around practical support (see the
  "Supporting a partner" section in the reference doc) rather than
  explaining their symptoms to them

## Proactive notifications

Notifications are two-step by design: a deterministic script checks
what's due (so nothing gets double-sent), and you (the assistant) write and
send the actual message (so it can be genuinely useful and personalized
rather than a canned string).

> **For you (the AI assistant), not the user:** These commands run behind the
> scenes when the user asks you to check for notifications. The user never sees
> them — they just say something like \"run the daily check.\"

```bash
python3 check_due_notifications.py
```

Returns a JSON list of events due for a notification today (period or
fertile window starting within 2 days, not already sent). For each event
in the list:

1. Write a short, warm message. For the `cycler` profile: mention the
   predicted date range and 1-2 concrete, grounded self-care suggestions
   (e.g. "worth having ibuprofen and a heating pad on hand"). For any
   `linked_partners` on the event, write a *different*, supportively-framed
   message (see the reference doc) — don't just forward the same text.
2. Send it:
   ```bash
   python3 -c "import notify; notify.send('<profile_name>', '<message>', title='<short title>')\""
   ```
3. Mark it sent so it isn't repeated tomorrow:
   ```bash
   python3 mark_notified.py <profile_name> <event_type> <cycle_anchor_date>
   ```

**Setting this up to actually run daily** depends on the environment:

- If running where you (the assistant) can be invoked on a schedule (e.g. a
  cron job or runner that executes an agent CLI prompt like
  `<agent-cli> -p "run the menstrual cycle companion daily check"`), help
  set that scheduled entry up for the user and confirm the exact command
  your host environment expects — don't assume, ask if unsure.
- Notification *delivery* itself is host-specific and configured in
  `config.json` (created by `cli.py init`) — see the docstring in
  `notify.py` for the supported methods (shell command, webhook, or a
  stdout fallback). Help the user fill this in with whatever their machine
  actually supports (e.g. `notify-send`, a `curl` to a personal ntfy.sh
  topic, a webhook into a messaging app) rather than guessing a method that
  might not be installed.

## Data model notes

SQLite database with `profiles`, `period_starts`, `daily_logs`, and
`notification_log` tables — see `scripts/db.py` for the schema. Prediction
math lives in `scripts/predict.py` (read its module docstring — it explains
the method, not just the mechanics). All scripts are safe to import from
each other (`db`, `predict`, `notify`) if you need to compose custom
one-off queries beyond what `cli.py` exposes, e.g. for a bespoke question
the user asks that doesn't map cleanly to an existing subcommand.
