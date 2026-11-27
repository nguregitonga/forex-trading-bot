"""
Strategy interface.

A strategy looks at price history up to and including the current bar and
either returns a TradeSignal or None. It must never look at future bars:
the backtester only ever passes data up to the current bar.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd


@dataclass
class TradeSignal:
    """An instruction to open a trade at the next bar's open."""

    direction: str            # 'long' or 'short'
    stop_loss: float          # absolute price
    take_profit: float        # absolute price
    reasons: List[str] = field(default_factory=list)
    strength: float = 0.0

    def __post_init__(self):
        if self.direction not in ("long", "short"):
            raise ValueError(f"direction must be 'long' or 'short', got {self.direction!r}")


class Strategy(ABC):
    """Base class for trading strategies."""

    name: str = "base"

    #: Bars of history the strategy needs before it can produce a signal
    warmup_bars: int = 50

    def prepare(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Add whatever indicator columns the strategy needs, once, before the
        backtest loop. Indicators must only use past values (rolling windows),
        so computing them up front does not leak future data.
        """
        return data

    @abstractmethod
    def generate_signal(self, history: pd.DataFrame) -> Optional[TradeSignal]:
        """
        Decide whether to open a trade.

        Args:
            history: Prepared data up to and including the current bar.

        Returns:
            TradeSignal to enter at the next bar's open, or None.
        """
