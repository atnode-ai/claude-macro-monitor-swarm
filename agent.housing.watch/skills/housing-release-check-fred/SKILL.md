# Housing Release Check (FRED)

Collapses Housing Watch's recurring multi-source web research into **one deterministic call**. On most scheduled runs nothing new has landed, so the common path must be cheap: this script returns a small JSON blob (never HTML/PDF), and on a no-new-release run the agent just refreshes the heartbeat and stops.

## Credential
- `FRED_API_KEY` (required) — free key from https://fred.stlouisfed.org/docs/api/api_key.html

## Run it
```
RunWithCredentials(skillName="Housing Release Check (FRED)",
  command="python3 skills/housing-release-check/housing_release_check.py --blackboard-file <PATH>")
```
`<PATH>` = the file path `ReadDocument` returns when the blackboard (doc `cmq5rqdws16qq06adoiw88r03`) is too large to inline (it reliably externalizes). The script reads ONLY the Housing section from that file — you never pull the other domains' sections into context.

## Scheduled-run flow (cheap path first)
1. `ReadDocument` the blackboard → it externalizes → note the returned file path. Do **not** read the full file into context.
2. Run this script with `--blackboard-file <PATH>`.
3. Inspect `any_new`:
   - **`any_new: false`** → update the Housing `Last checked` heartbeat line to `<now ET> - no new release`, emit ~2 lines, stop. **No Slack.**
   - **`any_new: true`** → for each report in `new_releases`: the actual/prior/MoM/YoY/single-family are already in the JSON. Do ONE targeted web lookup for **consensus** (FRED has no consensus) and, if useful, fetch the NAR/Census page for extra color (median price, inventory months). Append the row `Report | Latest date | Actual | Consensus | Surprise | Read`, update Current stance, and post a concise `#hyper-asset-monitoring` alert.

## Output schema (stdout JSON)
- `fred_ok` — false if `FRED_API_KEY` is unset (script still prints the blackboard `last_logged` baseline).
- `reports[name]` — `series, latest_ref (YYYY-MM), display (e.g. "1.413M SAAR"), raw, mom_pct, yoy_pct, prior_ref, prior_raw, single_family{display,raw,mom_pct}, last_logged, new_release`.
- `new_releases` — report names whose `latest_ref` is newer than the blackboard's last logged month.
- `any_new` — bool (null if `--blackboard-file` omitted).
- `context` — `mortgage_30yr`, `new_home_months_supply`.
- `last_logged`, `notes`.

## Series tracked
Building Permits `PERMIT` (SF `PERMIT1`) · Housing Starts `HOUST` (SF `HOUST1F`) · New Home Sales `HSN1F` · Existing Home Sales `EXHOSLUSM495S` (NAR data, carried by FRED) · context: `MORTGAGE30US`, `MSACSR`.

## Notes / gotchas
- **Use FRED, not Census EITS.** The Census EITS API (`api.census.gov/.../timeseries/eits`) 302-redirects to an empty body from the sandbox — unreliable. NAR existing-home-sales is available via FRED as `EXHOSLUSM495S`.
- **Units are scale-safe.** Counts normalize to "M SAAR" off the FRED `units` string, so existing-home-sales is correct whether FRED reports thousands or absolute units.
- **Dedup is reference-month based**, independent of any release-calendar guess — the authoritative no-dupe guard.
- **Consensus is not in FRED** — look it up only on a genuine new release (≤3×/month).
- Uses Python stdlib `urllib` (honors the sandbox `HTTPS_PROXY`); no pip install needed.
- NAR/Census release PAGES are for color only, fetched on-release — not on the cheap path.

KNOWN BUG (observed 2026-07-01): the blackboard-section dedup parser can return last_logged:null / new_release:true even when the May 2026 rows ARE already logged — a false positive. Cause: the Housing rows use bolded markdown cell markup (e.g. **Existing Home Sales** | **May 2026 (rel. Jun 9)** | ...) and the parser's regex only matched plain (non-bold) table rows. FIX: make the last-logged reference-month extraction tolerant of both plain and bold ('**...**') table-row formats when slicing the Housing section. Until patched, always visually confirm against the blackboard Housing rows before treating any_new:true as a genuine new release — the reference-month rows in the doc are authoritative.
