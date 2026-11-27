"""Performance statistics for a finished backtest."""

from typing import Dict

import numpy as np
import pandas as pd


def max_drawdown_percent(equity: pd.Series) -> float:
    """Largest peak-to-trough fall of the equity curve, in percent."""
    if equity.empty:
        return 0.0
    peaks = equity.cummax()
    drawdowns = (peaks - equity) / peaks * 100
    return float(drawdowns.max())


def sharpe_ratio(equity: pd.Series, periods_per_year: int = 252) -> float:
    """Annualised Sharpe ratio from daily equity returns (risk-free rate 0)."""
    if len(equity) < 3 or not isinstance(equity.index, pd.DatetimeIndex):
        return 0.0
    daily = equity.resample("1D").last().dropna()
    returns = daily.pct_change().dropna()
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * np.sqrt(periods_per_year))


def longest_streak(flags) -> int:
    best = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def compute_metrics(trades: pd.DataFrame, equity: pd.Series, initial_cash: float) -> Dict:
    """Summary statistics; works with zero trades."""
    final_equity = float(equity.iloc[-1]) if not equity.empty else initial_cash
    stats = {
        "initial_cash": initial_cash,
        "final_equity": round(final_equity, 2),
        "total_return_percent": round((final_equity / initial_cash - 1) * 100, 2),
        "max_drawdown_percent": round(max_drawdown_percent(equity), 2),
        "sharpe_ratio": round(sharpe_ratio(equity), 2),
        "total_trades": int(len(trades)),
    }

    if trades.empty:
        stats.update(win_rate=0.0, profit_factor=0.0, avg_win=0.0, avg_loss=0.0,
                     expectancy=0.0, avg_r_multiple=0.0, max_consecutive_losses=0,
                     total_costs=0.0, long_trades=0, short_trades=0)
        return stats

    pnl = trades["pnl"]
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gross_loss = -losses.sum()
    stats.update(
        win_rate=round(len(wins) / len(trades), 4),
        profit_factor=round(wins.sum() / gross_loss, 2) if gross_loss > 0 else float("inf"),
        avg_win=round(wins.mean(), 2) if len(wins) else 0.0,
        avg_loss=round(losses.mean(), 2) if len(losses) else 0.0,
        expectancy=round(pnl.mean(), 2),
        avg_r_multiple=round(trades["r_multiple"].mean(), 2),
        max_consecutive_losses=longest_streak(pnl <= 0),
        total_costs=round(trades["costs"].sum(), 2),
        long_trades=int((trades["direction"] == "long").sum()),
        short_trades=int((trades["direction"] == "short").sum()),
    )
    # Plain floats (not numpy types) so stats print and serialise cleanly
    return {k: (float(v) if isinstance(v, (np.floating,)) else v) for k, v in stats.items()}


def evaluate(stats: Dict, thresholds: Dict) -> Dict[str, bool]:
    """Compare against the `performance:` thresholds in settings.yaml."""
    return {
        "win_rate": stats["win_rate"] >= thresholds.get("min_win_rate", 0.45),
        "profit_factor": stats["profit_factor"] >= thresholds.get("min_profit_factor", 1.5),
        "max_drawdown": stats["max_drawdown_percent"] <= thresholds.get("max_drawdown_acceptable", 15.0),
    }
