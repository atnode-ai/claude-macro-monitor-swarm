"""Read helpers over data/ plus display formatting. Shared by every tool."""
from datetime import timedelta

from collectors import common as C

UNIT_HINTS = (("_bn", " $bn"), ("_k", "k"), ("_m", "m"), ("rate", "%"), ("_pct", "%"))


def releases(domain=None, report=None):
    """All release records, oldest first by (report, ref)."""
    base = C.DATA / "releases"
    out = []
    if not base.exists():
        return out
    for p in sorted(base.glob("*/*/*.json")):
        d, r = p.parts[-3], p.parts[-2]
        if domain and d != domain:
            continue
        if report and r != report:
            continue
        rec = C.load_json(p)
        rec["_path"] = str(p.relative_to(C.ROOT))
        out.append(rec)
    return out


def latest_per_report(domain):
    by = {}
    for rec in releases(domain):
        if rec.get("status") == "baseline" and rec["report"] in by:
            continue
        cur = by.get(rec["report"])
        if cur is None or rec["ref"] >= cur["ref"]:
            by[rec["report"]] = rec
    return by


def stance(domain):
    return C.load_json(C.DATA / "stances" / f"{domain}.json", {"stance": None, "updated_at": None})


def detected_between(start_dt, end_dt):
    out = []
    for rec in releases():
        if rec.get("status") == "baseline":
            continue
        t = C.parse_et(rec.get("detected_at"))
        if t and start_dt <= t <= end_dt:
            out.append(rec)
    return out


def health(now, stale_hours=None):
    stale_hours = stale_hours or C.thresholds()["health"]["stale_hours"]
    state = C.load_json(C.DATA / "state.json", {"reports": {}, "collectors": {}})
    doms, stale = [], []
    # weekends don't count: on Monday morning Friday's run is still "fresh"
    for d in C.domains_config():
        cs = state["collectors"].get(d["id"], {})
        last = C.parse_et(cs.get("last_success"))
        age = None
        if last:
            age = (now - last).total_seconds() / 3600
            wk = sum(1 for i in range((now.date() - last.date()).days) if (last.date() + timedelta(days=i + 1)).weekday() >= 5)
            age -= 24 * wk
        is_stale = age is None or age > stale_hours
        errs = [f"{r['id']}: {state['reports'].get(r['id'], {}).get('error')}" for r in d["reports"]
                if state["reports"].get(r["id"], {}).get("error")]
        rec = {"domain": d["id"], "name": d["name"], "last_success": cs.get("last_success"),
               "age_hours": None if age is None else round(age, 1), "stale": is_stale, "errors": errs}
        doms.append(rec)
        if is_stale or errs:
            stale.append(rec)
    alert = ""
    if stale:
        parts = []
        for s in stale:
            why = "stale" if s["stale"] else "errors"
            parts.append(f"{s['name']} ({why}; last ok {s['last_success'] or 'never'}{'; ' + '; '.join(s['errors']) if s['errors'] else ''})")
        alert = "HEALTH ALERT: " + " | ".join(parts) + ". The macro picture is blind here until these collectors recover."
    return {"all_ok": not stale, "domains": doms, "alert_text": alert, "checked_at": C.fmt_et(now)}


def _num(v, nd=1, sign=False):
    if v is None:
        return "n/a"
    if abs(v) >= 1000:
        s = f"{v:,.0f}"
        return ("+" + s) if sign and v > 0 else s
    s = f"{v:+.{nd}f}" if sign else f"{v:.{nd}f}"
    return s


def fmt_metric(key, v, freq="monthly"):
    part, _, t = key.rpartition(".") if "." in key else (key, "", "level")
    unit = next((u for hint, u in UNIT_HINTS if part.endswith(hint) or hint == "rate" and "rate" in part), "")
    label = part
    for hint in ("_bn", "_k", "_m", "_pct"):
        if label.endswith(hint):
            label = label[: -len(hint)]
    label = label.replace("_", " ")
    period = {"monthly": "m/m", "quarterly": "q/q", "weekly": "w/w"}.get(freq, "chg")
    if t == "chg_pct":
        return f"{label} {_num(v, 1, True)}% {period}"
    if t == "yoy_pct":
        return f"{label} {_num(v, 1)}% y/y"
    if t == "change_bp":
        return f"{label} {_num(v, 0, True)}bp"
    if t == "diff":
        u = "pp" if unit == "%" else unit
        nd = 0 if unit in ("k",) else (2 if abs(v or 0) < 1 else 1)
        return f"{label} {_num(v, nd, True)}{u} chg"
    nd = 0 if unit == "k" and abs(v or 0) >= 100 else (2 if unit == "%" or abs(v or 0) < 10 else 1)
    return f"{label} {_num(v, nd)}{unit}"


def fmt_metrics(metrics, freq="monthly", limit=None):
    items = [fmt_metric(k, v, freq) for k, v in (metrics or {}).items() if v is not None]
    return "; ".join(items[:limit] if limit else items)
