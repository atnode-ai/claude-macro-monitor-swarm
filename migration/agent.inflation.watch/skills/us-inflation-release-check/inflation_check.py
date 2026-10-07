#!/usr/bin/env python3
"""
US Inflation Release Check
==========================
One deterministic call that returns the latest CPI, PPI and PCE prints
(headline + core, MoM + YoY) as compact JSON, plus an `is_new` flag per
report so the caller can short-circuit a run when nothing fresh dropped.

Data sources (free / official):
  - CPI, PPI : BLS public API v2  (no key needed; key raises rate limits)
  - PCE      : BEA API            (free key required; set BEA_API_KEY)

The script does NOT fetch consensus/expected (that is a market survey, not
published by BLS/BEA). It returns actual / prior / MoM / YoY deterministically;
the caller fetches consensus with a single targeted web lookup on release days.

Usage:
  python3 inflation_check.py                # latest prints, is_new vs no baseline
  python3 inflation_check.py '{"CPI":"2026-05","PPI":"2026-05","PCE":"2026-04"}'
      # baseline = last reference month already logged per report; is_new=True
      # only when the latest reference month is newer than the baseline.

Env / credentials:
  BEA_API_KEY  (required for PCE; without it PCE is returned as 'unconfirmed')
  BLS_API_KEY  (optional; higher BLS rate limits)
"""
import json
import os
import sys
import datetime as dt

import requests

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BEA_URL = "https://apps.bea.gov/api/data"

# (label, SA series for MoM, NSA series for YoY)
BLS_SERIES = {
    "CPI": {
        "headline": ("CUSR0000SA0", "CUUR0000SA0"),
        "core":     ("CUSR0000SA0L1E", "CUUR0000SA0L1E"),
    },
    "PPI": {
        # Final demand (headline) and final demand less foods & energy (core)
        "headline": ("WPSFD49207", "WPUFD49207"),
        "core":     ("WPSFD49104", "WPUFD49104"),
    },
}

MONTHS = {f"M{m:02d}": m for m in range(1, 13)}


def _pct(new, old, digits=2):
    if old in (None, 0) or new is None:
        return None
    return round((new / old - 1.0) * 100.0, digits)


def _fetch_bls(start_year, end_year):
    series_ids = []
    for rep in BLS_SERIES.values():
        for sa, nsa in rep.values():
            series_ids += [sa, nsa]
    payload = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    key = os.environ.get("BLS_API_KEY")
    if key:
        payload["registrationkey"] = key
    r = requests.post(BLS_URL, json=payload, timeout=40)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS error: {data.get('message')}")
    out = {}
    for s in data["Results"]["series"]:
        pts = {}
        for d in s["data"]:
            m = MONTHS.get(d["period"])
            val = (d.get("value") or "").replace(",", "").strip()
            if m and val not in ("", "-"):
                try:
                    pts[(int(d["year"]), m)] = float(val)
                except ValueError:
                    continue          # skip suppressed / non-numeric points
        out[s["seriesID"]] = pts
    return out


def _mom_yoy(series_map, sa_id, nsa_id):
    sa = series_map.get(sa_id, {})
    nsa = series_map.get(nsa_id, {})
    if not nsa:
        return None
    latest = max(nsa)                       # (year, month)
    y, m = latest
    prior = (y, m - 1) if m > 1 else (y - 1, 12)
    yearago = (y - 1, m)
    return {
        "reference_month": f"{y:04d}-{m:02d}",
        "index_nsa": nsa.get(latest),
        "mom_pct": _pct(sa.get(latest), sa.get(prior)),
        "yoy_pct": _pct(nsa.get(latest), nsa.get(yearago), 1),
        "prior_index_nsa": nsa.get(prior),
    }


def _fetch_pce(start_year, end_year):
    key = os.environ.get("BEA_API_KEY")
    if not key:
        return {
            "headline": {"status": "unconfirmed", "reason": "BEA_API_KEY not set"},
            "core": {"status": "unconfirmed", "reason": "BEA_API_KEY not set"},
        }
    params = {
        "UserID": key,
        "method": "GetData",
        "datasetname": "NIPA",
        "TableName": "T20804",          # Price Indexes for PCE by Major Type of Product, Monthly
        "Frequency": "M",
        "Year": ",".join(str(y) for y in range(start_year, end_year + 1)),
        "ResultFormat": "JSON",
    }
    r = requests.get(BEA_URL, params=params, timeout=40)
    r.raise_for_status()
    rows = r.json()["BEAAPI"]["Results"]["Data"]
    # Match the two lines we care about by description (robust to line-code changes)
    wanted = {
        "headline": "personal consumption expenditures",
        "core": "pce excluding food and energy",
    }
    buckets = {k: {} for k in wanted}
    for row in rows:
        desc = row.get("LineDescription", "").strip().lower()
        for key_name, target in wanted.items():
            if desc == target:
                period = row["TimePeriod"]            # e.g. 2026M05
                y = int(period[:4]); m = int(period[5:])
                buckets[key_name][(y, m)] = float(row["DataValue"].replace(",", ""))
    out = {}
    for key_name, pts in buckets.items():
        if not pts:
            out[key_name] = {"status": "unconfirmed", "reason": "line not found in T20804"}
            continue
        latest = max(pts); y, m = latest
        prior = (y, m - 1) if m > 1 else (y - 1, 12)
        yearago = (y - 1, m)
        out[key_name] = {
            "reference_month": f"{y:04d}-{m:02d}",
            "index": pts.get(latest),
            "mom_pct": _pct(pts.get(latest), pts.get(prior)),
            "yoy_pct": _pct(pts.get(latest), pts.get(yearago), 1),
            "prior_index": pts.get(prior),
        }
    return out


def main():
    baseline = {}
    if len(sys.argv) > 1:
        try:
            baseline = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            print(json.dumps({"error": "baseline arg must be JSON"}))
            sys.exit(1)

    now = dt.datetime.utcnow()
    start_year, end_year = now.year - 1, now.year

    reports = {}
    try:
        bls = _fetch_bls(start_year, end_year)
        for rep, conf in BLS_SERIES.items():
            reports[rep] = {
                part: _mom_yoy(bls, sa, nsa) for part, (sa, nsa) in conf.items()
            }
    except Exception as e:                       # never crash the run
        reports["CPI"] = reports["PPI"] = {"status": "error", "reason": str(e)}

    try:
        reports["PCE"] = _fetch_pce(start_year, end_year)
    except Exception as e:
        reports["PCE"] = {"status": "error", "reason": str(e)}

    # is_new: latest headline reference month newer than the logged baseline
    any_new = False
    for rep, parts in reports.items():
        head = parts.get("headline") if isinstance(parts, dict) else None
        ref = head.get("reference_month") if isinstance(head, dict) else None
        base = baseline.get(rep)
        is_new = bool(ref and (not base or ref > base))
        if isinstance(parts, dict):
            parts["is_new"] = is_new
        any_new = any_new or is_new

    print(json.dumps({
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline": baseline,
        "any_new": any_new,
        "reports": reports,
    }, indent=2))


if __name__ == "__main__":
    main()
