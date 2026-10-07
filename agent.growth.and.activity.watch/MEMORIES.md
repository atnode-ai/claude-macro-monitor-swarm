# Attached memories (5)

## Macro-swarm collector scheduled runs: writing is core, readOnlyMode diagnosis
- id: cmqe86l0z0pq607ad21i5vw7k
- category: tools_and_workflows
- importance: 4
- content: For macro-swarm collector agents (Growth & Activity Watch et al.) scheduled release-check runs, WRITING to the blackboard (append rows, update Current stance, set/replace the 'Last checked' heartbeat line) and posting a Slack alert on a new release are the core of the job — not optional. Do NOT infer a 'no-write' or 'dry-run' guidance that is not literally present in the prompt. If blackboard/Slack writes appear silently blocked, the cause is almost certainly readOnlyMode=true on the scheduled invocation (set readOnlyMode=false to enable writes), NOT a prompt instruction to stay read-only.
- whenToUse: When executing or diagnosing scheduled release-check runs for the macro-monitoring swarm, especially if writes/alerts seem blocked or the agent is tempted to skip writing.

## Valid UpdateAgentConfig modelId values
- id: cmr3vj6540jt506adks78nrr3
- category: tools_and_workflows
- importance: 4
- content: Valid UpdateAgentConfig modelSettings.modelId values for this account (verified 2026-06-17): aliases 'opus-latest','sonnet-latest','kimi-latest','gpt-latest'; pinned 'claude-opus-4-8','claude-opus-4-7','claude-opus-4-6','claude-sonnet-4-6','claude-haiku-4-5-20251001','moonshotai/kimi-k2.6','openai/gpt-5.5','deepseek/deepseek-v4-pro'. NOTE: 'claude-sonnet-4-8' and 'claude-sonnet-4-5' are NOT valid (rejected). For mechanical collector/monitor agents prefer claude-sonnet-4-6 (balanced) or claude-haiku-4-5-20251001 (cheapest); reserve Opus for synthesis/orchestrator agents.
- whenToUse: When changing an agent's model via UpdateAgentConfig modelSettings.modelId, to pick a valid ID first-try and choose the right cost/capability tier.

## Memory injection cost lever
- id: cmr3vkl2c0jij07ad00dqzwif
- category: tools_and_workflows
- importance: 3
- content: Memory injection cost lever: the swarm's user-global memories are shared across all agents and high-importance ones get force-injected into every run's system prompt. To cut per-run cost on a specialized agent, lower importance to ~2 on memories irrelevant to that agent's job (they keep their whenToUse so they still surface contextually for agents that need them) and set exact/near-duplicate memories dormant at importance 1. Caveat: importance is GLOBAL, so lowering it stops upfront injection for the whole swarm — rely on whenToUse + memory-suggestion discovery to reach the agents that still need it. Memories cannot be deleted programmatically, only re-weighted.
- whenToUse: When reducing per-run token cost of an agent that shares a global memory pool, or when deduplicating/re-weighting memories.

## Growth & Activity Watch — ISM PMI fetch path
- id: cmr3vlw4o0jhb08adjfzrqa2h
- category: tools_and_workflows
- importance: 4
- content: Growth & Activity Watch — ISM PMI fetch path: the ismworld.org report page renders headline/sub-index figures in JS widgets that BrowserExtract/BrowserGetContent cannot reliably read (extraction returns only the page title 'Manufacturing PMI®'). On ISM release days, skip fighting the browser and use ExaSearch (category 'news', startPublishedDate = release day) for 'ISM Manufacturing/Services PMI <month year> report' — it returns the full sub-index table (composite, New Orders, Production, Prices, Employment, Supplier Deliveries, Backlog, Export Orders) plus the PRNewswire release URL in one call. Consensus (e.g. Reuters poll) also surfaces in the same results.
- whenToUse: When fetching ISM Manufacturing or Services PMI figures on their release days for the Growth & Activity domain — prefer ExaSearch news over browser-scraping ismworld.org.

## Macro-swarm blackboard write discipline
- id: cmto3dux6008b07ad2cbokkbo
- category: tools_and_workflows
- importance: 5
- content: Macro-swarm blackboard write discipline (all domain collectors): make TARGETED edits only — never replace a whole domain section with empty, blank or truncated content; if a write would blank the section, abort and report instead. New release rows are APPENDED into the markdown table immediately ABOVE the 'Current stance:' line, never below it and never below the Sources / Last-checked block. The heartbeat is a SINGLE 'Last checked: <YYYY-MM-DD HH:MM ET> — <status>' line that must be OVERWRITTEN in place each run (status = 'logged <report>' or 'no new release') — never create a second heartbeat line. No Slack post on a no-new-release run.
- whenToUse: When a macro-swarm domain collector writes to the Macro Monitor blackboard (doc cmq5rqdws16qq06adoiw88r03), or when configuring/reviewing a collector's scheduled-run prompt or system prompt.
