# Agent State Backup (skill id cmq2zoi2z0a1u07ad0unohtca)

Backs up a Hyperagent agent's full state and keeps it in sync. Trigger phrase: `backup_agent_state`.
Convention: one subfolder per agent named `agent.<slug>` in the shared backup location; tracked files are SYSTEM_PROMPT.md, skills/<name>/SKILL.md (+scripts), MEMORIES.md, SECTION_SNAPSHOT.md / PROJECT.md, backup_manifest.json. Never include credentials.
Bundled script: render_project_doc.py <doc.json> > PROJECT.md (renders a ReadDocument export to Markdown).
(Condensed from the skill's skillMd; the GitHub flow is described in the live skill. This run used the Google Drive variant.)
