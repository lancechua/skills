# Menstrual Cycle Companion

An AI assistant skill and CLI tool for tracking menstrual cycles, predicting periods and fertile windows, managing period-related discomfort with research-grounded advice, and sending proactive notifications to you (and a supporting partner, if applicable).

Data is stored locally in a SQLite database — nothing leaves your machine.

## What it does

**Log data**: Period starts, daily symptoms (flow, pain, mood), and free-form notes.

**Predict**: Based on your own cycle history, estimates when your next period will arrive, when ovulation is likely, and the fertile window — with ranges and confidence levels, never false certainty.

**Advise**: Gives you research-grounded guidance on managing dysmenorrhea (period pain), PMS symptoms, and cycle-related patterns. Tailors advice to what you've actually logged.

**Notify**: Sends you (and optionally a supporting partner) a heads-up a few days before your period or fertile window, with practical suggestions.

## Installation

This skill follows the standard Agent Skills format (`SKILL.md`), making it compatible with any AI assistant or coding agent that supports skills (such as Claude Code, Antigravity, Gemini CLI, Cursor, or OpenHands), as well as standalone CLI usage.

### Option 1: As an Agent Skill

Copy or symlink the skill directory into your agent's skills location:

```bash
# Global skills directory (e.g. ~/.agents/skills or ~/.claude/skills)
mkdir -p ~/.agents/skills
cp -r menstrual-cycle-companion ~/.agents/skills/

# Or project-level skills directory
mkdir -p .agents/skills
cp -r menstrual-cycle-companion .agents/skills/
```

*(If using Claude Code specifically, you can also place it in `~/.claude/skills/menstrual-cycle-companion`.)*

Once installed, restart your agent session or reload skills.

### Option 2: Standalone CLI / Local Clone

The core functionality requires only Python 3.9+ with standard library modules (no third-party pip dependencies required):

```bash
git clone https://github.com/YOUR_USERNAME/menstrual-cycle-companion.git
cd menstrual-cycle-companion
```

## One-time setup

Ask your AI assistant in conversation:

```
set up the menstrual cycle companion
```

Or run this manually in the skill's `scripts/` directory:

```bash
python3 cli.py init

# Syntax: python3 cli.py add-profile <name> <role: cycler|partner>
# Example: Alex tracks their cycle; Sam is a supporting partner
python3 cli.py add-profile alex cycler
python3 cli.py add-profile sam partner
python3 cli.py link sam alex
```

This creates:
- `~/.menstrual-cycle-companion/data.db` — SQLite database for all your logs
- `~/.menstrual-cycle-companion/config.json` — notification settings (see below)

If you want data stored elsewhere, set the environment variable:

```bash
export MCC_DATA_DIR=/path/to/your/data
```

### Bootstrap values (optional but helpful for early predictions)

If this is a first cycle with no history yet, tell your assistant your typical cycle length and period length so predictions don't wait for two full cycles:

```
update my profile with a typical cycle length of 28 days and period length of 5 days
```

Or manually:

```bash
python3 cli.py add-profile alex cycler --cycle-length 28 --period-length 5
```

## Usage

### Logging

**Log that a period started:**
```
my period started today
```

**Log a day's symptoms:**
```
log today: flow is medium, cramps are a 7/10, headache, mood is irritable
```

**See your history:**
```
show me my last 30 days of logs
```

Behind the scenes, the assistant runs the skill's CLI commands. You can also run them directly from a terminal:

```bash
python3 scripts/cli.py log-period alex --date 2026-09-13
python3 scripts/cli.py log-daily alex --date 2026-09-13 --flow medium --pain 7 --symptoms cramps,headache
python3 scripts/cli.py history alex --limit 30
```

### Predictions

**Ask when your next period is:**
```
when will my next period start?
```

