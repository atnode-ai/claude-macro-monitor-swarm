## US Inflation Release Check

Collapses the recurring Inflation Watch data-fetch workflow into ONE deterministic script call. Instead of scraping bls.gov HTML (which returns HTTP 403 and forces an expensive browser fallback) and hand-computing MoM/YoY, this hits the free official APIs and returns compact JSON.

### Run it
```
# via RunWithCredentials (injects BEA_API_KEY / BLS_API_KEY as env vars)
python3 skills/us-inflation-release-check/inflation_check.py '<baseline-json>'
```
`baseline-json` (optional) = the last reference month already logged on the blackboard per report, e.g. `'{"CPI":"2026-05","PPI":"2026-05","PCE":"2026-04"}'`. A report's `is_new` is true only when its latest reference month is newer than the baseline — this is your dedup gate.

### Output (compact JSON)
```
{
  "any_new": true,                 // OR across all reports' is_new — the run's short-circuit signal
  "reports": {
    "CPI": { "headline": {"reference_month","index_nsa","mom_pct","yoy_pct","prior_index_nsa"},
             "core": {...}, "is_new": true },
    "PPI": { "headline": {...}, "core": {...}, "is_new": false },
    "PCE": { "headline": {...}, "core": {...}, "is_new": false }
  }
}
```
- `mom_pct` is computed from the **seasonally-adjusted** index; `yoy_pct` from the **NSA** index (standard convention).
- Missing/suppressed points ("-") are skipped; a failed source yields `{"status":"error"|"unconfirmed", "reason":...}` — the script never crashes a run.

### Sources & series IDs
- **CPI** (BLS API v2): headline `CUSR0000SA0`/`CUUR0000SA0`, core `CUSR0000SA0L1E`/`CUUR0000SA0L1E` (SA for MoM / NSA for YoY).
- **PPI** final demand (BLS API v2): headline `WPSFD49207`/`WPUFD49207`, core (less foods & energy) `WPSFD49104`/`WPUFD49104`.
- **PCE** (BEA API, NIPA table `T20804`, monthly): matched by line description — "Personal consumption expenditures" (headline) and "PCE excluding food and energy" (core). Requires `BEA_API_KEY`.

### Important: consensus is NOT here
BLS/BEA publish actuals, not the market **consensus/expected**. This script returns actual / prior / MoM / YoY deterministically. On an actual release day, fetch consensus with ONE targeted web lookup (e.g. an econ calendar), compute surprise = actual − consensus, and if a figure can't be confirmed mark it `unconfirmed` — never invent it.

### Fallbacks
- BLS API is reliable and needs no key for low volume. If it ever fails, the BEA personal-income HTML page fetches fine (unlike bls.gov); only as a last resort use the browser.
- If `BEA_API_KEY` is unset, PCE returns `unconfirmed` — configure the free key to enable it.

### Cadence
Designed to run on the twice-daily Inflation Watch schedule. On quiet runs (`any_new=false`) the caller should write only the heartbeat line and stay silent on Slack.
