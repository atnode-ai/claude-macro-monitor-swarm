# Domain Agent — Revised Config (scheduled + heartbeat)

## Why this change

**Problem:** the 6 domain agents were built on **live mode** (`aliveConfig`, 60-min) and have written nothing to the blackboard since creation. Meanwhile the orchestrator, which uses **scheduled invocations**, fires reliably (confirmed: a successful scheduled run wrote the Macro Synthesis). So scheduled triggers are the proven mechanism here; live mode is not firing.

**Two fixes, combined below:**
1. **Switch each domain agent from live mode → scheduled invocations** (weekday release-checks), matching the orchestrator's working pattern.
2. **Add a heartbeat** — every run stamps a `Last checked` line in the agent's blackboard section even when there's no new release, so 'alive but quiet' is distinguishable from 'dead'. (The absence of this is why the outage was invisible for ~24h.)

Also ensure each agent has the tools it needs (see Tools).

## Scheduled invocations to add

Add these to every domain agent (timezone America/New_York, threadStrategy `new`, status `active`). They blanket the two main US release windows (08:30 ET and 10:00 ET):

**1) Release check — morning**
- rrule: `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0`

**2) Release check — late morning (+ daily heartbeat)**
- rrule: `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=11;BYMINUTE=0`

**Central Banks & Policy Watch only — add a third:**
**3) Decision check — afternoon**
- rrule: `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=14;BYMINUTE=30` (catches FOMC 14:00 ET; BoE/ECB land in the morning checks)

**Invocation prompt (identical for all; references the agent's own sources/section):**
```
Scheduled release check.
1. DEDUP: Read the Macro Monitor blackboard (doc cmq5rqdws16qq06adoiw88r03), YOUR domain section; note the latest logged date per report.
2. CHECK each of your official sources for a release newer than logged (use the browser if a source blocks plain fetch).
3. NEW release → capture headline + key sub-readings, consensus, prior, surprise (mark 'unconfirmed' if not verifiable); append a row to your section table; update Current stance; post a concise alert to #hyper-asset-monitoring (C0B8B76L7NH).
4. HEARTBEAT (ALWAYS, even if nothing new): set your section's 'Last checked' line to the current time (ET) with status 'logged <report>' or 'no new release'. Never post to Slack on a no-new-release run.
```

**Remove the live-mode config** (`aliveConfig`) when you add these.

## System-prompt addendum

Append this block to each domain agent's existing system prompt (it is domain-agnostic — it relies on the sources/lens already in that agent's prompt):

```
## Run model (scheduled + heartbeat)
You run on SCHEDULED invocations (not live mode). On every run:
1. Dedup: read your blackboard section first; never log the same release twice.
2. Write-on-new-release: append a row + update Current stance only when a genuinely new release has landed.
3. HEARTBEAT (every run, unconditional): update a line
   'Last checked: <YYYY-MM-DD HH:MM ET> — <status>'
   in your section, REPLACING the previous value, so liveness is visible even on quiet days.
   status = 'logged <report>' if you wrote a row this run, else 'no new release'.
4. Alert discipline: post to #hyper-asset-monitoring only on a new/material release; a heartbeat-only run stays silent.
5. Never fabricate figures (mark 'unconfirmed'); free/public sources only.
```

## Per-domain parameters

| Agent | Blackboard section | Extra schedule |
|---|---|---|
| Inflation Watch | Inflation | — |
| Labor Watch | Labor | — |
| Growth & Activity Watch | Growth & Activity | — |
| Housing Watch | Housing | — |
| Sentiment & Surveys Watch | Sentiment & Surveys | — |
| Central Banks & Policy Watch | Central Banks & Policy | + afternoon decision check (14:30 ET) |

Each agent's sources and analytical lens already live in its system prompt — no per-agent edits to those are needed; just append the addendum and add the invocations.

## Tools to enable (each agent)

Confirm these are ON for every domain agent (the saved orchestrator showed only Tables + Slack, so the domains likely also need the rest enabled):
- **Web Search / Web Fetch** — to read the release pages.
- **Browser** — fallback for sources that block plain fetch (BLS 403s, ISM SSO).
- **Document read/write** — to read & update the blackboard.
- **Slack** — to alert #hyper-asset-monitoring.
- **Live Mode: OFF** (replaced by the scheduled invocations).
- executionMode: **auto** (unattended).

## Blackboard schema change

