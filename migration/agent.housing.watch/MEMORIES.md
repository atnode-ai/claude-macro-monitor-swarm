# Memories — A - Housing Watch (5)

## 1. FRED EXHOSLUSM495S units / dedup parsers
- id: cmr31vhpu05v508adjmp4cqjn
- category: tools_and_workflows
- importance: 3
- content: FRED series EXHOSLUSM495S (Existing Home Sales / NAR) returns values in ACTUAL UNITS (e.g. 4,170,000), not thousands — unlike PERMIT/HOUST/HSN1F which are in thousands. To display as millions SAAR, multiply by 0.000001 (not 0.001). Macro-collector dedup parsers must strip markdown bold/italic (** and _) from the date column before tokenizing, or rows like '**May 2026 (rel...)**' fail to match and re-trigger as new. Central-banks/sentiment dedup parsers must also handle 'Mon DD, YYYY' and 'Mon DD–DD, YYYY' date ranges (not just ISO YYYY-MM-DD), or a logged decision like 'Jun 17–18, 2026' parses to None and gets falsely re-logged.
- whenToUse: When fetching FRED housing series or writing/debugging blackboard dedup parsers for macro collectors.

## 2. Python 3.9 sandbox / PEP 604 hints
- id: cmr31vtvr060306adssrfmafd
- category: tools_and_workflows
- importance: 4
- content: The agent sandbox runs Python 3.9 (verified 3.9.25). PEP 604 union syntax (e.g. `def f() -> float | None:`, `x: dict | None`) raises `TypeError: unsupported operand type(s) for |` at module-import time on 3.9 unless `from __future__ import annotations` is the FIRST import (before any other import, and before module-level annotated assignments). When writing Python scripts that use `X | Y` type hints and will run in-sandbox (or be tested via RunWithCredentials), add `from __future__ import annotations` at the top of every file. Note: a `sed` insert keyed on `#!/usr/bin/env python3` silently skips files with no shebang — insert before the first `import` instead.
- whenToUse: When writing or running Python scripts in the sandbox that use modern X|Y type-hint syntax.

## 3. No public Hyperagent document API; GitHub-backed blackboard for external scripts
- id: cmr3vhusz0k6i07adimtaqfdf
- category: tools_and_workflows
- importance: 3
- content: Hyperagent does NOT expose a public REST document API equivalent to the in-sandbox ReadDocument/UpdateDocument tools. For external/standalone scripts (e.g. deterministic cron jobs) that need to read or persist macro-swarm blackboard state, use a GitHub-backed file instead: repo atnode-ai/macro-monitor-swarm (branch main), file blackboard/blackboard.md holding the full 7-domain blackboard seeded from the live Hyperagent doc cmq5rqdws16qq06adoiw88r03 (seed commit 9e12764, 2026-06-30). Read/write via the GitHub Contents API (GET for content+blob SHA, PUT with base64 content + SHA, 409-conflict retry) — one read + one write per run. The existing 'GitHub Push (PAT) — atnode-ai' skill's GITHUB_TOKEN works if scoped to macro-monitor-swarm. Repo layout: blackboard/blackboard.md + <agent>/<agent>_cron.py (e.g. housing_watch/housing_watch_cron.py, market_watch/market_watch_cron.py, inflation_watch/inflation_cron.py).
- whenToUse: When building external/standalone scripts that need to read or persist macro-swarm blackboard state, or when tempted to assume a public Hyperagent document REST API exists.

## 4. Economic-release consensus sources
- id: cmr3vibnd0jsg07adjgz1pev5
- category: tools_and_workflows
- importance: 3
- content: For economic-release consensus/forecast estimates (which FRED/BLS/BEA do NOT carry), a free structured option is Parse.bot's Investing.com Economic Calendar API: GET .../uk-investing-com-api/get_calendar with start_date/end_date (YYYY-MM-DD), importance (low/medium/high), country_ids (US = 5); returns per-event actual/forecast/previous. Free tier = 100 credits/mo, 5 req/min — ample for ~3-5 release days/month. Match the right event by partial event_name string (e.g. 'CPI m/m', 'Building Permits', 'New Home Sales', 'Non-Farm Employment Change'). Trading Economics API also exposes a 'housing' group calendar filter (api.tradingeconomics.com/calendar/country/united%20states/group/housing) but has no ongoing free tier (~$75-99/mo). For minimal change, ExaAnswer on active release days (~$0.01/lookup) gives consensus without a paid data feed.
- whenToUse: When needing economic-release consensus/forecast estimates that FRED/BLS/BEA do not carry — e.g. wiring consensus into a macro collector when a new print lands.

## 5. Housing Release Check any_new false-positive caveat
- id: cmr3vkscf0jho06adthbzw10p
- category: tools_and_workflows
- importance: 2
- content: Housing Release Check (FRED) skill dedup caveat: the script can return last_logged:null and any_new:true even when all four reports are already logged on the blackboard, when its row-parser fails to extract the last-logged reference month from the Housing section markdown. The reference-month dedup is AUTHORITATIVE — before treating any_new=true as a real new release, manually compare each series' latest_ref from FRED against the reference month already in the blackboard Housing rows. If every FRED latest_ref matches an existing logged row, treat the run as no-new-release: update only the 'Last checked' heartbeat and post NO Slack. Do not re-log a release whose reference month is already present.
- whenToUse: Use this memory when troubleshooting or executing the Housing Release Check (FRED) skill, specifically when the script flags a new release (any_new:true) but returns a null last_logged value, to prevent duplicate blackboard entries and redundant Slack alerts.
