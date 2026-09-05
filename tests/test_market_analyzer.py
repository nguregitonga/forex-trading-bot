"""
Unit tests for market analyzer
"""

import pytest
import pandas as pd
import numpy as np
from src.market.market_analyzer import MarketAnalyzer, TrendDirection, MarketCondition


class TestMarketAnalyzer:
    """Test MarketAnalyzer functionality"""
    
    def test_analyzer_initialization(self):
        """Test analyzer initializes correctly"""
        analyzer = MarketAnalyzer(min_confirmation_signals=2)
        assert analyzer.min_confirmation_signals == 2
    
    def test_analyze_trend_uptrend(self):
        """Test trend analysis for uptrend"""
        # Create uptrend data
        data = pd.DataFrame({
            'Close': [100 + i for i in range(30)],
            'MA9': [99 + i for i in range(30)],
            'MA21': [98 + i for i in range(30)],
        })
        
        analyzer = MarketAnalyzer()
        trend = analyzer.analyze_trend(data)
        
        # Should detect uptrend
        assert trend in [TrendDirection.UPTREND, TrendDirection.STRONG_UPTREND]
    
    def test_analyze_trend_downtrend(self):
        """Test trend analysis for downtrend"""
        # Create downtrend data
        data = pd.DataFrame({
            'Close': [100 - i for i in range(30)],
            'MA9': [99 - i for i in range(30)],
            'MA21': [98 - i for i in range(30)],
        })
        
        analyzer = MarketAnalyzer()
        trend = analyzer.analyze_trend(data)
        
        # Should detect downtrend
        assert trend in [TrendDirection.DOWNTREND, TrendDirection.STRONG_DOWNTREND]
    
    def test_analyze_trend_neutral(self):
        """Test trend analysis for neutral market"""
        # Create sideways data
        data = pd.DataFrame({
            'Close': [100, 101, 100, 101, 100] * 6,
            'MA9': [100.5] * 30,
            'MA21': [100.5] * 30,
        })
        
        analyzer = MarketAnalyzer()
        trend = analyzer.analyze_trend(data)
        
        # Should detect neutral
        assert trend == TrendDirection.NEUTRAL
    
    def test_analyze_rsi_overbought(self):
        """Test RSI overbought detection"""
        data = pd.DataFrame({
            'RSI': [75.0]
        })
        
        analyzer = MarketAnalyzer()
        result = analyzer.analyze_rsi(data)
        
        assert result['condition'] == 'overbought'
        assert result['value'] == 75.0
    
    def test_analyze_rsi_oversold(self):
        """Test RSI oversold detection"""
        data = pd.DataFrame({
            'RSI': [25.0]
        })
        
        analyzer = MarketAnalyzer()
        result = analyzer.analyze_rsi(data)
        
        assert result['condition'] == 'oversold'
        assert result['value'] == 25.0
    
    def test_analyze_rsi_neutral(self):
        """Test RSI neutral detection"""
        data = pd.DataFrame({
            'RSI': [50.0]
        })
        
        analyzer = MarketAnalyzer()
        result = analyzer.analyze_rsi(data)
        
        assert result['condition'] == 'neutral'
    
    def test_analyze_macd_bullish(self):
        """Test MACD bullish signal"""
        data = pd.DataFrame({
            'MACD': [0.5],
            'MACD_Signal': [0.3],
            'MACD_Hist': [0.2]
        })
        
        analyzer = MarketAnalyzer()
        result = analyzer.analyze_macd(data)
        
        assert result['signal'] == 'bullish'
    
    def test_analyze_macd_bearish(self):
        """Test MACD bearish signal"""
        data = pd.DataFrame({
            'MACD': [0.3],
            'MACD_Signal': [0.5],
            'MACD_Hist': [-0.2]
        })
        
        analyzer = MarketAnalyzer()
        result = analyzer.analyze_macd(data)
        
        assert result['signal'] == 'bearish'
    
    def test_analyze_bollinger_bands(self):
        """Test Bollinger Bands analysis"""
        data = pd.DataFrame({
            'Close': [105.0],
            'BB_Upper': [110.0],
            'BB_Middle': [105.0],
            'BB_Lower': [100.0]
        })
        
        analyzer = MarketAnalyzer()
        result = analyzer.analyze_bollinger_bands(data)
        
        assert 'position' in result
        assert 'condition' in result
        assert 'volatility' in result
        assert 0 <= result['position'] <= 1
    
    def test_detect_support_resistance(self):
        """Test support/resistance detection"""
        data = pd.DataFrame({
            'High': [110, 111, 112, 113, 114],
            'Low': [100, 101, 102, 103, 104]
        })
        
        analyzer = MarketAnalyzer()
        support, resistance = analyzer.detect_support_resistance(data, lookback=5)
        
        # Resistance should be highest high, support should be lowest low
        assert resistance == 114
        assert support == 100
    
    def test_detect_divergence_none(self):
        """Test no divergence detection"""
        data = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104],
            'RSI': [40, 45, 50, 55, 60]
        })
        
        analyzer = MarketAnalyzer()
        divergence = analyzer.detect_divergence(data)
        
        # No divergence in this data
        assert divergence == 'none'
    
    def test_generate_signals_no_data(self):
        """Test signal generation with insufficient data"""
        data = pd.DataFrame({
            'Close': [100, 101]
        })
        
        analyzer = MarketAnalyzer()
        signals = analyzer.generate_signals(data)
        
        assert signals['signal'] == 'NONE'
        assert signals['confidence'] == 0
    
    def test_get_market_summary(self):
        """Test market summary generation"""
        # Create sample data with all required columns
        dates = pd.date_range('2024-01-01', periods=60, freq='h')
        data = pd.DataFrame({
            'Close': [100 + i*0.1 for i in range(60)],
            'High': [101 + i*0.1 for i in range(60)],
            'Low': [99 + i*0.1 for i in range(60)],
            'MA9': [100 + i*0.1 for i in range(60)],
            'MA21': [100 + i*0.1 for i in range(60)],
            'RSI': [50 + i*0.2 for i in range(60)],
            'MACD': [0.1 + i*0.01 for i in range(60)],
            'MACD_Signal': [0.09 + i*0.01 for i in range(60)],
            'BB_Upper': [105 + i*0.1 for i in range(60)],
            'BB_Middle': [100 + i*0.1 for i in range(60)],
            'BB_Lower': [95 + i*0.1 for i in range(60)],
        }, index=dates)
        
        analyzer = MarketAnalyzer()
        summary = analyzer.get_market_summary(data)
        
        # Check summary has required keys
        assert 'timestamp' in summary
        assert 'close_price' in summary
        assert 'trend' in summary
        assert 'condition' in summary
        assert 'signals' in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
