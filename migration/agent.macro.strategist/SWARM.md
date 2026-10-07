# Macro Monitoring Swarm — Index

Backup of the macro-monitoring swarm (project: Substack.extractor). One `agent.<slug>` folder per agent; each holds `SYSTEM_PROMPT.md`, `agent_config.json`, and `backup_manifest.json`. This orchestrator folder also holds the shared snapshots (`PROJECT.md`, `ARCHITECTURE.md`, `BLACKBOARD.md`, `DOMAIN_AGENT_REVISED_CONFIG.md`, `MEMORIES.md`), the orchestrator's attached-skill snapshots under `skills/`, and this index.

Last backup: 2026-10-07.

> **Note on the orchestrator folder name.** The orchestrator's display name is now **"A - Macro Strategist"** (a dashboard-grouping "A - " prefix was added after the original backup). The backup folder is deliberately kept as `agent.macro.strategist` for continuity — do NOT fork a new `agent.a.-.macro.strategist` folder. The display-name prefix is cosmetic; all coordination is keyed on section names / document IDs / channel IDs, not the display name.

## Topology

3-tier design — domains are agents, reports are scheduled triggers, one orchestrator synthesizes. Agents coordinate through a shared blackboard doc (no direct agent-to-agent messaging). Alerts route to Slack `#hyper-asset-monitoring` (channel `C0B8B76L7NH`). The swarm now has **7 domain collectors** (a 7th, Market Watch / Financial Conditions & Markets, was added after the original six) + the orchestrator.

Domain collectors run on **scheduled invocations + a heartbeat** (not live mode): weekday release-checks that stamp a `Last checked` line in their blackboard section every run, so a dead collector is visible. See `DOMAIN_AGENT_REVISED_CONFIG.md`.

## Agents

| Agent (display name) | Folder | Role | Sources / beat |
|---|---|---|---|
| A - Macro Strategist | agent.macro.strategist | Orchestrator: reads blackboard, applies cross-indicator logic, owns Slack alerts + domain health check; ONE active schedule — "Weekly consolidated (Friday)" 17:00 ET | all seven domains |
| A - Inflation Watch | agent.inflation.watch | Domain collector (scheduled + heartbeat) | CPI, PPI, PCE |
| A - Labor Watch | agent.labor.watch | Domain collector (scheduled + heartbeat) | NFP, ADP, JOLTS, Jobless Claims, UK Labour Market |
| A - Growth & Activity Watch | agent.growth.and.activity.watch | Domain collector (scheduled + heartbeat) | GDP, Retail Sales (+ Chicago Fed CARTS nowcast), ISM PMI, Industrial Production, Durable Goods, Trade Balance |
| A - Housing Watch | agent.housing.watch | Domain collector (scheduled + heartbeat) | Building Permits & Housing Starts, Existing & New Home Sales |
| A - Sentiment & Surveys Watch | agent.sentiment.and.surveys.watch | Domain collector (scheduled + heartbeat) | UMich Sentiment, Conference Board Confidence, German Ifo |
| A - Central Banks & Policy Watch | agent.central.banks.and.policy.watch | Domain collector (scheduled + heartbeat; +14:30 ET decision check) | FOMC (decisions/minutes/Beige Book/speeches), BoE, ECB, Eurozone CPI & GDP flash |
| A - Market Watch | agent.market.watch | Domain collector (scheduled; 09:00 + 16:30 ET) | Treasury yield curve (10y-2y, 10y-3m), HY/IG credit spreads, Chicago Fed NFCI/ANFCI, SLOOS, market-implied Fed path (futures), 5y5y/10y breakevens; MOVE/VIX/DXY context |

Orchestrator agent id: `cmq667l5l00jp07adt010uj06`. Other agents' live configs are backed up from their own threads (GetAgentConfig only reads the agent whose thread it runs in).

## Related project documents (snapshotted in this folder)

- `ARCHITECTURE.md` — "Macro Monitoring Swarm — Architecture" (doc id `cmq5rkc1815wk06advgj6mndl`). Static design reference; now covers all 7 domains.
- `BLACKBOARD.md` — "Macro Monitor — Blackboard" (doc id `cmq5rqdws16qq06adoiw88r03`). Live runtime state; point-in-time snapshot (deterministically rendered by the Macro Blackboard Digest skill, `--mode markdown`) — the in-platform doc is the source of truth and will diverge as agents write.
- `PROJECT.md` — the Substack.extractor project document (doc id `cmq5nbodk14p808ad869iobt1`).
- `DOMAIN_AGENT_REVISED_CONFIG.md` — "Domain Agent — Revised Config (scheduled + heartbeat)" (doc id `cmq75s3ob02to07ad95xo18ke`). The scheduled-invocation + heartbeat migration spec, attached to the orchestrator as a context file.
- `MEMORIES.md` — snapshot of the 15 memories attached to the orchestrator.

## Orchestrator skills (snapshotted under skills/)

- `skills/agent-state-backup/` — Agent State Backup (`render_project_doc.py`). This backup convention.
- `skills/github-push-pat/` — GitHub Push (PAT) for cloudburostaff (`github_push.py`).
- `skills/github-push-pat-atnode-ai/` — GitHub Push (PAT) for the atnode-ai org (`github_push.py`).
- `skills/macro-blackboard-digest/` — Macro Blackboard Digest & Health (`macro_blackboard_digest.py`). Step 1 of every orchestrator run.

## Recovery notes

- `agent_config.json` is the sanitized live-config snapshot (name, description, icon, executionMode, delegation, modelSettings, learning, tools enabled, integrations, skills, memories, contextFiles, scheduledInvocations). It contains no secrets. Model: `claude-opus-4-8`; default subagent model: sonnet.
- Slack delivery uses the connected workspace Slack integration to channel `C0B8B76L7NH`; no token is stored here.
- GitHub access is via the connected GitHub app (MCP) or the GitHub Push (PAT) skills; PAT values are injected at runtime by RunWithCredentials and are never stored in this repo.
- Tools to enable on restore (each domain agent + orchestrator): Web search/fetch, Browser, Slack, Document read/write, Tables.
