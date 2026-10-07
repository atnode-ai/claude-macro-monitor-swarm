# Macro Blackboard Digest & Health

Deterministic reader for the **Macro Monitor blackboard** (doc `cmq5rqdws16qq06adoiw88r03`). It does the mechanical work the Macro Strategist used to do by hand every run — parsing the whole doc, doing the 36-hour staleness arithmetic across seven domains, and re-emitting the blackboard as markdown for the weekly public site — so the LLM keeps only the genuine synthesis.

**No credentials.** Pure Python stdlib (`zoneinfo` for `America/New_York`).

## Why it exists (cost)
Every scheduled run otherwise reads the entire ~59 KB blackboard into context and reasons over seven `Last checked` timestamps. This script turns that into one cheap call:
- `--mode health` → ~1 KB (98% smaller than the raw doc)
- `--mode digest` (lean, default) → ~20 KB (~67% smaller), keeps all 7 Current-stance lines, what landed today, the prior synthesis lines, and the full current Macro Synthesis section ready to edit in place
- `--mode digest --full` → ~43 KB, every report row
- `--mode markdown` → deterministic blackboard→markdown (no LLM transcription)

## Input — the externalized blackboard file
1. `ReadDocument(cmq5rqdws16qq06adoiw88r03)` — the doc is large, so it **externalizes to a file**; the result hands you a file path.
2. Pass that path as `--blackboard-file`. **Do NOT read the file's full contents into context** — hand the path straight to the script (this is the whole point).

## Usage
```
# fetch the script into the workspace (no credentials needed)
FetchSkillScripts("Macro Blackboard Digest & Health")

# liveness only — cheapest call
python3 skills/macro-blackboard-digest/macro_blackboard_digest.py \
  --blackboard-file <readdoc.json> --mode health

# lean digest for the wrap (default)
python3 skills/macro-blackboard-digest/macro_blackboard_digest.py \
  --blackboard-file <readdoc.json>

# all report rows
python3 ... --blackboard-file <readdoc.json> --full

# weekly public-report blackboard page — deterministic markdown
python3 ... --blackboard-file <readdoc.json> --mode markdown > bb.md

# testing: pin "now" (ET wall clock) to simulate staleness
python3 ... --blackboard-file <readdoc.json> --mode health --now "2026-06-19 12:00"
```
(No credentials, so plain `python3` via Bash after `FetchSkillScripts` works; `RunWithCredentials` also works and is harmless.)

## Output — `health` block
```json
{
  "threshold_hours": 36,
  "all_fresh": true,
  "checked_at": "2026-06-17 17:19 ET",
  "stale_domains": [{"domain": "...", "last_checked": "...", "age_hours": 49.0}],
  "fresh_domains": [{"domain": "Inflation", "last_checked": "2026-06-17 11:03 ET", "age_hours": 6.3}],
  "alert_text": ""   // empty when all fresh; otherwise the ready-to-post HEALTH ALERT line
}
```
- The seven domains checked, in order: **Inflation, Labor, Growth & Activity, Housing, Sentiment & Surveys, Central Banks & Policy, Financial Conditions & Markets**.
- A domain is **stale** if its `Last checked … ET` timestamp is missing or older than **36h**. `alert_text` is pre-formatted for `#hyper-asset-monitoring`.
- **Health-alert rule:** post `alert_text` to Slack whenever `all_fresh` is `false` — this fires even on a quiet day, separate from macro alerts. Always write the result into the Macro Synthesis `Swarm health:` line.

## Output — `digest` (default lean)
Adds to the `health` block:
- `fresh_today`: `[{domain, report, latest_date}]` — reports whose **date column mentions today** (heuristic; verify before alerting). The fast answer to "what landed today?"
- `domains[]`: per domain — `name`, `tracks`, `current_stance` (full text — the key cross-indicator signal), `last_checked`, `age_hours`, `stale`, `reports_total` (count), and `reports` (lean: only rows released today; `--full` = all rows, narrative cells truncated ~160 chars).
- `prior_synthesis`: `{regime_watch, week_ahead, swarm_health}` extracted from the existing Macro Synthesis section, so you update those lines instead of rewriting from scratch.
- `synthesis_current`: the **full verbatim current Macro Synthesis section content**, and `synthesis_section_id`: that section's id. Edit the section in place with `UpdateDocument(operation:"replace", sectionId: synthesis_section_id, content: <your edit of synthesis_current>)` — **no second `ReadDocument`-and-parse of the blackboard file is needed**. (Historically the run re-read the section separately after the digest; these two fields eliminate that extra step.)

## Output — `markdown`
Reconstructs every publishable section (all but "How this doc works": the 7 domains + "3rd-Party Analysis" + "Macro Synthesis") as `## Section` + content, inserting a blank line before any pipe table so GitHub renders it. This is the deterministic source for the weekly public report's blackboard page (`bb-<YYYY-Www>.md`).

## Run integration
The orchestrator now runs **one** scheduled invocation, **"Weekly consolidated (Friday)" 17:00 ET** (the former Daily macro wrap, Weekly look-ahead, and Saturday public report are paused). That single run uses:
- `--mode digest` → synthesize from the 7 stances + `fresh_today`; edit the Macro Synthesis section **in place** via `synthesis_current` + `synthesis_section_id`; if `health.all_fresh` is false, post `alert_text`; always write the `Swarm health:` line.
- `--mode digest --full` → all report rows for the public business report.
- `--mode markdown` → the blackboard snapshot page, skipping any manual reconstruction.

Ad-hoc/interactive runs use `--mode digest` (or `--mode health` for a liveness-only check).

## Parsing notes / caveats
- The `Last checked` regex tolerates `_italic_` and `**bold:**` decoration and, when a section has stray "Last checked" text inside a table, locks onto the **most recent** timestamp (the real heartbeat).
- `released_today` is a string-match heuristic on the date column — a hint, not proof. Confirm against the actual release before firing a macro alert.
- Report tables are keyed by each table's own header cells, so domains with different schemas (e.g. Markets vs Inflation) parse correctly.
- `current_stance` is kept in full intentionally — it is the highest-signal field for cross-domain synthesis.
- `synthesis_section_id` falls back through `id` / `sectionId` / `_id` on the section object; if the blackboard schema ever omits all three it returns `null`, in which case fall back to the prior read-then-edit path.
