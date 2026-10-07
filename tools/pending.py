"""Work queue for the macro-release routine.

    python -m tools.pending list              # compact queue
    python -m tools.pending brief <report> <ref>
                                              # context packet for one domain-analyst
    python -m tools.pending apply <inbox.json>
                                              # validate analyst output, merge, compute surprise,
                                              # update stance, dequeue; prints the alert decision
    python -m tools.pending alerts            # alert texts for everything applied this run

The analyst only ever writes data/inbox/<report>-<ref>.json. This module is
the single writer of release records after the collector, so a malformed
LLM answer is rejected here instead of corrupting the blackboard.
"""
import json
import sys
from pathlib import Path

from collectors import common as C
from tools import alert_gate, store

PENDING = C.DATA / "pending.json"
OUTBOX = C.DATA / "outbox.json"
MAX_READ = 320
MAX_STANCE = 700


def _pending():
    return C.load_json(PENDING, {"items": []})


def _find(report, ref):
    for it in _pending()["items"]:
        if it["report"] == report and it["ref"] == ref:
            return it
    return None


def cmd_list():
    items = _pending()["items"]
    print(json.dumps({"count": len(items), "items": [
        {k: it[k] for k in ("domain", "report", "ref", "tier", "needs_fetch")} for it in items]}, indent=2))


def cmd_brief(report, ref):
    it = _find(report, ref)
    if not it:
        raise SystemExit(f"{report} {ref} is not pending")
    rec = C.load_json(C.ROOT / it["path"])
    dom, rep = C.report_index()[report]
    history = [r for r in store.releases(dom["id"], report) if r["ref"] < ref and r.get("status") != "baseline"][-3:]
    packet = {
        "task": "analyse_release",
        "inbox_file": f"data/inbox/{report}-{ref}.json",
        "release": {k: rec.get(k) for k in ("domain", "report", "name", "ref", "tier", "metrics", "prior",
                                            "source_url", "needs_fetch", "signals", "fedwatch_check_needed",
                                            "due_date")},
        "report_type": rep["type"],
        "metric_keys": list((rec.get("metrics") or {}).keys()) or rep.get("fields", []),
        "web_fields": rep.get("fields", []) if rep["type"] in ("web", "decision") else [],
        "history": [{"ref": h["ref"], "metrics": h.get("metrics"), "consensus": h.get("consensus"),
                     "read": h.get("read")} for h in history],
        "current_stance": store.stance(dom["id"]).get("stance"),
        "lens_file": dom["lens"],
    }
    print(json.dumps(packet, indent=2, ensure_ascii=False))


def _validate(out, rec, rep):
    errs = []
    metric_keys = set((rec.get("metrics") or {}).keys())
    web = rep["type"] == "web"
    if web:
        m = out.get("metrics") or {}
        if not isinstance(m, dict):
            errs.append("metrics must be an object")
        else:
            bad = [k for k, v in m.items() if v is not None and not isinstance(v, (int, float))]
            if bad:
                errs.append(f"non-numeric metrics: {bad}")
            metric_keys = set(m.keys())
    elif out.get("metrics"):
        errs.append("metrics are collector-owned for API reports; do not send them")
    cons = out.get("consensus")
    if cons is not None:
        if not isinstance(cons, dict):
            errs.append("consensus must be an object or null")
        else:
            extra = set(cons) - metric_keys
            if extra:
                errs.append(f"consensus keys not in metrics: {sorted(extra)}")
            bad = [k for k, v in cons.items() if not isinstance(v, (int, float))]
            if bad:
                errs.append(f"non-numeric consensus: {bad}")
            if cons and not out.get("consensus_source"):
                errs.append("consensus_source is required when consensus is given")
    if not out.get("read") or len(out["read"]) > MAX_READ:
        errs.append(f"read is required and must be <= {MAX_READ} chars")
    if out.get("stance") and len(out["stance"]) > MAX_STANCE:
        errs.append(f"stance must be <= {MAX_STANCE} chars")
    return errs


