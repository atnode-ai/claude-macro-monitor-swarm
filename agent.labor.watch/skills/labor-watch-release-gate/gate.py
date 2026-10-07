#!/usr/bin/env python3
"""
Labor Watch -- Release Gate
Deterministic release-calendar gate for the macro-monitoring swarm's Labor domain.

Given today's date (US Eastern) and, optionally, the last-logged release date per
report, it returns which labour reports could plausibly have a NEW release worth
checking today. On the ~80% of run-days when nothing is calendar-possible, it returns
an empty "due" list so the agent can write its heartbeat and STOP -- without fetching
any source or opening the browser (the expensive operations).

Reports & rules (all US Eastern; UK release is ET-converted):
  claims : Initial Jobless Claims (DOL ETA) -- weekly, every Thursday 08:30 ET.
  nfp    : Employment Situation / Non-Farm Payrolls (BLS) -- 1st Friday of month 08:30 ET.
  adp    : ADP National Employment Report -- Wednesday before NFP (~08:15 ET).
  jolts  : JOLTS (BLS) -- irregular, ~first ~12 days of month, 10:00 ET (date drifts).
  uk     : UK Labour Market (ONS) -- ~3rd Tuesday of month, 07:00 BST (~02:00-03:00 ET).

Philosophy: err toward "check" ONLY inside each report's plausible window, and use the
last-logged dates (the dedup baseline the agent reads off the blackboard) to suppress
re-checks once a print is logged. Days clearly outside every window return nothing-due.
NFP/claims/adp/uk have firm weekday anchors; JOLTS dates drift, so it uses a conservative
day-of-month window. ALWAYS pass --last so the second daily run dedups the first.

stdlib only (no pip install). Python 3.9+ (zoneinfo) with a manual US-Eastern fallback.

Usage:
  python3 gate.py
  python3 gate.py --today 2026-06-18
  python3 gate.py --last '{"claims":"2026-06-12","nfp":"2026-06-06","adp":"2026-06-04","jolts":"2026-06-03","uk":"2026-06-10"}'
"""
import argparse
import json
import sys
from datetime import datetime, date, timedelta

MON, TUE, WED, THU, FRI = 0, 1, 2, 3, 4

SOURCES = {
    "claims": ("Initial Jobless Claims (DOL ETA)",
               "https://www.dol.gov/ui/data.pdf",
               "script-fetchable (requests)"),
    "nfp":    ("Non-Farm Payrolls / Employment Situation (BLS)",
               "https://www.bls.gov/news.release/empsit.htm",
               "BROWSER (BLS 403s plain fetch)"),
    "adp":    ("ADP National Employment Report",
               "https://adpemploymentreport.com/",
               "script-fetchable (requests)"),
    "jolts":  ("JOLTS (BLS)",
               "https://www.bls.gov/news.release/jolts.htm",
               "BROWSER (BLS 403s plain fetch)"),
    "uk":     ("UK Labour Market (ONS)",
               "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/"
               "employmentandemployeetypes/bulletins/uklabourmarket/latest",
               "script-fetchable (requests)"),
}


