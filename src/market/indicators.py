"""
Technical indicators library
Calculates various technical indicators for market analysis
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
from src.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators"""
    
    @staticmethod
    def moving_average(data: pd.Series, period: int) -> pd.Series:
        """
        Simple Moving Average (SMA)
        
        Args:
            data: Price series (usually Close prices)
            period: MA period
        
        Returns:
            Series with MA values
        """
        return data.rolling(window=period).mean()
    
    @staticmethod
    def exponential_moving_average(data: pd.Series, period: int) -> pd.Series:
        """
        Exponential Moving Average (EMA)
        
        Args:
            data: Price series
            period: EMA period
        
        Returns:
            Series with EMA values
        """
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index (RSI)
        Measures momentum: overbought (>70) or oversold (<30)
        
        Args:
            data: Price series (usually Close prices)
            period: RSI period (default 14)
        
        Returns:
            Series with RSI values (0-100)
        """
        # Calculate price changes
        delta = data.diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gains and losses
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def macd(
        data: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence)
        Shows momentum and trend changes
        
        Args:
            data: Price series (usually Close prices)
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line EMA period
        
        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands
        Shows volatility and price extremes
        
        Args:
            data: Price series (usually Close prices)
            period: SMA period
            std_dev: Standard deviation multiplier
        
        Returns:
            Tuple of (Upper band, Middle band, Lower band)
        """
        middle = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    @staticmethod
    def atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Average True Range (ATR)
        Measures volatility
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period
        
        Returns:
            Series with ATR values
        """
        # Calculate true range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate ATR
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def stochastic(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
        smooth_k: int = 3,
        smooth_d: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Stochastic Oscillator
        Compares close to price range over time
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: Stochastic period
            smooth_k: K smoothing period
            smooth_d: D smoothing period
        
        Returns:
            Tuple of (K line, D line)
        """
        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()
        
        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        k_smooth = k.rolling(window=smooth_k).mean()
        d_smooth = k_smooth.rolling(window=smooth_d).mean()
        
        return k_smooth, d_smooth
    
    @staticmethod
    def add_all_indicators(data: pd.DataFrame) -> pd.DataFrame:
        """
        Add all technical indicators to DataFrame
        
        Args:
            data: DataFrame with OHLC data
        
        Returns:
            DataFrame with added indicator columns
        """
        try:
            logger.info("Calculating technical indicators...")
            
            # Moving averages
            data['MA9'] = TechnicalIndicators.moving_average(data['Close'], 9)
            data['MA21'] = TechnicalIndicators.moving_average(data['Close'], 21)
            data['MA50'] = TechnicalIndicators.moving_average(data['Close'], 50)
            
            # RSI
            data['RSI'] = TechnicalIndicators.rsi(data['Close'], period=14)
            
            # MACD
            data['MACD'], data['MACD_Signal'], data['MACD_Hist'] = TechnicalIndicators.macd(
                data['Close'],
                fast=12,
                slow=26,
                signal=9
            )
            
            # Bollinger Bands
            data['BB_Upper'], data['BB_Middle'], data['BB_Lower'] = TechnicalIndicators.bollinger_bands(
                data['Close'],
                period=20,
                std_dev=2.0
            )
            
            # ATR
            data['ATR'] = TechnicalIndicators.atr(
                data['High'],
                data['Low'],
                data['Close'],
                period=14
            )
            
            # Stochastic
            data['Stoch_K'], data['Stoch_D'] = TechnicalIndicators.stochastic(
                data['High'],
                data['Low'],
                data['Close'],
                period=14
            )
            
            logger.info("Technical indicators calculated successfully")
            return data
        
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return data
    
    @staticmethod
    def get_indicator_summary(data: pd.DataFrame) -> dict:
        """
        Get summary of current indicator values
        
        Args:
            data: DataFrame with indicators
        
        Returns:
            Dictionary with indicator values
        """
        if data.empty:
            return {}
        
        latest = data.iloc[-1]
        
        summary = {
            'Close': latest['Close'],
            'MA9': latest.get('MA9'),
            'MA21': latest.get('MA21'),
            'RSI': latest.get('RSI'),
            'MACD': latest.get('MACD'),
            'MACD_Signal': latest.get('MACD_Signal'),
            'BB_Upper': latest.get('BB_Upper'),
            'BB_Lower': latest.get('BB_Lower'),
            'ATR': latest.get('ATR'),
            'Stoch_K': latest.get('Stoch_K'),
        }
        
        return summary


def demo_indicators():
    """Demo function to calculate indicators"""
    from src.market.data_fetcher import DataFetcher
    
    # Fetch data
    fetcher = DataFetcher()
    data = fetcher.fetch_forex_data('EURUSD', interval='1h', period='3mo')
    
    if data.empty:
        logger.error("No data fetched")
        return
    
    # Add indicators
    data = TechnicalIndicators.add_all_indicators(data)
    
    # Print summary
    summary = TechnicalIndicators.get_indicator_summary(data)
    logger.info("\nCurrent Indicator Values:")
    logger.info("="*50)
    for key, value in summary.items():
        if value is not None:
            logger.info(f"{key:20s}: {value:.4f}")
    logger.info("="*50)
    
    # Show recent data
    logger.info("\nRecent Data (Last 5 candles):")
    logger.info(data[['Close', 'MA9', 'MA21', 'RSI', 'MACD']].tail())


if __name__ == "__main__":
    demo_indicators()
