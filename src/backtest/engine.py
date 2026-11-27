"""
Bar-by-bar backtesting engine.

How a bar is processed (no look-ahead):
1. If a signal was produced on the previous bar's close, open the trade at this
   bar's OPEN, paying half the spread and slippage. Risk limits are checked
   first, using this bar's date.
2. If a trade is open, check this bar's high/low against the stop loss and take
   profit. If both are touched in the same bar, the stop is assumed to fill
   first (the conservative choice). A gap through the stop fills at the open.
3. Mark the open trade to market at the close and record equity.
4. Ask the strategy for a signal using data up to and including this bar.

One position at a time. Position size comes from PositionSizer (% of the
current balance at risk); daily loss, drawdown and losing-streak limits come
from RiskManager.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from src.backtest import instruments
from src.backtest.metrics import compute_metrics, evaluate
from src.logger import get_logger
from src.risk.position_sizer import PositionSizer
from src.risk.risk_manager import RiskManager
from src.strategy.base import Strategy, TradeSignal

logger = get_logger(__name__)

# Modules that log every trade at INFO; silenced during a run to keep output readable.
_CHATTY_LOGGERS = ("src.risk.position_sizer", "src.risk.risk_manager", "src.market")


@dataclass
class BacktestConfig:
    initial_cash: float = 10_000.0
    risk_per_trade_percent: float = 1.0
    commission: float = 0.0005      # fraction of notional, charged on entry AND exit
    slippage: float = 0.0002        # fraction of price, on entries and stop/market exits
    spread: float = 0.0001          # full bid-ask spread as a fraction of price
    max_daily_loss_percent: float = 5.0
    max_drawdown_percent: float = 10.0
    max_consecutive_losses: int = 3
    min_lot: float = 0.01
    max_lot: float = 10.0
    lot_step: float = 0.01

    @classmethod
    def from_settings(cls, settings: Dict) -> "BacktestConfig":
        bt, risk = settings.get("backtesting", {}), settings.get("risk_management", {})
        return cls(
            initial_cash=float(bt.get("initial_cash", cls.initial_cash)),
            risk_per_trade_percent=float(risk.get("risk_per_trade_percent", cls.risk_per_trade_percent)),
            commission=float(bt.get("commission", cls.commission)),
            slippage=float(bt.get("slippage", cls.slippage)),
            spread=float(bt.get("spread", cls.spread)),
            max_daily_loss_percent=float(risk.get("max_daily_loss_percent", cls.max_daily_loss_percent)),
            max_drawdown_percent=float(risk.get("max_drawdown_percent", cls.max_drawdown_percent)),
            max_consecutive_losses=int(risk.get("max_consecutive_losses", cls.max_consecutive_losses)),
        )


@dataclass
class _Position:
    direction: str
    entry_time: pd.Timestamp
    entry_price: float
    stop_loss: float
    take_profit: float
    lots: float
    risk_usd: float
    entry_commission: float
    reasons: List[str]


@dataclass
class BacktestResult:
    symbol: str
    strategy: str
    trades: pd.DataFrame
    equity: pd.Series
    stats: Dict
    checks: Dict[str, bool] = field(default_factory=dict)
    halted_reason: Optional[str] = None
    skipped_signals: Dict[str, int] = field(default_factory=dict)

    def report(self) -> str:
        s = self.stats
        pf = "inf" if s["profit_factor"] == float("inf") else f"{s['profit_factor']:.2f}"
        start = self.equity.index[0] if len(self.equity) else "-"
        end = self.equity.index[-1] if len(self.equity) else "-"
        lines = [
            "=" * 60,
            f"BACKTEST: {self.symbol} | strategy: {self.strategy}",
            f"Period: {start} -> {end}",
            "=" * 60,
            f"Initial cash:        ${s['initial_cash']:,.2f}",
            f"Final equity:        ${s['final_equity']:,.2f}",
            f"Total return:        {s['total_return_percent']:+.2f}%",
            f"Max drawdown:        {s['max_drawdown_percent']:.2f}%",
            f"Sharpe ratio:        {s['sharpe_ratio']:.2f}",
            "-" * 60,
            f"Trades:              {s['total_trades']} ({s.get('long_trades', 0)} long / {s.get('short_trades', 0)} short)",
            f"Win rate:            {s['win_rate'] * 100:.1f}%",
            f"Profit factor:       {pf}",
            f"Average win / loss:  ${s['avg_win']:,.2f} / ${s['avg_loss']:,.2f}",
            f"Expectancy / trade:  ${s['expectancy']:,.2f} ({s['avg_r_multiple']:+.2f}R)",
            f"Longest losing run:  {s['max_consecutive_losses']}",
            f"Trading costs paid:  ${s['total_costs']:,.2f}",
        ]
        if self.skipped_signals:
            skipped = ", ".join(f"{k}: {v}" for k, v in self.skipped_signals.items())
            lines.append(f"Signals skipped:     {skipped}")
        if self.halted_reason:
            lines.append(f"TRADING HALTED:      {self.halted_reason}")
        if self.checks:
            lines.append("-" * 60)
            for name, ok in self.checks.items():
                lines.append(f"{'PASS' if ok else 'FAIL'}  {name.replace('_', ' ')}")
        lines.append("=" * 60)
        return "\n".join(lines)


class Backtester:
    """Run a Strategy over historical OHLC data."""

    def __init__(self, strategy: Strategy, config: BacktestConfig = None,
                 performance_thresholds: Dict = None):
        self.strategy = strategy
        self.config = config or BacktestConfig()
        self.thresholds = performance_thresholds or {}

    # ------------------------------------------------------------ cost model
    def _fill(self, price: float, direction: str, opening: bool, slippage: bool = True) -> float:
        """Price actually paid/received after half-spread and slippage."""
        cost = self.config.spread / 2 + (self.config.slippage if slippage else 0.0)
        buying = (direction == "long") == opening
        return price * (1 + cost) if buying else price * (1 - cost)

    def _round_lots(self, lots: float) -> float:
        step = self.config.lot_step
        lots = int(lots / step) * step  # round down: never risk more than planned
        return round(min(max(lots, self.config.min_lot), self.config.max_lot), 2)

    # ------------------------------------------------------------------- run
    def run(self, data: pd.DataFrame, symbol: str = "EURUSD") -> BacktestResult:
        missing = [c for c in ("Open", "High", "Low", "Close") if c not in data.columns]
        if missing:
            raise ValueError(f"Data is missing columns: {missing}")
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Data needs a DatetimeIndex (bar timestamps)")

        previous_levels = {name: logging.getLogger(f"forex_bot.{name}").level for name in _CHATTY_LOGGERS}
        for name in _CHATTY_LOGGERS:
            logging.getLogger(f"forex_bot.{name}").setLevel(logging.WARNING)
        try:
            return self._run(data.sort_index(), symbol)
        finally:
            for name, level in previous_levels.items():
                logging.getLogger(f"forex_bot.{name}").setLevel(level)

    def _run(self, data: pd.DataFrame, symbol: str) -> BacktestResult:
        cfg = self.config
        data = self.strategy.prepare(data)

        risk = RiskManager(
            account_size=cfg.initial_cash,
            max_daily_loss_percent=cfg.max_daily_loss_percent,
            max_drawdown_percent=cfg.max_drawdown_percent,
            max_consecutive_losses=cfg.max_consecutive_losses,
            max_open_positions=1,
        )
        sizer = PositionSizer(
            account_size=cfg.initial_cash,
            risk_percent=cfg.risk_per_trade_percent,
            min_position_size=cfg.min_lot,
            max_position_size=cfg.max_lot,
        )
        pip = instruments.pip_size(symbol)

        balance = cfg.initial_cash
        position: Optional[_Position] = None
        pending: Optional[TradeSignal] = None
        trades: List[Dict] = []
        equity_points: List[float] = []
        skipped: Dict[str, int] = {}
        halted_reason: Optional[str] = None
        losing_streak_day = None

        opens, highs, lows, closes = (data[c].to_numpy() for c in ("Open", "High", "Low", "Close"))
        times = data.index

        def close_position(pos: _Position, raw_exit: float, when, reason: str, slip: bool):
            nonlocal balance
            exit_price = self._fill(raw_exit, pos.direction, opening=False, slippage=slip)
            gross = instruments.pnl_usd(symbol, pos.direction, pos.entry_price, exit_price, pos.lots)
            exit_commission = instruments.notional_usd(symbol, exit_price, pos.lots) * cfg.commission
            net = gross - pos.entry_commission - exit_commission
            balance += net
            risk.record_trade(symbol, pos.entry_price, exit_price, pos.lots, net, net > 0,
                              timestamp=when.to_pydatetime())
            # Price-only cost: what spread+slippage took versus the raw prices
            raw_gross = instruments.pnl_usd(symbol, pos.direction, pos.entry_price, raw_exit, pos.lots)
            trades.append({
                "entry_time": pos.entry_time, "exit_time": when, "direction": pos.direction,
                "entry_price": round(pos.entry_price, 6), "exit_price": round(exit_price, 6),
                "stop_loss": round(pos.stop_loss, 6), "take_profit": round(pos.take_profit, 6),
                "lots": pos.lots, "pnl": round(net, 2),
                "pips": round((exit_price - pos.entry_price) / pip * (1 if pos.direction == "long" else -1), 1),
                "r_multiple": round(net / pos.risk_usd, 2) if pos.risk_usd else 0.0,
                "costs": round(pos.entry_commission + exit_commission + (raw_gross - gross), 2),
                "exit_reason": reason, "balance": round(balance, 2),
                "signal_reasons": "; ".join(pos.reasons),
            })

        for i in range(len(data)):
            now = times[i]
            o, h, l, c = opens[i], highs[i], lows[i], closes[i]

            # New day: a losing-streak pause from a previous day expires.
            if losing_streak_day is not None and now.date() > losing_streak_day:
                risk.reset_consecutive_losses()
                losing_streak_day = None

            # 1. Enter at this bar's open on the previous bar's signal.
            if pending is not None and position is None and halted_reason is None:
                allowed, why = risk.can_trade(now=now.to_pydatetime())
                if allowed:
                    position = self._open(pending, o, now, symbol, sizer, balance)
                    if position is None:
                        skipped["invalid stop"] = skipped.get("invalid stop", 0) + 1
                else:
                    key = why.split(":")[0]
                    skipped[key] = skipped.get(key, 0) + 1
                    if why.startswith("Drawdown"):
                        halted_reason = why
            pending = None

            # 2. Stop loss / take profit inside this bar.
            if position is not None:
                p = position
                if p.direction == "long":
                    stop_hit, target_hit = l <= p.stop_loss, h >= p.take_profit
                    stop_fill = min(o, p.stop_loss)
                    target_fill = max(o, p.take_profit) if o >= p.take_profit else p.take_profit
                else:
                    stop_hit, target_hit = h >= p.stop_loss, l <= p.take_profit
                    stop_fill = max(o, p.stop_loss)
                    target_fill = min(o, p.take_profit) if o <= p.take_profit else p.take_profit
                if stop_hit:
                    close_position(p, stop_fill, now, "stop_loss", slip=True)
                    position = None
                elif target_hit:
                    close_position(p, target_fill, now, "take_profit", slip=False)
                    position = None

                if position is None and risk.consecutive_losses >= cfg.max_consecutive_losses:
                    losing_streak_day = now.date()
                if position is None and risk.get_current_drawdown_percent() > cfg.max_drawdown_percent:
                    halted_reason = halted_reason or (
                        f"Drawdown limit exceeded on {now.date()}: "
                        f"{risk.get_current_drawdown_percent():.2f}% > {cfg.max_drawdown_percent}%")

            # 3. Mark to market.
            unrealised = 0.0
            if position is not None:
                mark = self._fill(c, position.direction, opening=False, slippage=False)
                unrealised = instruments.pnl_usd(symbol, position.direction, position.entry_price,
                                                 mark, position.lots) - position.entry_commission
            equity_points.append(balance + unrealised)

            # 4. Signal for the next bar (never on the final bar).
            if position is None and halted_reason is None and i < len(data) - 1:
                pending = self.strategy.generate_signal(data.iloc[: i + 1])

        if position is not None:
            close_position(position, closes[-1], times[-1], "end_of_data", slip=True)
            equity_points[-1] = balance

        trades_df = pd.DataFrame(trades)
        equity = pd.Series(equity_points, index=times, name="equity")
        stats = compute_metrics(trades_df, equity, cfg.initial_cash)
        checks = evaluate(stats, self.thresholds) if stats["total_trades"] else {}
        return BacktestResult(symbol, self.strategy.name, trades_df, equity, stats,
                              checks, halted_reason, skipped)

    def _open(self, signal: TradeSignal, raw_open: float, now, symbol: str,
              sizer: PositionSizer, balance: float) -> Optional[_Position]:
        entry = self._fill(raw_open, signal.direction, opening=True)
        stop_distance = (entry - signal.stop_loss) if signal.direction == "long" else (signal.stop_loss - entry)
        # Gapped past the stop or target at the open: the setup is gone.
        if stop_distance <= 0 or (signal.direction == "long" and signal.take_profit <= entry) \
                or (signal.direction == "short" and signal.take_profit >= entry):
            return None

        sizer.update_account_size(balance)
        pip = instruments.pip_size(symbol)
        sized = sizer.calculate_position_size(
            entry_price=entry, stop_loss_price=signal.stop_loss, pip_value=pip,
            pip_value_per_lot=instruments.pip_value_per_lot(symbol, entry),
        )
        if not sized.get("valid"):
            return None
        lots = self._round_lots(sized["lot_size"])
        risk_usd = abs(instruments.pnl_usd(symbol, signal.direction, entry, signal.stop_loss, lots))
        commission = instruments.notional_usd(symbol, entry, lots) * self.config.commission
        return _Position(signal.direction, now, entry, signal.stop_loss, signal.take_profit,
                         lots, risk_usd, commission, signal.reasons)
