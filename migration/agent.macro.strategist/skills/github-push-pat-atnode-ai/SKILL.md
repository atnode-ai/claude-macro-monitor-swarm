# GitHub Push (PAT) — atnode-ai

Commit a set of files to a GitHub repository branch in **one commit**, using a personal access token scoped to the **atnode-ai** organization. This is a sibling of the base "GitHub Push (PAT)" skill with an independent `GITHUB_TOKEN` credential, so the cloudburostaff token and the atnode-ai token can both be configured at once.

## Credential
- `GITHUB_TOKEN` — a GitHub Personal Access Token with write access to atnode-ai repos.
  - Classic PAT with the **`repo`** scope, OR
  - Fine-grained PAT with **Contents: Read and write** on `atnode-ai/agentweb` (add `Administration` if it must also create the repo / change Pages).

## Script
`github_push.py` — commits files via the Git Data API: read branch head → base tree → create a base64 blob per file → build a tree on the base → create a commit → move the branch ref. Creates/updates only (no deletes). Uses `requests` (honors `HTTPS_PROXY`); run `python3 -m pip install --quiet requests` first if needed.

```
python3 skills/github-push-atnode/github_push.py \
  --owner atnode-ai --repo agentweb --branch main \
  --message "<commit message>" --manifest <files.json>
```

### Manifest format
`files.json` is a JSON array; each entry has a repo `path` plus a source:
```json
[
  {"path": "macro-monitor/index.html", "local": "/agent/workspace/site/index.html"},
  {"path": "macro-monitor/inline.txt", "content": "inline UTF-8 text"}
]
```
- `local` — read bytes from a local file (text or binary).
- `content` — inline UTF-8 text.
- `path` — destination path inside the repo.

On success prints JSON: `{ ok, commit, html_url, files, branch }`.
