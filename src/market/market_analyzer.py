"""
Market analyzer for identifying trading opportunities
Analyzes market conditions and generates trading signals
"""

import pandas as pd
import numpy as np
from enum import Enum
from typing import Dict, List, Tuple
from src.logger import get_logger
from src.market.indicators import TechnicalIndicators

logger = get_logger(__name__)


class TrendDirection(Enum):
    """Trend direction"""
    STRONG_UPTREND = 3
    UPTREND = 2
    NEUTRAL = 1
    DOWNTREND = -2
    STRONG_DOWNTREND = -3


class MarketCondition(Enum):
    """Market condition"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    BREAKOUT = "breakout"
    UNCLEAR = "unclear"


class MarketAnalyzer:
    """Analyze market conditions and generate signals"""
    
    def __init__(self, min_confirmation_signals: int = 2):
        """
        Initialize market analyzer
        
        Args:
            min_confirmation_signals: Minimum signals needed before trade entry
        """
        self.min_confirmation_signals = min_confirmation_signals
        logger.info(f"MarketAnalyzer initialized with min_confirmation: {min_confirmation_signals}")
    
    def analyze_trend(self, data: pd.DataFrame) -> TrendDirection:
        """
        Analyze trend direction using moving averages
        
        Args:
            data: DataFrame with OHLC data and MAs
        
        Returns:
            TrendDirection enum
        """
        if data.empty or len(data) < 1:
            return TrendDirection.NEUTRAL
        
        latest = data.iloc[-1]
        close = latest['Close']
        
        # Get moving averages
        ma9 = latest.get('MA9')
        ma21 = latest.get('MA21')
        ma50 = latest.get('MA50')
        
        if pd.isna(ma9) or pd.isna(ma21):
            return TrendDirection.NEUTRAL
        
        # Trend rules
        if close > ma9 > ma21:
            return TrendDirection.STRONG_UPTREND if pd.isna(ma50) or ma21 > ma50 else TrendDirection.UPTREND
        elif close < ma9 < ma21:
            return TrendDirection.STRONG_DOWNTREND if pd.isna(ma50) or ma21 < ma50 else TrendDirection.DOWNTREND
        else:
            return TrendDirection.NEUTRAL
    
    def analyze_rsi(self, data: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze RSI for overbought/oversold conditions
        
        Args:
            data: DataFrame with RSI indicator
        
        Returns:
            Dictionary with RSI analysis
        """
        if data.empty or 'RSI' not in data.columns:
            return {'value': None, 'condition': 'unknown'}
        
        rsi = data.iloc[-1]['RSI']
        
        if pd.isna(rsi):
            return {'value': None, 'condition': 'unknown'}
        
        if rsi > 70:
            condition = 'overbought'
        elif rsi < 30:
            condition = 'oversold'
        else:
            condition = 'neutral'
        
        return {
            'value': rsi,
            'condition': condition,
            'strength': abs(rsi - 50) / 50  # 0-1 scale
        }
    
    def analyze_macd(self, data: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze MACD for momentum and trend changes
        
        Args:
            data: DataFrame with MACD indicators
        
        Returns:
            Dictionary with MACD analysis
        """
        if data.empty or 'MACD' not in data.columns:
            return {'signal': 'unknown', 'momentum': 0}
        
        latest = data.iloc[-1]
        macd = latest['MACD']
        signal = latest['MACD_Signal']
        histogram = latest['MACD_Hist']
        
        if pd.isna(macd) or pd.isna(signal):
            return {'signal': 'unknown', 'momentum': 0}
        
        # Determine signal
        if macd > signal:
            signal_type = 'bullish'
        elif macd < signal:
            signal_type = 'bearish'
        else:
            signal_type = 'neutral'
        
        return {
            'signal': signal_type,
            'momentum': float(histogram) if not pd.isna(histogram) else 0,
            'macd': float(macd),
            'signal_line': float(signal)
        }
    
    def analyze_bollinger_bands(self, data: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze Bollinger Bands for volatility and extremes
        
        Args:
            data: DataFrame with Bollinger Bands
        
        Returns:
            Dictionary with BB analysis
        """
        if data.empty or 'BB_Upper' not in data.columns:
            return {'position': 'unknown', 'volatility': 0}
        
        latest = data.iloc[-1]
        close = latest['Close']
        upper = latest['BB_Upper']
        middle = latest['BB_Middle']
        lower = latest['BB_Lower']
        
        if pd.isna(upper) or pd.isna(lower):
            return {'position': 'unknown', 'volatility': 0}
        
        # Position in bands (0-1, where 0.5 is middle)
        band_range = upper - lower
        if band_range == 0:
            position = 0.5
        else:
            position = (close - lower) / band_range
        
        # Determine condition
        if position > 0.8:
            condition = 'at_upper_band'
        elif position < 0.2:
            condition = 'at_lower_band'
        else:
            condition = 'in_range'
        
        volatility = (upper - lower) / middle if middle != 0 else 0
        
        return {
            'position': position,
            'condition': condition,
            'volatility': float(volatility)
        }
    
    def get_market_condition(self, data: pd.DataFrame) -> MarketCondition:
        """
        Determine overall market condition
        
        Args:
            data: DataFrame with OHLC data and indicators
        
        Returns:
            MarketCondition enum
        """
        if data.empty or len(data) < 50:
            return MarketCondition.UNCLEAR
        
        trend = self.analyze_trend(data)
        rsi_analysis = self.analyze_rsi(data)
        macd_analysis = self.analyze_macd(data)
        bb_analysis = self.analyze_bollinger_bands(data)
        
        # Determine condition
        if trend in [TrendDirection.STRONG_UPTREND, TrendDirection.UPTREND]:
            return MarketCondition.TRENDING_UP
        elif trend in [TrendDirection.STRONG_DOWNTREND, TrendDirection.DOWNTREND]:
            return MarketCondition.TRENDING_DOWN
        elif rsi_analysis['condition'] in ['overbought', 'oversold']:
            return MarketCondition.RANGING
        else:
            return MarketCondition.UNCLEAR
    
    def detect_support_resistance(
        self,
        data: pd.DataFrame,
        lookback: int = 20
    ) -> Tuple[float, float]:
        """
        Detect support and resistance levels
        
        Args:
            data: DataFrame with OHLC data
            lookback: Number of candles to lookback
        
        Returns:
            Tuple of (support_level, resistance_level)
        """
        if data.empty or len(data) < lookback:
            return 0, 0
        
        recent_data = data.tail(lookback)
        
        resistance = recent_data['High'].max()
        support = recent_data['Low'].min()
        
        return support, resistance
    
    def detect_divergence(self, data: pd.DataFrame, lookback: int = 5) -> str:
        """
        Detect RSI divergence patterns
        
        Args:
            data: DataFrame with RSI
            lookback: Number of candles to check
        
        Returns:
            'bullish_divergence', 'bearish_divergence', or 'none'
        """
        if data.empty or len(data) < lookback or 'RSI' not in data.columns:
            return 'none'
        
        recent = data.tail(lookback)
        prices = recent['Close'].values
        rsi_values = recent['RSI'].values
        
        # Remove NaN values
        valid_idx = ~(np.isnan(prices) | np.isnan(rsi_values))
        if not valid_idx.any():
            return 'none'
        
        # Bullish divergence: Lower lows in price, higher lows in RSI
        if prices[-1] < prices[0] and rsi_values[-1] > rsi_values[0]:
            return 'bullish_divergence'
        
        # Bearish divergence: Higher highs in price, lower highs in RSI
        if prices[-1] > prices[0] and rsi_values[-1] < rsi_values[0]:
            return 'bearish_divergence'
        
        return 'none'
    
    def generate_signals(self, data: pd.DataFrame) -> Dict[str, any]:
        """
        Generate trading signals based on all analysis
        
        Args:
            data: DataFrame with OHLC and indicators
        
        Returns:
            Dictionary with signal analysis
        """
        if data.empty or len(data) < 50:
            return {
                'signal': 'NONE',
                'strength': 0,
                'confidence': 0,
                'reason': 'Insufficient data'
            }
        
        signals = []
        
        # Trend signal
        trend = self.analyze_trend(data)
        if trend == TrendDirection.STRONG_UPTREND:
            signals.append({'type': 'BUY', 'strength': 1.0, 'reason': 'Strong uptrend'})
        elif trend == TrendDirection.UPTREND:
            signals.append({'type': 'BUY', 'strength': 0.7, 'reason': 'Uptrend'})
        elif trend == TrendDirection.STRONG_DOWNTREND:
            signals.append({'type': 'SELL', 'strength': 1.0, 'reason': 'Strong downtrend'})
        elif trend == TrendDirection.DOWNTREND:
            signals.append({'type': 'SELL', 'strength': 0.7, 'reason': 'Downtrend'})
        
        # RSI signal
        rsi_analysis = self.analyze_rsi(data)
        if rsi_analysis['condition'] == 'oversold':
            signals.append({'type': 'BUY', 'strength': 0.6, 'reason': 'RSI oversold'})
        elif rsi_analysis['condition'] == 'overbought':
            signals.append({'type': 'SELL', 'strength': 0.6, 'reason': 'RSI overbought'})
        
        # MACD signal
        macd_analysis = self.analyze_macd(data)
        if macd_analysis['signal'] == 'bullish':
            signals.append({'type': 'BUY', 'strength': 0.7, 'reason': 'MACD bullish'})
        elif macd_analysis['signal'] == 'bearish':
            signals.append({'type': 'SELL', 'strength': 0.7, 'reason': 'MACD bearish'})
        
        # Divergence signal
        divergence = self.detect_divergence(data)
        if divergence == 'bullish_divergence':
            signals.append({'type': 'BUY', 'strength': 0.8, 'reason': 'Bullish divergence'})
        elif divergence == 'bearish_divergence':
            signals.append({'type': 'SELL', 'strength': 0.8, 'reason': 'Bearish divergence'})
        
        # Aggregate signals
        buy_signals = [s for s in signals if s['type'] == 'BUY']
        sell_signals = [s for s in signals if s['type'] == 'SELL']
        
        if len(buy_signals) >= self.min_confirmation_signals:
            avg_strength = np.mean([s['strength'] for s in buy_signals])
            reasons = [s['reason'] for s in buy_signals]
            return {
                'signal': 'BUY',
                'strength': avg_strength,
                'confirmation_count': len(buy_signals),
                'confidence': min(len(buy_signals) / 4, 1.0),  # Max 4 signals
                'reasons': reasons
            }
        
        elif len(sell_signals) >= self.min_confirmation_signals:
            avg_strength = np.mean([s['strength'] for s in sell_signals])
            reasons = [s['reason'] for s in sell_signals]
            return {
                'signal': 'SELL',
                'strength': avg_strength,
                'confirmation_count': len(sell_signals),
                'confidence': min(len(sell_signals) / 4, 1.0),
                'reasons': reasons
            }
        
        else:
            all_reasons = [s['reason'] for s in signals]
            return {
                'signal': 'HOLD',
                'strength': 0,
                'confirmation_count': max(len(buy_signals), len(sell_signals)),
                'confidence': 0,
                'reasons': all_reasons if all_reasons else ['No clear signals']
            }
    
    def get_market_summary(self, data: pd.DataFrame) -> Dict[str, any]:
        """
        Get comprehensive market analysis summary
        
        Args:
            data: DataFrame with OHLC and indicators
        
        Returns:
            Dictionary with market summary
        """
        return {
            'timestamp': data.index[-1] if not data.empty else None,
            'close_price': data.iloc[-1]['Close'] if not data.empty else 0,
            'trend': self.analyze_trend(data).name,
            'condition': self.get_market_condition(data).value,
            'rsi': self.analyze_rsi(data),
            'macd': self.analyze_macd(data),
            'bollinger_bands': self.analyze_bollinger_bands(data),
            'support_resistance': self.detect_support_resistance(data),
            'divergence': self.detect_divergence(data),
            'signals': self.generate_signals(data)
        }


def demo_analyzer():
    """Demo function for market analyzer"""
    from src.market.data_fetcher import DataFetcher
    from src.market.indicators import TechnicalIndicators
    
    # Fetch data
    fetcher = DataFetcher()
    data = fetcher.fetch_forex_data('EURUSD', interval='1h', period='3mo')
    
    if data.empty:
        logger.error("No data fetched")
        return
    
    # Add indicators
    data = TechnicalIndicators.add_all_indicators(data)
    
    # Analyze market
    analyzer = MarketAnalyzer(min_confirmation_signals=2)
    summary = analyzer.get_market_summary(data)
    
    # Print results
    logger.info("\n" + "="*60)
    logger.info("MARKET ANALYSIS SUMMARY")
    logger.info("="*60)
    logger.info(f"Time: {summary['timestamp']}")
    logger.info(f"Price: {summary['close_price']:.5f}")
    logger.info(f"Trend: {summary['trend']}")
    logger.info(f"Market Condition: {summary['condition']}")
    logger.info(f"\nRSI Analysis:")
    logger.info(f"  Value: {summary['rsi']['value']:.2f}")
    logger.info(f"  Condition: {summary['rsi']['condition']}")
    logger.info(f"\nMACD Analysis:")
    logger.info(f"  Signal: {summary['macd']['signal']}")
    logger.info(f"  Momentum: {summary['macd']['momentum']:.5f}")
    logger.info(f"\nBollinger Bands:")
    logger.info(f"  Position: {summary['bollinger_bands']['position']:.2f}")
    logger.info(f"  Volatility: {summary['bollinger_bands']['volatility']:.4f}")
    logger.info(f"\nSupport/Resistance:")
    support, resistance = summary['support_resistance']
    logger.info(f"  Support: {support:.5f}")
    logger.info(f"  Resistance: {resistance:.5f}")
    logger.info(f"\nDivergence: {summary['divergence']}")
    logger.info(f"\nTrading Signal:")
    logger.info(f"  Signal: {summary['signals']['signal']}")
    logger.info(f"  Confidence: {summary['signals']['confidence']:.2%}")
    logger.info(f"  Confirmations: {summary['signals']['confirmation_count']}")
    logger.info(f"  Reasons:")
    for reason in summary['signals']['reasons']:
        logger.info(f"    - {reason}")
    logger.info("="*60)


if __name__ == "__main__":
    demo_analyzer()
