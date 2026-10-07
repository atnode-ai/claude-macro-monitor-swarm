#!/usr/bin/env python3
"""
Chicago Fed CARTS — Retail Sales Nowcast fetcher/parser.

CARTS (Chicago Fed Advance Retail Trade Summary) is a weekly mixed-frequency
model nowcast of the U.S. Census Bureau's retail & food services sales EXCLUDING
motor vehicles & parts ("ex. auto"). It projects month-over-month growth both
NOMINAL (seasonally adjusted) and INFLATION-ADJUSTED, and is published twice a
month at 8:30 a.m. ET: a "preliminary" release near month-end (weekly data through
mid-month) and a "final" release the day before the Census retail-sales report
(data through the end of the prior month).

This script downloads the canonical CARTS release PDF, extracts the projection,
and prints a structured summary (and JSON). No credentials required — public data.

Source: https://www.chicagofed.org/research/data/carts/current-data
PDF:    https://www.chicagofed.org/-/media/publications/carts/carts.pdf

Usage:
    python3 carts_nowcast.py                 # human summary + JSON
    python3 carts_nowcast.py --json          # JSON only
    python3 carts_nowcast.py --save out.pdf  # also keep the downloaded PDF
    python3 carts_nowcast.py --pdf path.pdf  # parse a local PDF (skip download)
"""
import sys
import os
import re
import json
import time
import argparse
import datetime as dt

PDF_URL = "https://www.chicagofed.org/-/media/publications/carts/carts.pdf"
ABOUT_URL = "https://www.chicagofed.org/research/data/carts/current-data"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
MONTH_IDX = {m: i + 1 for i, m in enumerate(MONTHS)}


def _ensure_pypdf():
    """Import pypdf, installing it on the fly if the runtime lacks it."""
    try:
        import pypdf  # noqa
        return
    except ImportError:
        pass
    import subprocess
    # bootstrap pip if needed, then install pypdf into the user site
    try:
        subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"],
                       check=False, capture_output=True)
    except Exception:
        pass
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "pypdf"],
                   check=True)


def fetch_pdf(url=PDF_URL, save_path=None, timeout=90):
    """Download the latest CARTS PDF with cache-busting (honors HTTPS_PROXY)."""
    import urllib.request
    bust = f"nocache={int(time.time())}"
    full = url + (("&" if "?" in url else "?") + bust)
    req = urllib.request.Request(full, headers={
        "User-Agent": "Mozilla/5.0 (CARTS-nowcast-skill)",
        "Cache-Control": "no-cache, no-store, max-age=0",
        "Pragma": "no-cache",
        "Accept": "application/pdf,*/*",
    })
    # urllib reads HTTP(S)_PROXY from the environment automatically.
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    if not data[:5] == b"%PDF-":
        raise RuntimeError(f"Downloaded content is not a PDF (got {len(data)} bytes, "
                           f"head={data[:16]!r}); URL={full}")
    if save_path:
        with open(save_path, "wb") as f:
            f.write(data)
    return data


def extract_text(pdf_bytes=None, pdf_path=None):
    _ensure_pypdf()
    from pypdf import PdfReader
    import io
    reader = PdfReader(pdf_path if pdf_path else io.BytesIO(pdf_bytes))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def _norm(s):
    """Normalize PDF quirks: unicode dashes/minus -> '-', collapse whitespace."""
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    s = s.replace("‘", "'").replace("’", "'")
    return s


def _signed(tok):
    tok = tok.strip().replace("*", "")
    if tok in ("", "+", "-"):
        return None
    try:
        return float(tok)
    except ValueError:
        return None


