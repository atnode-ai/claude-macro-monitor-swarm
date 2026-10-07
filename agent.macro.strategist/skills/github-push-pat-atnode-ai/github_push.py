#!/usr/bin/env python3
"""
GitHub Push (PAT) — commit many files (text OR binary) to a repo branch in a
single commit via the GitHub REST Git Data API.

Auth: reads the PAT from env var GITHUB_TOKEN (injected by RunWithCredentials).
Network: uses `requests`, which honors HTTPS_PROXY in the sandbox.

Why the Git Data API: it creates blobs with `encoding: base64`, so binary files
(PNGs, zips, etc.) commit correctly — unlike the contents API / some MCP wrappers
that store the payload as a UTF-8 text blob.

Usage:
  python3 github_push.py --owner O --repo R --branch B --message "msg" --manifest files.json

manifest files.json: JSON array of objects, each either
  {"path": "repo/dir/file.md", "local": "/abs/local/path"}      # read bytes from local file (text or binary)
  {"path": "repo/dir/file.md", "content": "inline text content"} # inline UTF-8 text
"path" is the destination path inside the repo.

Prints the new commit sha + html_url on success; exits non-zero on failure.
"""
import argparse, base64, json, os, sys, time
import requests

API = "https://api.github.com"


def _headers():
    tok = os.environ.get("GITHUB_TOKEN")
    if not tok:
        print("ERROR: GITHUB_TOKEN not set in environment", file=sys.stderr)
        sys.exit(2)
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "hyperagent-github-push-pat",
    }


def _req(method, url, **kw):
    """HTTP with light retry on 5xx/429."""
    for attempt in range(4):
        r = requests.request(method, url, headers=_headers(), timeout=60, **kw)
        if r.status_code < 500 and r.status_code != 429:
            return r
        time.sleep(2 * (attempt + 1))
    return r


def _die(msg, r=None):
    print(f"ERROR: {msg}", file=sys.stderr)
    if r is not None:
        print(f"  HTTP {r.status_code}: {r.text[:500]}", file=sys.stderr)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--message", required=True)
    ap.add_argument("--manifest", required=True, help="JSON array of {path, local|content}")
    a = ap.parse_args()

    files = json.load(open(a.manifest, encoding="utf-8"))
    if not files:
        _die("manifest is empty")
    base = f"{API}/repos/{a.owner}/{a.repo}"

    # 1) current branch head commit
    r = _req("GET", f"{base}/git/ref/heads/{a.branch}")
    if r.status_code != 200:
        _die(f"could not read branch '{a.branch}' (does it exist? token scope?)", r)
    base_commit = r.json()["object"]["sha"]

    # 2) base tree
    r = _req("GET", f"{base}/git/commits/{base_commit}")
    if r.status_code != 200:
        _die("could not read base commit", r)
    base_tree = r.json()["tree"]["sha"]

    # 3) one base64 blob per file (handles text + binary uniformly)
    tree_entries = []
    for f in files:
        path = f["path"]
        if "local" in f:
            data = open(f["local"], "rb").read()
        else:
            data = f.get("content", "").encode("utf-8")
        b64 = base64.b64encode(data).decode("ascii")
        rb = _req("POST", f"{base}/git/blobs", json={"content": b64, "encoding": "base64"})
        if rb.status_code not in (200, 201):
            _die(f"blob create failed for {path}", rb)
        tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": rb.json()["sha"]})

    # 4) new tree on top of base
    rt = _req("POST", f"{base}/git/trees", json={"base_tree": base_tree, "tree": tree_entries})
    if rt.status_code not in (200, 201):
        _die("tree create failed", rt)
    new_tree = rt.json()["sha"]

    # 5) commit
    rc = _req("POST", f"{base}/git/commits",
              json={"message": a.message, "tree": new_tree, "parents": [base_commit]})
    if rc.status_code not in (200, 201):
        _die("commit create failed", rc)
    new_commit = rc.json()["sha"]

    # 6) move the branch ref
    rp = _req("PATCH", f"{base}/git/refs/heads/{a.branch}", json={"sha": new_commit, "force": False})
    if rp.status_code not in (200, 201):
        _die("ref update failed", rp)

    print(json.dumps({
        "ok": True,
        "commit": new_commit,
        "html_url": f"https://github.com/{a.owner}/{a.repo}/commit/{new_commit}",
        "files": len(files),
        "branch": a.branch,
    }, indent=2))


if __name__ == "__main__":
    main()
