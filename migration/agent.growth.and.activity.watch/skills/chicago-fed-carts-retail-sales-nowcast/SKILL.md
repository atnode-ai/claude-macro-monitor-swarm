# Chicago Fed CARTS — Retail Sales Nowcast

Fetches and parses the **Chicago Fed Advance Retail Trade Summary (CARTS)** — a weekly, mixed-frequency **model nowcast** of U.S. Census Bureau retail & food services sales **excluding motor vehicles & parts ("ex. auto")**. CARTS projects month-over-month growth in two forms — **nominal (seasonally adjusted)** and **inflation-adjusted** — giving an early, high-frequency read on consumer demand ahead of the official Census retail-sales release.

**No credentials required — CARTS is free, public data.**

## What it measures
- Combines eight weekly indicators — payment-card transactions (Bloomberg Second Measure, Consumer Edge, Facteus, Numerator, SafeGraph), foot traffic (Advan Research), EIA gasoline sales, and Morning Consult consumer sentiment — with Census MRTS/MARTS monthly data via a **mixed-frequency dynamic factor model**, producing a Weekly Index of Retail Trade that, aggregated to a month, benchmarks to Census data.
- The inflation leg uses a mixed-frequency VAR over the BEA ex-auto chain-weighted price index, BLS CPI commodities ex-autos, EIA weekly gas prices, State Street PriceStats online prices, and the Adobe/Numerator price indices.
- Output: projected **m/m % change** in ex-auto retail & food services sales — **nominal SA** and **inflation-adjusted**.

## Release cadence
Published at **8:30 a.m. ET**, **twice a month**:
- **Preliminary** — near month-end, summarizing weekly data through ~mid-month.
- **Final** — the **day before** the Census Bureau's Advance Retail Sales release, summarizing data through the end of the prior month.

Canonical PDF (overwritten each release): `https://www.chicagofed.org/-/media/publications/carts/carts.pdf`
Live data page (JS chart, not plain-fetchable): `https://www.chicagofed.org/research/data/carts/current-data`
About / methodology: `https://www.chicagofed.org/research/data/carts/about`

## Where it sits in the macro chain
CARTS is **one step upstream of "Retail Sales → GDP."** It is a *leading preview* of the same ex-auto retail & food services number the Census Advance Retail Sales report measures — available a day to ~two weeks earlier and at higher frequency. Consumer spending is ~two-thirds of GDP, so a turn in CARTS is an early read on demand. Treat it as a **nowcast/preview**, not an independent indicator: it is a model output (no market consensus) and previews — does not replace — the official print.

## Script: `carts_nowcast.py`
Downloads the latest CARTS PDF (cache-busted so you always get the freshest release), extracts text with `pypdf`, and returns structured fields.

**Dependencies:** stdlib `urllib` for the fetch (honors the sandbox `HTTPS_PROXY`); `pypdf` for PDF text extraction (the script auto-installs it via pip if missing). No API key.

**Usage:**
```
python3 carts_nowcast.py            # human-readable summary + JSON
python3 carts_nowcast.py --json     # JSON only (machine-readable)
python3 carts_nowcast.py --save carts.pdf   # also keep the downloaded PDF
python3 carts_nowcast.py --pdf local.pdf    # parse a local PDF (offline)
```

**Output JSON schema:**
```
{
  "source", "source_url", "pdf_url", "fetched_at",
  "release_date":         e.g. "March 16, 2026",
  "reference_month":      e.g. "February"  (the month being projected),
  "projection": { "nominal_sa_pct": 0.1, "inflation_adjusted_pct": -0.1 },
  "data_available_as_of": e.g. "March 12, 2026",
  "release_type":         "preliminary" | "final" | "unknown"  (inferred),
  "release_type_basis":   why it was classified,
  "recent_monthly_values": {
    "months":                 ["Feb '26","Jan","Dec '25","Nov","Oct","Sep"],
    "sales_ex_auto_pct":      [ ... last 6 m/m % ... ],
    "inflation_adjusted_pct": [ ... last 6 m/m % ... ]
  },
  "headline":             the raw projection sentence,
  "warnings": []
}
```

## Interpreting the output
- **nominal vs inflation-adjusted:** a soft *real* number alongside a firmer *nominal* one means price (often gasoline) is flattering the headline while real volume is weaker — the same energy-vs-core split seen in CPI/PPI.
- **preliminary vs final:** `release_type` is inferred from the data-cutoff date vs the reference month (cutoff after the month ends → final; mid-month cutoff → preliminary). Always also surface `release_date` and `data_available_as_of` so a human can verify.
- The figures are a **model projection** — label them a nowcast, never the official Census print.

## Using it in the macro-monitoring swarm
CARTS belongs to the **Growth & Activity** domain as a leading preview of the existing "Retail Sales (Advance)" line. Log it as a nowcast row with the Consensus column set to "(nowcast — no mkt consensus)". **Alert discipline:** escalate to Slack only when CARTS shows a material divergence ahead of the Census print, or when CARTS and the subsequent hard print confirm the same directional move — otherwise it is doc-only.

## Caveats
- The current-data web page renders its numbers in a JS chart that plain HTTP cannot read — the **PDF is the authoritative parseable source**, which this script uses.
- The PDF is overwritten each release; the script cache-busts and validates the `%PDF-` magic header. If a CDN serves a stale copy, re-run.
- Scope is **ex. auto** (excludes motor vehicles & parts) — do not compare directly to the total retail-sales headline.
- `pypdf` text extraction can occasionally glue tokens; the script parses the authoritative headline sentence for the key figures and treats the 6-month table as best-effort (emits a `warning` if it can't parse it).
