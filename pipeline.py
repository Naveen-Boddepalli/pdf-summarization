"""
pipeline.py  —  Report → Dense Synthesis + Charts
================================================
Usage:
    python pipeline.py "reports/skipper_2025.pdf"

Output:
    output/<ReportTitle>/
        synthesis.md          ← 20-30 page dense synthesis
        visuals/
            figures.md        ← all charts described + markdown tables
            chart_01_*.png    ← auto-generated chart PNGs

Strategy:
    - Uses LOCAL Ollama model (qwen2.5:3b) — 100% free, no API key
    - Only 4-6 LLM calls total regardless of report size
    - No rate limits — runs entirely on your machine
    - Chunks large docs to fit qwen2.5:3b context window (~4k tokens)

Requirements:
    pip install pymupdf python-dotenv openai matplotlib pandas
    Ollama must be running: ollama serve
    Model must be pulled: ollama pull qwen2.5:3b
"""

import pathlib
import sys
import time

import fitz
from dotenv import load_dotenv
from openai import OpenAI

from agents.chart_generator import generate_all_charts

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
CALL_DELAY = 0  # no rate limit — local model
MAX_CHARS = 12_000  # qwen2.5:3b has small context; safe chunk size
MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434/v1"


# ── Setup ─────────────────────────────────────────────────────────────────────
def setup_ollama() -> OpenAI:
    # No API key needed for Ollama — just connect to local server
    client = OpenAI(api_key="ollama", base_url=OLLAMA_URL)
    # Verify Ollama is running
    try:
        client.models.list()
    except Exception:
        sys.exit(
            "\n[ERROR] Cannot connect to Ollama at localhost:11434\n"
            "Make sure Ollama is running: open a new terminal and run: ollama serve\n"
        )
    return client


def call_ollama(client: OpenAI, prompt: str, step_name: str) -> str:
    """Single Ollama call — no rate limits, no retries needed."""
    print(f"  Calling Ollama ({MODEL}): {step_name}...")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.1,
        )
        text = response.choices[0].message.content
        print(f"  ✓ {step_name} complete ({len(text):,} chars returned)")
        return text
    except Exception as e:
        raise RuntimeError(f"Failed during {step_name}") from e


# ── PDF Reading ───────────────────────────────────────────────────────────────
def read_pdf(path: str) -> str:
    doc = fitz.open(path)
    text = "\n".join(page.get_text() for page in doc)
    print(f"  Pages : {len(doc)}")
    print(f"  Chars : {len(text):,}")
    return text


# ── Prompts ───────────────────────────────────────────────────────────────────


def prompt_extract(text: str) -> str:
    return f"""You are a forensic data extraction specialist. Your job is lossless extraction.

Read this report section and extract EVERYTHING without summarizing or paraphrasing:

1. Every statistic, percentage, number, ratio, date, and unit of measure — with full context
2. Every table — reproduce in markdown table format exactly as it appears
3. Every chart or figure — describe it fully and state the data values behind it
4. Every methodology detail: sample sizes, confidence intervals, data sources
5. Every finding, conclusion, and recommendation — verbatim where possible
6. All named entities: companies, people, products, countries, regions

Output as structured markdown with clear section headings matching the report.
Do NOT compress, summarize, or drop any detail. This is a reference extraction.

REPORT TEXT:
---
{text}
---
"""


def prompt_analyse(extraction: str, title: str) -> str:
    return f"""You are a senior research analyst. Perform deep analysis of this extracted report data.

Report title: {title}

Produce the following sections:

## 1. Top 10 Critical Insights
Each insight must cite a specific number or statistic from the data.

## 2. Causal Chain Map
Format: Driver → Effect → Outcome (with supporting data at each step)
List at least 5 causal chains.

## 3. Cross-Cutting Themes
5-6 major themes that appear across multiple sections, each with supporting data points.

## 4. Contradictions & Data Gaps
Where the report's own data conflicts with itself, or where key data is missing.

## 5. Chart Specifications
For every dataset that should be visualized, emit a JSON spec in a fenced code block.

Single-series bar chart:
```json
{{"chart_type": "bar", "title": "...", "xlabel": "...", "ylabel": "...", "categories": [...], "values": [...]}}
```

Multi-series grouped bar:
```json
{{"chart_type": "grouped_bar", "title": "...", "xlabel": "...", "ylabel": "...", "categories": [...], "series": [{{"name": "...", "values": [...]}}]}}
```

Line chart:
```json
{{"chart_type": "line", "title": "...", "xlabel": "...", "ylabel": "...", "series": [{{"name": "...", "x": [...], "y": [...]}}]}}
```

Pie chart:
```json
{{"chart_type": "pie", "title": "...", "categories": [...], "values": [...]}}
```

Horizontal bar:
```json
{{"chart_type": "horizontal_bar", "title": "...", "xlabel": "...", "ylabel": "...", "categories": [...], "values": [...]}}
```

EXTRACTED DATA:
---
{extraction}
---
"""


