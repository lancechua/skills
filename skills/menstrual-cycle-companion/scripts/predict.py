"""
Cycle prediction.

Method (see references/clinical-basis.md for the research this is based on):

1. Cycle length is predicted from the cycler's OWN recent history, not a
   population average. We take the last up to 6 logged cycle lengths and use
   the median (robust to one unusually long/short cycle) as the point
   estimate, and the median absolute deviation (MAD) as the uncertainty band.
2. Ovulation is estimated by counting backward from the predicted next
   period using the luteal phase length, NOT forward from day 1. This is
   because research consistently finds the luteal phase is more consistent
   within an individual than the follicular phase, which is where most of the
   cycle-to-cycle variability lives. Luteal length defaults to 14 days but
   should be overridden per-profile if the person has cycle tracking data
   (BBT/LH strips) suggesting a different personal average — luteal phases
   of 10-16 days are all within normal range and the "fixed at 14" figure is
   a simplification, not a hard biological constant.
3. The fertile window is ovulation-day minus 5 to ovulation-day plus 1,
   reflecting sperm survival (~5 days) and egg viability (~24h) — standard
   clinical guidance (e.g. ACOG, Mayo Clinic patient materials).
4. Everything is returned as a RANGE, and the module refuses to call itself
   contraception-grade. Calendar-based fertile window estimates carry real
   error, especially for irregular cyclers — this should be communicated to
   the user every time a fertile window is surfaced.

If fewer than 2 period_starts are logged, prediction falls back to the
profile's bootstrap values (asked once, up front) and returns a
lower-confidence estimate anchored on the single most recent start date.
"""

import statistics
from datetime import date, timedelta

import db

DEFAULT_LUTEAL_LENGTH = 14
MIN_PLAUSIBLE_CYCLE = 15
MAX_PLAUSIBLE_CYCLE = 90
LOOKBACK_CYCLES = 6


def _parse(d):
    return date.fromisoformat(d)


def _cycle_lengths(starts):
    """starts: list of ISO date strings, ascending. Returns plausible gaps."""
    lengths = []
    for prev, cur in zip(starts, starts[1:]):  # noqa
        gap = (_parse(cur) - _parse(prev)).days
        if MIN_PLAUSIBLE_CYCLE <= gap <= MAX_PLAUSIBLE_CYCLE:
            lengths.append(gap)
        # else: likely a data entry error or a genuinely irregular/missed
        # cycle worth flagging to the user rather than silently averaging in
    return lengths


def predict(profile_name):
    profile = db.get_profile(profile_name)
    if not profile:
        raise ValueError(f"No profile named {profile_name!r}")

    starts = [p["start_date"] for p in db.get_period_starts(profile_name)]
    luteal_length = profile.get("bootstrap_luteal_length") or DEFAULT_LUTEAL_LENGTH

    if len(starts) >= 2:
        recent = starts[-(LOOKBACK_CYCLES + 1) :]
        lengths = _cycle_lengths(recent)
        if not lengths:
            return _bootstrap_predict(
                profile,
                starts[-1],
                note=(
                    "Recent gaps between logged periods were outside the "
                    "plausible 15-90 day range, so recent history couldn't be "
                    "used. Falling back to bootstrap estimates."
                ),
            )
        predicted_length = round(statistics.median(lengths))
        if len(lengths) >= 2:
            spread = round(
                statistics.median([abs(l - predicted_length) for l in lengths])
            )
        else:
            spread = 3  # single data point: keep a conservative band
        spread = max(2, spread)
        confidence = "high" if len(lengths) >= 4 else "moderate"
        last_start = starts[-1]
        source = f"last {len(lengths)} logged cycle(s)"
    else:
        return _bootstrap_predict(profile, starts[-1] if starts else None)

    return _build_result(
        last_start, predicted_length, spread, luteal_length, confidence, source
    )


def _bootstrap_predict(profile, last_start, note=None):
    cycle_length = profile.get("bootstrap_cycle_length")
    luteal_length = profile.get("bootstrap_luteal_length") or DEFAULT_LUTEAL_LENGTH
    if not cycle_length or not last_start:
        return {
            "status": "needs_bootstrap",
            "message": (
                "Not enough data to predict yet. Log at least one period "
                "start date, and ideally also record typical cycle length "
                "and period length so we can estimate before two full "
                "cycles have been logged."
            ),
        }
    result = _build_result(
        last_start,
        cycle_length,
        spread=4,
        luteal_length=luteal_length,
        confidence="low (bootstrap estimate, not yet based on logged history)",
        source="bootstrap values",
    )
    if note:
        result["note"] = note
    return result


def _build_result(
    last_start, predicted_length, spread, luteal_length, confidence, source
):
    last = _parse(last_start)
    next_period = last + timedelta(days=predicted_length)
    ovulation = next_period - timedelta(days=luteal_length)
    fertile_start = ovulation - timedelta(days=5)
    fertile_end = ovulation + timedelta(days=1)

    return {
        "status": "ok",
        "last_period_start": last_start,
        "predicted_cycle_length_days": predicted_length,
        "uncertainty_days": spread,
        "confidence": confidence,
        "based_on": source,
        "next_period": {
            "estimate": next_period.isoformat(),
            "range": [
                (next_period - timedelta(days=spread)).isoformat(),
                (next_period + timedelta(days=spread)).isoformat(),
            ],
        },
        "estimated_ovulation": ovulation.isoformat(),
        "fertile_window": {
            "start": fertile_start.isoformat(),
            "end": fertile_end.isoformat(),
            "caveat": (
                "Calendar-based fertile window estimates carry real "
                "uncertainty, more so with irregular cycles. Not a "
                "contraceptive method on its own."
            ),
        },
        "luteal_length_assumed_days": luteal_length,
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 2:
        print("Usage: python predict.py <profile_name>")
        sys.exit(1)
    print(json.dumps(predict(sys.argv[1]), indent=2))
