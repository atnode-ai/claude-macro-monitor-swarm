# Survey Release Checker

Deterministic **release-calendar gate** plus a **best-effort fetch/parse** for the
three reports on the Sentiment & Surveys Watch beat. Purpose: most scheduled runs
land on days when nothing releases, so this lets a run decide cheaply (no network)
whether to do any work at all.

## Commands
Run with the persistent sandbox (Python 3). `requests` is only needed for `fetch`
(`pip install requests` if missing); `due`/`selftest` need no network.

- `python3 checker.py due [--now 2026-06-30T11:00]`
  → `{"as_of": "<iso ET>", "due": [...]}`. **Empty list = quiet day.** Defaults to now (ET).
- `python3 checker.py fetch --report <umich_prelim|umich_final|conf_board|ifo>`
  → compact JSON (see contract below).
- `python3 checker.py selftest` → verifies the calendar/gate math offline.

## Release calendar (US Eastern)
| report | schedule | time |
|---|---|---|
| `umich_prelim` | 2nd Friday | ~10:00 ET |
| `umich_final` | last Friday | ~10:00 ET |
| `conf_board` | last Tuesday | ~10:00 ET |
| `ifo` | last Monday | ~04:00 ET (10:00 CET) |

`due` flags a report only on its scheduled date once the release time has passed.
This matches the agent's two daily runs: the 09:00 ET run catches Ifo (pre-market);
the 11:00 ET run catches UMich/Conference Board (10:00 ET).

## fetch JSON contract
```
{"report", "release_date", "headline", "subreadings": {...},
 "source_url", "confirmed": bool, "notes"}
```
Watched sub-readings: UMich → `infl_exp_1yr`, `infl_exp_5_10yr`;
Conference Board → `jobs_plentiful_minus_hard_to_get`; Ifo → `current_assessment`, `expectations`.

**Fallback policy (important):** any field the parser cannot confidently extract is
returned `null` with `confirmed=false`. The script NEVER guesses a number. Page
layouts drift and some fields (e.g. the Conference Board labour differential,
consensus/prior) are often not on the landing page — expect `confirmed=false` there.
On a partial/failed parse, the agent confirms the missing field with a targeted
web/exa search or logs it `unconfirmed` per the beat's guardrails.

## How the agent uses it each run
1. Read the blackboard **Sentiment & Surveys** section (doc `cmq5rqdws16qq06adoiw88r03`) — dedup baseline.
2. `due` → if empty, write only the `Last checked: <ts ET> - no new release` heartbeat line (replacing the prior one) and stop.
3. For each due report: `fetch`, dedup against the blackboard, then append one row (`Report | Latest date | Actual | Consensus | Surprise | Read`) and update **Current stance**.
4. Slack `#hyper-asset-monitoring` (`C0B8B76L7NH`) **only** for a genuinely new landing; heartbeat-only runs stay silent.

The script is stateless — it does not know what is already logged. Dedup, stance,
heartbeat, and Slack remain the agent's responsibility.