def now_eastern():
    """Return a datetime in US Eastern. zoneinfo if available, else manual DST."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        u = datetime.utcnow()

        def nth_sunday(year, month, n):
            d = date(year, month, 1)
            first_sun = d + timedelta(days=(6 - d.weekday()) % 7)
            return first_sun + timedelta(days=7 * (n - 1))

        # US DST: 2 AM 2nd Sunday March -> 2 AM 1st Sunday November.
        dst_start = datetime(u.year, 3, nth_sunday(u.year, 3, 2).day, 7)  # 2AM ET = 07 UTC
        dst_end = datetime(u.year, 11, nth_sunday(u.year, 11, 1).day, 6)  # 2AM ET = 06 UTC
        offset = -4 if (dst_start <= u < dst_end) else -5
        return u + timedelta(hours=offset)


def first_weekday_of_month(year, month, weekday):
    d = date(year, month, 1)
    return d + timedelta(days=(weekday - d.weekday()) % 7)


def nth_weekday_of_month(year, month, weekday, n):
    return first_weekday_of_month(year, month, weekday) + timedelta(days=7 * (n - 1))


def prev_month(year, month):
    return (year - 1, 12) if month == 1 else (year, month - 1)


def most_recent_weekday(today, weekday):
    return today - timedelta(days=(today.weekday() - weekday) % 7)


def parse_iso(s):
    if not s:
        return None
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def anchor_first_friday_based(today, offset_days=0):
    """Most recent (first-Friday-of-month + offset) date on/before today."""
    ff = nth_weekday_of_month(today.year, today.month, FRI, 1) + timedelta(days=offset_days)
    if today >= ff:
        return ff
    py, pm = prev_month(today.year, today.month)
    return nth_weekday_of_month(py, pm, FRI, 1) + timedelta(days=offset_days)


def anchor_third_tuesday(today):
    ut = nth_weekday_of_month(today.year, today.month, TUE, 3)
    if today >= ut:
        return ut
    py, pm = prev_month(today.year, today.month)
    return nth_weekday_of_month(py, pm, TUE, 3)


def decide(today, last):
    reports = {}

    def emit(key, due, reason, anchor=None):
        name, url, fetch = SOURCES[key]
        reports[key] = {
            "due": due,
            "reason": reason,
            "anchor_release": anchor.isoformat() if anchor else None,
            "report": name,
            "source_url": url,
            "fetch": fetch,
        }

    # --- claims: weekly Thursday ---
    thu = most_recent_weekday(today, THU)
    lc = parse_iso(last.get("claims"))
    if lc is not None:
        due = lc < thu
        reason = f"most-recent Thu={thu}; last logged {lc} -> {'newer print available' if due else 'already logged'}"
    else:
        due = today == thu
        reason = f"most-recent Thu={thu}; {'release day' if due else 'not Thursday'} (no last date supplied)"
    emit("claims", due, reason, thu)

    # --- nfp: first Friday ---
    nfp = anchor_first_friday_based(today, 0)
    ln = parse_iso(last.get("nfp"))
    if ln is not None:
        due = ln < nfp
        reason = f"1st-Friday anchor={nfp}; last logged {ln} -> {'new print available' if due else 'already logged'}"
    else:
        due = today == nfp
        reason = f"1st-Friday anchor={nfp}; {'release day' if due else 'not the first Friday'} (no last date)"
    emit("nfp", due, reason, nfp)

    # --- adp: Wednesday before NFP (first Friday - 2) ---
    adp = anchor_first_friday_based(today, -2)
    la = parse_iso(last.get("adp"))
    if la is not None:
        due = la < adp
        reason = f"Wed-before-NFP anchor={adp}; last logged {la} -> {'new print available' if due else 'already logged'}"
    else:
        due = today == adp
        reason = f"Wed-before-NFP anchor={adp}; {'release day' if due else 'not ADP day'} (no last date)"
    emit("adp", due, reason, adp)

    # --- jolts: irregular; conservative first-~12-days window + month dedup ---
    in_window = today.day <= 12 and today.weekday() < 5  # weekday in first 12 days
    lj = parse_iso(last.get("jolts"))
    if lj is not None:
        logged_this_month = (lj.year, lj.month) == (today.year, today.month)
        due = in_window and not logged_this_month
        reason = (f"window(day<=12,weekday)={in_window}; last logged {lj} "
                  f"({'this month -> done' if logged_this_month else 'prior month -> check'})")
    else:
        due = in_window
        reason = f"window(day<=12,weekday)={in_window}; date drifts -> conservative window (no last date)"
    emit("jolts", due, reason, None)

    # --- uk: ~3rd Tuesday (ONS) ---
    uk = anchor_third_tuesday(today)
    lu = parse_iso(last.get("uk"))
    if lu is not None:
        due = lu < uk
        reason = f"3rd-Tuesday anchor={uk}; last logged {lu} -> {'new print available' if due else 'already logged'}"
    else:
        due = today == uk
        reason = f"3rd-Tuesday anchor={uk}; {'release day' if due else 'not the 3rd Tuesday'} (no last date)"
    emit("uk", due, reason, uk)

    return reports


def main():
    ap = argparse.ArgumentParser(description="Labor Watch release-calendar gate")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today, US Eastern)")
    ap.add_argument("--last", help='JSON map of report->last-logged RELEASE date, '
                                    'e.g. {"claims":"2026-06-12","nfp":"2026-06-06"}')
    args = ap.parse_args()

    et = now_eastern()
    today = parse_iso(args.today) if args.today else et.date()
    try:
        last = json.loads(args.last) if args.last else {}
        if not isinstance(last, dict):
            raise ValueError
    except Exception:
        print("ERROR: --last must be a JSON object mapping report->YYYY-MM-DD", file=sys.stderr)
        sys.exit(2)

    reports = decide(today, last)
    due = [k for k, v in reports.items() if v["due"]]
    now_et_str = et.strftime("%Y-%m-%d %H:%M") + " ET"

    if due:
        checks = "; ".join(f"{k} [{SOURCES[k][2]}] {SOURCES[k][1]}" for k in due)
        action = (f"DUE: {', '.join(due)}. Check ONLY these: {checks}. "
                  "For each new print capture headline + key sub-readings, consensus, prior, "
                  "surprise (mark 'unconfirmed' if not verifiable); append one row per release "
                  "to the Labor section; update Current stance; post a concise alert to "
                  "#hyper-asset-monitoring (C0B8B76L7NH). Use the BROWSER only for nfp/jolts.")
        heartbeat_status = "logged " + "+".join(due)
    else:
        action = ("NOTHING DUE. Write the heartbeat line only; do NOT fetch any source, "
                  "do NOT open the browser, do NOT post to Slack. End the run (one-line summary).")
        heartbeat_status = "no new release"

    out = {
        "now_et": now_et_str,
        "today": today.isoformat(),
        "weekday": today.strftime("%A"),
        "due": due,
        "skip_all": len(due) == 0,
        "heartbeat_line": f"Last checked: {now_et_str} - {heartbeat_status}",
        "action": action,
        "reports": reports,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
