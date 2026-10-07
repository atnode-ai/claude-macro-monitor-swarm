#!/usr/bin/env python3
"""
housing_release_check.py - Housing Watch's deterministic release-check fetcher.

Collapses the recurring multi-source web research (Census construction, NAR,
Census sales) into a SINGLE deterministic call against the FRED API, and decides
whether a genuinely NEW release has landed by comparing each series' latest
reference month against what's already logged in the Macro Monitor blackboard's
Housing section.

Why FRED (not Census EITS): the Census EITS API (api.census.gov/.../timeseries/eits)
302-redirects to an empty body from the sandbox and is unreliable. FRED returns
clean JSON for every series we track, including NAR Existing Home Sales
(EXHOSLUSM495S). Fetch the NAR / Census release PAGES only for extra color
(median price, inventory months) when a NEW print actually needs logging.

Design goal: most runs find nothing new, so the common path must be cheap.
This script emits one compact JSON blob to stdout. On a no-new-release run the
caller just updates the heartbeat and stops - no HTML/PDF ever enters context.

Credentials: env var FRED_API_KEY (free: https://fred.stlouisfed.org/docs/api/api_key.html).

Usage:
  python3 housing_release_check.py [--blackboard-file PATH] [--months 16]

  --blackboard-file PATH  Path to the externalized ReadDocument export of the
                          blackboard (the file path ReadDocument returns when the
                          doc is too large to inline). If given, the script reads
                          the Housing section, extracts the last logged reference
                          month per report, and sets new_release per report.
                          If omitted, new_release/any_new are null (dedup manually).
  --months N              Observations to pull per series (default 16; needs >=13
                          for YoY).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request

FRED_BASE = "https://api.stlouisfed.org/fred"

# Tracked reports -> FRED series. Single-family splits are context sub-readings.
REPORTS = {
    "Building Permits":     {"series": "PERMIT",        "sf": "PERMIT1",  "kind": "saar"},
    "Housing Starts":       {"series": "HOUST",         "sf": "HOUST1F",  "kind": "saar"},
    "Existing Home Sales":  {"series": "EXHOSLUSM495S", "sf": None,       "kind": "saar"},
    "New Home Sales":       {"series": "HSN1F",         "sf": None,       "kind": "saar"},
}
# Context-only series (no new-release decision; latest level only).
CONTEXT = {
    "mortgage_30yr":            {"series": "MORTGAGE30US", "kind": "pct"},
    "new_home_months_supply":   {"series": "MSACSR",       "kind": "months"},
}

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _opener():
    """Build an opener that honors the sandbox HTTPS proxy."""
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    handler = urllib.request.ProxyHandler({"https": proxy, "http": proxy}) if proxy \
        else urllib.request.ProxyHandler()
    return urllib.request.build_opener(handler)


def _get_json(url, opener, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "housing-watch/1.0"})
    with opener.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fred_series_units(series_id, key, opener):
    """Return the FRED-reported units string for a series (for scale-safe display)."""
    url = f"{FRED_BASE}/series?" + urllib.parse.urlencode(
        {"series_id": series_id, "api_key": key, "file_type": "json"})
    try:
        data = _get_json(url, opener)
        return (data.get("seriess") or [{}])[0].get("units", "") or ""
    except Exception:
        return ""


def fred_observations(series_id, key, opener, months):
    """Latest `months` observations, newest first, as [(date, float|None), ...]."""
    url = f"{FRED_BASE}/series/observations?" + urllib.parse.urlencode({
        "series_id": series_id, "api_key": key, "file_type": "json",
        "sort_order": "desc", "limit": months})
    data = _get_json(url, opener)
    out = []
    for o in data.get("observations", []):
        v = o.get("value", ".")
        out.append((o.get("date"), None if v in (".", "", None) else float(v)))
    return out


def normalize(raw, units, kind):
    """Return a human display string + a normalized SAAR-millions value (or None)."""
    if raw is None:
        return ("n/a", None)
    u = (units or "").lower()
    if kind == "pct" or "percent" in u:
        return (f"{raw:.2f}%", None)
    if kind == "months" or "month" in u:
        return (f"{raw:.1f} mo", None)
    # housing counts -> normalize to MILLIONS of units (swarm convention), scale-safe
    if "thousand" in u:
        millions = raw / 1000.0
    elif "number of units" in u or raw >= 100000:
        millions = raw / 1e6
    else:  # default to thousands (PERMIT/HOUST/HSN1F native units)
        millions = raw / 1000.0
    return (f"{millions:.3f}M SAAR", millions)


def pct(cur, prev):
    if cur is None or prev in (None, 0):
        return None
    return round((cur - prev) / prev * 100.0, 1)


def first_valid(obs, start=0):
    for i in range(start, len(obs)):
        if obs[i][1] is not None:
            return i, obs[i]
    return None, (None, None)


def ref_month_str(date_iso):
    """'2026-05-01' -> '2026-05'."""
    return date_iso[:7] if date_iso else None


# ---- blackboard parsing (dedup baseline) -----------------------------------

def extract_housing_section(path):
    raw = open(path, "r", encoding="utf-8").read()
    # Primary: the externalized ReadDocument export is JSON {sections:[{name,content}]}.
    try:
        doc = json.loads(raw)
        secs = doc.get("sections") or (doc.get("document") or {}).get("sections") or []
        for s in secs:
            if re.search(r"housing", str(s.get("name", "")), re.I):
                return s.get("content", "") or ""
    except Exception:
        pass
    # Fallback: treat as text, grab from a 'Housing' heading to the next heading.
    m = re.search(r"(^|\n)#{1,4}\s*Housing.*?(?=\n#{1,4}\s|\Z)", raw, re.S | re.I)
    return m.group(0) if m else raw


def last_logged_ref_months(housing_md):
    """report name -> (year, month) of the latest reference month logged."""
    best = {}
    for line in housing_md.split("\n"):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c != ""]
        if len(cells) < 2:
            continue
        name = re.sub(r"[^A-Za-z ]", "", cells[0]).strip().lower()
        report = next((r for r in REPORTS if r.lower() == name), None)
        if not report:
            continue
        mm = re.search(r"([A-Za-z]{3,9})\s+(\d{4})", cells[1])
        if not mm:
            continue
        mon = _MONTHS.get(mm.group(1)[:3].lower())
        if not mon:
            continue
        ym = (int(mm.group(2)), mon)
        if report not in best or ym > best[report]:
            best[report] = ym
    return best


def ym_tuple(ref):  # '2026-05' -> (2026, 5)
    return (int(ref[:4]), int(ref[5:7])) if ref else None


# ---- main -------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blackboard-file")
    ap.add_argument("--months", type=int, default=16)
    args = ap.parse_args()

    key = os.environ.get("FRED_API_KEY", "").strip()
    result = {
        "as_of_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fred_ok": bool(key),
        "reports": {},
        "context": {},
        "new_releases": [],
        "any_new": None,
        "notes": [],
    }

    last_logged = {}
    if args.blackboard_file:
        try:
            last_logged = last_logged_ref_months(
                extract_housing_section(args.blackboard_file))
            result["last_logged"] = {k: f"{v[0]:04d}-{v[1]:02d}"
                                     for k, v in last_logged.items()}
        except Exception as e:
            result["notes"].append(f"blackboard parse failed: {e}")

    if not key:
        result["notes"].append(
            "FRED_API_KEY not set - fetch skipped. Set the skill credential to enable.")
        print(json.dumps(result, indent=2))
        return

    opener = _opener()
    new_releases = []
    try:
        for report, cfg in REPORTS.items():
            units = fred_series_units(cfg["series"], key, opener)
            obs = fred_observations(cfg["series"], key, opener, args.months)
            i0, (d0, v0) = first_valid(obs, 0)
            if v0 is None:
                result["reports"][report] = {"series": cfg["series"], "error": "no data"}
                continue
            i1, (d1, v1) = first_valid(obs, i0 + 1)
            # year-ago: same calendar month, ~12 obs back
            v12 = obs[i0 + 12][1] if len(obs) > i0 + 12 else None
            disp, _ = normalize(v0, units, cfg["kind"])
            entry = {
                "series": cfg["series"],
                "latest_ref": ref_month_str(d0),
                "display": disp,
                "raw": v0,
                "mom_pct": pct(v0, v1),
                "yoy_pct": pct(v0, v12),
                "prior_ref": ref_month_str(d1),
                "prior_raw": v1,
            }
            if cfg.get("sf"):
                sfu = fred_series_units(cfg["sf"], key, opener)
                sfo = fred_observations(cfg["sf"], key, opener, args.months)
                _, (_, sfv) = first_valid(sfo, 0)
                _, (_, sfv1) = first_valid(sfo, 1)
                if sfv is not None:
                    entry["single_family"] = {
                        "series": cfg["sf"],
                        "display": f"{sfv:.0f}k" if sfv < 100000 else f"{sfv/1000:.0f}k",
                        "raw": sfv, "mom_pct": pct(sfv, sfv1)}
            # new-release decision
            if args.blackboard_file:
                ll = last_logged.get(report)
                cur = ym_tuple(entry["latest_ref"])
                entry["last_logged"] = (f"{ll[0]:04d}-{ll[1]:02d}" if ll else None)
                entry["new_release"] = bool(cur and (ll is None or cur > ll))
                if entry["new_release"]:
                    new_releases.append(report)
            else:
                entry["new_release"] = None
            result["reports"][report] = entry

        for label, cfg in CONTEXT.items():
            units = fred_series_units(cfg["series"], key, opener)
            obs = fred_observations(cfg["series"], key, opener, args.months)
            _, (_, v0) = first_valid(obs, 0)
            disp, _ = normalize(v0, units, cfg["kind"])
            result["context"][label] = disp

        if args.blackboard_file:
            result["new_releases"] = new_releases
            result["any_new"] = len(new_releases) > 0
    except Exception as e:
        result["fred_ok"] = False
        result["notes"].append(f"FRED fetch error: {e}")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