The assistant returns:
- An estimate + range (e.g., "around Sept 24, likely Sept 22–26")
- Estimated ovulation date
- Fertile window (with a note that it's a calendar estimate, not a verified method)
- Confidence level

The prediction uses your own logged history once you have 2+ cycle starts. Until then, it bootstraps from the cycle length you provided during setup.

### Advice

**Ask for period pain management:**
```
my period pain is really bad this month, what can I do?
```

The assistant gives evidence-based suggestions tailored to your logged data. Advice draws from:
- NSAIDs (first-line, most research support)
- Heat therapy (strong evidence, zero risk)
- Exercise (works as a preventive habit)
- Magnesium (modest effect, works best with other approaches)
- When to see a doctor (unusually severe, not responding to NSAIDs, etc.)

See `references/clinical-basis.md` in the skill for the full research grounding.

### Notifications

Set up proactive heads-ups for upcoming periods and fertile windows. This requires two things:

**1. Configure your notification method** in `~/.menstrual-cycle-companion/config.json`:

```json
{
  "profiles": {
    "alex": {
      "method": "shell",
      "command": "notify-send \"Period Alert\" \"{message}\""
    },
    "sam": {
      "method": "webhook",
      "url": "https://ntfy.sh/your-private-topic"
    }
  }
}
```

**Supported methods:**

- **`shell`**: Runs a command on your machine. Examples:
  - Linux with `notify-send`: `"notify-send \"Cycle\" \"{message}\""`
  - macOS with `terminal-notifier`: `"terminal-notifier -title Cycle -message '{message}'"`
  - Slack webhook (curl): `"curl -X POST -H 'Content-type: application/json' --data '{\"text\":\"{message}\"}' https://hooks.slack.com/..."`
  - ntfy.sh push: `"curl -d '{message}' https://ntfy.sh/your-topic"`

- **`webhook`**: POSTs `{"message": "...", "title": "..."}` as JSON to a URL. Good for:
  - [ntfy.sh](https://ntfy.sh) (free, privacy-friendly push notifications)
  - Home Assistant
  - Telegram bot bridges
  - Any custom webhook

- **`stdout`** (default): Just prints to the terminal. Works out of the box.

**2. Set up a daily check** via cron (or your system's task scheduler):

**Option A: Automated Python script (standalone, no LLM required)**
```bash
# Run daily at 8 AM
0 8 * * * cd /path/to/skill && PYTHONPATH=scripts python3 -c "
import check_due_notifications, notify
for event in check_due_notifications.due_events():
    msg = f\"{event['profile_name']}: period predicted {event['prediction']['next_period']['estimate']}\"
    notify.send(event['profile_name'], msg)
    import mark_notified
    mark_notified.db.record_notification(event['profile_id'], event['event_type'], event['cycle_anchor_date'])
"
```

**Option B: Automated via AI agent runner (for contextual, LLM-authored messages)**
If your AI CLI supports non-interactive execution (e.g. `claude -p`, `gemini -p`, etc.):

```bash
0 8 * * * <agent-cli> -p "run the menstrual cycle companion daily check" 2>&1 >> ~/.menstrual-cycle-companion/notifications.log
```

This invokes the assistant daily, which loads the skill and checks for due notifications. The assistant writes warm, contextual messages (with differentiated wording for partners) and sends them via your configured method.

## How predictions work

**The math:** Predictions count backward from the next expected period using the luteal phase length, not forward from day 1. This is because research consistently shows the luteal phase (after ovulation) is more stable within an individual than the follicular phase (before ovulation), which is where most cycle-to-cycle variation lives.

**Why a range, not a single date:** Even "regular" cycles vary by a few days cycle to cycle. Showing a range ("around the 24th, could be 22–26") is honest about that uncertainty.

**Confidence:** With fewer than 2 logged cycles, confidence is "low (bootstrap)" — based on what you provided during setup. With 2+ cycles logged, confidence improves as your actual history builds.

**Fertile window:** The standard clinical estimate is ovulation-day minus 5 through ovulation-day plus 1, accounting for sperm viability (~5 days) and egg viability (~24 hours). This is a calendar estimate with real uncertainty, especially for irregular cyclers — never rely on it as a contraceptive method on its own.

For technical details, see `scripts/predict.py` and `references/clinical-basis.md`.

## For a supporting partner

If you're supporting a cycling partner, create a `partner` profile and link it to theirs:

```
set up a partner profile for sam linked to alex
```

You'll get differently-worded notifications focused on what you can *do* (have pain relief on hand, take something off their plate) rather than what they are experiencing. You can ask your assistant:

```
what's coming up for alex? how can I help?
```

And the assistant will give you a heads-up and practical suggestions.

## Privacy & data storage

- **Data stays local**: Everything lives in `~/.menstrual-cycle-companion/data.db`, a SQLite file only readable by you
- **No cloud sync**: The skill does not upload your logs to any cloud service. Your data stays on your machine
- **No telemetry**: The skill does not track what you log
- **Notifications**: Whatever delivery method you configure (shell command, webhook, etc.) is your choice — you're in control of where notification content goes

## Testing

The project includes an automated test suite with 100% standard library Python (`unittest`):

- `tests/test_db.py`: Database initialization, schema constraints, profile management, period and symptom logging, and notification logs.
- `tests/test_predict.py`: Cycle length calculation, bootstrap fallback, ovulation date estimation, and fertile window calculation.
- `tests/test_notifications.py`: Lookahead event evaluation, deduplication, and notification delivery methods (stdout, shell, webhook).
- `tests/test_cli.py`: End-to-end command-line interface execution.

### Running all tests

From the skill's root directory:

```bash
python3 -m unittest discover -s tests -v
```

Or from the repository root:

```bash
python3 -m unittest discover -s skills/menstrual-cycle-companion/tests -v
```

### Running individual test files

```bash
python3 -m unittest skills/menstrual-cycle-companion/tests/test_db.py
python3 -m unittest skills/menstrual-cycle-companion/tests/test_predict.py
python3 -m unittest skills/menstrual-cycle-companion/tests/test_notifications.py
python3 -m unittest skills/menstrual-cycle-companion/tests/test_cli.py
```

*Note: Tests automatically use isolated temporary directories for `MCC_DATA_DIR`, so your personal data in `~/.menstrual-cycle-companion` is never touched.*

## Contributing

Found a bug? Want to improve the prediction logic, add new advice, or tweak the clinical grounding?

- Check `references/clinical-basis.md` if your change involves health advice — it documents what's evidence-supported
- Test your changes by running the automated tests or prompting your AI agent to test scenarios
- Submit a pull request with a description of what you changed and why

## License

MIT. Use, modify, distribute freely. See `LICENSE` for details.

## Questions?

- **How do I interpret my predictions?** See the "How predictions work" section above, or read `scripts/predict.py`
- **Is this a medical device?** No. It's a logging and prediction tool grounded in research, but it doesn't diagnose or treat anything. Always see a doctor for unusually severe pain, irregular cycles, or any concern
- **Can I use this for contraception?** The fertile window prediction is a calendar estimate with known limitations — not reliable on its own. Pair it with other methods if pregnancy prevention is critical
- **Why does the assistant suggest seeing a doctor sometimes?** See the "When to suggest seeing a doctor" section in `references/clinical-basis.md` — certain patterns warrant professional evaluation

## Acknowledgments

Built for AI assistants and autonomous agents following the open Agent Skills standard. Clinical grounding draws from recent research, including:
- Henry et al. (2024), *Human Reproduction*: within-individual cycle variability
- Yuan et al. (2026), *Frontiers in Medicine*: heat therapy for dysmenorrhea
- Tsai et al. (2024), *Sports Medicine Open*: exercise for dysmenorrhea
- Natural Cycles dataset (600k+ cycles): real-world cycle characteristics

See `references/clinical-basis.md` for full citations.
