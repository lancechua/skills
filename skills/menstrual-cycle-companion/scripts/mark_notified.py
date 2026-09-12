"""Mark a cycle event as notified so it won't be sent again.
Usage: python mark_notified.py <profile_name> <event_type> <cycle_anchor_date>
"""

import sys

import db

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Usage: python mark_notified.py <profile_name> <event_type> <cycle_anchor_date>"
        )
        sys.exit(1)
    profile_name, event_type, anchor_date = sys.argv[1:4]
    profile = db.get_profile(profile_name)
    if not profile:
        print(f"No profile named {profile_name!r}")
        sys.exit(1)
    db.record_notification(profile["id"], event_type, anchor_date)
    print(f"Marked {event_type} for {profile_name} on {anchor_date} as notified.")
