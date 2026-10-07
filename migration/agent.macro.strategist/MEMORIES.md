# Attached Memories — A - Macro Strategist

Snapshot of the 15 memories attached to this agent (source_agent_id `cmq667l5l00jp07adt010uj06`), exported 2026-10-07. Content only; no secrets. Memory IDs are stable lookup keys.

---

## 1. GitHub integration vs PAT skill (tools_and_workflows, importance 2)
`id: cmq7lu6ds03q107adeaq9zo19`

User has a native GitHub integration connected with their own credentials (commits author as 'cloudburostaff'). Prefer the connected integration for repo operations rather than asking for a token; the 'GitHub Push (PAT)' skill (git-over-HTTPS / REST Git Data API via RunWithCredentials) is needed only for committing real binary files (which the MCP integration cannot do) or when the MCP integration is unavailable.

**When to use:** When performing GitHub repo operations — deciding between the native integration and the PAT-based push skill.

---

## 2. Substack vault archival convention (tools_and_workflows, importance 2)
`id: cmq7luip5044n07adxyg0vi4h`

User archives extracted Substack post bundles to GitHub under a 'vault.substack' folder in the shared repo cloudburostaff/agent.hyperagent.talfco (branch main), organized by publication subfolder (e.g. vault.substack/<writer>/<slug>.md plus _manifest.json). Table screenshots within posts should be transcribed to real markdown text tables (via vision) and the image links replaced, producing a fully text-based note.

**When to use:** When extracting, archiving, or committing Substack posts (or similar article content with table screenshots) to GitHub.

---

## 3. Macro-monitoring swarm overview (project_context, importance 4)
`id: cmq7lup7c03sr07ad6u1i2jyz`

User built a macro-monitoring agent swarm: 7 domain collector agents (Inflation, Labor, Growth & Activity, Housing, Sentiment & Surveys, Central Banks & Policy, Market Watch / Financial Conditions & Markets) plus a Macro Strategist orchestrator. They coordinate via a shared project-doc blackboard 'Macro Monitor — Blackboard' (id cmq5rqdws16qq06adoiw88r03) — domain agents write digest rows to their section; the orchestrator reads all and writes Macro Synthesis. Architecture is documented in 'Macro Monitoring Swarm — Architecture' (id cmq5rkc1815wk06advgj6mndl). Alerts go to Slack #hyper-asset-monitoring (C0B8B76L7NH).

**When to use:** When working on the macro-monitoring swarm — building, modifying, running, or backing up its agents or coordination docs.

---

## 4. Orchestrator coordination + schedule (project_context, importance 3)
`id: cmq7lzhi403xf07adv4z0okbh`

The Macro Strategist orchestrator cannot directly invoke the domain agents (Inflation, Labor, Growth & Activity, Housing, Sentiment & Surveys, Central Banks & Policy, Market Watch). Agents coordinate ONLY through the shared 'Macro Monitor — Blackboard' doc (cmq5rqdws16qq06adoiw88r03); each domain agent writes its own section. The orchestrator only reads sections and writes the Macro Synthesis. It now has ONE active scheduled invocation: 'Weekly consolidated (Friday)' 17:00 ET — a single run that does the end-of-week synthesis + domain health check, publishes the public site (business report + detailed blackboard), and posts one Slack summary. The former 'Daily macro wrap' (weekdays 17:00), 'Weekly look-ahead' (Sun 17:00), and 'Weekly public report' (Sat 09:00) are PAUSED (superseded by the Friday consolidated run).

**When to use:** When diagnosing communication issues within the macro swarm, verifying the schedule, or needing the blackboard document ID where domain agents write.

---

## 5. 7th domain: Market Watch (project_context, importance 3)
`id: cmqe7wf4l0ooi07adszukqtu1`

