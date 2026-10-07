#!/usr/bin/env python3
"""Macro Blackboard Digest & Health.

Reads the Macro Monitor blackboard (the JSON file that ReadDocument externalizes
to disk) and emits, deterministically, either:

  --mode digest   (default) compact per-domain JSON: Current stance, tracks,
                  parsed release-table rows, the parsed `Last checked` timestamp,
                  age in hours, and a >36h staleness flag — PLUS a top-level
                  `health` block (all_fresh / stale_domains / fresh_domains) with
                  a ready-to-post HEALTH ALERT string, the prior synthesis's
                  Regime-watch / Week-ahead / Swarm-health lines for continuity,
                  AND the full verbatim current Macro Synthesis section content
                  (`synthesis_current`) plus its `synthesis_section_id` so the run
                  can edit it in place with UpdateDocument(replace) without a
                  second ReadDocument-and-parse of the blackboard.

  --mode health   only the health block (cheapest call — domain liveness only).

  --mode markdown reconstructs the blackboard as GitHub-flavored markdown
                  (`## Section` + content, tables made GFM-safe). Mirrors the
                  weekly public-report Step 4a so the model never hand-copies it.

The orchestrator never has to read the whole blackboard into context, and the
36-hour staleness arithmetic / markdown reconstruction leave the LLM entirely.

No credentials. Pure stdlib (zoneinfo for America/New_York).

Usage:
  python3 macro_blackboard_digest.py --blackboard-file <readdocument.json>
  python3 macro_blackboard_digest.py --blackboard-file <f> --mode health
  python3 macro_blackboard_digest.py --blackboard-file <f> --mode markdown
  python3 macro_blackboard_digest.py --blackboard-file <f> --now "2026-06-17 17:00"
"""
import argparse
import json
import re
import sys
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover - zoneinfo present on py3.9+
    ET = None

# The seven domain sections, in blackboard order. Health + digest cover these.
DOMAIN_SECTIONS = [
    "Inflation",
    "Labor",
    "Growth & Activity",
    "Housing",
    "Sentiment & Surveys",
    "Central Banks & Policy",
    "Financial Conditions & Markets",
]
# Sections excluded from --mode markdown (everything else is reconstructed).
MARKDOWN_SKIP = {"How this doc works"}
STALE_HOURS = 36

# "Last checked ... 2026-06-17 11:03 ET" — tolerant of _italic_ / **bold:** decoration.
TS_RE = re.compile(
    r"Last checked[^\n]*?(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})\s*ET",
    re.IGNORECASE,
)


