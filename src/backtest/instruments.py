"""
Forex instrument maths: pip sizes and converting price moves into account currency.

All values assume a USD trading account and standard lots of 100,000 units.
"""

from src.logger import get_logger

logger = get_logger(__name__)

LOT_UNITS = 100_000
_warned_crosses = set()


def normalize(symbol: str) -> str:
    return symbol.upper().replace("/", "").replace("=X", "")


def pip_size(symbol: str) -> float:
    """0.01 for JPY pairs, 0.0001 for everything else."""
    return 0.01 if normalize(symbol).endswith("JPY") else 0.0001


def _quote_to_usd(symbol: str, price: float) -> float:
    """Multiplier converting an amount in the quote currency into USD."""
    sym = normalize(symbol)
    if sym.endswith("USD"):      # EURUSD, GBPUSD: quote is already USD
        return 1.0
    if sym.startswith("USD"):    # USDJPY, USDCHF: divide by the pair's own price
        return 1.0 / price
    if sym not in _warned_crosses:  # EURGBP etc. would need a second rate
        logger.warning(f"{sym} is a cross pair: P&L treated as USD (approximation)")
        _warned_crosses.add(sym)
    return 1.0


def pip_value_per_lot(symbol: str, price: float) -> float:
    """USD value of a one-pip move on one standard lot (10.0 for EURUSD)."""
    return pip_size(symbol) * LOT_UNITS * _quote_to_usd(symbol, price)


def pnl_usd(symbol: str, direction: str, entry: float, exit_: float, lots: float) -> float:
    """Profit or loss in USD of a closed position."""
    sign = 1 if direction == "long" else -1
    return sign * (exit_ - entry) * lots * LOT_UNITS * _quote_to_usd(symbol, exit_)


def notional_usd(symbol: str, price: float, lots: float) -> float:
    """USD size of a position, used for commission."""
    sym = normalize(symbol)
    units = lots * LOT_UNITS
    if sym.startswith("USD"):
        return units
    return units * price * _quote_to_usd(symbol, price)
