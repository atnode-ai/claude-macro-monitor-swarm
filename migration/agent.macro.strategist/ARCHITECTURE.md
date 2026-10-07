# Macro Monitoring Swarm — Architecture

## Overview & Verdict

This document defines how to decompose a swarm of agents that monitors the **23 macro economic data releases** catalogued in `vault.substack/danielsan2401/macro-economics-the-complete-guide.md` (CPI, PCE, PPI, NFP, JOLTS, ADP, Jobless Claims, GDP, Retail Sales, ISM PMI, FOMC, BoE/ECB, housing, sentiment surveys, trade, etc.).

**Verdict:** Use a **3-tier hierarchy**, not a flat one. Neither "one agent per report" (23+ agents → noise, cost, no cross-view) nor "one monolithic inflation agent" (too coarse) is right. The clean answer maps granularity onto three *different* platform primitives:

| Concept | Hyperagent primitive | Owns |
|---|---|---|
| **Domain** (e.g. Inflation) | a **named Agent** | The analytical lens, prompt, tools, source skills |
| **Report** (e.g. CPI) | a **scheduled invocation** on that agent | *Timing* — its own release-calendar trigger |
| **Macro** (whole picture) | an **Orchestrator agent** | Cross-indicator synthesis & regime-change alerts |

The middle row is the key unlock: **per-report behaviour without per-report agents.** CPI, PPI and PCE become three scheduled invocations on a single *Inflation Watch* agent.

## Design Principle

Decompose along the axis of **what varies independently**:

- **Analytical lens varies by domain.** How you read an inflation print (vs. consensus, core vs. headline, impact on the Fed path) is shared across CPI/PPI/PCE but differs from how you read a jobs print. → the *agent* (system prompt + tools) is the domain.
- **Timing varies by report.** CPI drops ~mid-month, claims every Thursday, FOMC 8×/year. → the *scheduled invocation* (its `rrule`/trigger) is the report.
- **Synthesis is a distinct job.** "What does the accumulation of this week's prints mean for the cycle?" is cross-domain and cannot live inside any single domain agent. → the *orchestrator* is the macro view.

Keeping these on separate primitives means you can add a report (new invocation) without touching the domain agent, retune a domain's lens (edit one prompt) without touching schedules, and evolve the macro narrative (orchestrator) independently.

## Topology

**~7 domain collectors + 1 orchestrator.** (Trade Balance folds into Growth & Activity — it feeds GDP net exports and would otherwise be a near-idle standalone agent. A 7th domain — **Financial Conditions & Markets** — was added later to cover market-priced leading signals that none of the original six owned.)

| Domain agent | Reports → each becomes a scheduled invocation |
|---|---|
| **Inflation Watch** | CPI, PCE, PPI |
| **Labor Watch** | Non-Farm Payrolls, ADP, JOLTS, Jobless Claims, UK Labour Market |
| **Growth & Activity Watch** | GDP, Retail Sales (+ Chicago Fed CARTS nowcast), ISM PMI (Mfg + Services), Industrial Production, Durable Goods, Trade Balance |
| **Housing Watch** | Building Permits & Housing Starts, Existing & New Home Sales |
| **Sentiment & Surveys Watch** | UMich Sentiment, Conference Board Confidence, German Ifo |
| **Central Banks & Policy Watch** | FOMC decision, FOMC minutes / Beige Book / speeches, BoE, ECB, Eurozone CPI & GDP flash |
| **💹 Market Watch** (Financial Conditions & Markets) | Treasury yield curve (10y–2y, 10y–3m), HY/IG credit spreads, Chicago Fed NFCI/ANFCI, SLOOS, market-implied Fed path (futures), breakevens (5y5y, 10y) |
| **🧠 Macro Strategist** (orchestrator) | reads all seven domains; applies the Master Cross-Indicator table |

