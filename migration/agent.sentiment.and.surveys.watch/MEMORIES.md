# Memories

## Macro-swarm collector first-run baseline backfill
- id: cmqe89sdu0oqk07ad7pnkbnja
- category: tools_and_workflows
- importance: 2

For macro-swarm domain collector agents: when a domain's blackboard section is still empty ('awaiting first release') on the first real run, backfill the latest available prints for each tracked report as baseline rows even if they aren't fresh today — this gives the orchestrator data to synthesize. Do NOT post a Slack alert for backfilled stale prints (only genuinely fresh landings trigger Slack). Set the heartbeat status to 'logged baseline (...)'.

whenToUse: Use this memory when configuring or debugging a macro-swarm domain collector agent's first execution on an empty blackboard, specifically to guide how to backfill baseline data without triggering false-alarm Slack notifications.
