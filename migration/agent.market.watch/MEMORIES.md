# Attached memories (1)

## Macro Monitor blackboard — read via file slice, never whole
- id: cmqijatqh010708advjosyj2v
- category: tools_and_workflows
- importance: 4

### Content
The Macro Monitor blackboard (doc cmq5rqdws16qq06adoiw88r03) is a large JSON document whose full ReadDocument output exceeds token limits and externalizes to a file. Do NOT read the whole doc into context. Instead: ReadDocument returns a file path; parse that file as JSON with node, locate the sections array, and slice only your own domain section (e.g. find a section whose name matches 'Financial Conditions') to dedup against last-logged levels. Section names in order: How this doc works | Inflation | Labor | Growth & Activity | Housing | Sentiment & Surveys | Central Banks & Policy | Financial Conditions & Markets | 3rd-Party Analysis (external) | Macro Synthesis.

### whenToUse
Use when running macro-swarm collectors or Market Watch tasks that need to read or update the Macro Monitor blackboard without exceeding token limits by parsing the externalized JSON file and slicing specific domain sections.
