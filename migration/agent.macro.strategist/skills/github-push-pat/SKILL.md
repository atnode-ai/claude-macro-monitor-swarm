# GitHub Push (PAT)

Commit a set of files to a GitHub repository branch in **one commit**, using a personal access token. Built for two cases the GitHub MCP integration can't cover:

1. **Binary files** — uses the Git Data API with `encoding: base64` blobs, so PNGs/zips/etc. commit as real bytes (the MCP `push_files`/`create_or_update_file` store the payload as a UTF-8 text blob and corrupt binaries).
2. **Integration outages** — runs via `RunWithCredentials`, independent of the MCP/`ExecuteIntegration` path.

## Credential

- `GITHUB_TOKEN` — a GitHub Personal Access Token, injected as an env var at run time (never stored in the repo or printed).
  - Fine-grained PAT: **Contents → Read and write** on the target repo (e.g. `cloudburostaff/agent.hyperagent.talfco`).
  - or classic PAT with the **`repo`** scope.

## Script

`github_push.py` — commits files via the Git Data API: read branch head → base tree → create a base64 blob per file → build a tree on the base → create a commit → move the branch ref.

```
python3 skills/github-push-pat/github_push.py \
  --owner <owner> --repo <repo> --branch <branch> \
  --message "<commit message>" --manifest <files.json>
```

### Manifest format

`files.json` is a JSON array; each entry has a repo `path` plus a source:

```json
[
  {"path": "dir/notes.md", "local": "/agent/workspace/out/notes.md"},
  {"path": "dir/image.png", "local": "/agent/workspace/out/image.png"},
  {"path": "dir/inline.txt", "content": "inline UTF-8 text"}
]
```

- `local` — read bytes from a local file (works for text **and** binary).
- `content` — inline UTF-8 text (convenience for small text files).
- `path` — destination path inside the repo.

## Run with credentials

```
RunWithCredentials(
  skillName="GitHub Push (PAT)",
  command="python3 skills/github-push-pat/github_push.py --owner cloudburostaff --repo agent.hyperagent.talfco --branch main --message 'msg' --manifest /agent/workspace/backup_staging/push.json"
)
```

On success prints JSON: `{ ok, commit, html_url, files, branch }`. On failure prints the HTTP status + body and exits non-zero.

## Notes

- Single commit on top of the current branch head (non-force). If the branch moved between read and write, re-run.
- Uses `requests`, which honors the sandbox `HTTPS_PROXY`.
- Does not delete files; it only creates/updates the paths in the manifest (entries are layered on the existing base tree).