def prompt_synthesize(extraction: str, analysis: str, title: str) -> str:
    return f"""You are a technical synthesis writer. Write a dense, expert-level reference document in markdown.
Target length: 20-30 pages. Preserve EVERY number, table, and finding. Do not compress.

Use this exact structure:

# {title} — Synthesis

## Executive Summary
2-3 paragraphs. Most critical findings with the top 5 numbers called out explicitly.

## Methodology & Scope
Sample sizes, date ranges, geographies, data sources, known limitations.

## Section-by-Section Findings
One subsection (###) per major report section. For each:
- Preserve ALL statistics with units
- Reproduce every table in markdown format  
- Use > blockquote for the single most critical insight per section
- Use **bold** for all key numbers inline

## Cross-Cutting Themes
Each theme with data from multiple sections proving it.

## Causal Chain Analysis
Use A → B → C format with data at each node.

## Contradictions & Data Gaps
Where the report conflicts with itself or lacks data.

## Recommendations
Numbered list, verbatim or near-verbatim from the report.

## Raw Data Index
Every single number from the report, indexed:
[N] Context description: value unit (section)

---
EXTRACTION:
{extraction}

ANALYSIS:
{analysis}
---
"""


def prompt_figures(extraction: str) -> str:
    return f"""You are a data visualization specialist.

From the extraction below, create a complete visuals reference file.

For EVERY chart, graph, figure, or data table in the report, output:

## Figure N — [Exact title]

**Type:** bar / line / pie / table / etc
**Description:** What this visual shows (2-3 sentences)
**Key Insight:** The single most important thing this visual proves

Reproduce the data as a markdown table:
| Col | Col |
|-----|-----|
| ... | ... |

Then emit a JSON chart spec in a fenced code block for auto-rendering:
```json
{{"chart_type": "bar|line|pie|grouped_bar|horizontal_bar",
  "title": "...", "xlabel": "...", "ylabel": "...",
  "categories": [...], "values": [...]}}
```

---

EXTRACTION:
{extraction}
---
"""


# ── Chunked extraction for very large docs ────────────────────────────────────
def extract_text(client: OpenAI, text: str) -> str:
    """
    If the doc fits in one call, extract it in one shot.
    If too large, split into chunks, extract each, then merge.
    qwen2.5:3b has a small context window. MAX_CHARS is the safe chunk size.
    """
    if len(text) <= MAX_CHARS:
        return call_ollama(client, prompt_extract(text), "full document extraction")

    # Split into chunks
    chunks = [text[i : i + MAX_CHARS] for i in range(0, len(text), MAX_CHARS)]
    print(f"  Doc too large for one call → splitting into {len(chunks)} chunks")

    results = []
    for i, chunk in enumerate(chunks, 1):
        result = call_ollama(
            client,
            prompt_extract(chunk),
            f"extraction {i}/{len(chunks)}",
        )
        results.append(result)
        if i < len(chunks):
            print(f"  Waiting {CALL_DELAY}s before next chunk...")
            time.sleep(CALL_DELAY)

    return "\n\n---NEXT SECTION---\n\n".join(results)


# ── Main ──────────────────────────────────────────────────────────────────────
def run(pdf_path: str) -> None:
    p = pathlib.Path(pdf_path)
    title = p.stem.replace("_", " ").title()

    print(f"\n{'='*60}")
    print(f"  Report : {p.name}")
    print(f"  Title  : {title}")
    print(f"{'='*60}\n")

    # Output dirs
    out_dir = pathlib.Path("output") / p.stem
    visuals_dir = out_dir / "visuals"
    out_dir.mkdir(parents=True, exist_ok=True)
    visuals_dir.mkdir(exist_ok=True)

    client = setup_ollama()
    raw_text = read_pdf(pdf_path)

    # ── Step 1: Extract
    print("\n[1/4] Extracting all data from report...")
    extraction = extract_text(client, raw_text)
    (out_dir / "_extraction_raw.txt").write_text(extraction, encoding="utf-8")
    print(f"  Extraction saved: {len(extraction):,} chars")

    # ── Step 2: Analyse
    print(f"\n[2/4] Analysing... (waiting {CALL_DELAY}s)")
    time.sleep(CALL_DELAY)
    analysis = call_ollama(
        client,
        prompt_analyse(extraction[:MAX_CHARS], title),
        "deep analysis",
    )
    (out_dir / "_analysis_raw.txt").write_text(analysis, encoding="utf-8")

    # ── Step 3: Synthesize
    print(f"\n[3/4] Writing synthesis... (waiting {CALL_DELAY}s)")
    time.sleep(CALL_DELAY)
    synthesis = call_ollama(
        client,
        prompt_synthesize(extraction[:MAX_CHARS], analysis[:80_000], title),
        "synthesis document",
    )

    # ── Step 4: Figures
    print(f"\n[4/4] Extracting figures & chart specs... (waiting {CALL_DELAY}s)")
    time.sleep(CALL_DELAY)
    figures_md = call_ollama(
        client,
        prompt_figures(extraction[:MAX_CHARS]),
        "figures and charts",
    )

    # ── Render charts from JSON specs
    print("\n  Rendering chart PNGs...")
    generated_charts = generate_all_charts(figures_md, visuals_dir)

    chart_index = ""
    if generated_charts:
        chart_index = "\n\n---\n\n## Generated Chart Files\n\n"
        for fname in generated_charts:
            chart_index += f"![{fname}](visuals/{fname})\n\n"

    # ── Save final outputs
    (out_dir / "synthesis.md").write_text(synthesis, encoding="utf-8")
    (visuals_dir / "figures.md").write_text(figures_md + chart_index, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  Done!")
    print(f"  Synthesis  → output/{p.stem}/synthesis.md")
    print(f"  Figures    → output/{p.stem}/visuals/figures.md")
    if generated_charts:
        print(f"  Charts     → {len(generated_charts)} PNG(s) in output/{p.stem}/visuals/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python pipeline.py "reports/your_report.pdf"')
        sys.exit(1)
    run(sys.argv[1])
