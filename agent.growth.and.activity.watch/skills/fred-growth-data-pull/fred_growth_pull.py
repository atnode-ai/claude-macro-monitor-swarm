#!/usr/bin/env python3
"""
FRED Growth-Data Pull  --  Growth & Activity Watch (macro-monitoring swarm)

Collapses 5 of the 6 hard-data series the Growth & Activity collector tracks into a
SINGLE FRED API batch, so a routine release-check run is one tool call instead of
~5 separate page fetches + parses. Includes a release-calendar look-back so quiet
days are cheap to confirm.

COVERS (via FRED, free):
  - GDP                 A191RL1Q225SBEA (real GDP, % chg QoQ annualised) + GDPC1 (level)
  - Retail Sales        RSAFS (advance retail & food services, headline $)         [control group: Census only]
  - Industrial Prod.    INDPRO (total index) + TCU (capacity utilisation %)
  - Durable Goods       DGORDER (new orders) + NEWORDER (core capex, nondef ex-air)
  - Trade Balance       BOPGSTB (goods & services balance, $)

NOT covered here (handle separately, only on their calendar days):
  - ISM PMI  -> proprietary, delisted from FRED in 2016. Read the ISM Report On Business
               via the browser (Mfg ~1st business day, Services ~3rd).
  - Chicago Fed CARTS retail nowcast -> use the "Chicago Fed CARTS - Retail Sales Nowcast" skill.
  - Market CONSENSUS is not on FRED -> look it up (quick WebSearch) ONLY when a new print lands.

CREDENTIAL: FRED_API_KEY  (free: https://fredaccount.stlouisfed.org/apikeys)

USAGE:
  python3 fred_growth_pull.py                  # all series + IN-DOMAIN release calendar (default)
  python3 fred_growth_pull.py --since 2026-06-10   # also flag series FRED refreshed on/after this date
  python3 fred_growth_pull.py --mode calendar      # ONLY the release calendar (quiet-day glance)
  python3 fred_growth_pull.py --all-releases       # include EVERY release in the window (verbose, ~250/wk)
  python3 fred_growth_pull.py --days 5             # calendar look-back window (default 7)
  python3 fred_growth_pull.py --series INDPRO,RSAFS  # restrict to specific FRED ids

By default the release calendar is filtered to THIS domain (GDP/Retail/IP/Durable Goods/Trade)
to keep output small; recent_releases reports total_releases_in_window + shown counts.

OUTPUT: compact JSON to stdout. A human-readable one-liner per series is in `.summary`.
NEVER FABRICATES: on any fetch/parse failure a series is marked status="unconfirmed" with the
error text, so the caller marks that blackboard cell 'unconfirmed' rather than guessing.
"""

import os
import sys
import json
import argparse
import datetime as dt

try:
    import requests
except ImportError:
    sys.stderr.write("requests not installed -- run: pip install requests\n")
    raise

FRED_BASE = "https://api.stlouisfed.org/fred"
TIMEOUT = 30

# key, fred_id, label, kind:
#   pct    -> value is already a % (report as-is, e.g. GDP QoQ annualised)
#   level  -> report level only (e.g. trade balance $, capacity utilisation %)
#   flow   -> report level + month-over-month % change (sales / orders / index)
SERIES = [
    {"key": "gdp_qoq_saar",   "id": "A191RL1Q225SBEA", "label": "Real GDP (QoQ, ann.)",            "kind": "pct"},
    {"key": "gdp_level",      "id": "GDPC1",            "label": "Real GDP (level, chained $)",     "kind": "flow"},
    {"key": "retail_total",   "id": "RSAFS",            "label": "Advance Retail & Food Svcs",      "kind": "flow"},
    {"key": "indpro",         "id": "INDPRO",           "label": "Industrial Production (index)",   "kind": "flow"},
    {"key": "cap_util",       "id": "TCU",              "label": "Capacity Utilisation",            "kind": "level"},
    {"key": "durable_orders", "id": "DGORDER",          "label": "Durable Goods New Orders",        "kind": "flow"},
    {"key": "core_capex",     "id": "NEWORDER",         "label": "Core capex (nondef ex-air)",      "kind": "flow"},
    {"key": "trade_balance",  "id": "BOPGSTB",          "label": "Trade Balance (goods & svcs)",    "kind": "level"},
]

# FRED release-name keywords that belong to THIS domain (for the calendar highlight).
DOMAIN_RELEASE_KEYWORDS = [
    "gross domestic product", "retail", "industrial production",
    "durable goods", "manufacturers' shipments", "international trade", "advance report",
]


def api_key():
    k = os.environ.get("FRED_API_KEY", "").strip()
    if not k:
        sys.stderr.write("FRED_API_KEY not set in environment.\n")
        sys.exit(2)
    return k


