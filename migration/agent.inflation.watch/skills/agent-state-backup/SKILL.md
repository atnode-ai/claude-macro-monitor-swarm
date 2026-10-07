# Agent State Backup

Backs up a Hyperagent agent's full state to GitHub and keeps it in sync. **Trigger phrase: `backup_agent_state`.**

## Convention

- **Repo:** `cloudburostaff/agent.hyperagent.talfco`, branch `main` — one shared repo for all agents.
- **Folder:** one subfolder per agent, named `agent.<slug>` (slug = the agent name lowercased with spaces → dots, e.g. `agent.fgqc.aum.monitor`).
- **Tracked files** in each agent folder:
  - `PROJECT.md` — exported project document.
  - `SYSTEM_PROMPT.md` — the agent's system prompt.
  - `SKILL.md` — skill manifest + docs. Multiple skills → `skills/<skill-name>/SKILL.md` plus that skill's scripts.
  - skill scripts and any other created files (e.g. `monitor_fgqc_aum.py`).
  - `backup_manifest.json` — project doc id, skill ids/names, system-prompt source, tracked files, last backup timestamp. Makes re-runs deterministic and the repo self-describing.
- **Never commit credentials or secrets.**

## Bundled script

- `render_project_doc.py <doc.json>` — renders a `ReadDocument` JSON export into deterministic Markdown. Save the `ReadDocument` output to a JSON file, then: `python3 render_project_doc.py doc.json > PROJECT.md`.

## Resolving the target

1. Identify the agent:
   - **Named-agent thread** → the current agent; its system prompt and attached skills come from `GetAgentConfig`.
   - **Project / general thread** → the project; system prompt and skills come from the project document and its recorded skills (read `backup_manifest.json` in the folder, or the project doc mapping).
2. Determine the folder `agent.<slug>`. If a matching `backup_manifest.json` exists, trust it. **If the target is ambiguous, ask the user — never guess or write to the wrong folder.**

## Procedure (on `backup_agent_state`)

1. **Gather** current state into a local staging dir:
   - Project doc: `ReadDocument(projectDocId)` → save the JSON → `python3 render_project_doc.py doc.json > PROJECT.md`.
   - System prompt: `GetAgentConfig().systemPrompt` → `SYSTEM_PROMPT.md` (or the maintained prompt if the agent isn't a named agent yet).
   - Skills: for each skill, `GetKnowledgeDetails(skillId)` → write `skillMd` to `SKILL.md`; `FetchSkillScripts(skillName)` → copy the scripts.
   - Refresh `backup_manifest.json` (bump `last_backup`).
2. **Diff**: for each staged file, `github__get_file_contents` for `agent.<slug>/<file>` (ref `refs/heads/main`) and compare content. Classify each as new / changed / unchanged.
3. **Sync-commit**: push all new + changed files in **one commit** via `github__push_files` (`{owner, repo, branch, message, files:[{path, content}]}`). It handles creates and updates without per-file SHAs. Skip unchanged files. Stage the params on disk and pass `paramsFile` to avoid corrupting Unicode. Files removed locally are **flagged in the summary, not auto-deleted**, unless the user confirms removal.
4. **Summarize**: target agent + folder, added / updated / unchanged / flagged files, and the commit URL.

## Notes

- GitHub access is via the connected GitHub integration (MCP `github__*` actions), so this runs inside Hyperagent — not as a standalone cron.
- The repo root `BACKUP.md` documents this same convention for anyone browsing the repo.
