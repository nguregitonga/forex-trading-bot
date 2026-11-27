"""
Confirmation strategy: trade when the MarketAnalyzer agrees from several angles.

Entry: MarketAnalyzer.generate_signals() returns BUY or SELL with at least
`min_confirmation_signals` agreeing signals (trend, RSI, MACD, divergence),
and the trend itself must not point the other way.
Stop loss: `atr_multiplier` x ATR away from the current close.
Take profit: `risk_reward_ratio` x the stop distance.
"""

from typing import Optional

import pandas as pd

from src.market.indicators import TechnicalIndicators
from src.market.market_analyzer import MarketAnalyzer, TrendDirection
from src.strategy.base import Strategy, TradeSignal

_BULLISH = {TrendDirection.UPTREND, TrendDirection.STRONG_UPTREND}
_BEARISH = {TrendDirection.DOWNTREND, TrendDirection.STRONG_DOWNTREND}


class ConfirmationStrategy(Strategy):
    """Multi-signal confirmation entries with ATR-based stops."""

    name = "confirmation"

    def __init__(
        self,
        min_confirmation_signals: int = 2,
        atr_multiplier: float = 1.5,
        risk_reward_ratio: float = 1.5,
        min_strength: float = 0.0,
        window: int = 120,
    ):
        """
        Args:
            min_confirmation_signals: Agreeing signals needed (settings: entry_confirmation_count)
            atr_multiplier: Stop distance in ATRs
            risk_reward_ratio: Take-profit distance as a multiple of the stop (settings: min_risk_reward_ratio)
            min_strength: Skip signals whose average strength is below this (0-1)
            window: Bars of recent history passed to the analyzer (keeps backtests fast)
        """
        if atr_multiplier <= 0 or risk_reward_ratio <= 0:
            raise ValueError("atr_multiplier and risk_reward_ratio must be positive")
        self.analyzer = MarketAnalyzer(min_confirmation_signals=min_confirmation_signals)
        self.atr_multiplier = atr_multiplier
        self.risk_reward_ratio = risk_reward_ratio
        self.min_strength = min_strength
        self.window = max(window, self.warmup_bars)

    def prepare(self, data: pd.DataFrame) -> pd.DataFrame:
        if "ATR" in data.columns and "MA21" in data.columns:
            return data
        return TechnicalIndicators.add_all_indicators(data.copy())

    def generate_signal(self, history: pd.DataFrame) -> Optional[TradeSignal]:
        if len(history) < self.warmup_bars:
            return None

        recent = history.iloc[-self.window:]
        analysis = self.analyzer.generate_signals(recent)
        side = analysis.get("signal")
        if side not in ("BUY", "SELL") or analysis.get("strength", 0) < self.min_strength:
            return None

        # Don't fight the trend: oversold/divergence buys in a downtrend are skipped.
        trend = self.analyzer.analyze_trend(recent)
        if (side == "BUY" and trend in _BEARISH) or (side == "SELL" and trend in _BULLISH):
            return None

        latest = recent.iloc[-1]
        atr = latest.get("ATR")
        close = latest["Close"]
        if pd.isna(atr) or atr <= 0:
            return None

        stop_distance = self.atr_multiplier * atr
        target_distance = stop_distance * self.risk_reward_ratio
        if side == "BUY":
            direction, stop, target = "long", close - stop_distance, close + target_distance
        else:
            direction, stop, target = "short", close + stop_distance, close - target_distance

        return TradeSignal(
            direction=direction,
            stop_loss=stop,
            take_profit=target,
            reasons=list(analysis.get("reasons", [])),
            strength=float(analysis.get("strength", 0)),
        )
