# Legacy: Hyperagent swarm

The original swarm's backup sits at the repo root in the `agent.<slug>/` folders (one per agent: SYSTEM_PROMPT.md, agent_config.json, MEMORIES.md, SECTION_SNAPSHOT.md, skills/). The orchestrator folder `agent.macro.strategist/` also holds ARCHITECTURE.md and the last BLACKBOARD.md snapshot. The same backup lives on Google Drive under `agent.hyperagent.talfco/`.

Those folders are reference only. Nothing in the Claude Code swarm reads them, and the old prompts reference platform tools (ReadDocument, ExecuteIntegration, RunWithCredentials) that don't exist in Claude Code.

What was carried over, and where it went, is in [../MIGRATION.md](../MIGRATION.md). The domain lenses in `config/lenses/` are condensed from each agent's SYSTEM_PROMPT.md; the cross-indicator chain from the strategist's prompt; the release cadence from the strategist's calendar memory.
