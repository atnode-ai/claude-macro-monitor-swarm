"""Deterministic surprise + alert decision for one release record.

surprise = actual - consensus, per metric that has a consensus. A release
alerts when its tier is in always_alert_tiers, when a policy rate changed,
when a market snapshot fired, or when any surprise reaches its threshold.
"""
import json
import sys

from collectors import common as C


def evaluate(rec, thr=None):
    thr = thr or C.thresholds()
    reasons = []
    surprise = {}
    cons = rec.get("consensus") or {}
    for k, c in cons.items():
        a = (rec.get("metrics") or {}).get(k)
        if isinstance(a, (int, float)) and isinstance(c, (int, float)):
            # Official prints are rounded (CPI 0.29 -> "0.3%"); compare at the
            # consensus precision so a 0.3 vs 0.2 print counts as +0.1.
            nd = max(1, len(repr(float(c)).split(".")[1].rstrip("0")))
            surprise[k] = round(round(a, nd) - c, nd)
    limits = thr["surprise"].get(rec["report"], {})
    material = False
    for k, lim in limits.items():
        if k in surprise and abs(surprise[k]) >= lim - 1e-9:
            material = True
            reasons.append(f"{k} surprise {surprise[k]:+g} (threshold {lim:g})")
    if rec.get("tier") in thr["always_alert_tiers"]:
        reasons.append(f"tier-{rec['tier']} release")
    chg = (rec.get("metrics") or {}).get("rate.change_bp")
    if chg:
        material = True
        reasons.append(f"policy rate moved {chg:+.0f}bp")
    if rec.get("signals"):
        material = True
        reasons.append("market move: " + "; ".join(rec["signals"]))
    alert = material or rec.get("tier") in thr["always_alert_tiers"]
    if not cons and not rec.get("signals") and rec.get("type") != "decision":
        reasons.append("no consensus available; surprise not assessed")
    return {"surprise": surprise or None, "material": material, "alert": alert, "reasons": reasons}


if __name__ == "__main__":
    rec = C.load_json(sys.argv[1])
    print(json.dumps(evaluate(rec), indent=2))