def cmd_apply(path):
    out = C.load_json(path)
    report, ref = out.get("report"), out.get("ref")
    it = _find(report, ref)
    if not it:
        raise SystemExit(f"{report} {ref} is not pending")
    rec_path = C.ROOT / it["path"]
    rec = C.load_json(rec_path)
    dom, rep = C.report_index()[report]
    errs = _validate(out, rec, rep)
    if errs:
        print(json.dumps({"ok": False, "errors": errs}, indent=2))
        return 1
    now = C.now_et()
    if rep["type"] == "web":
        rec["metrics"] = {k: v for k, v in (out.get("metrics") or {}).items() if v is not None}
        rec["verified"] = len(set(out.get("sources") or [])) >= 2
        if out.get("ref_actual") and out["ref_actual"] != ref:
            rec["ref_note"] = f"analyst reports reference period {out['ref_actual']}"
    rec["fields"] = out.get("fields") or rec.get("fields")
    rec["consensus"] = out.get("consensus")
    rec["consensus_source"] = out.get("consensus_source")
    rec["sources"] = out.get("sources") or []
    rec["read"] = out["read"].strip()
    gate = alert_gate.evaluate(rec)
    rec["surprise"] = gate["surprise"]
    rec["alert"] = {"alert": gate["alert"], "material": gate["material"], "reasons": gate["reasons"]}
    rec["status"] = "analysed"
    rec["analysed_at"] = C.fmt_et(now)
    C.save_json(rec_path, rec)
    if out.get("stance"):
        C.save_json(C.DATA / "stances" / f"{dom['id']}.json",
                    {"domain": dom["id"], "stance": out["stance"].strip(), "updated_at": C.fmt_et(now),
                     "from": f"{report} {ref}"})
    p = _pending()
    p["items"] = [i for i in p["items"] if not (i["report"] == report and i["ref"] == ref)]
    C.save_json(PENDING, p)
    ob = C.load_json(OUTBOX, {"items": []})
    ob["items"].append({"report": report, "ref": ref, "path": it["path"], "alert": gate["alert"]})
    C.save_json(OUTBOX, ob)
    Path(path).unlink(missing_ok=True)
    print(json.dumps({"ok": True, "report": report, "ref": ref, **gate}, indent=2))
    return 0


def alert_text(rec):
    _, rep = C.report_index()[rec["report"]]
    freq = rep.get("freq", "monthly")
    head = f"*{rec['name']}* ({rec['ref']})"
    lines = [f"{head}: {store.fmt_metrics(rec.get('metrics'), freq, limit=4)}"]
    if rec.get("consensus"):
        cons = "; ".join(store.fmt_metric(k, v, freq) for k, v in rec["consensus"].items())
        sur = ", ".join(f"{k} {v:+g}" for k, v in (rec.get("surprise") or {}).items())
        lines.append(f"vs consensus {cons} -> surprise {sur}")
    elif rec.get("signals"):
        lines.append("Signals: " + "; ".join(rec["signals"]))
    else:
        lines.append("Consensus unconfirmed.")
    if rec.get("read"):
        lines.append(rec["read"])
    if rec.get("source_url"):
        lines.append(f"<{rec['source_url']}|source>")
    if not rec.get("verified", True):
        lines.append("_Figures from a single web source: unconfirmed._")
    return "\n".join(lines)


def cmd_alerts(clear=False):
    ob = C.load_json(OUTBOX, {"items": []})
    texts = []
    for it in ob["items"]:
        if it["alert"]:
            texts.append(alert_text(C.load_json(C.ROOT / it["path"])))
    dep = C.deployment()
    print(json.dumps({"channel_id": dep["slack"]["channel_id"], "messages": texts,
                      "applied": len(ob["items"])}, indent=2, ensure_ascii=False))
    if clear:
        C.save_json(OUTBOX, {"items": []})


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "list":
        cmd_list()
    elif cmd == "brief":
        cmd_brief(argv[1], argv[2])
    elif cmd == "apply":
        return cmd_apply(argv[1])
    elif cmd == "alerts":
        cmd_alerts(clear="--clear" in argv)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