Each domain section gains a heartbeat line. Example for the Inflation section:
```
**Tracks:** CPI, PCE, PPI · **Agent:** Inflation Watch

| Report | Latest date | Actual | Consensus | Surprise | Read |
|---|---|---|---|---|---|
| _(awaiting first release)_ | | | | | |

**Current stance:** —
**Last checked:** — (set by the agent each run)
```
The agent overwrites the **Last checked** line every run. (Optional orchestrator upgrade: in the daily wrap, flag any domain whose Last checked is >36h old as a health alert — surfaces a dead agent automatically.)

## How to apply (per agent)

Pick one path for each of the 6 agents.

**Path A — from the agent's own thread (recommended; lets the agent self-apply):**
Open a thread with the domain agent and send:
> Update your own config: (1) remove the live-mode/aliveConfig; (2) add the two scheduled invocations from the 'Domain Agent — Revised Config' doc (Central Banks adds the third); (3) append the 'Run model (scheduled + heartbeat)' system-prompt block from that doc; (4) ensure Web Search/Fetch, Browser, Document read/write, and Slack are enabled; executionMode auto. Then show me the config card to save.
The agent runs GetAgentConfig → UpdateAgentConfig on itself and returns a savable card.

**Path B — UI:**
Agent settings → turn **Live Mode off** → add the scheduled invocation(s) (rrules above) → paste the system-prompt addendum at the end of the prompt → toggle the tools on → Save.

**Verify:** after a weekday 09:00/11:00 ET run, the agent's section should show an updated **Last checked** line; its execution history should show scheduled runs.

## Path A — exact paste-in message

Paste the following into each domain agent's OWN thread. Replace `«SECTION»` (appears twice) with that agent's blackboard section, per the table at the bottom. For **Central Banks & Policy Watch only**, also add the third invocation (marked).

```
Reconfigure yourself and then show me a config card to save. Steps:

1. Call GetAgentConfig to read your current config.
2. Call UpdateAgentConfig (on yourself) with ONLY these changes; leave everything else as-is:

A) Turn OFF live mode (stop using aliveConfig). If it can't be cleared via the tool, say so and I'll switch Live Mode off in the UI.

B) Set scheduledInvocations (timezone America/New_York, threadStrategy "new", status "active"):
   • name: "Release check — morning"
     rrule: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0"
   • name: "Release check — late morning + heartbeat"
     rrule: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=11;BYMINUTE=0"
   • [CENTRAL BANKS & POLICY ONLY] name: "Decision check — afternoon"
     rrule: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=14;BYMINUTE=30"
   Use this prompt for EVERY invocation:
   "Scheduled release check. (1) DEDUP: read the Macro Monitor blackboard (doc cmq5rqdws16qq06adoiw88r03), the «SECTION» section; note the latest logged date per report. (2) CHECK each of your official sources for a release newer than logged (use the browser if a source blocks plain fetch). (3) NEW release -> capture headline + key sub-readings, consensus, prior, surprise (mark 'unconfirmed' if not verifiable); append a row to your section table; update Current stance; post a concise alert to #hyper-asset-monitoring (C0B8B76L7NH). (4) HEARTBEAT (ALWAYS, even if nothing new): set the section's 'Last checked' line to the current time (ET) with status 'logged <report>' or 'no new release'. Never post to Slack on a no-new-release run."

C) Append this block to the END of your existing system prompt (keep all current text):
   ## Run model (scheduled + heartbeat)
   You run on SCHEDULED invocations (not live mode). On every run:
   1. Dedup: read your blackboard section («SECTION») first; never log the same release twice.
   2. Write-on-new-release: append a row + update Current stance only when a genuinely new release has landed.
   3. HEARTBEAT (every run, unconditional): update a line 'Last checked: <YYYY-MM-DD HH:MM ET> - <status>' in your section, REPLACING the previous value, so liveness is visible even on quiet days. status = 'logged <report>' if you wrote a row this run, else 'no new release'.
   4. Alert discipline: post to #hyper-asset-monitoring only on a new/material release; a heartbeat-only run stays silent.
   5. Never fabricate figures (mark 'unconfirmed'); free/public sources only.

D) Ensure these tools are enabled: Web Search, Web Fetch, Browser, Document read/write, Slack. executionMode: auto.

3. Show me the AGENTCONFIG card so I can review and save.
```

**`«SECTION»` value per agent:**

| Agent (open its thread) | Replace «SECTION» with | Extra invocation |
|---|---|---|
| Inflation Watch | Inflation | — |
| Labor Watch | Labor | — |
| Growth & Activity Watch | Growth & Activity | — |
| Housing Watch | Housing | — |
| Sentiment & Surveys Watch | Sentiment & Surveys | — |
| Central Banks & Policy Watch | Central Banks & Policy | add the 14:30 ET "Decision check — afternoon" |
