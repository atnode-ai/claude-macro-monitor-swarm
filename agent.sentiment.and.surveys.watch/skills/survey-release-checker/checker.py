#!/usr/bin/env python3
"""
survey-release-checker
======================
Deterministic release-calendar GATE + best-effort fetch/parse for the
"A - Sentiment & Surveys Watch" macro collector.

WHY THIS EXISTS
---------------
~90% of scheduled runs land on days when none of the three surveys release.
This script lets a run decide CHEAPLY (no network) whether anything is plausibly
due. On quiet days the agent writes only its heartbeat line and stops. When a
report IS due, the agent calls `fetch` for that one report and receives compact
JSON instead of pulling raw HTML into the model context.

REPORTS / CALENDAR (release time shown in US Eastern):
  umich_prelim  U. Michigan Surveys of Consumers, PRELIMINARY  2nd Friday   ~10:00 ET
  umich_final   U. Michigan Surveys of Consumers, FINAL        last Friday  ~10:00 ET
  conf_board    Conference Board Consumer Confidence           last Tuesday ~10:00 ET
  ifo           ifo Business Climate Index                     last Monday  ~04:00 ET (10:00 CET)

CONTRACT
--------
`due`   -> {"as_of": "<iso ET>", "due": ["conf_board", ...]}   # empty list == quiet day
`fetch` -> {"report","release_date","headline","subreadings":{...},
            "source_url","confirmed":bool,"notes":"..."}
Any field that cannot be confidently extracted is null with confirmed=false.
NEVER guess a number. The agent fills gaps via a targeted search or logs the
field 'unconfirmed', and ALWAYS does its own blackboard dedup + Slack decision.
This script is stateless: it does not know what is already logged. The gate only
says "is something scheduled and released by now"; dedup stays with the agent.

NETWORK: uses `requests` (honors HTTPS_PROXY in this sandbox). No browser.
If requests is missing: pip install requests
"""

from __future__ import annotations
import argparse
import calendar
import datetime as dt
import json
import re

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover - fallback if tzdata unavailable
    ET = dt.timezone(dt.timedelta(hours=-4))

# Local Eastern release hour:minute (approximate, used only for the day-of gate).
RELEASE_ET = {
    "umich_prelim": (10, 0),
    "umich_final": (10, 0),
    "conf_board": (10, 0),
    "ifo": (4, 0),
}

SOURCES = {
    "umich_prelim": "https://www.sca.isr.umich.edu/",
    "umich_final": "https://www.sca.isr.umich.edu/",
    "conf_board": "https://www.conference-board.org/topics/consumer-confidence",
    "ifo": "https://www.ifo.de/en/ifo-business-climate-index",
}


# ---- calendar helpers -------------------------------------------------------
def _weekday_dates(year, month, weekday):
    """All dates in (year, month) that fall on `weekday` (Mon=0 .. Sun=6)."""
    n = calendar.monthrange(year, month)[1]
    return [
        dt.date(year, month, d)
        for d in range(1, n + 1)
        if dt.date(year, month, d).weekday() == weekday
    ]


def scheduled_dates(year, month):
    fridays = _weekday_dates(year, month, 4)
    tuesdays = _weekday_dates(year, month, 1)
    mondays = _weekday_dates(year, month, 0)
    return {
        "umich_prelim": fridays[1],    # 2nd Friday
        "umich_final": fridays[-1],    # last Friday
        "conf_board": tuesdays[-1],    # last Tuesday
        "ifo": mondays[-1],            # last Monday
    }


def due_reports(now_et):
    """Reports scheduled for now_et's date whose release time has already passed."""
    sched = scheduled_dates(now_et.year, now_et.month)
    out = []
    for rep, d in sched.items():
        if d != now_et.date():
            continue
        hh, mm = RELEASE_ET[rep]
        rel = dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=ET)
        if now_et >= rel:
            out.append(rep)
    return sorted(out)


# ---- best-effort fetch / parse ----------------------------------------------
def _get(url, timeout=20):
    import requests
    headers = {"User-Agent": "Mozilla/5.0 (macro-collector)"}
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text