**Classification rule (why Market Watch is its own domain):** assign an indicator by what it *measures and leads*, not by its publisher. Market Watch owns **market-priced** financial-conditions data only — real-activity nowcasts stay in the real-economy domains (e.g. the Chicago Fed publishes both the NFCI → Market Watch *and* CARTS → Growth & Activity). Financial conditions lead the real economy by ~6–18m, making this the leading edge of the cross-indicator chain.

**Axis note:** Geography (US / UK / EU) is the alternative top-level split, but domain-first is better — the analytical playbook (leads/lags relationships) is organised by domain, not by country. Treat geography as a *tag/section within* each domain instead.

## Why Not One Agent Per Report

- **Idle sprawl & maintenance.** Most releases are *monthly*; 23 agents sit idle ~95% of the time but each is config + prompt + a GitHub `agent.<slug>` backup folder to maintain.
- **No cross-view, which is where the value is.** The source post's thesis: *"regime changes almost never come from a single data point."* Per-report agents are blind to each other, so the orchestrator ends up doing all the real analysis anyway — making the leaf agents thin wrappers.
- **Alert fatigue.** 23 agents each pinging Slack = noise. A domain agent batches naturally: *"Inflation week: CPI hot, PPI cooling, PCE Friday."*
- **Cost & rate limits** scale with agent count and redundant context.

**The one exception — tier-1 movers.** The highest-impact, precisely-timed releases (**CPI, NFP, FOMC decision**, arguably PCE) warrant a *dedicated invocation* fired at the exact release instant (e.g. 08:30 ET) for sub-minute turnaround + immediate alert. But that is still a scheduled invocation *on the domain agent*, not a separate agent.

## Coordination — Blackboard Pattern

Do **not** wire agents to message each other directly (fragile, ordering-dependent, hard to debug). Coordinate through a **shared blackboard = a project-scoped document**, with one section per domain. Domain agents write; the orchestrator reads all and writes the synthesis section. State survives across runs and is human-visible.

```
        ┌──────────── Macro Monitor blackboard (project doc) ───────────┐
        │  §Inflation  §Labor  §Growth  §Housing  §Sentiment  §Policy   │
        └───▲────▲────────▲────────▲────────▲──────────▲───────┬────────┘
   write │    │ write     │        │        │          │       │ read all
     ┌───┴─┐┌─┴───┐   ┌───┴──┐  ┌──┴───┐ ┌──┴────┐ ┌───┴───┐   ▼
     │Infl ││Labor│   │Growth│  │House │ │Sentmt │ │Policy │ ┌─────────────┐
     └─────┘└─────┘   └──────┘  └──────┘ └───────┘ └───────┘ │MacroStrateg.│
       (domain collectors: fetch release → digest → write)   └─────┬───────┘
                                                                    ▼ alert
                                                  Slack #hyper-asset-monitoring
```

- **Fan-out (domain agents):** on each report's trigger, pull the release from its **official source link**, capture print vs. consensus + prior, write a short structured digest into the domain's section (date, actual, consensus, surprise, one-line read).
- **Fan-in (orchestrator):** reads every section and produces the unified narrative.

**Blackboard schema (per domain section):** a small table of `Report | Latest date | Actual | Consensus | Surprise | Read`, plus a free-text "current domain stance."

## Orchestrator Logic

The **Master Cross-Indicator Reference Table** (already in the archived post) *is* the orchestrator's reasoning spec — feed it that table verbatim. It encodes, for each release: what it **leads**, what it **lags**, and its **primary asset impact**. The orchestrator's job:

1. Read all domain sections from the blackboard.
2. Sequence the latest prints along the leads/lags chain (e.g. ISM Prices Paid → PPI → CPI → PCE → Fed path).
3. Detect **alignment** — multiple domains telling the same story (e.g. ISM Services <50 + rising claims + falling JOLTS + soft retail sales = labour market turning).
4. Emit a unified macro narrative and flag regime-change risk.

