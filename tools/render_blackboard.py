"""data/ -> blackboard/BLACKBOARD.md (human view; the JSON stays the source of truth).

    python -m tools.render_blackboard [--rows 6] [--out blackboard/BLACKBOARD.md]
"""
import argparse
import sys

from collectors import common as C
from tools import store


def _cell(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def domain_section(dom, rows):
    recs = store.releases(dom["id"])
    recs.sort(key=lambda r: (r.get("detected_at") or "", r["ref"]))
    recs = recs[-rows:]
    idx = C.report_index()
    out = [f"## {dom['name']}", ""]
    tracks = ", ".join(r["name"] for r in dom["reports"])
    out.append(f"**Tracks:** {tracks}")
    out.append("")
    out.append("| Report | Period | Actual | Prior | Consensus | Surprise | Read |")
    out.append("|---|---|---|---|---|---|---|")
    if not recs:
        out.append("| _(no releases logged yet)_ | | | | | | |")
    for r in reversed(recs):
        freq = idx[r["report"]][1].get("freq", "monthly")
        actual = store.fmt_metrics(r.get("metrics"), freq) or ("_awaiting fetch_" if r.get("needs_fetch") else "")
        if r.get("signals"):
            actual = "; ".join(r["signals"])
        prior = store.fmt_metrics(r.get("prior"), freq)
        cons = store.fmt_metrics(r.get("consensus"), freq) if r.get("consensus") else (
            "unconfirmed" if r.get("status") == "analysed" else "")
        sur = ", ".join(f"{k} {v:+g}" for k, v in (r.get("surprise") or {}).items())
        read = r.get("read") or ("_baseline (pre-migration)_" if r.get("status") == "baseline" else "_pending analysis_")
        if r.get("source_url"):
            read += f" [source]({r['source_url']})"
        if not r.get("verified", True):
            read += " _(single-source, unconfirmed)_"
        out.append(f"| **{_cell(r['name'])}** | {r['ref']} | {_cell(actual)} | {_cell(prior)} | {_cell(cons)} | {_cell(sur)} | {_cell(read)} |")
    st = store.stance(dom["id"])
    out.append("")
    out.append(f"**Current stance:** {st.get('stance') or '_not set yet_'}"
               + (f" _(updated {st['updated_at']})_" if st.get("updated_at") else ""))
    return out


def markets_block():
    m = C.load_json(C.DATA / "markets_latest.json")
    if not m:
        return []
    out = ["", f"**Latest market levels** (as of {m['as_of']}):", "",
           "| Series | Level | 1d | 5d | Unit |", "|---|---|---|---|---|"]
    for k, s in m["series"].items():
        five = next((v for kk, v in s.items() if kk.startswith("chg_") and kk != "chg_1d"), None)
        out.append(f"| {k} | {s['level']:.2f} | {s['chg_1d']:+.0f} | {five:+.0f} | {s.get('unit', 'bp')} |")
    return out


def synthesis_block():
    files = sorted((C.DATA / "synthesis").glob("*.json"))
    out = ["## Macro Synthesis", ""]
    if not files:
        return out + ["_No synthesis yet; the Friday strategist run writes it._"]
    s = C.load_json(files[-1])
    out.append(f"**{s.get('week')}: {s.get('regime', '')}**")
    out.append("")
    out.append(s.get("executive_summary", ""))
    out.append("")
    out.append(f"**Regime watch:** {s.get('regime_watch', '')}")
    wa = "; ".join(f"{e.get('weekday', '')} {e['date']} {e.get('name', e.get('report'))}" for e in s.get("week_ahead", []))
    out.append(f"**Week ahead:** {wa}")
    out.append(f"**Swarm health:** {s.get('swarm_health', '')}")
    return out


def render(rows=6):
    now = C.now_et()
    lines = ["# Macro Monitor: Blackboard", "",
             f"_Rendered {C.fmt_et(now)} from data/. Do not edit by hand; edit data/ or rerun the tools._", ""]
    for dom in C.domains_config():
        lines += domain_section(dom, rows)
        if dom["id"] == "markets":
            lines += markets_block()
        lines.append("")
    lines += synthesis_block()
    h = store.health(now)
    lines += ["", "## Collector health", "",
              "| Domain | Last success | Age (h, weekdays) | Status |", "|---|---|---|---|"]
    for d in h["domains"]:
        status = "stale" if d["stale"] else ("errors: " + "; ".join(d["errors"]) if d["errors"] else "ok")
        lines.append(f"| {d['name']} | {d['last_success'] or 'never'} | {d['age_hours'] if d['age_hours'] is not None else ''} | {_cell(status)} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=6)
    ap.add_argument("--out", default="blackboard/BLACKBOARD.md")
    a = ap.parse_args(argv)
    md = render(a.rows)
    p = C.ROOT / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(md, encoding="utf-8")
    print(f"wrote {a.out} ({len(md)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
