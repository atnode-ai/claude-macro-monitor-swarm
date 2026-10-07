# Attached memories (A - Labor Watch)

## 1. After UpdateAgentConfig, verify the draft via configFileId
- id: cmq7lkiwy03mw07ad6lql4ztq
- category: tools_and_workflows
- importance: 3
- content: After UpdateAgentConfig, the new draft is stored under a new fileId (returned as configFileId) and is NOT cached locally. To verify the draft field-by-field, call FetchStoredFile with that configFileId, then inspect the JSON with node -e rather than reading the whole file.
- whenToUse: Use this memory when you need to verify an UpdateAgentConfig draft and need to know how to retrieve the new fileId, bypass local cache, and inspect the resulting JSON file.

## 2. DOL jobless-claims PDF 403s; use Trading Economics
- id: cmr3vk95j0m7l07aditxt5gh4
- category: tools_and_workflows
- importance: 4
- content: The DOL weekly jobless-claims PDF (https://www.dol.gov/ui/data.pdf) 403s to all automated fetchers — WebFetch, curl (even with a browser User-Agent) — and the in-browser Chrome PDF viewer exposes no DOM text, so the primary source cannot be read in-sandbox. When the day's release isn't yet search-indexed, confirm the live initial-claims figure, 4-week moving average, and continuing claims from a fast-updating tracker like Trading Economics (https://tradingeconomics.com/united-states/jobless-claims) via BrowserExtract. investing.com and FXStreet both time out under anti-bot. Mark the consensus 'unconfirmed' if it can't be verified rather than guessing.
- whenToUse: When checking the weekly US jobless-claims release (Labor Watch Thursday run) and the DOL PDF blocks fetchers or the figure isn't yet search-indexed.

## 3. Ghost blog preferences / Building the Macro Swarm series
- id: cmr3vkozu0j7k06ad39e6q4k9
- category: preference
- importance: 4
- content: User publishes long-form write-ups to a Ghost-based blog at atnode.ai by copy-pasting content delivered in-thread. For blog deliverables: produce clean copy-paste Markdown (headings + short paragraphs), plus an italicised one-line dek/subtitle (for Ghost's subtitle field) and a blockquote pull-quote. Series identity lives in a Ghost tag/kicker (not repeated in every headline); keep unique/distinctive words leading in the headline and vary the format label. Current series: 'Building the Macro Swarm' (main tag slug building-the-macro-swarm; companion addons carry the second tag building-the-macro-swarm-addon). The plan is split across a lean hub doc 'Blog Series Plan — Building the Macro Swarm' (id cmr2grubh02lk07ad8f9kqjmo) plus four companion docs: Article Outlines (cmssmune4073l07adncf4b7nh), Article Drafts (cmssmw8ek05t307adblozgkyb), Addon Outlines (cmsso5x6u07i907ad53yxoq01), Addon Drafts (cmsso77lx070006adxeu22ble). Pull a companion doc in only when working on that piece; the hub carries the series identity, title convention, publishing log and article/addon plan tables. Default voice: confident, concrete, a touch wry; British spelling with domain/agent proper names kept as deployed (e.g. 'Labor', not 'Labour').
- whenToUse: When drafting, titling, or planning blog articles for the user's Ghost blog, especially the 'Building the Macro Swarm' series.

## 4. Release gate does not handle holiday-shifted releases
- id: cmr3vluuo0jqz07adkzbtpeug
- category: tools_and_workflows
- importance: 4
- content: Labor Watch — the 'Labor Watch — Release Gate' skill anchors NFP on the calendar first Friday and does NOT account for holiday-shifted releases. When a US federal holiday falls in the release window (e.g. July 4 observed on Fri Jul 3 → BLS moved the June Employment Situation to Thu Jul 2), BLS/DOL shift the release date and the gate can under-report due (or flag it on the wrong day). On any run near a US holiday, cross-check the blackboard's own prior 'Current stance' notes (which often pre-flag the shift, e.g. 'June NFP tomorrow (Thu ... holiday calendar shift)') and manually override the gate to check NFP/claims when a shift is plausible. The reference-month/last-logged dedup remains authoritative against double-logging.
- whenToUse: On any Labor Watch scheduled release-check run near a US federal holiday, or when the release gate result seems to disagree with the blackboard's prior stance about an imminent print.