**Orchestrator triggers:**
- **Post-release synthesis** — shortly after each tier-1 print.
- **Daily macro wrap** — e.g. 17:00 ET.
- **Weekly look-ahead** — Sunday: the upcoming release calendar + what to watch.

## Synthesis Is Blackboard-Only (No Live Web at Fan-In)

A recurring design question: when the orchestrator reasons over the blackboard to produce the Macro Synthesis, does it *also* reach out to the internet? **No — and that is deliberate.** Fan-in is a pure read-and-reason step over state the domain collectors have already written.

**Separation of concerns:**
- **Collectors touch the internet; the orchestrator does not.** Each domain agent fetches from its primary source (mostly FRED, plus official statement pages — FOMC/ECB/BoE, Census/NAR), dedups against what it already logged, and writes a compact digest row. That is the *only* place live external data enters the swarm.
- **The orchestrator synthesizes from the blackboard alone.** It reads the seven domains' digests + each *Current stance* line, sequences the prints along the leads/lags chain, judges alignment, and writes the narrative. Its hard guardrail: **base every claim on what is in the blackboard; if a domain is stale or empty, say so rather than inventing.** A thin day is flagged as *blind*, never silently backfilled from a search.
- **Even the "Week ahead" line is web-free** — written from a baked-in release-calendar memory, so no lookup is needed to know what is due.

**Why enforce this boundary:** single source of truth, no double-counting (collectors have already reconciled/deduped the figures), a deterministic and cheap run, and — most importantly — no risk of the orchestrator introducing a number that disagrees with what a collector logged. Re-fetching at fan-in would reintroduce exactly the inconsistency the blackboard exists to prevent.

**The one sanctioned exception.** The orchestrator *does* hold web-search tools (Exa) for *ad-hoc interactive* tasks — e.g. "here is an indicator named in a news article; is it worth tracking?" There it traces the claim to its primary source, cross-checks cited figures against the blackboard, and marks anything unconfirmable as *"unconfirmed."* That is a one-off verification path, distinct from the routine synthesis loop, and it never blends raw web data into the macro read.

## Model Choice for the Orchestrator (Why Not an Open-Source Swap)

Could the Macro Strategist run on an open-weight model (e.g. a mid-size Qwen MoE) instead of Claude? This splits into two questions, and the first is the gate.

**1. Availability — the real gate.** The platform is **Claude-native**. An agent's model must come from the account's curated model catalog (`modelSettings.modelId`); it is *not* a free-form field pointing at an arbitrary Hugging Face checkpoint. A self-hosted open-weight model is not a per-agent toggle unless the platform has added it to the catalog. So the first question is empirical — *is it in the picker?* — not about quality. Sub-agents, skill-apps, and artifact generation are Claude end-to-end too.

**2. Capability — if it *were* selectable.** The Strategist is engineered so the **heavy lifting is offloaded to deterministic skills**: the "Macro Blackboard Digest & Health" script does the parsing, the staleness math (>36h → stale), the dedup, and even returns ready-to-post `alert_text`. That deliberately shrinks the LLM's job, which then splits cleanly:

- **Where a mid-size open model is likely fine:** the synthesis *writing* — weaving seven stances into a coherent narrative + regime-watch + week-ahead lines.
- **Where frontier models still lead, and where it matters here:** faithful **agentic tool-calling** across a *dense, conditional* system prompt (quiet-day Slack gate, health-alert-overrides-quiet override, WRITE-BLOCKED banner, dedup rules, externalized-file handling) and the **anti-hallucination discipline** ("never invent — base every claim on the blackboard"). A missed guardrail is not cosmetic: it is a **false alert to the team channel** or a **fabricated figure** propagating into everyone's macro read. The orchestrator is the swarm's *judgment layer*, so its errors are the most expensive in the system.

