# Memories — A - Inflation Watch

## UpdateAgentConfig replaces array fields wholesale
- id: cmq7luzrv03m908adkbg8c472
- category: tools_and_workflows
- importance: 4
- content: UpdateAgentConfig replaces array fields wholesale — passing a partial 'tools' or 'integrations' array wipes all unlisted entries. Omit these arrays entirely when you don't intend to change them.
- whenToUse: Use this knowledge when modifying an agent's configuration using UpdateAgentConfig to prevent accidentally wiping out existing tools or integrations by sending partial arrays.

## Live Mode cannot be disabled via UpdateAgentConfig
- id: cmq7lznju03xj07adfoogswsq
- category: tools_and_workflows
- importance: 3
- content: Live Mode cannot be turned off via UpdateAgentConfig — aliveConfig is not present in the editable config (returns undefined). Live Mode is a separate runtime UI toggle. When asked to disable live mode programmatically, set up scheduled invocations and tell the user to switch Live Mode off in the UI.
- whenToUse: Use when a user asks to programmatically disable, turn off, or toggle an agent's Live Mode or aliveConfig, as this cannot be done via UpdateAgentConfig and requires setting up scheduled invocations while directing the user to the UI.

## Scheduled invocations need readOnlyMode=false for writes
- id: cmq7m00ez042p07ad283uat18
- category: tools_and_workflows
- importance: 4
- content: For scheduled invocations (UpdateAgentConfig), readOnlyMode must be false if the invocation prompt requires writing to documents/blackboard or posting to Slack — readOnlyMode=true silently blocks those actions.
- whenToUse: Use this memory when troubleshooting why a scheduled agent run is failing to write to documents, update the blackboard, or post Slack alerts, or when configuring UpdateAgentConfig for automated tasks that require write permissions.

## BLS pages 403 to WebFetch
- id: cmqe83wvz0p2907adulrmxaz2
- category: tools_and_workflows
- importance: 4
- content: BLS pages (bls.gov) reliably return HTTP 403 to WebFetch. To verify CPI/PPI release dates and reference months without a browser, use WebSearch (which surfaces BLS release-summary pages and schedule pages) or ExaContents/ExaSearch instead of WebFetch. BEA personal-income pages do fetch successfully via WebFetch.
- whenToUse: When checking BLS CPI/PPI release schedules or BEA PCE data and a plain WebFetch is blocked.

## Inflation Watch canonical data path
- id: cmqiiye1c00we06ad323a5h7z
- category: tools_and_workflows
- importance: 2
- content: Inflation Watch (A - Inflation Watch) canonical data path: use the "US Inflation Release Check" skill, NOT bls.gov HTML scraping (bls.gov reliably 403s and forces an expensive browser fallback). The skill hits the free BLS public API v2 for CPI/PPI and the BEA API for PCE, returns headline+core MoM/YoY plus an is_new dedup flag. Series IDs: CPI CUSR0000SA0 / CUUR0000SA0 (core CUSR0000SA0L1E / CUUR0000SA0L1E), PPI final demand WPSFD49207 / WPUFD49207 (core WPSFD49104 / WPUFD49104; SA for MoM, NSA for YoY); PCE = BEA NIPA table T20804 (needs free BEA_API_KEY). Consensus/expected is NOT on the BLS/BEA APIs — fetch it with one targeted web lookup on release days and mark any unverifiable figure 'unconfirmed' (never invent).
- whenToUse: When running or debugging the Inflation Watch CPI/PPI/PCE data fetch, or deciding how to obtain a US inflation figure — prefer the skill/APIs over scraping bls.gov.