def load_sections(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        if isinstance(data.get("sections"), list):
            return data["sections"]
        doc = data.get("document")
        if isinstance(doc, dict) and isinstance(doc.get("sections"), list):
            return doc["sections"]
    raise ValueError("Could not locate a 'sections' array in the blackboard file.")


def section_by_name(sections, name):
    for s in sections:
        if (s.get("name") or s.get("title")) == name:
            return s
    return None


def section_content(section):
    if not section:
        return ""
    return section.get("content") or section.get("text") or section.get("body") or ""


def now_et(override):
    if override:
        # Accept "YYYY-MM-DD HH:MM" (assumed ET wall clock).
        dt = datetime.strptime(override.strip(), "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=ET) if ET else dt
    return datetime.now(ET) if ET else datetime.now()


def parse_last_checked(content, now):
    """Return (iso_str_or_None, age_hours_or_None). Uses the MOST RECENT
    timestamp-bearing 'Last checked' match, so stray in-table mentions lose to
    the real heartbeat line."""
    best = None
    for m in TS_RE.finditer(content):
        y, mo, d, hh, mm = (int(x) for x in m.groups())
        try:
            dt = datetime(y, mo, d, hh, mm, tzinfo=ET) if ET else datetime(y, mo, d, hh, mm)
        except ValueError:
            continue
        if best is None or dt > best:
            best = dt
    if best is None:
        return None, None
    age = (now - best).total_seconds() / 3600.0
    return best.strftime("%Y-%m-%d %H:%M ET"), round(age, 1)


def extract_line(content, label):
    """Capture a labelled paragraph (e.g. 'Current stance') from its label line
    until a blank line or a Sources/Last-checked boundary. Markdown kept intact."""
    lines = content.split("\n")
    out, capturing = [], False
    for ln in lines:
        low = ln.lower()
        if not capturing and label.lower() in low:
            capturing = True
            out.append(ln.strip())
            continue
        if capturing:
            if ln.strip() == "":
                break
            if re.match(r"^[_*\s]*(sources|last checked)\b", low):
                break
            out.append(ln.strip())
    text = " ".join(out).strip()
    return text or None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_") or "col"


def today_tokens(now):
    """Date fragments the blackboard uses for 'released today' (e.g. 'Jun 17')."""
    mon = now.strftime("%b")
    return {f"{mon} {now.day}", f"{mon} {now.day:02d}"}


def parse_tables(content, now, cell_truncate=160):
    """Parse every GFM pipe table in the section, keyed by that table's own
    header cells. Long narrative cells are truncated to keep the digest compact;
    the first column (indicator name) is kept whole. Flags rows whose date column
    mentions today's date as a `released_today` hint (heuristic — the run verifies)."""
    rows = []
    header = None
    toks = today_tokens(now)
    for ln in content.split("\n"):
        if not ln.strip().startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") and c for c in cells):  # separator row
            continue
        if header is None:
            header = [slug(c) for c in cells]
            continue
        row = {}
        date_blob = ""
        for i, c in enumerate(cells):
            key = header[i] if i < len(header) else f"col{i}"
            if "date" in key:
                date_blob += " " + c
            if i > 0 and len(c) > cell_truncate:
                c = c[: cell_truncate - 1].rstrip() + "…"
            row[key] = c
        row["released_today"] = any(t in date_blob for t in toks)
        rows.append(row)
    return rows


def build_digest(sections, now, full=False):
    domains, stale, fresh, fresh_today = [], [], [], []
    for name in DOMAIN_SECTIONS:
        sec = section_by_name(sections, name)
        content = section_content(sec)
        last_checked, age = parse_last_checked(content, now) if content else (None, None)
        is_stale = (age is None) or (age > STALE_HOURS)
        reports = parse_tables(content, now)
        # Lean (default): keep only rows that landed today; non-fresh rows are
        # unchanged from prior runs and already synthesised. `--full` keeps all.
        shown = reports if full else [r for r in reports if r.get("released_today")]
        rec = {
            "name": name,
            "present": sec is not None,
            "tracks": extract_line(content, "Tracks:"),
            "current_stance": extract_line(content, "Current stance"),
            "last_checked": last_checked,
            "age_hours": age,
            "stale": is_stale,
            "reports_total": len(reports),
            "reports": shown,
        }
        domains.append(rec)
        for r in reports:
            if r.get("released_today"):
                label = next((v for k, v in r.items() if "report" in k or "indicator" in k),
                             list(r.values())[0])
                date_v = next((v for k, v in r.items() if "date" in k), "")
                fresh_today.append({"domain": name, "report": label, "latest_date": date_v})
        entry = {"domain": name, "last_checked": last_checked, "age_hours": age}
        (stale if is_stale else fresh).append(entry)

    all_fresh = len(stale) == 0
    if all_fresh:
        alert_text = ""
    else:
        parts = []
        for e in stale:
            seen = e["last_checked"] or "never (no heartbeat found)"
            ago = f", {e['age_hours']}h ago" if e["age_hours"] is not None else ""
            parts.append(f"{e['domain']} (last seen {seen}{ago})")
        alert_text = (
            "HEALTH ALERT — stale macro domain(s) >%dh since last check: " % STALE_HOURS
            + "; ".join(parts)
            + ". The macro picture is blind here until these collectors run."
        )

    synth_sec = section_by_name(sections, "Macro Synthesis")
    synth = section_content(synth_sec)
    prior = {
        "regime_watch": extract_line(synth, "Regime watch"),
        "week_ahead": extract_line(synth, "Week ahead"),
        "swarm_health": extract_line(synth, "Swarm health"),
    }
    # Full verbatim current Macro Synthesis section + its id, so the run can
    # edit it in place via UpdateDocument(replace) WITHOUT a second
    # ReadDocument-and-parse of the externalized blackboard file.
    synth_section_id = None
    if synth_sec:
        synth_section_id = (
            synth_sec.get("id")
            or synth_sec.get("sectionId")
            or synth_sec.get("_id")
        )

    health = {
        "threshold_hours": STALE_HOURS,
        "all_fresh": all_fresh,
        "checked_at": now.strftime("%Y-%m-%d %H:%M ET") if ET else str(now),
        "stale_domains": stale,
        "fresh_domains": fresh,
        "alert_text": alert_text,
    }
    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M ET") if ET else str(now),
        "health": health,
        "fresh_today": fresh_today,
        "domains": domains,
        "prior_synthesis": prior,
        "synthesis_section_id": synth_section_id,
        "synthesis_current": synth,
    }


def build_markdown(sections):
    """Reconstruct the blackboard as GitHub-flavored markdown (Step 4a).
    Ensures a blank line precedes every pipe table so GFM renders it."""
    out = []
    for sec in sections:
        name = sec.get("name") or sec.get("title") or ""
        if name in MARKDOWN_SKIP:
            continue
        content = section_content(sec)
        out.append(f"## {name}")
        out.append("")
        prev_blank = True
        prev_pipe = False
        for ln in content.split("\n"):
            is_pipe = ln.lstrip().startswith("|")
            if is_pipe and not prev_pipe and not prev_blank:
                out.append("")  # GFM needs a blank line before a table
            out.append(ln)
            prev_blank = ln.strip() == ""
            prev_pipe = is_pipe
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(description="Macro Monitor blackboard digest + health.")
    ap.add_argument("--blackboard-file", required=True,
                    help="Path to the JSON file ReadDocument externalized for the blackboard doc.")
    ap.add_argument("--mode", choices=["digest", "health", "markdown"], default="digest")
    ap.add_argument("--full", action="store_true",
                    help="Digest mode: include ALL report rows (default keeps only rows released today + a per-domain count).")
    ap.add_argument("--now", default=None,
                    help='Override "now" as ET wall clock "YYYY-MM-DD HH:MM" (testing/determinism).')
    args = ap.parse_args()

    try:
        sections = load_sections(args.blackboard_file)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return 2

    if args.mode == "markdown":
        sys.stdout.write(build_markdown(sections))
        return 0

    digest = build_digest(sections, now_et(args.now), full=args.full)
    if args.mode == "health":
        print(json.dumps(digest["health"], ensure_ascii=False, indent=2))
    else:
        print(json.dumps(digest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