**Verdict / cost lever.** Keep the orchestrator on a strong reasoning model. If **cost** is the motivation, the right lever *within* the platform is **right-sizing the collectors** — the domain agents are mechanical scrape-and-dedup jobs that tolerate a cheaper tier — while the orchestrator keeps the strongest reasoning because that is where judgment and alert quality live. If the motivation is **open-source / data sovereignty**, that is an infrastructure decision, not a model-picker toggle.

## Scheduling & Cadence

| Pattern | Reports | Trigger |
|---|---|---|
| Weekly | Jobless Claims | Thu 08:30 ET |
| Monthly (fixed-ish) | CPI, PPI, NFP, Retail Sales, JOLTS, IP, Durable Goods, sentiment surveys | release-day invocation |
| Quarterly | GDP | release-day |
| 8×/year (pre-scheduled) | FOMC, BoE, ECB | per published calendar |
| Event / precise | CPI, NFP, FOMC | dedicated exact-time invocation + instant alert |

**Don't hard-code dates.** Release dates drift month to month. Give each domain agent a lightweight **"calendar refresh"** invocation (e.g. weekly) that reads the official release schedules and **re-arms** a near-term precise trigger, rather than baking fixed dates into an `rrule`.

**Example `rrule`s:** Jobless Claims `FREQ=WEEKLY;BYDAY=TH`; daily wrap `FREQ=DAILY`; weekly look-ahead `FREQ=WEEKLY;BYDAY=SU`. The 30-minute floor on intervals applies.

## Alerting Strategy (signal ≫ noise)

Separate **routine logging** from **alerts**:

- **Domain agents → log, don't shout.** Every release gets written to the blackboard regardless of outcome. No Slack ping for an in-line print.
- **Orchestrator → owns alerts.** Fires to **Slack `#hyper-asset-monitoring` (C0B8B76L7NH)** only when:
  - a print's **surprise vs. consensus** exceeds a per-report threshold, OR
  - **multiple domains align** into a regime-change signal, OR
  - a **tier-1 event** (CPI/NFP/FOMC) lands (always alert, with the read).
- **Alert payload:** headline (report, actual vs. consensus, surprise), the cross-indicator implication, and the updated macro stance — not a raw data dump.

This keeps the channel high-signal: domain noise stays in the doc; only "this matters" reaches Slack.

## Mapping to Hyperagent Primitives

- **Domain agent = named Agent.** System prompt = the domain's analytical lens (how to read its prints). Tools = web fetch/search + the Substack-to-Markdown skill + a small per-domain "fetch latest release" skill keyed to the official source URLs.
- **Report = scheduled invocation** on the agent (its `rrule`/trigger + a prompt: *"pull latest {report}, compare to consensus, write digest to blackboard §{domain}, alert only if surprise > X"*).
- **Live mode** can back the polling-style watches (checklist: *has the new release dropped?*).
- **Delivery:** native Slack integration → `#hyper-asset-monitoring`.
- **State/backup:** each agent backs up to its own GitHub folder `agent.<slug>` in `cloudburostaff/agent.hyperagent.talfco` via the existing `backup_agent_state` convention.
- **Blackboard:** a project-scoped document shared across all swarm threads.

## Recommended Build Sequence

1. **Create the blackboard** — a project-scoped "Macro Monitor" doc with one section per domain + a synthesis section.
2. **Build Inflation Watch end-to-end** as the template: CPI/PPI/PCE invocations → digests to the blackboard → alert to `#hyper-asset-monitoring` on surprise. Validate the full loop on one domain.
3. **Clone the pattern** to the other five domains, swapping sources, prompts, and schedules.
4. **Stand up the Macro Strategist** orchestrator with the Master Cross-Indicator table as its spec and the three trigger types.
5. **Tune alert thresholds** per report to dial in signal vs. noise.
6. **Wire backups** (`agent.<slug>`) and document each agent's config.

Start narrow (one domain, working end-to-end) before fanning out — it de-risks the schedule/alert plumbing before you multiply it six times.
