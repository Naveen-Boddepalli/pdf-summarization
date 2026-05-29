"""
chart_generator.py
Parses JSON chart specs from the analyst output and renders them as
.png files using matplotlib. 100% free, no API calls.
"""

import json
import re
import matplotlib
matplotlib.use("Agg")  # headless — no display required
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from pathlib import Path

# ── Global style ──────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  "#ffffff",
    "axes.facecolor":    "#f8f8f6",
    "axes.edgecolor":    "#cccccc",
    "axes.grid":         True,
    "grid.color":        "#e0e0e0",
    "grid.linewidth":    0.6,
    "font.family":       "sans-serif",
    "font.size":         11,
    "axes.titlesize":    13,
    "axes.titleweight":  "bold",
    "axes.labelsize":    11,
    "xtick.labelsize":   10,
    "ytick.labelsize":   10,
    "legend.fontsize":   10,
    "legend.framealpha": 0.8,
})

PALETTE = ["#1D9E75", "#534AB7", "#D85A30", "#185FA5", "#BA7517",
           "#993556", "#0F6E56", "#3C3489", "#993C1D", "#0C447C"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _finish(fig, ax, spec: dict, path: Path):
    title = spec.get("title", path.stem.replace("_", " "))
    ax.set_title(title)
    if spec.get("xlabel"):
        ax.set_xlabel(spec["xlabel"])
    if spec.get("ylabel"):
        ax.set_ylabel(spec["ylabel"])
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"    Saved chart → {path.name}")


def _sanitize_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", s)[:60]


# ── Chart renderers ───────────────────────────────────────────────────────────

def render_bar(spec: dict, path: Path):
    categories = spec.get("categories", [])
    values     = spec.get("values", [])
    if not categories or not values:
        print(f"    Skipping bar chart (no data): {spec.get('title')}")
        return

    fig, ax = plt.subplots(figsize=(max(6, len(categories) * 0.9 + 2), 4))
    bars = ax.bar(categories, values,
                  color=PALETTE[:len(values)], width=0.6, zorder=3)

    # value labels on top of bars
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.01,
            f"{val:,}" if isinstance(val, int) else f"{val:.2f}",
            ha="center", va="bottom", fontsize=9
        )

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"{x:,.0f}" if x >= 1000 else f"{x:g}"
    ))
    _finish(fig, ax, spec, path)


def render_grouped_bar(spec: dict, path: Path):
    """
    spec["series"] = [{"name": "2023", "values": [...]}, ...]
    spec["categories"] = ["APAC", "EMEA", ...]
    """
    series     = spec.get("series", [])
    categories = spec.get("categories", [])
    if not series or not categories:
        print(f"    Skipping grouped bar (no data): {spec.get('title')}")
        return

    df = pd.DataFrame({s["name"]: s["values"] for s in series}, index=categories)
    fig, ax = plt.subplots(figsize=(max(7, len(categories) * 1.2 + 2), 4))
    df.plot(kind="bar", ax=ax, color=PALETTE[:len(series)], width=0.7,
            zorder=3, edgecolor="white", linewidth=0.4)
    ax.set_xticklabels(categories, rotation=30, ha="right")
    ax.legend(loc="upper right")
    _finish(fig, ax, spec, path)


def render_line(spec: dict, path: Path):
    series = spec.get("series", [])
    if not series:
        print(f"    Skipping line chart (no data): {spec.get('title')}")
        return

    fig, ax = plt.subplots(figsize=(9, 4))
    for i, s in enumerate(series):
        x = s.get("x", list(range(len(s.get("y", [])))))
        y = s.get("y", [])
        ax.plot(x, y, marker="o", markersize=5,
                color=PALETTE[i % len(PALETTE)], linewidth=2,
                label=s.get("name", f"Series {i+1}"))

    if len(series) > 1:
        ax.legend()
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"{x:,.0f}" if x >= 1000 else f"{x:g}"
    ))
    _finish(fig, ax, spec, path)


def render_pie(spec: dict, path: Path):
    labels = spec.get("categories", spec.get("labels", []))
    values = spec.get("values", [])
    if not labels or not values:
        print(f"    Skipping pie chart (no data): {spec.get('title')}")
        return

    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct="%1.1f%%",
        colors=PALETTE[:len(values)], startangle=140,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5}
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title(spec.get("title", ""))
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"    Saved chart → {path.name}")


def render_horizontal_bar(spec: dict, path: Path):
    categories = spec.get("categories", [])
    values     = spec.get("values", [])
    if not categories or not values:
        print(f"    Skipping hbar (no data): {spec.get('title')}")
        return

    fig, ax = plt.subplots(figsize=(8, max(3, len(categories) * 0.5 + 1)))
    bars = ax.barh(categories, values,
                   color=PALETTE[:len(values)], height=0.6, zorder=3)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + max(values) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}" if isinstance(val, int) else f"{val:.2f}",
            va="center", fontsize=9
        )
    ax.invert_yaxis()
    _finish(fig, ax, spec, path)


# ── Dispatcher ────────────────────────────────────────────────────────────────

RENDERERS = {
    "bar":            render_bar,
    "grouped_bar":    render_grouped_bar,
    "line":           render_line,
    "pie":            render_pie,
    "horizontal_bar": render_horizontal_bar,
    "hbar":           render_horizontal_bar,
}


def render_chart(spec: dict, out_dir: Path, index: int) -> str:
    """Render one chart spec to a PNG. Returns the filename or empty string."""
    chart_type = spec.get("chart_type", "bar").lower().replace(" ", "_")
    renderer   = RENDERERS.get(chart_type, render_bar)
    title_slug = _sanitize_name(spec.get("title", f"chart_{index}"))
    filename   = f"chart_{index:02d}_{title_slug}.png"
    path       = out_dir / filename

    try:
        renderer(spec, path)
        return filename
    except Exception as e:
        print(f"    ERROR rendering chart {index} ({spec.get('title')}): {e}")
        return ""


# ── JSON extractor from analyst text ─────────────────────────────────────────

def extract_chart_specs(text: str) -> list[dict]:
    """
    Pull all JSON objects that contain 'chart_type' from a block of text.
    The analyst is prompted to embed them; this function harvests them.
    """
    specs = []

    # Try ```json ... ``` fenced blocks first
    fenced = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    for raw in fenced:
        try:
            obj = json.loads(raw)
            if "chart_type" in obj:
                specs.append(obj)
        except json.JSONDecodeError:
            pass

    # Fall back to bare {...} blocks if nothing fenced was found
    if not specs:
        bare = re.findall(r"(\{[^{}]*\"chart_type\"[^{}]*\})", text, re.DOTALL)
        for raw in bare:
            try:
                obj = json.loads(raw)
                specs.append(obj)
            except json.JSONDecodeError:
                pass

    return specs


def generate_all_charts(analyst_output: str, visuals_dir: Path) -> list[str]:
    """
    Parse the analyst output for chart specs and render each one.
    Returns a list of generated filenames.
    """
    specs = extract_chart_specs(analyst_output)
    if not specs:
        print("    No chart specs found in analyst output.")
        return []

    print(f"  Found {len(specs)} chart spec(s). Rendering...")
    generated = []
    for i, spec in enumerate(specs, start=1):
        fname = render_chart(spec, visuals_dir, i)
        if fname:
            generated.append(fname)

    return generated
