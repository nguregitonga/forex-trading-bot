"""
Tests for the backtesting engine, instruments maths, metrics and strategy.

The engine tests use a scripted strategy and hand-built candles so every fill
and P&L can be checked exactly.
"""

import numpy as np
import pandas as pd
import pytest

from src.backtest import Backtester, BacktestConfig
from src.backtest import instruments
from src.backtest.metrics import compute_metrics, max_drawdown_percent
from src.strategy import ConfirmationStrategy, Strategy, TradeSignal

NO_COSTS = dict(commission=0.0, slippage=0.0, spread=0.0)


def candles(rows, start="2025-03-03 00:00"):
    """rows: list of (open, high, low, close)."""
    idx = pd.date_range(start, periods=len(rows), freq="h")
    return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx)


class ScriptedStrategy(Strategy):
    """Returns pre-set signals on given bar numbers and records what it saw."""

    name = "scripted"
    warmup_bars = 0

    def __init__(self, signals):
        self.signals = signals          # {bar_index: TradeSignal}
        self.seen_lengths = []

    def generate_signal(self, history):
        self.seen_lengths.append(len(history))
        return self.signals.get(len(history) - 1)


def run(rows, signals, symbol="EURUSD", **cfg):
    config = BacktestConfig(**{**NO_COSTS, **cfg})
    strategy = ScriptedStrategy(signals)
    return Backtester(strategy, config).run(candles(rows), symbol=symbol), strategy


FLAT = (1.1000, 1.1005, 1.0995, 1.1000)


class TestInstruments:
    def test_pip_sizes(self):
        assert instruments.pip_size("EURUSD") == 0.0001
        assert instruments.pip_size("USDJPY") == 0.01
        assert instruments.pip_size("eur/usd") == 0.0001

    def test_pip_value_per_lot(self):
        assert instruments.pip_value_per_lot("EURUSD", 1.10) == pytest.approx(10.0)
        # USDJPY at 150: 0.01 * 100000 / 150 = $6.67 per pip per lot
        assert instruments.pip_value_per_lot("USDJPY", 150.0) == pytest.approx(6.6667, rel=1e-3)

    def test_pnl_usd(self):
        # 20 pips on 1 lot of EURUSD = $200
        assert instruments.pnl_usd("EURUSD", "long", 1.1000, 1.1020, 1.0) == pytest.approx(200.0)
        assert instruments.pnl_usd("EURUSD", "short", 1.1000, 1.1020, 1.0) == pytest.approx(-200.0)