def parse(text):
    """Parse CARTS projection fields from extracted PDF text."""
    t = _norm(text)
    flat = re.sub(r"[ \t]+", " ", t)
    out = {
        "source": "Chicago Fed Advance Retail Trade Summary (CARTS)",
        "source_url": ABOUT_URL,
        "pdf_url": PDF_URL,
        "fetched_at": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "release_date": None,
        "reference_month": None,
        "projection": {"nominal_sa_pct": None, "inflation_adjusted_pct": None},
        "data_available_as_of": None,
        "release_type": None,         # inferred: preliminary | final | unknown
        "release_type_basis": None,
        "recent_monthly_values": {},
        "headline": None,
        "warnings": [],
    }

    # Release date: "Month D, YYYY" near the top (PDF often drops the space: "March16,2026")
    m = re.search(r"\b(" + "|".join(MONTHS) + r")\s*(\d{1,2})\s*,\s*(\d{4})", flat)
    if m:
        out["release_date"] = f"{m.group(1)} {int(m.group(2))}, {m.group(3)}"

    # Headline projection sentence -> reference month + nominal SA% + real%
    hm = re.search(
        r"For the month of (" + "|".join(MONTHS) + r")\b.*?projected to (increase|decrease)\s*([+-]?\d+\.\d+)%"
        r".*?seasonally adjusted.*?(increase|decrease)\s*([+-]?\d+\.\d+)%\s*when adjusted for inflation",
        flat, re.IGNORECASE | re.DOTALL)
    if hm:
        out["reference_month"] = hm.group(1)
        nominal = abs(float(hm.group(3))) * (-1 if hm.group(2).lower() == "decrease" else 1)
        real = abs(float(hm.group(5))) * (-1 if hm.group(4).lower() == "decrease" else 1)
        out["projection"]["nominal_sa_pct"] = round(nominal, 2)
        out["projection"]["inflation_adjusted_pct"] = round(real, 2)
        out["headline"] = re.sub(r"\s+", " ", hm.group(0).strip())
    else:
        out["warnings"].append("Could not parse the headline projection sentence.")

    # "data available as of Month D, YYYY"
    dm = re.search(r"data available as of\s+(" + "|".join(MONTHS) + r")\s*(\d{1,2})\s*,\s*(\d{4})",
                   flat, re.IGNORECASE)
    if dm:
        out["data_available_as_of"] = f"{dm.group(1)} {int(dm.group(2))}, {dm.group(3)}"

    # Recent Monthly Values table (best-effort, line-based for robustness).
    # The two data rows are the only lines holding >=5 decimal numbers; the month
    # header is the only line holding >=4 month abbreviations.
    num_re = re.compile(r"[+-]?\d+\.\d+")
    abbrevs = [m[:3] for m in MONTHS]
    abbr_re = re.compile(r"\b(" + "|".join(abbrevs) + r")\b\s*('?\d{2})?")
    value_rows = []
    months_row = None
    for line in t.splitlines():
        nline = _norm(line)
        nums = num_re.findall(nline)
        if len(nums) >= 5:
            value_rows.append([_signed(x) for x in nums[:6]])
        elif months_row is None:
            abbr = abbr_re.findall(nline)
            if len(abbr) >= 4:
                months_row = [(a + (" " + y if y else "")).strip() for a, y in abbr][:6]
    if months_row:
        out["recent_monthly_values"]["months"] = months_row
    if len(value_rows) >= 1:
        out["recent_monthly_values"]["sales_ex_auto_pct"] = value_rows[0]
    if len(value_rows) >= 2:
        out["recent_monthly_values"]["inflation_adjusted_pct"] = value_rows[1]
    if not value_rows:
        out["warnings"].append("Could not parse the recent monthly values table.")

    # Infer preliminary vs final from the data-cutoff vs the reference month.
    if out["reference_month"] and out["data_available_as_of"]:
        try:
            ref_i = MONTH_IDX[out["reference_month"]]
            asof = re.match(r"(" + "|".join(MONTHS) + r")\s+(\d{1,2}),\s+(\d{4})",
                            out["data_available_as_of"])
            asof_month = MONTH_IDX[asof.group(1)]
            asof_day = int(asof.group(2))
            # If the cutoff is in a month AFTER the reference month, the reference
            # month is fully observed -> "final"; if cutoff is within the reference
            # month (mid-month), it's the "preliminary".
            if asof_month != ref_i:  # cutoff month differs (next month) -> final
                out["release_type"] = "final"
                out["release_type_basis"] = "data cutoff falls after the reference month ends"
            else:
                out["release_type"] = "preliminary" if asof_day <= 20 else "final"
                out["release_type_basis"] = "data cutoff is within the reference month (mid-month)"
        except Exception:
            out["release_type"] = "unknown"
    else:
        out["release_type"] = "unknown"
    if out["release_type"] == "unknown":
        out["warnings"].append("Could not infer preliminary/final; report raw dates.")
    return out


def summarize(d):
    p = d["projection"]
    lines = []
    lines.append("Chicago Fed CARTS — Retail Sales Nowcast")
    lines.append("=" * 44)
    rt = (d.get("release_type") or "unknown").upper()
    lines.append(f"Release: {d.get('release_date')}  ({rt})")
    lines.append(f"Reference month: {d.get('reference_month')}  "
                 f"(data as of {d.get('data_available_as_of')})")
    lines.append("Retail & food services sales ex. auto, m/m:")
    lines.append(f"   Nominal (SA):        {_fmt(p['nominal_sa_pct'])}")
    lines.append(f"   Inflation-adjusted:  {_fmt(p['inflation_adjusted_pct'])}")
    rmv = d.get("recent_monthly_values") or {}
    if rmv.get("months"):
        lines.append("Recent months: " + ", ".join(rmv["months"]))
    if rmv.get("sales_ex_auto_pct"):
        lines.append("   nominal:  " + " ".join(_fmt(x) for x in rmv["sales_ex_auto_pct"]))
    if rmv.get("inflation_adjusted_pct"):
        lines.append("   real:     " + " ".join(_fmt(x) for x in rmv["inflation_adjusted_pct"]))
    if d.get("warnings"):
        lines.append("Warnings: " + "; ".join(d["warnings"]))
    return "\n".join(lines)


def _fmt(x):
    if x is None:
        return "n/a"
    return f"{x:+.1f}%"


def main():
    ap = argparse.ArgumentParser(description="Fetch + parse the Chicago Fed CARTS nowcast.")
    ap.add_argument("--json", action="store_true", help="print JSON only")
    ap.add_argument("--save", metavar="PATH", help="save the downloaded PDF to PATH")
    ap.add_argument("--pdf", metavar="PATH", help="parse a local PDF instead of downloading")
    args = ap.parse_args()

    if args.pdf:
        text = extract_text(pdf_path=args.pdf)
    else:
        data = fetch_pdf(save_path=args.save)
        text = extract_text(pdf_bytes=data)

    result = parse(text)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(summarize(result))
        print()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
