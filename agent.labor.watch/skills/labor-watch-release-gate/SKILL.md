# Labor Watch — Release Gate

A deterministic, dependency-free release-calendar gate for the Labor domain of the macro-monitoring swarm. Its job is to answer one question cheaply: **"Could any of my five reports have a new release worth checking today?"** On most run-days the answer is *no*, and the agent should then write its heartbeat and stop — without firing the expensive operations (web fetches and especially the browser, which BLS pages force because they 403 plain fetches).

## Why this exists (cost control)
The agent runs twice every weekday. Without a gate it checks all five sources every run and falls back to the browser for the two BLS reports (NFP, JOLTS) even when no release is calendar-possible. The gate collapses that multi-step check into one tiny stdlib call. On a "nothing due" day the entire run becomes: gate → write heartbeat → stop.

## Reports & rules (all US Eastern; UK is ET-converted)
| key | report | rule | fetch method |
|-----|--------|------|--------------|
| `claims` | Initial Jobless Claims (DOL ETA) | weekly, every **Thursday** 08:30 ET | script-fetchable — https://www.dol.gov/ui/data.pdf |
| `nfp` | Non-Farm Payrolls / Employment Situation (BLS) | **1st Friday** of month 08:30 ET | **BROWSER** (BLS 403s) — https://www.bls.gov/news.release/empsit.htm |
| `adp` | ADP National Employment Report | **Wednesday before NFP** (~08:15 ET) | script-fetchable — https://adpemploymentreport.com/ |
| `jolts` | JOLTS (BLS) | irregular, ~**first 12 days** of month, 10:00 ET (date drifts) | **BROWSER** (BLS 403s) — https://www.bls.gov/news.release/jolts.htm |
| `uk` | UK Labour Market (ONS) | ~**3rd Tuesday** of month, 07:00 BST (~02:00–03:00 ET) | script-fetchable — ONS bulletin /uklabourmarket/latest |

`claims`, `nfp`, `adp`, `uk` have firm weekday anchors. `jolts` dates drift, so it uses a conservative first-12-weekday-days window plus same-month dedup. Erring toward "check" only inside each window, combined with the dedup baseline, eliminates the vast majority of wasteful runs without risking a missed print.

## Usage
```bash
python3 gate.py                       # today = now (US Eastern)
python3 gate.py --today 2026-06-18    # override the date (testing)
python3 gate.py --last '{"claims":"2026-06-11","nfp":"2026-06-05","adp":"2026-06-03","jolts":"2026-06-03","uk":"2026-06-16"}'
```
`--last` is a JSON object mapping each report key to the **release date you last logged** for it (read these off the blackboard Labor section). **Always pass `--last`** so the 11:00 ET run dedups against the 09:00 ET run; without it, anchor reports flag "due" only on the exact release day.

## Output (JSON on stdout)
- `due`: list of report keys to check this run (often empty).
- `skip_all`: true when `due` is empty → quiet run.
- `heartbeat_line`: ready-to-write line, e.g. `Last checked: 2026-06-18 09:01 ET - no new release` or `... - logged claims`. Write this verbatim to the Labor section every run (replacing the previous value).
- `action`: a human-readable instruction for this run.
- `now_et`, `today`, `weekday`: convenience fields.
- `reports`: per-report `{due, reason, anchor_release, source_url, fetch}` for transparency/debugging.

## How the agent should use it (gate-first run pattern)
1. Read the blackboard Labor section → note last-logged release date per report (dedup baseline).
2. Run the gate with `--last`.
3. If `skip_all` → write `heartbeat_line` to the Labor section, emit a one-line thread summary, **stop**. No fetch / no browser / no Slack.
4. Else → fetch ONLY the `due` sources (browser only for `nfp`/`jolts`); capture headline + key sub-readings, consensus, prior, surprise (mark `unconfirmed` if not verifiable); append one row per release; update Current stance; post a concise Slack alert to #hyper-asset-monitoring (C0B8B76L7NH); write `heartbeat_line` (status `logged <reports>`).

## Maintenance notes
- stdlib only (datetime, zoneinfo with a manual US-Eastern DST fallback) — runs with no `pip install`.
- The windows are intentionally conservative. If BLS shifts NFP to a 2nd Friday in a given month (rare), the `--last` dedup still forces a check because the logged date stays behind the new release. JOLTS/UK exact dates can be tightened by consulting the official annual schedules if false-positive checks ever become costly.

## `--last` argument contract (get this right or the gate misfires)

- `--last` must be a **single JSON object** mapping report key -> `YYYY-MM-DD`. A colon-delimited form like `--last "claims:2026-08-01"` is rejected with: `ERROR: --last must be a JSON object mapping report->YYYY-MM-DD`.
  Correct: `python3 gate.py --last '{"claims":"2026-08-08","nfp":"2026-08-07","adp":"2026-08-05","jolts":"2026-08-04","uk_labour":"2026-07-21"}'`
- Report keys accepted: `claims`, `nfp`, `adp`, `jolts`, plus the UK key. Note the gate returns UK under `reports.uk` even when passed as `uk_labour` — read the returned key names rather than assuming symmetry.
- **Pass the RELEASE date, not the reference-month date.** The blackboard rows show both (e.g. `Jul 2026 (rel. Aug 7)`); the gate compares against its release-date anchors. Passing a reference-month end (e.g. `nfp: 2026-07-31` for the Jul print released Aug 7) makes the gate report `due: true` for a report that is already logged — a false positive that can lead to an unnecessary browser fetch or a duplicate row.
- After reading the gate result, always re-check each `due` report against the blackboard's own logged release dates and its `Next:` line in Current stance; the last-logged dedup remains authoritative over the gate.

## Fetching notes per source

### `uk` — ONS Labour market overview (/uklabourmarket/latest)
The bulletin is script/ExaContents-fetchable, but the default `summary: true, highlights: true` mode returns highlight fragments with the digits elided (e.g. 'decreasing by ...0 (0...%)'), so headline figures cannot be read from it. Recipe that works in one pass:
1. `ExaContents` with `text: true` (summary/highlights off) on the /latest URL — this yields unemployment rate, employment rate, economic inactivity, payrolled-employee m/m + y/y and the Claimant Count level.
2. The full text is truncated before the Average Weekly Earnings section, and ONS never publishes consensus. Do ONE `ExaSearch` (category `news`, `startPublishedDate` = release day) for 'UK labour market <month year> ONS average weekly earnings unemployment vacancies' — BBC / Anadolu / Irish News / FXStreet reliably carry regular AWE, total AWE (incl. bonuses), the public vs private sector split, the claimant-count rate and the market forecast for the unemployment rate (the consensus figure to log).

Capture per UK release: unemployment rate (+ q/q, y/y), employment rate, inactivity, regular AWE and total AWE y/y, private- vs public-sector regular pay (the BoE-relevant split), claimant count level + rate, vacancies level + q/q, payrolled employees m/m and y/y (both the confirmed month and the flash month). Note that the ONS 'next release' date on the bulletin gives the exact next UK anchor date — use it to sanity-check the gate's 3rd-Tuesday assumption.
