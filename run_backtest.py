#!/usr/bin/env python
"""
Backtest the confirmation strategy on historical Forex data.

Examples:
    python run_backtest.py                              # EURUSD, 1h, last year
    python run_backtest.py --symbol GBPUSD --interval 4h --period 2y
    python run_backtest.py --symbol all                 # every pair in settings.yaml
    python run_backtest.py --csv data/raw/EURUSD_1h.csv --symbol EURUSD
    python run_backtest.py --start 2025-01-01 --end 2025-12-31 --interval 1d

Notes:
    Yahoo Finance only serves about the last 730 days of 1h/4h data,
    and about 60 days of anything shorter. Use 1d for longer history.
    Results (trades and equity curve CSVs) are written to results/.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.backtest import Backtester, BacktestConfig
from src.config import load_settings
from src.market.data_fetcher import DataFetcher
from src.strategy import ConfirmationStrategy


def parse_args():
    p = argparse.ArgumentParser(description="Backtest the Forex confirmation strategy")
    p.add_argument("--symbol", default="EURUSD", help="Pair such as EURUSD, or 'all' for settings.yaml symbols")
    p.add_argument("--interval", default="1h", help="1h, 4h or 1d (default 1h)")
    p.add_argument("--period", default="1y", help="Yahoo period: 1mo, 3mo, 6mo, 1y, 2y (default 1y)")
    p.add_argument("--start", help="Start date YYYY-MM-DD (overrides --period)")
    p.add_argument("--end", help="End date YYYY-MM-DD")
    p.add_argument("--csv", help="Use a saved CSV (DataFetcher.save_data format) instead of downloading")
    p.add_argument("--config", help="Path to settings.yaml (default config/settings.yaml)")
    p.add_argument("--atr-multiplier", type=float, default=1.5, help="Stop distance in ATRs (default 1.5)")
    p.add_argument("--out", default="results", help="Folder for trade and equity CSVs")
    return p.parse_args()


def load_data(args, symbol: str, fetcher: DataFetcher) -> pd.DataFrame:
    if args.csv:
        return pd.read_csv(args.csv, index_col=0, parse_dates=True)
    return fetcher.fetch_forex_data(symbol, interval=args.interval, period=args.period,
                                    start=args.start, end=args.end)


def main() -> int:
    args = parse_args()
    settings = load_settings(args.config)
    strat_cfg = settings["strategy"]
    risk_cfg = settings["risk_management"]

    symbols = settings["trading"].get("symbols", ["EURUSD"]) if args.symbol.lower() == "all" else [args.symbol.upper()]
    fetcher = DataFetcher()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []

    for symbol in symbols:
        data = load_data(args, symbol, fetcher)
        valid, message = fetcher.validate_data(data)
        if not valid:
            print(f"[{symbol}] skipped: {message} (check the symbol, dates and your internet connection)")
            continue

        strategy = ConfirmationStrategy(
            min_confirmation_signals=int(strat_cfg.get("entry_confirmation_count", 2)),
            atr_multiplier=args.atr_multiplier,
            risk_reward_ratio=float(risk_cfg.get("min_risk_reward_ratio", 1.5)),
        )
        backtester = Backtester(strategy, BacktestConfig.from_settings(settings),
                                performance_thresholds=settings["performance"])
        result = backtester.run(data, symbol=symbol)
        print(result.report())

        tag = f"{symbol}_{args.interval}"
        if not result.trades.empty:
            result.trades.to_csv(out_dir / f"{tag}_trades.csv", index=False)
        result.equity.to_csv(out_dir / f"{tag}_equity.csv")
        summary.append((symbol, result.stats))

    if len(summary) > 1:
        print("\nSUMMARY")
        print(f"{'Pair':<8}{'Trades':>8}{'Win %':>8}{'PF':>7}{'Return %':>10}{'Max DD %':>10}")
        for symbol, s in summary:
            pf = "inf" if s["profit_factor"] == float("inf") else f"{s['profit_factor']:.2f}"
            print(f"{symbol:<8}{s['total_trades']:>8}{s['win_rate'] * 100:>8.1f}{pf:>7}"
                  f"{s['total_return_percent']:>10.2f}{s['max_drawdown_percent']:>10.2f}")

    if summary:
        print(f"\nTrade logs and equity curves saved to {out_dir}/")
    return 0 if summary else 1


if __name__ == "__main__":
    sys.exit(main())
