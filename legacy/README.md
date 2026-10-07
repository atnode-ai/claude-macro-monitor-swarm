# Legacy: Hyperagent swarm

The original swarm's backup lives on Google Drive under `agent.hyperagent.talfco/` (one `agent.<slug>/` folder per agent: SYSTEM_PROMPT.md, agent_config.json, MEMORIES.md, SECTION_SNAPSHOT.md, skills/). It is not copied here: this repo has to stand alone in any account, and the old prompts reference platform tools (ReadDocument, ExecuteIntegration, RunWithCredentials) that don't exist in Claude Code.

What was carried over, and where it went, is in [../MIGRATION.md](../MIGRATION.md). The domain lenses in `config/lenses/` are condensed from each agent's SYSTEM_PROMPT.md; the cross-indicator chain from the strategist's prompt; the release cadence from the strategist's calendar memory.