class TestEngineMechanics:
    def test_enters_at_next_bar_open_and_hits_take_profit(self):
        rows = [FLAT, (1.1002, 1.1010, 1.1000, 1.1008), (1.1008, 1.1035, 1.1005, 1.1030)]
        signal = TradeSignal("long", stop_loss=1.0982, take_profit=1.1022)
        result, _ = run(rows, {0: signal})

        trade = result.trades.iloc[0]
        assert trade["entry_price"] == pytest.approx(1.1002)   # bar 1 open, not bar 0 close
        assert trade["exit_reason"] == "take_profit"
        assert trade["exit_price"] == pytest.approx(1.1022)
        # Risk 1% of $10,000 = $100 over 20 pips -> 0.5 lots; +20 pips -> +$100
        assert trade["lots"] == pytest.approx(0.5)
        assert trade["pnl"] == pytest.approx(100.0, abs=0.01)
        assert trade["r_multiple"] == pytest.approx(1.0, abs=0.01)
        assert result.stats["final_equity"] == pytest.approx(10_100.0, abs=0.01)

    def test_stop_loss_loses_one_r(self):
        rows = [FLAT, (1.1000, 1.1004, 1.0990, 1.0995), (1.0995, 1.0996, 1.0970, 1.0975)]
        signal = TradeSignal("long", stop_loss=1.0980, take_profit=1.1030)
        result, _ = run(rows, {0: signal})

        trade = result.trades.iloc[0]
        assert trade["exit_reason"] == "stop_loss"
        assert trade["pnl"] == pytest.approx(-100.0, abs=0.5)

    def test_stop_wins_when_both_levels_hit_in_same_bar(self):
        rows = [FLAT, (1.1000, 1.1050, 1.0950, 1.1000)]
        signal = TradeSignal("long", stop_loss=1.0980, take_profit=1.1020)
        result, _ = run(rows, {0: signal})
        assert result.trades.iloc[0]["exit_reason"] == "stop_loss"

    def test_gap_through_stop_fills_at_open(self):
        rows = [FLAT, (1.1000, 1.1002, 1.0995, 1.0998), (1.0960, 1.0965, 1.0950, 1.0955)]
        signal = TradeSignal("long", stop_loss=1.0980, take_profit=1.1050)
        result, _ = run(rows, {0: signal})
        trade = result.trades.iloc[0]
        assert trade["exit_price"] == pytest.approx(1.0960)   # worse than the stop
        assert trade["pnl"] < -100

    def test_short_trade(self):
        rows = [FLAT, (1.1000, 1.1003, 1.0990, 1.0992), (1.0992, 1.0995, 1.0975, 1.0978)]
        signal = TradeSignal("short", stop_loss=1.1020, take_profit=1.0980)
        result, _ = run(rows, {0: signal})
        trade = result.trades.iloc[0]
        assert trade["exit_reason"] == "take_profit"
        assert trade["pnl"] == pytest.approx(100.0, abs=0.01)

    def test_open_trade_closed_at_end_of_data(self):
        rows = [FLAT, (1.1000, 1.1005, 1.0998, 1.1004), (1.1004, 1.1008, 1.1001, 1.1006)]
        signal = TradeSignal("long", stop_loss=1.0900, take_profit=1.1200)
        result, _ = run(rows, {0: signal})
        assert result.trades.iloc[0]["exit_reason"] == "end_of_data"

    def test_strategy_never_sees_future_bars(self):
        rows = [FLAT] * 6
        result, strategy = run(rows, {})
        # Bar i sees exactly i+1 bars; no call on the final bar.
        assert strategy.seen_lengths == [1, 2, 3, 4, 5]

    def test_costs_reduce_profit(self):
        rows = [FLAT, (1.1002, 1.1010, 1.1000, 1.1008), (1.1008, 1.1035, 1.1005, 1.1030)]
        signal = TradeSignal("long", stop_loss=1.0982, take_profit=1.1022)
        free, _ = run(rows, {0: signal})
        costly, _ = run(rows, {0: signal}, commission=0.00005, slippage=0.0001, spread=0.0001)
        assert costly.trades.iloc[0]["pnl"] < free.trades.iloc[0]["pnl"]
        assert costly.trades.iloc[0]["costs"] > 0

    def test_skips_signal_when_open_gaps_past_stop(self):
        rows = [FLAT, (1.0970, 1.0975, 1.0960, 1.0965)]
        signal = TradeSignal("long", stop_loss=1.0980, take_profit=1.1020)
        result, _ = run(rows, {0: signal})
        assert result.trades.empty
        assert result.skipped_signals.get("invalid stop") == 1

    def test_drawdown_limit_halts_trading(self):
        # Repeated 1R losses; risking 5% each, 3 losses breach a 10% drawdown limit.
        rows, signals = [], {}
        for k in range(6):
            base = len(rows)
            rows += [FLAT, (1.1000, 1.1002, 1.0975, 1.0978)]
            signals[base] = TradeSignal("long", stop_loss=1.0980, take_profit=1.1040)
        result, _ = run(rows, signals, risk_per_trade_percent=5.0, max_consecutive_losses=99,
                        max_daily_loss_percent=99)
        assert result.halted_reason is not None
        assert len(result.trades) == 3

    def test_daily_loss_limit_blocks_rest_of_day(self):
        rows, signals = [], {}
        for k in range(6):
            base = len(rows)
            rows += [FLAT, (1.1000, 1.1002, 1.0975, 1.0978)]
            signals[base] = TradeSignal("long", stop_loss=1.0980, take_profit=1.1040)
        result, _ = run(rows, signals, risk_per_trade_percent=2.0, max_consecutive_losses=99,
                        max_daily_loss_percent=5.0)
        assert len(result.trades) == 3          # -2%, -4%, -6% -> limit hit
        assert result.skipped_signals.get("Daily loss limit exceeded") == 3
        assert result.halted_reason is None

    def test_losing_streak_pauses_until_next_day(self):
        rows, signals = [], {}
        for k in range(5):                  # five losing setups on the same day
            base = len(rows)
            rows += [FLAT, (1.1000, 1.1002, 1.0975, 1.0978)]
            signals[base] = TradeSignal("long", stop_loss=1.0980, take_profit=1.1040)
        result, _ = run(rows, signals, max_consecutive_losses=3)
        assert len(result.trades) == 3
        assert result.skipped_signals.get("Max consecutive losses reached") == 2

    def test_rejects_data_without_datetime_index(self):
        data = candles([FLAT, FLAT]).reset_index(drop=True)
        with pytest.raises(ValueError):
            Backtester(ScriptedStrategy({})).run(data)


