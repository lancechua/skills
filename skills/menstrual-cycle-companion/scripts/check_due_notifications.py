"""
Returns which upcoming cycle events (across all cycler profiles) are
due for a notification today, and haven't already been sent.

This script is deliberately deterministic: it only does date arithmetic and
deduplication. Deciding WHAT to say (self-care tips, how a partner can
help) is the AI assistant's job when the skill is invoked — see SKILL.md. Keeping the
message-writing out of this script means the advice can draw on current
context (recent logged symptoms, severity, etc.) instead of a canned string.

Intended to be called by an AI assistant once a day, either interactively or because
a scheduled task/cron job runs an agent CLI (e.g. `claude -p`, `gemini -p`, etc.):
    0 8 * * * <agent-cli> "Run the menstrual cycle companion daily check"
which loads this skill and has the assistant run this script.

LOOKAHEAD_DAYS controls how many days before an event to start notifying.
"""

import json
from datetime import date, datetime

import db
import predict

LOOKAHEAD_DAYS = 2  # start notifying this many days before period/fertile window


def due_events():
    today = datetime.now().date()  # noqa
    events = []
    for profile in db.list_profiles():
        if profile["role"] != "cycler":
            continue
        result = predict.predict(profile["name"])
        if result.get("status") != "ok":
            continue

        next_period_date = date.fromisoformat(result["next_period"]["estimate"])
        days_until_period = (next_period_date - today).days
        if 0 <= days_until_period <= LOOKAHEAD_DAYS:
            anchor = result["next_period"]["estimate"]
            if not db.was_notified(profile["id"], "period_upcoming", anchor):
                events.append(
                    {
                        "profile_name": profile["name"],
                        "profile_id": profile["id"],
                        "event_type": "period_upcoming",
                        "cycle_anchor_date": anchor,
                        "days_until": days_until_period,
                        "prediction": result,
                    }
                )

        fertile_start = date.fromisoformat(result["fertile_window"]["start"])
        days_until_fertile = (fertile_start - today).days
        if 0 <= days_until_fertile <= LOOKAHEAD_DAYS:
            anchor = result["fertile_window"]["start"]
            if not db.was_notified(profile["id"], "fertile_window_upcoming", anchor):
                events.append(
                    {
                        "profile_name": profile["name"],
                        "profile_id": profile["id"],
                        "event_type": "fertile_window_upcoming",
                        "cycle_anchor_date": anchor,
                        "days_until": days_until_fertile,
                        "prediction": result,
                    }
                )

        # attach linked partner profiles so the assistant knows who else
        # might want a (differently-worded) heads up
        if events:
            linked = [
                p["name"]
                for p in db.list_profiles()
                if p.get("linked_profile_id") == profile["id"]
            ]
            for e in events:
                if e["profile_name"] == profile["name"]:
                    e["linked_partners"] = linked

    return events


if __name__ == "__main__":
    print(json.dumps(due_events(), indent=2))
