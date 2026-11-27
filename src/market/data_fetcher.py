"""
Market data fetching, validation and storage.

Downloads Forex OHLCV data (Yahoo Finance via yfinance by default), validates it,
adds basic features, resamples timeframes and saves/loads CSV files.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.logger import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = ["Open", "High", "Low", "Close"]

# yfinance does not offer a native 4h interval: download 1h and resample.
_RESAMPLE_INTERVALS = {"4h": ("1h", "4h")}


class DataFetcher:
    """Fetch, validate and store Forex market data."""

    def __init__(self, source: str = "yfinance", data_dir: str = "data/raw"):
        self.source = source
        self.data_dir = Path(data_dir)

    # ------------------------------------------------------------------ fetch
    @staticmethod
    def to_yahoo_symbol(symbol: str) -> str:
        """EURUSD -> EURUSD=X (Yahoo Finance Forex ticker)."""
        symbol = symbol.upper().replace("/", "")
        return symbol if symbol.endswith("=X") else f"{symbol}=X"

    def fetch_forex_data(
        self,
        symbol: str,
        interval: str = "1h",
        period: str = "6mo",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Download OHLCV data. Returns an empty DataFrame if the download fails
        (no network, unknown symbol, yfinance not installed).
        """
        if self.source != "yfinance":
            logger.error(f"Data source '{self.source}' is not implemented yet")
            return pd.DataFrame()

        try:
            import yfinance as yf
        except ImportError:
            logger.error("yfinance is not installed: pip install -r requirements.txt")
            return pd.DataFrame()

        download_interval, resample_to = _RESAMPLE_INTERVALS.get(interval, (interval, None))
        ticker = self.to_yahoo_symbol(symbol)

        try:
            kwargs = {"interval": download_interval, "progress": False, "auto_adjust": False}
            if start:
                kwargs.update(start=start, end=end)
            else:
                kwargs["period"] = period
            data = yf.download(ticker, **kwargs)
        except Exception as exc:  # network errors, rate limits, bad params
            logger.warning(f"Download failed for {symbol}: {exc}")
            return pd.DataFrame()

        if data is None or data.empty:
            logger.warning(f"No data returned for {symbol} ({interval}, {period})")
            return pd.DataFrame()

        # Newer yfinance returns MultiIndex columns (field, ticker) even for one ticker.
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.loc[:, ~data.columns.duplicated()]
        keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in data.columns]
        data = data[keep].dropna(subset=REQUIRED_COLUMNS)

        if resample_to:
            data = self.resample_data(data, resample_to)

        logger.info(f"Fetched {len(data)} {interval} candles for {symbol}")
        return data

    def fetch_multiple_symbols(
        self, symbols: List[str], interval: str = "1h", period: str = "3mo"
    ) -> Dict[str, pd.DataFrame]:
        """Fetch several symbols; symbols that return no data are skipped."""
        results = {}
        for symbol in symbols:
            data = self.fetch_forex_data(symbol, interval=interval, period=period)
            if not data.empty:
                results[symbol] = data
        return results

    # --------------------------------------------------------------- features
    @staticmethod
    def add_technical_features(data: pd.DataFrame, volume_window: int = 20) -> pd.DataFrame:
        """Add Returns, Daily_Range, Typical_Price and Volume_MA columns."""
        result = data.copy()
        result["Returns"] = result["Close"].pct_change()
        result["Daily_Range"] = result["High"] - result["Low"]
        result["Typical_Price"] = (result["High"] + result["Low"] + result["Close"]) / 3
        if "Volume" in result.columns:
            result["Volume_MA"] = result["Volume"].rolling(volume_window, min_periods=1).mean()
        else:
            result["Volume_MA"] = float("nan")
        return result

    @staticmethod
    def resample_data(data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Resample OHLCV data to a higher timeframe (e.g. '4h', '1D')."""
        if data.empty:
            return data
        agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
        if "Volume" in data.columns:
            agg["Volume"] = "sum"
        return data.resample(timeframe).agg(agg).dropna(subset=["Open", "Close"])

    # ------------------------------------------------------------- validation
    @staticmethod
    def validate_data(data: pd.DataFrame) -> Tuple[bool, str]:
        """Check data is non-empty, has OHLC columns, no NaNs and sane prices."""
        if data is None or data.empty:
            return False, "Data is empty"

        missing = [c for c in REQUIRED_COLUMNS if c not in data.columns]
        if missing:
            return False, f"Missing columns: {', '.join(missing)}"

        ohlc = data[REQUIRED_COLUMNS]
        if ohlc.isna().any().any():
            return False, f"Data contains NaN values ({int(ohlc.isna().sum().sum())})"

        bad = (
            (ohlc["High"] < ohlc["Low"])
            | (ohlc["High"] < ohlc[["Open", "Close"]].max(axis=1))
            | (ohlc["Low"] > ohlc[["Open", "Close"]].min(axis=1))
            | (ohlc <= 0).any(axis=1)
        )
        if bad.any():
            return False, f"Invalid OHLC relationships in {int(bad.sum())} rows"

        return True, "Validation passed"

    # ---------------------------------------------------------------- storage
    def _path(self, symbol: str, interval: str) -> Path:
        return self.data_dir / f"{symbol.upper()}_{interval}.csv"

    def save_data(self, data: pd.DataFrame, symbol: str, interval: str) -> Path:
        """Save data to data_dir/SYMBOL_interval.csv."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(symbol, interval)
        data.to_csv(path)
        logger.info(f"Saved {len(data)} rows to {path}")
        return path

    def load_data(self, symbol: str, interval: str) -> pd.DataFrame:
        """Load data saved with save_data(); empty DataFrame if missing."""
        path = self._path(symbol, interval)
        if not path.exists():
            logger.warning(f"No saved data at {path}")
            return pd.DataFrame()
        return pd.read_csv(path, index_col=0, parse_dates=True)
