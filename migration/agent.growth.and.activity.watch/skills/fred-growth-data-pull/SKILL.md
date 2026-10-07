# FRED Growth-Data Pull

Single-call FRED batch for the **Growth & Activity** collector. Replaces ~5 separate source fetches per run with one API call, and adds a recent-release calendar (filtered to this domain by default) so quiet days are cheap to confirm.

## Covers (FRED, free)
| Report | FRED series | Reported as |
|---|---|---|
| Real GDP | `A191RL1Q225SBEA` (+ `GDPC1` level) | QoQ annualised % |
| Retail Sales (headline) | `RSAFS` | level + m/m % |
| Industrial Production | `INDPRO` (+ `TCU` cap-util) | index + m/m % |
| Durable Goods | `DGORDER` (+ `NEWORDER` core capex) | level + m/m % |
| Trade Balance | `BOPGSTB` | level ($) |

## NOT covered (handle separately)
- **ISM PMI** — proprietary, delisted from FRED (2016). Read the ISM Report On Business via the browser, only on its release days (Mfg ~1st business day, Services ~3rd).
- **Chicago Fed CARTS** retail nowcast — use the "Chicago Fed CARTS — Retail Sales Nowcast" skill.
- **Market consensus** — not on FRED. Look it up (WebSearch) only when a new print lands.
- **Retail Sales control group** — not a clean FRED series; pull from the Census release when a new retail print lands.

## Credential
`FRED_API_KEY` — free from https://fredaccount.stlouisfed.org/apikeys  (value NOT included in this backup)

## Run it
```
python3 fred_growth_pull.py                       # all series + IN-DOMAIN release calendar (default)
python3 fred_growth_pull.py --since 2026-06-10     # flag series FRED refreshed since last run
python3 fred_growth_pull.py --mode calendar        # quiet-day glance: just the calendar
python3 fred_growth_pull.py --all-releases         # include EVERY release in the window (verbose, ~250/wk)
python3 fred_growth_pull.py --days 5 --series INDPRO,RSAFS
```
Execute via RunWithCredentials (FRED_API_KEY is injected as an env var). NOTE: the saved script lives in a folder with spaces, so quote the path:
`RunWithCredentials({ skillName: "FRED Growth-Data Pull", command: "python3 \"skills/FRED Growth-Data Pull/fred_growth_pull.py\" --since <last-run-date>" })`

## Output (compact JSON)
- `recent_releases`: an object — `{window_days, domain_only, total_releases_in_window, shown, releases[]}`. By default `releases[]` holds ONLY this domain's releases (GDP/Retail/IP/Durable Goods/Trade); `--all-releases` includes everything. Each release row: `{date, release, in_my_domain}`.
- `series[]`: each has `latest_period`, `latest_value`, `prior_value`, `mom_pct`, `last_updated`, `refreshed_since` (true if FRED refreshed it on/after `--since`), and a human `summary` line.
- `unconfirmed[]`: FRED ids that failed (network/parse) — mark those blackboard cells `unconfirmed`, never guess.

## How to use in a release-check run
1. Read the blackboard Growth & Activity section → note last logged period per report.
2. Run this skill with `--since <last-run-date>`. A series is a NEW print only if its `latest_period` is newer than what you last logged. (`last_updated` / `refreshed_since` moving without a new `latest_period` = a revision, not a new print — do not re-log.)
3. For a genuinely new print: look up consensus, compute surprise vs consensus, append the blackboard row, update Current stance, post the Slack alert.
4. Always refresh the heartbeat line, even on a quiet run.

## Notes / failure handling
- Never fabricates: any series that errors is returned with `status:"unconfirmed"` + the error text; reflect that in the blackboard rather than guessing.
- `requests` honours the sandbox HTTPS proxy. If missing, `pip install requests` first.
- Dedup on `latest_period`, not on `last_updated` (FRED revises history).
- Verified live 2026-06-17: all 8 series returned `ok`, calendar filtered 226 → 5 in-domain rows.
