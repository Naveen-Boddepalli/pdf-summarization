# Report → Dense Synthesis + Charts

Turns any PDF report (100s of pages) into:
- `synthesis.md` — a 20-30 page dense, expert-level synthesis preserving all data
- `visuals/figures.md` — all charts described with markdown tables
- `visuals/chart_*.png` — auto-generated chart images from extracted data

**100% free** — use any local model or online model (with api key) + open-source Python libs.

---

## Quickstart

### 1. Get a free Gemini API key
Go to https://aistudio.google.com → sign in → "Get API key" → copy it. (change the function as per the model)

or 

add the model running on your local machine.

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your API key
```bash
cp .env.example .env
# Edit .env and paste your key
```

### 4. Run on a report
```bash
python pipeline.py reports/your_report.pdf
```

### 5. Find your output
```
output/
└── your_report/
    ├── synthesis.md        ← 20-30 page synthesis
    └── visuals/
        ├── figures.md      ← chart descriptions + data tables
        ├── chart_01_*.png
        ├── chart_02_*.png
        └── ...
```

---

## Folder Structure

```
report-to-synthesis/
├── reports/              ← drop PDF files here
├── output/               ← generated output appears here
├── agents/
│   ├── extractor.py      ← extracts all data from PDF chunks
│   ├── analyst.py        ← finds insights + emits chart specs
│   ├── synthesizer.py    ← writes the dense synthesis doc
│   └── chart_generator.py← renders chart PNGs from JSON specs
├── n8n/
│   └── workflow.json     ← import into n8n for auto-triggering
├── pipeline.py           ← main script — run this
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## How it works

1. **PyMuPDF** reads the PDF and splits it into ~5-page chunks
2. **Extractor agent** processes each chunk — extracts every number, table, and finding
3. **Analyst agent** finds themes, causal chains, contradictions, and emits JSON chart specs
4. **Synthesizer agent** writes the 20-30 page synthesis MD
5. **Analyst agent** (second pass) writes the figures.md with data tables
6. **chart_generator.py** parses the JSON specs and renders PNG charts with matplotlib

---

## Supported chart types

| chart_type | Description |
|---|---|
| `bar` | Single-series vertical bar |
| `grouped_bar` | Multi-series grouped bar |
| `line` | Single or multi-series line |
| `pie` | Pie / donut |
| `horizontal_bar` | Horizontal bar (good for rankings) |

---

## n8n automation (optional)

To auto-trigger on new files:
1. Start n8n: `npx n8n`
2. Open http://localhost:5678
3. Import `n8n/workflow.json`
4. Set the `PROJECT_DIR` env var to this project's path
5. Drop a PDF into `reports/` — pipeline runs automatically

---

## Tips for large reports (200+ pages)

- Gemini 1.5 Flash handles up to 1 million tokens — most reports fit in one call
- OR your local model can handle it as we will make it into chunks as per model
- The pipeline chunks automatically so nothing gets cut off
- For very large reports, expect 5-10 minutes total runtime
- All API calls are within Gemini's free tier (1500 requests/day)

---

## Costs

**Zero.** Everything used here is free:
- Gemini 1.5 Flash: free tier (15 req/min, 1500 req/day) or Groq API
- PyMuPDF: open source
- CrewAI: open source
- matplotlib / pandas: open source
- n8n self-hosted: free
