#!/usr/bin/env python
"""
Plot equity curves saved by run_backtest.py.

    python plot_equity.py results/                       # -> results/equity_curves.png
    python plot_equity.py /tmp/r1 reports/equity_curves.png --title "Realistic costs"
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display needed (servers, GitHub Actions)
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

COLORS = ["#2563eb", "#ea580c", "#059669", "#9333ea", "#dc2626", "#0891b2", "#ca8a04"]


def load_curves(folder: Path) -> dict:
    curves = {}
    for path in sorted(folder.glob("*_equity.csv")):
        series = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
        curves[path.stem.replace("_equity", "").replace("_", " ")] = series
    return curves


def plot(curves: dict, out: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 5.5), dpi=120)
    start = next(iter(curves.values())).iloc[0]
    for (name, series), color in zip(curves.items(), COLORS):
        final = series.iloc[-1]
        change = (final / series.iloc[0] - 1) * 100
        ax.plot(series.index, series.values, color=color, linewidth=1.6,
                label=f"{name}  {change:+.1f}%  (${final:,.0f})")
    ax.axhline(start, color="#6b7280", linewidth=1, linestyle="--", alpha=0.7)
    ax.set_title(title, fontsize=13, loc="left", pad=12)
    ax.set_ylabel("Account balance (USD)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("${x:,.0f}"))
    locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.grid(alpha=0.25)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=9)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser(description="Plot backtest equity curves")
    p.add_argument("folder", help="Folder containing *_equity.csv files from run_backtest.py")
    p.add_argument("output", nargs="?", help="PNG path (default: <folder>/equity_curves.png)")
    p.add_argument("--title", default="Account balance by pair")
    args = p.parse_args()

    folder = Path(args.folder)
    curves = load_curves(folder)
    if not curves:
        print(f"No *_equity.csv files in {folder}")
        return 1
    out = Path(args.output) if args.output else folder / "equity_curves.png"
    plot(curves, out, args.title)
    print(f"Saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