class TestMetrics:
    def test_max_drawdown(self):
        equity = pd.Series([100, 120, 90, 130, 117])
        assert max_drawdown_percent(equity) == pytest.approx(25.0)

    def test_metrics_with_no_trades(self):
        equity = pd.Series([10_000.0] * 3, index=pd.date_range("2025-01-01", periods=3))
        stats = compute_metrics(pd.DataFrame(), equity, 10_000.0)
        assert stats["total_trades"] == 0
        assert stats["total_return_percent"] == 0

    def test_profit_factor_and_win_rate(self):
        trades = pd.DataFrame({
            "pnl": [200.0, -100.0, 100.0, -100.0],
            "r_multiple": [2.0, -1.0, 1.0, -1.0],
            "costs": [1.0] * 4,
            "direction": ["long", "short", "long", "long"],
        })
        equity = pd.Series([10_000.0, 10_100.0], index=pd.date_range("2025-01-01", periods=2))
        stats = compute_metrics(trades, equity, 10_000.0)
        assert stats["win_rate"] == 0.5
        assert stats["profit_factor"] == 1.5
        assert stats["expectancy"] == 25.0
        assert stats["long_trades"] == 3


class TestConfirmationStrategy:
    @staticmethod
    def trending_data(n=300, step=0.0004, seed=1):
        rng = np.random.default_rng(seed)
        close = 1.10 + np.cumsum(step + rng.normal(0, 0.0003, n))
        open_ = np.r_[close[0], close[:-1]]
        high = np.maximum(open_, close) + 0.0004
        low = np.minimum(open_, close) - 0.0004
        idx = pd.date_range("2025-01-01", periods=n, freq="h")
        return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close}, index=idx)

    def test_no_signal_during_warmup(self):
        strategy = ConfirmationStrategy()
        data = strategy.prepare(self.trending_data(n=30))
        assert strategy.generate_signal(data) is None

    def test_long_signal_in_uptrend_has_valid_levels(self):
        strategy = ConfirmationStrategy(risk_reward_ratio=2.0)
        data = strategy.prepare(self.trending_data())
        signals = [strategy.generate_signal(data.iloc[: i + 1]) for i in range(60, len(data))]
        longs = [s for s in signals if s is not None and s.direction == "long"]
        assert longs, "expected long signals in a steady uptrend"
        assert not any(s is not None and s.direction == "short" for s in signals)
        s = longs[-1]
        close = data["Close"].iloc[-1]
        assert s.stop_loss < s.take_profit
        risk, reward = None, None
        # Reward is 2x risk around the signal bar's close
        for i in range(60, len(data)):
            sig = strategy.generate_signal(data.iloc[: i + 1])
            if sig is not None:
                c = data["Close"].iloc[i]
                risk, reward = c - sig.stop_loss, sig.take_profit - c
                break
        assert reward == pytest.approx(2 * risk)

    def test_full_backtest_runs(self):
        strategy = ConfirmationStrategy()
        result = Backtester(strategy, BacktestConfig()).run(self.trending_data(n=500), "EURUSD")
        assert len(result.equity) == 500
        assert result.stats["total_trades"] >= 1
        assert "Final equity" in result.report()

    def test_invalid_parameters(self):
        with pytest.raises(ValueError):
            ConfirmationStrategy(atr_multiplier=0)


class TestTradeSignal:
    def test_rejects_bad_direction(self):
        with pytest.raises(ValueError):
            TradeSignal("buy", stop_loss=1.0, take_profit=1.2)
