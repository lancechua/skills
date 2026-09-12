#!/usr/bin/env python3
"""
Command-line interface for the menstrual cycle companion.
Run `python cli.py <command> --help` for details on any command.
"""

import argparse
import json
import sys
from datetime import datetime

import db
import predict as predict_mod


def cmd_init(args):
    db.init_db()
    import notify

    notify.write_default_config_if_missing()
    print(f"Initialized database at {db.get_db_path()}")
    print(
        f"Notification config at {notify.get_config_path()} (edit this to wire up real notifications)"
    )


def cmd_add_profile(args):
    pid = db.add_profile(
        args.name,
        args.role,
        bootstrap_cycle_length=args.cycle_length,
        bootstrap_period_length=args.period_length,
        bootstrap_luteal_length=args.luteal_length,
    )
    print(f"Added profile {args.name!r} (role={args.role}, id={pid})")


def cmd_link(args):
    profile = db.get_profile(args.partner_name)
    linked = db.get_profile(args.cycler_name)
    if not profile or not linked:
        print("Both profiles must exist first.")
        sys.exit(1)
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE profiles SET linked_profile_id = ? WHERE id = ?",
            (linked["id"], profile["id"]),
        )
    print(
        f"Linked {args.partner_name} as supporting partner of {args.cycler_name}"
    )


def cmd_bootstrap(args):
    db.update_bootstrap(
        args.name,
        cycle_length=args.cycle_length,
        period_length=args.period_length,
        luteal_length=args.luteal_length,
    )
    print(f"Updated bootstrap values for {args.name!r}")


def cmd_log_period(args):
    d = args.date or datetime.now().date().isoformat()  # noqa: DTZ005
    db.log_period_start(args.name, d, notes=args.notes)
    print(f"Logged period start for {args.name} on {d}")


def cmd_log_daily(args):
    d = args.date or datetime.now().date().isoformat()  # noqa: DTZ005
    db.log_daily(
        args.name,
        d,
        flow=args.flow,
        pain=args.pain,
        symptoms=args.symptoms,
        mood=args.mood,
        notes=args.notes,
    )
    print(f"Logged daily entry for {args.name} on {d}")


def cmd_predict(args):
    result = predict_mod.predict(args.name)
    print(json.dumps(result, indent=2))


def cmd_history(args):
    starts = db.get_period_starts(args.name, limit=args.limit)
    daily = db.get_daily_logs(args.name, limit=args.limit)
    out = {
        "profile": args.name,
        "recent_period_starts": starts,
        "recent_daily_logs": daily,
    }
    print(json.dumps(out, indent=2))


def cmd_profiles(args):
    profiles = db.list_profiles()
    if not profiles:
        print("No profiles found. Run `cli.py add-profile` to create one.")
        return
    for p in profiles:
        extra = []
        if p["bootstrap_cycle_length"]:
            extra.append(f"cycle={p['bootstrap_cycle_length']}d")
        if p["bootstrap_period_length"]:
            extra.append(f"period={p['bootstrap_period_length']}d")
        if p["linked_profile_id"]:
            extra.append(f"linked_to_id={p['linked_profile_id']}")
        extra_str = f" ({', '.join(extra)})" if extra else ""
        print(f"- {p['name']} [role={p['role']}]{extra_str}")


def main():
    parser = argparse.ArgumentParser(
        description="Menstrual cycle companion CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Initialize the database and config")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("add-profile", help="Create a new profile")
    p.add_argument("name")
    p.add_argument("role", choices=["cycler", "partner"])
    p.add_argument(
        "--cycle-length",
        type=int,
        help="Typical cycle length in days (bootstrap)",
    )
    p.add_argument(
        "--period-length",
        type=int,
        help="Typical period length in days (bootstrap)",
    )
    p.add_argument(
        "--luteal-length",
        type=int,
        help="Typical luteal phase length in days (bootstrap, default 14)",
    )
    p.set_defaults(func=cmd_add_profile)

    p = sub.add_parser(
        "link", help="Link a partner profile to a cycler profile"
    )
    p.add_argument("partner_name")
    p.add_argument("cycler_name")
    p.set_defaults(func=cmd_link)

    p = sub.add_parser(
        "bootstrap", help="Update a profile's bootstrap estimates"
    )
    p.add_argument("name")
    p.add_argument("--cycle-length", type=int)
    p.add_argument("--period-length", type=int)
    p.add_argument("--luteal-length", type=int)
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("log-period", help="Log that a period started")
    p.add_argument("name", help="Profile name")
    p.add_argument("--date", help="ISO date YYYY-MM-DD (defaults to today)")
    p.add_argument("--notes", help="Optional free-form notes")
    p.set_defaults(func=cmd_log_period)

    p = sub.add_parser("log-daily", help="Log a day's symptoms/flow/pain")
    p.add_argument("name", help="Profile name")
    p.add_argument("--date", help="ISO date YYYY-MM-DD (defaults to today)")
    p.add_argument(
        "--flow", choices=["none", "spotting", "light", "medium", "heavy"]
    )
    p.add_argument(
        "--pain", type=int, help="Pain scale 0-10 (0=none, 10=worst)"
    )
    p.add_argument(
        "--symptoms", help="Comma-separated tags: cramps,headache,bloating,etc."
    )
    p.add_argument("--mood", help="Free text mood note")
    p.add_argument("--notes", help="Optional free text notes")
    p.set_defaults(func=cmd_log_daily)

    p = sub.add_parser(
        "predict", help="Predict next period, ovulation, fertile window"
    )
    p.add_argument("name", help="Profile name")
    p.set_defaults(func=cmd_predict)

    p = sub.add_parser("history", help="Show logged history for a profile")
    p.add_argument("name", help="Profile name")
    p.add_argument(
        "--limit", type=int, default=30, help="Max entries to return"
    )
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("profiles", help="List all profiles")
    p.set_defaults(func=cmd_profiles)

    args = parser.parse_args()
    try:
        args.func(args)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