def _get(path, params):
    params = dict(params)
    params["api_key"] = api_key()
    params["file_type"] = "json"
    r = requests.get(f"{FRED_BASE}/{path}", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def fmt_period(date_str, frequency_short):
    """Turn an observation date into a human label: 2026Q1 / Apr-2026 / 2026-04-01."""
    try:
        d = dt.date.fromisoformat(date_str)
    except Exception:
        return date_str
    fs = (frequency_short or "").upper()
    if fs.startswith("Q"):
        return f"{d.year}Q{(d.month - 1) // 3 + 1}"
    if fs.startswith("M"):
        return d.strftime("%b-%Y")
    return date_str


def pct_change(curr, prev):
    try:
        c, p = float(curr), float(prev)
        if p == 0:
            return None
        return round((c - p) / abs(p) * 100.0, 2)
    except Exception:
        return None


def pull_series(spec, since=None):
    out = {"key": spec["key"], "fred_id": spec["id"], "label": spec["label"], "status": "ok"}
    try:
        info = _get("series", {"series_id": spec["id"]})["seriess"][0]
        freq = info.get("frequency_short", "")
        out["units"] = info.get("units_short") or info.get("units")
        out["frequency"] = info.get("frequency")
        out["last_updated"] = info.get("last_updated")
        out["observation_end"] = info.get("observation_end")
        out["latest_period"] = fmt_period(info.get("observation_end", ""), freq)

        obs = _get("series/observations",
                   {"series_id": spec["id"], "sort_order": "desc", "limit": 3})["observations"]
        vals = [o for o in obs if o.get("value") not in (None, ".", "")]
        if not vals:
            out["status"] = "unconfirmed"
            out["error"] = "no numeric observations returned"
            out["summary"] = f"{spec['label']}: unconfirmed (no data)"
            return out

        latest = vals[0]
        out["latest_value"] = latest["value"]
        prior = vals[1] if len(vals) > 1 else None
        if prior:
            out["prior_period"] = fmt_period(prior["date"], freq)
            out["prior_value"] = prior["value"]

        if spec["kind"] == "flow" and prior:
            out["mom_pct"] = pct_change(latest["value"], prior["value"])

        # Did FRED refresh this series on/after --since? (revision OR new print)
        if since and out.get("last_updated"):
            try:
                lu = dt.date.fromisoformat(out["last_updated"][:10])
                out["refreshed_since"] = lu >= since
            except Exception:
                out["refreshed_since"] = None

        unit = out.get("units") or ""
        upd = (out.get("last_updated") or "?")[:10]
        if spec["kind"] == "pct":
            out["summary"] = f"{spec['label']} {out['latest_period']} = {latest['value']}% (annualised rate) | updated {upd}"
        elif spec["kind"] == "flow" and out.get("mom_pct") is not None:
            out["summary"] = f"{spec['label']} {out['latest_period']} = {latest['value']} {unit} ({out['mom_pct']:+.2f}% m/m) | updated {upd}"
        else:
            out["summary"] = f"{spec['label']} {out['latest_period']} = {latest['value']} {unit} | updated {upd}"
    except Exception as e:
        out["status"] = "unconfirmed"
        out["error"] = f"{type(e).__name__}: {e}"
        out["summary"] = f"{spec['label']}: unconfirmed ({type(e).__name__})"
    return out


def recent_releases(days, domain_only=True):
    """Recent FRED release dates in the look-back window. By DEFAULT only this domain's
    releases are returned (keeps output tiny — FRED publishes ~250 releases/week); pass
    domain_only=False (CLI: --all-releases) for the full list."""
    try:
        end = dt.date.today()
        start = end - dt.timedelta(days=days)
        data = _get("releases/dates", {
            "sort_order": "desc", "limit": 1000,
            "include_release_dates_with_no_data": "false",
            "realtime_start": start.isoformat(), "realtime_end": end.isoformat(),
        })
        rows, total = [], 0
        for rd in data.get("release_dates", []):
            name = rd.get("release_name", "")
            d = rd.get("date", "")
            try:
                if dt.date.fromisoformat(d) < start:
                    continue
            except Exception:
                pass
            total += 1
            mine = any(kw in name.lower() for kw in DOMAIN_RELEASE_KEYWORDS)
            if domain_only and not mine:
                continue
            rows.append({"date": d, "release": name, "in_my_domain": mine})
        rows.sort(key=lambda x: x["date"], reverse=True)
        return {"window_days": days, "domain_only": domain_only,
                "total_releases_in_window": total, "shown": len(rows), "releases": rows}
    except Exception as e:
        return {"status": "unconfirmed", "error": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser(description="FRED Growth-Data Pull")
    ap.add_argument("--since", help="YYYY-MM-DD: flag series FRED refreshed on/after this date")
    ap.add_argument("--days", type=int, default=7, help="calendar look-back window (default 7)")
    ap.add_argument("--mode", choices=["full", "calendar"], default="full")
    ap.add_argument("--series", help="comma-separated FRED ids to restrict to")
    ap.add_argument("--all-releases", action="store_true",
                    help="show ALL releases in the window, not just this domain's (verbose)")
    args = ap.parse_args()

    since = None
    if args.since:
        try:
            since = dt.date.fromisoformat(args.since)
        except ValueError:
            sys.stderr.write("--since must be YYYY-MM-DD\n")
            sys.exit(2)

    result = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "note": "ISM PMI and CARTS are NOT in this pull (handle separately). Consensus not on FRED.",
        "recent_releases": recent_releases(args.days, domain_only=not args.all_releases),
    }

    if args.mode == "full":
        specs = SERIES
        if args.series:
            wanted = {s.strip().upper() for s in args.series.split(",")}
            specs = [s for s in SERIES if s["id"].upper() in wanted]
        series_out = [pull_series(s, since=since) for s in specs]
        result["series"] = series_out
        result["unconfirmed"] = [s["fred_id"] for s in series_out if s["status"] != "ok"]

    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