def _num_after(text, *labels):
    """First number appearing shortly after any of the given labels (else None)."""
    for lab in labels:
        m = re.search(re.escape(lab) + r"[^0-9\-]{0,40}(-?\d{1,3}(?:\.\d)?)", text, re.I)
        if m:
            return float(m.group(1))
    return None


def fetch_report(report):
    url = SOURCES[report]
    res = {
        "report": report,
        "release_date": None,
        "headline": None,
        "subreadings": {},
        "source_url": url,
        "confirmed": False,
        "notes": "",
    }
    try:
        html = _get(url)
    except Exception as e:  # network/parse must never crash the run
        res["notes"] = f"fetch failed: {e}. Agent should confirm via targeted search."
        return res

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    if report.startswith("umich"):
        res["headline"] = _num_after(text, "Index of Consumer Sentiment", "Consumer Sentiment")
        res["subreadings"] = {
            "infl_exp_1yr": _num_after(text, "year-ahead", "one-year", "next year"),
            "infl_exp_5_10yr": _num_after(text, "5-10", "five-to-ten", "long-run", "long run"),
        }
    elif report == "conf_board":
        res["headline"] = _num_after(text, "Consumer Confidence Index", "Confidence Index")
        res["subreadings"] = {"jobs_plentiful_minus_hard_to_get": None}
        res["notes"] = "labour differential rarely on page; confirm via release PDF/search."
    elif report == "ifo":
        res["headline"] = _num_after(text, "Business Climate", "ifo Business Climate")
        res["subreadings"] = {
            "current_assessment": _num_after(text, "Current Assessment", "current situation"),
            "expectations": _num_after(text, "Expectations"),
        }

    have_head = res["headline"] is not None
    have_subs = any(v is not None for v in res["subreadings"].values())
    res["confirmed"] = bool(have_head and have_subs)
    if not res["confirmed"] and not res["notes"]:
        res["notes"] = "partial/uncertain parse; confirm headline + subreadings before logging."
    return res


# ---- selftest ---------------------------------------------------------------
def selftest():
    sd = scheduled_dates(2026, 6)
    expect = {
        "umich_prelim": dt.date(2026, 6, 12),
        "umich_final": dt.date(2026, 6, 26),
        "conf_board": dt.date(2026, 6, 30),
        "ifo": dt.date(2026, 6, 29),
    }
    assert sd == expect, f"calendar mismatch: {sd} != {expect}"
    assert due_reports(dt.datetime(2026, 6, 17, 11, 0, tzinfo=ET)) == []           # quiet day
    assert due_reports(dt.datetime(2026, 6, 29, 9, 0, tzinfo=ET)) == ["ifo"]        # ifo, both runs
    assert due_reports(dt.datetime(2026, 6, 30, 9, 0, tzinfo=ET)) == []            # CB pre-10:00
    assert due_reports(dt.datetime(2026, 6, 30, 11, 0, tzinfo=ET)) == ["conf_board"]
    assert due_reports(dt.datetime(2026, 6, 12, 11, 0, tzinfo=ET)) == ["umich_prelim"]
    print("selftest OK ->", {k: str(v) for k, v in sd.items()})


# ---- cli --------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description="survey release calendar gate + best-effort fetch")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("due", help="list reports due as of now (or --now ISO ET)")
    d.add_argument("--now")
    f = sub.add_parser("fetch", help="best-effort fetch+parse one report")
    f.add_argument("--report", required=True, choices=list(SOURCES))
    sub.add_parser("selftest", help="verify calendar/gate logic (no network)")
    a = p.parse_args(argv)

    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "due":
        now = (
            dt.datetime.fromisoformat(a.now).replace(tzinfo=ET)
            if a.now
            else dt.datetime.now(ET)
        )
        print(json.dumps({"as_of": now.isoformat(), "due": due_reports(now)}))
    elif a.cmd == "fetch":
        print(json.dumps(fetch_report(a.report), indent=2))


if __name__ == "__main__":
    main()
