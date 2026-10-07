#!/usr/bin/env python3
"""Render a Hyperagent document (ReadDocument JSON) into Markdown.

Usage:
    python3 render_project_doc.py <doc.json> > PROJECT.md

Input: a JSON file holding the ReadDocument output for a document — an object
with `title`, optional `description`, and `sections` (each with `name`,
`content`, and `order`). Sections that are empty (or only whitespace) are
skipped.

Output: Markdown on stdout — an H1 title, the description, then each non-empty
section as an H2 heading followed by its content, ordered by `order`. The
rendering is deterministic so repeated backups produce stable, reviewable diffs.
"""
import json
import sys


def render(doc):
    lines = []
    lines.append("# " + (doc.get("title") or "Document"))
    desc = (doc.get("description") or "").strip()
    if desc:
        lines.append("")
        lines.append(desc)
    sections = sorted(doc.get("sections", []), key=lambda s: s.get("order", 0))
    for s in sections:
        content = (s.get("content") or "").strip()
        if not content:
            continue
        lines.append("")
        lines.append("## " + (s.get("name") or "Section"))
        lines.append("")
        lines.append(content)
    return "\n".join(lines).rstrip() + "\n"


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: render_project_doc.py <doc.json>")
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        doc = json.load(f)
    sys.stdout.write(render(doc))


if __name__ == "__main__":
    main()
