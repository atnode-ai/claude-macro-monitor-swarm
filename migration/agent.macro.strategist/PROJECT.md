# Substack.extractor

_Project document for Substack.extractor_

## Goals

To extract substack blog entries to markdown files

## Critical Facts

- Source project: timf34/Substack2Markdown (MIT License, Python). Upstream supports free scraping (requests + BeautifulSoup + html2text) and premium scraping (Selenium + login via config.py with EMAIL/PASSWORD; needs Chrome/Edge).
- This project ships an adapted, sandbox-friendly free-content scraper at skills/substack-to-markdown/substack_to_markdown.py. No Selenium, no login; works in the HTTP/HTTPS-proxied sandbox.
- Premium/paywalled posts cannot be scraped in this sandbox (no browser, no credentials). They are auto-detected (h2.paywall-title) and skipped. Premium requires running the upstream tool locally.
- Runtime dependencies: requests, beautifulsoup4, html2text, markdown, tqdm. Install with pip at run time.
- Extraction selectors (mirrored from upstream): title h1.post-title/h2; subtitle h3.subtitle; date/author/cover-image from ld+json; likes div.like-button-container button div.label; body div.available-content. HTML to markdown via html2text (ignore_links=False, body_width=0).

## Research & Findings

_Accumulated research and discoveries._

## Decisions

- Scope the in-sandbox skill to FREE content only; document premium as a local-only path (browser + user's Substack credentials required). Approved by user on 2026-06-08.
- Improve post discovery over upstream: prefer the Substack archive API (<pub>/api/v1/archive?sort=new) so --number reliably grabs the newest N; fall back to sitemap.xml, then feed.xml.
- Restrict discovered URLs to real posts (must contain /p/) and skip about/archive/podcast pages.
- Output layout: <output-dir>/<writer>/<slug>.md plus a _manifest.json of metadata; optional images saved under <writer>/images/<slug>/ with markdown links rewritten to relative paths.
- Verified working in-sandbox against astralcodexten.substack.com: whole-publication (newest N), single /p/ post, legacy and mdx frontmatter, and image download + link rewrite.

## Tasks

### Todo

_Add tasks here._

### In Progress

### Done

**Done — 2026-06-08:**
- Extracted danielsan2401 "MACRO ECONOMICS: The Complete Guide to Economic Data Releases" (free, 2026-04-26, ~6,800 words, 24 images) to markdown (MDX frontmatter).
- Committed to cloudburostaff/agent.hyperagent.talfco @ main → vault.substack/danielsan2401/ (commit c8cef1b): macro-economics-the-complete-guide.md (image links → Substack CDN so they render inline on GitHub) + _manifest.json.
- Delivered offline ZIP (md with relative links + 24 local PNGs, 765 KB) to the thread.
- OPEN: real PNG binaries not yet in repo (GitHub MCP is text-only). Add via git-over-HTTPS+PAT or GitHub web upload.

**Done — 2026-06-08 (Phase 2, table OCR):**
- The 24 post images were screenshots of tables. Transcribed all 24 to markdown text tables via vision (one file per image), then replaced every image link in the markdown with its table. Verified: 24/24 replaced, 0 image links remaining, 24/24 tables used once, frontmatter + body + conclusion intact.
- Re-committed text-only markdown to cloudburostaff/agent.hyperagent.talfco @ main → vault.substack/danielsan2401/macro-economics-the-complete-guide.md (commit 9b11916). Now fully text-based, so the GitHub binary limitation no longer applies.
- Minor fidelity notes: corrected one obvious source typo ("Participaton"→"Participation"); kept source's "(NDCA)" abbreviation as shown. Internal "|" separators escaped as "\|" so cells render correctly.

**Done — 2026-06-08 (Phase 3, source links):**
- Added an "Official release" row to each of the 23 report reference cards, linking to the agency page where that specific report is published/downloadable (Master Cross-Indicator table skipped — it is a synthesis). 28 links total (some cards have 2-3 sources: Jobless Claims, FOMC Minutes & Fed Speeches, BoE & ECB, Home Sales).
- All URLs verified to resolve. Fixes: BoE Monetary Policy Report URL was 404 -> used https://www.bankofengland.co.uk/monetary-policy; ISM Report On Business confirmed publicly accessible via browser (bot UA gets SSO-redirected); Jobless Claims uses DOLETA weekly-claims page + dol.gov/ui/data.pdf; BLS news.release pages return 403 to bots but are the correct canonical URLs.
- Re-committed to cloudburostaff/agent.hyperagent.talfco @ main → vault.substack/danielsan2401/macro-economics-the-complete-guide.md (commit eda03b4).

**Done — 2026-06-08 (Phase 4, swarm implementation v1):**
- Created project-scoped blackboard doc "Macro Monitor — Blackboard" (id cmq5rqdws16qq06adoiw88r03): 6 domain sections (Inflation, Labor, Growth & Activity, Housing, Sentiment & Surveys, Central Banks & Policy) + Macro Synthesis, each seeded with the Report|Latest date|Actual|Consensus|Surprise|Read schema.
- Built two agent DRAFTS (await user save in UI): Inflation Watch (draft 6uHmK0nD; live mode 60min, deliver slack_channel C0B8B76L7NH, watches CPI/PPI/PCE, writes blackboard) and Macro Strategist orchestrator (draft iFHKFJPd; scheduled daily 17:00 ET wrap + Sunday look-ahead, reads blackboard, applies cross-indicator chain, owns Slack alerts).
- Tools were intentionally left to the card defaults; user must confirm Web fetch/search, Browser, Slack, and Document read/write are enabled when saving. Remaining 5 domain agents are clones of Inflation Watch (swap sources/lens/section), to generate on go-ahead.

**Done — 2026-06-08 (Phase 4 cont., cloned domains):**
- Cloned the 5 remaining domain agent DRAFTS from the Inflation Watch template (await user save in UI): Labor Watch (fehQwyVN), Growth & Activity Watch (ip0I4cZZ), Housing Watch (1T86eqlx), Sentiment & Surveys Watch (pVd37AVW), Central Banks & Policy Watch (apTVeHdF). All: executionMode auto, live-mode 60min watch, deliver slack_channel C0B8B76L7NH, write to their blackboard section (doc cmq5rqdws16qq06adoiw88r03), dedup against last logged date.
- Inflation Watch was re-issued fresh (db3cqJff) after the original card went 'outdated'. Macro Strategist orchestrator is saved/live (this thread runs as it).
- Full swarm now: 6 domain collectors + orchestrator + blackboard. User must save each domain card and confirm Web/Browser/Slack/Document tools are enabled.

## Notes

_Miscellaneous notes and observations._

**Proposed macro-monitoring swarm architecture (under discussion, 2026-06-08):**
Recommendation: do NOT build one agent per report (23+ agents = noise, cost, no cross-view). Use a 3-tier design:
- Domain = AGENT (~6): Inflation, Labor, Growth & Activity (incl. Trade), Housing, Sentiment & Surveys, Central Banks & Policy.
- Report = SCHEDULED INVOCATION on its domain agent (rrule timed to that report's release calendar). This gives per-report timing without per-report agents.
- Macro = ORCHESTRATOR agent ("Macro Strategist") that fans-in domain digests and applies the Master Cross-Indicator (leads/lags) table as its reasoning spec.
Coordination = blackboard via a shared project doc (one section per domain; orchestrator reads all, writes synthesis). Alerts to Slack #hyper-asset-monitoring (C0B8B76L7NH): domain agents log routinely, orchestrator fires the "this matters" alerts on surprises/regime change. Each agent backs up to GitHub agent.<slug> per existing convention.