The macro-monitoring swarm gained a 7th domain agent: 'A - Market Watch' (Financial Conditions & Markets), covering market-priced data only — Treasury yield curve (10y-2y, 10y-3m), HY/IG credit spreads (ICE BofA OAS), Chicago Fed NFCI/ANFCI, SLOOS, market-implied Fed path (fed funds/SOFR futures, CME FedWatch), 5y5y breakevens / 10y real yield, with MOVE/VIX/DXY as context. It writes to a 'Financial Conditions & Markets' section on the blackboard (doc cmq5rqdws16qq06adoiw88r03), positioned after Central Banks & Policy, and runs scheduled checks at 9:00 ET and 16:30 ET (the latter feeds the orchestrator's 17:00 daily wrap). The orchestrator's domain-liveness health check and the Architecture doc Topology were updated to cover all seven domains.

**When to use:** When modifying the swarm architecture, updating the 7th domain 'Market Watch' configuration, troubleshooting blackboard structure, or adjusting the 09:00 and 16:30 ET scheduled checks.

---

## 6. GetAgentConfig / CreateAgentConfig cross-thread guardrail (tools_and_workflows, importance 2)
`id: cmqe7wn6n0oy606ad5ge0xvlg`

GetAgentConfig only reads the live config of the agent whose thread you are in — it cannot read a sibling agent's live config from an orchestrator/other thread. Re-issuing a CreateAgentConfig card spawns a NEW (duplicate) agent rather than editing an existing one, so a duplicate would double-run scheduled invocations and double-post alerts. Before re-issuing a create-new-agent card, confirm with the user whether the agent already exists. To capture a sibling agent's exact live config, run the backup/snapshot from within that agent's own thread where it can GetAgentConfig on itself.

**When to use:** When inspecting, modifying, or backing up an agent's configuration, particularly across multiple agent threads or from an orchestrator, to prevent accidental duplication and redundant scheduled tasks.

---

## 7. Indicator domain classification (domain_knowledge, importance 3)
`id: cmqe7wt0y0p0907adpct6z1w2`

In the macro-monitoring swarm, indicators are classified into domains by WHAT THEY MEASURE AND LEAD, not by their publisher or frequency. Real-activity nowcasts (e.g. Chicago Fed CARTS retail nowcast, Atlanta Fed GDPNow, regional Fed surveys like Empire State/Philly Fed) belong in real-economy domains (Growth & Activity); market-priced/financial-conditions series (yield curve, HY/IG credit spreads, Chicago Fed NFCI, SLOOS, fed funds/SOFR futures, breakevens) belong in the Markets domain — even when the same publisher issues both (the Chicago Fed issues both CARTS and the NFCI). New leading indicators that merely preview a series an existing domain already tracks should be logged as a preview, with alerts restricted to material divergence or multi-source confirmation. CARTS lives in Growth & Activity (it nowcasts Census Retail Sales).

**When to use:** When configuring the swarm taxonomy or deciding whether a new indicator/nowcast/survey belongs in Growth & Activity vs the Markets domain.

---

## 8. CARTS retail-sales nowcast skill (tools_and_workflows, importance 2)
`id: cmqe815z60r8e08adgvjcatfc`

A skill 'Chicago Fed CARTS — Retail Sales Nowcast' (script carts_nowcast.py) fetches/parses the Chicago Fed Advance Retail Trade Summary PDF (https://www.chicagofed.org/-/media/publications/carts/carts.pdf) — a weekly model nowcast of Census retail & food services sales ex. auto, returning projected m/m growth nominal (SA) + inflation-adjusted, release date, reference month, inferred preliminary/final, and 6-month history. No credentials; cache-busted; pypdf auto-installed. CARTS belongs to the Growth & Activity domain as a LEADING PREVIEW of the existing 'Retail Sales (Advance)' line (one step upstream of Retail Sales → GDP), logged as a nowcast row with Consensus '(nowcast — no mkt consensus)', alert only on divergence or confirmation.

**When to use:** When fetching CARTS / retail-sales nowcast data or wiring it into the Growth & Activity domain agent.

---

## 9. Sandbox scripting cautions (tools_and_workflows, importance 2)
`id: cmqe8172g0o9g06adsv4nvsb3`

Sandbox scripting cautions observed repeatedly: (1) the sandbox can reset mid-run after a transient error — pip-installed packages (requests, pypdf) and downloaded files in /agent/workspace are lost and must be re-fetched/re-installed in the same Bash invocation. Prefer self-bootstrapping scripts (stdlib urllib, which honors HTTPS_PROXY, over requests; auto-install pypdf via ensurepip+pip if missing). (2) Chicago Fed CARTS and similar pages render figures in JS charts that plain HTTP/ExaContents cannot read — fetch and parse the underlying PDF instead. Use cache-busting query params and validate the %PDF- magic header.

**When to use:** When writing or running Python scripts in the sandbox, scraping data pages, or fetching/parsing PDFs.

---

## 10. Google Drive access (tools_and_workflows, importance 2)
`id: cmqe85n9r0ogd07adz48fkmwa`

User's Google Drive files are owned by the account cloudburostaff@gmail.com (Cloudburo Virtual Agent), and a native google-drive integration is available via ExecuteIntegration (GoogleDriveGetFileMetadata, GoogleDriveDownloadFile, etc.). When a thread restricts integrations to a fixed selection that excludes Drive, RequestToolAccess fails — the user must add Google Drive via the thread's integration picker. Private files cannot be fetched anonymously from the sandbox (the public uc?export=download / drive.usercontent.google.com link redirects to a Google sign-in page); use the connected integration or have the user set sharing to 'Anyone with the link'.

**When to use:** When diagnosing Google Drive access issues, executing Drive integrations under cloudburostaff@gmail.com, or resolving sandbox download failures from private file restrictions.

---

## 11. Verbatim system-prompt edit procedure (tools_and_workflows, importance 2)
`id: cmqe8bapx0oz806ada2ct2iod`

To edit an agent's system prompt while preserving the rest exactly (e.g. append/insert a section verbatim): 1) GetAgentConfig to obtain configPath; 2) use node to read the systemPrompt field from configPath into a workspace file — never retype/paraphrase it from memory; 3) make the edit via file manipulation; 4) verify the original portion is byte-for-byte unchanged (e.g. assert combined.slice(0, orig.length) === orig); 5) call UpdateAgentConfig with systemPromptFilePath and OMIT all array fields (tools/integrations/skills/memories/scheduledInvocations) so nothing is wiped. Also decode XML entities (e.g. &gt; -> >, &amp; -> &) when reproducing text from a web-context <prompt> verbatim, since those arrive XML-escaped.

**When to use:** When asked to edit an agent's system prompt while keeping the rest exact — especially appending/inserting text verbatim, or reproducing text from a web-context prompt.

---

## 12. Orchestrator cheap-run playbook (tools_and_workflows, importance 3)
`id: cmqikwp0901ql06adie1590y7`

Macro Strategist (orchestrator) — cheap run playbook. The orchestrator now runs ONE scheduled invocation: 'Weekly consolidated (Friday)' 17:00 ET (the former Daily macro wrap, Weekly look-ahead, and Saturday public report are paused/superseded). Step 1 of EVERY run is the "Macro Blackboard Digest & Health" skill (skillId cmqikv9c001rd06aden8i820k; script macro_blackboard_digest.py; no credentials) — NOT reading the whole blackboard into context. Call it directly by name; do NOT SearchKnowledge for it each run.

Flow: (1) ReadDocument the blackboard (doc cmq5rqdws16qq06adoiw88r03) — it externalizes to a file; pass that path via --blackboard-file and NEVER read the full doc into context. (2) --mode digest (lean default): returns all 7 Current-stance lines + fresh_today + prior_synthesis + synthesis_current (FULL verbatim Macro Synthesis) + synthesis_section_id + per-domain reports_total. Use synthesis_current + synthesis_section_id to edit the section IN PLACE via UpdateDocument(replace) — NO second ReadDocument-and-parse. Add --full for every report row; --mode health is the ~1KB liveness-only call; --mode markdown reconstructs the blackboard for the public-site build. (3) Health: the script parses each domain's Last-checked ET stamp, flags >36h stale, and returns a ready alert_text — post it to #hyper-asset-monitoring whenever all_fresh=false, and always write the result into the Macro Synthesis 'Swarm health:' line. (4) Synthesis: weave the 7 stances + fresh_today into Macro Synthesis (narrative + Regime watch + Week ahead + Swarm health), editing lines in place. (5) The Friday consolidated run ALWAYS ships a public report and ALWAYS posts one Slack summary: use --mode markdown for the blackboard reconstruction and --mode digest --full for the report rows. (6) PART D — SELF-AUDIT & CORRECT (mandatory, added Sep 2026): after the report is drafted but BEFORE the GitHub commit and the Slack post, fact-check the draft against the 'Macro Friday Report — Factual Accuracy Audit' rubric — independently derive each dated event's weekday from its date, recompute figures/bar-chart heights against the blackboard, and check claim grounding, internal consistency and attribution (Warsh, correct reference months). Correct errors in place before anything ships and append a one-line 'Self-audit: <N> corrections' note to the Macro Synthesis.

**When to use:** On every Macro Strategist scheduled run (the Friday consolidated run) or any ad-hoc synthesis run, and when configuring/debugging the orchestrator's cheap run path.

---

## 13. US/UK/EZ macro release calendar (domain_knowledge, importance 5)
`id: cmqikynya01s907adswfuy8ab`

US/UK/EZ macro release calendar (orchestrator Week-ahead aid; all times ET, cadence-based — exact dates shift monthly, so treat as expectation only; the blackboard digest's reference-month dedup is authoritative for what is actually new). Use to write the Macro Synthesis "Week ahead" line and to recognize a genuinely empty calendar day (quiet → no Slack) without web lookups.

MONTHLY US cadence (prior month unless noted): ISM Manufacturing — 1st business day, 10:00; ISM Services — 3rd business day, 10:00; ADP — Wed before NFP, 8:15; Employment Situation/NFP — 1st Friday, 8:30; JOLTS — ~first week, 10:00 (data lags ~2 months); CPI — ~10th–15th, 8:30; PPI — within a day of CPI, 8:30; Retail Sales — ~15th–17th, 8:30; Industrial Production — ~mid-month, 9:15; Empire State — ~15th; Philly Fed — ~3rd Thursday; Housing: Building Permits + Starts ~16th–18th (8:30), Existing Home Sales ~20th–22nd (10:00), New Home Sales ~23rd–26th (10:00); Durable Goods — ~24th–27th, 8:30; GDP — ~end-month, 8:30 (three successive monthly estimates per quarter: advance → second → third); PCE / Personal Income & Outlays (Fed's preferred gauge) — ~end-month (~26th–31st), 8:30; Conference Board Consumer Confidence — last Tuesday, 10:00; UMich Sentiment — prelim ~mid-month Fri, final ~end-month Fri, 10:00. WEEKLY: Initial Jobless Claims — every Thursday, 8:30 (shifts on holiday weeks).

CENTRAL BANKS (8 meetings/yr each, ~every 6 weeks — confirm exact dates from official calendars): FOMC — 2-day meeting, decision 14:00 day 2, SEP/dot-plot at the 4 quarterly meetings (Mar/Jun/Sep/Dec); ECB — Governing Council decision + presser; BoE — MPC decision Thursdays 12:00 UK + minutes/votes.

UK/EZ (swarm tracks these): UK Labour Market (ONS) ~mid-month Tue; UK CPI ~mid-month Wed; Eurozone HICP flash ~end-month, final ~mid-following-month.

Lead/lag framing for the Week-ahead is in the system prompt's cross-indicator chain; this memory is only the schedule.

**When to use:** When drafting the macroeconomic weekly outlook or determining whether a specific calendar day lacks major scheduled US/UK/EZ releases.

---

## 14. Report word-density preference (preference, importance 3)
`id: cmr3viu900k7707advzgm26ag`

When asked for a formal business/technical report with a target page count, the user expects realistic word density of ~300-400 words per page (not dense plain text), accounting for headings, bullet lists, charts/tables/callout boxes, executive summaries and title pages. Use plenty of structural elements and white space.

**When to use:** When producing a formal business or technical report with a target page count or word-count constraint.

---

## 15. GitHub PAT scope + script notes (tools_and_workflows, importance 3)
`id: cmr3vjobn0k7y07adhmi5w6jz`

The GITHUB_TOKEN credential backing the 'GitHub Push (PAT)' skill is a classic PAT with full 'repo' scope (login cloudburostaff, verified via api.github.com/user — scopes include repo, workflow, gist). It can create new repositories and enable GitHub Pages via the REST API programmatically, so dedicated-repo + Pages setup does not require manual GitHub UI steps. The github_push.py script needs `requests` installed (python3 -m pip install requests) in-sandbox each run, and skill credentials expire mid-thread — re-run FetchSkillScripts to refresh before RunWithCredentials.

**When to use:** When using the GitHub Push (PAT) skill to commit, create repos, or enable GitHub Pages programmatically.
