"""
Unit tests for technical indicators
"""

import pytest
import pandas as pd
import numpy as np
from src.market.indicators import TechnicalIndicators


class TestMovingAverage:
    """Test moving average calculations"""
    
    def test_moving_average_basic(self):
        """Test basic MA calculation"""
        data = pd.Series([1, 2, 3, 4, 5])
        ma = TechnicalIndicators.moving_average(data, period=2)
        
        # MA should be NaN for first element, then average of previous 2
        assert pd.isna(ma.iloc[0])
        assert ma.iloc[1] == 1.5  # (1+2)/2
        assert ma.iloc[2] == 2.5  # (2+3)/2
        assert ma.iloc[3] == 3.5  # (3+4)/2
        assert ma.iloc[4] == 4.5  # (4+5)/2
    
    def test_moving_average_period_larger_than_data(self):
        """Test MA when period is larger than data"""
        data = pd.Series([1, 2, 3])
        ma = TechnicalIndicators.moving_average(data, period=5)
        
        # All should be NaN since period > data length
        assert ma.isna().all()


class TestRSI:
    """Test RSI calculations"""
    
    def test_rsi_basic(self):
        """Test basic RSI calculation"""
        # Create simple uptrend
        data = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                         110, 111, 112, 113, 114, 115])
        rsi = TechnicalIndicators.rsi(data, period=14)
        
        # In strong uptrend, RSI should be high (>70)
        assert rsi.iloc[-1] > 70
    
    def test_rsi_range(self):
        """Test RSI is between 0 and 100"""
        data = pd.Series(np.random.uniform(100, 110, 100))
        rsi = TechnicalIndicators.rsi(data, period=14)
        
        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()


class TestMACD:
    """Test MACD calculations"""
    
    def test_macd_basic(self):
        """Test basic MACD calculation"""
        # Create uptrend
        data = pd.Series([100 + i for i in range(50)])
        macd_line, signal_line, histogram = TechnicalIndicators.macd(data)
        
        # Should have correct length
        assert len(macd_line) == len(data)
        assert len(signal_line) == len(data)
        assert len(histogram) == len(data)
    
    def test_macd_histogram_calculation(self):
        """Test MACD histogram = MACD - Signal"""
        data = pd.Series(np.random.uniform(100, 110, 50))
        macd_line, signal_line, histogram = TechnicalIndicators.macd(data)
        
        # Histogram should equal MACD - Signal
        calculated_hist = macd_line - signal_line
        pd.testing.assert_series_equal(histogram, calculated_hist, check_exact=False)


class TestBollingerBands:
    """Test Bollinger Bands calculations"""
    
    def test_bollinger_bands_structure(self):
        """Test BB structure"""
        data = pd.Series(np.random.uniform(100, 110, 50))
        upper, middle, lower = TechnicalIndicators.bollinger_bands(data, period=20)
        
        # Should have correct length
        assert len(upper) == len(data)
        assert len(middle) == len(data)
        assert len(lower) == len(data)
    
    def test_bollinger_bands_relationship(self):
        """Test upper > middle > lower"""
        data = pd.Series(np.random.uniform(100, 110, 50))
        upper, middle, lower = TechnicalIndicators.bollinger_bands(data, period=20)
        
        # After period, upper should be > middle > lower
        valid_idx = ~(upper.isna() | middle.isna() | lower.isna())
        assert (upper[valid_idx] > middle[valid_idx]).all()
        assert (middle[valid_idx] > lower[valid_idx]).all()


class TestATR:
    """Test Average True Range calculations"""
    
    def test_atr_basic(self):
        """Test basic ATR calculation"""
        high = pd.Series([110, 111, 112, 113, 114])
        low = pd.Series([100, 101, 102, 103, 104])
        close = pd.Series([105, 106, 107, 108, 109])
        
        atr = TechnicalIndicators.atr(high, low, close, period=2)
        
        # ATR should exist and be positive
        assert len(atr) == len(high)
        assert (atr.dropna() > 0).all()


class TestStochastic:
    """Test Stochastic Oscillator calculations"""
    
    def test_stochastic_basic(self):
        """Test basic stochastic calculation"""
        high = pd.Series([110, 111, 112, 113, 114, 115])
        low = pd.Series([100, 101, 102, 103, 104, 105])
        close = pd.Series([105, 106, 107, 108, 109, 110])
        
        k, d = TechnicalIndicators.stochastic(high, low, close, period=3)
        
        # Should have correct length
        assert len(k) == len(high)
        assert len(d) == len(high)
    
    def test_stochastic_range(self):
        """Test stochastic is between 0 and 100"""
        high = pd.Series(np.random.uniform(110, 120, 50))
        low = pd.Series(np.random.uniform(100, 110, 50))
        close = pd.Series(np.random.uniform(105, 115, 50))
        
        k, d = TechnicalIndicators.stochastic(high, low, close, period=14)
        
        # K and D should be between 0 and 100
        valid_k = k.dropna()
        valid_d = d.dropna()
        
        assert (valid_k >= 0).all()
        assert (valid_k <= 100).all()
        assert (valid_d >= 0).all()
        assert (valid_d <= 100).all()


class TestAddAllIndicators:
    """Test adding all indicators to DataFrame"""
    
    def test_add_all_indicators_creates_columns(self):
        """Test all indicator columns are created"""
        # Create sample OHLC data
        data = pd.DataFrame({
            'Open': np.random.uniform(100, 110, 100),
            'High': np.random.uniform(110, 120, 100),
            'Low': np.random.uniform(90, 100, 100),
            'Close': np.random.uniform(100, 110, 100),
        })
        
        # Ensure proper OHLC structure
        data['High'] = data[['Open', 'High', 'Close']].max(axis=1)
        data['Low'] = data[['Open', 'Low', 'Close']].min(axis=1)
        
        result = TechnicalIndicators.add_all_indicators(data)
        
        # Check all indicators are present
        expected_indicators = [
            'MA9', 'MA21', 'MA50',
            'RSI',
            'MACD', 'MACD_Signal', 'MACD_Hist',
            'BB_Upper', 'BB_Middle', 'BB_Lower',
            'ATR',
            'Stoch_K', 'Stoch_D'
        ]
        
        for indicator in expected_indicators:
            assert indicator in result.columns
    
    def test_add_all_indicators_no_error_with_small_data(self):
        """Test function handles small datasets gracefully"""
        data = pd.DataFrame({
            'Open': [100, 101],
            'High': [102, 103],
            'Low': [99, 100],
            'Close': [100.5, 101.5],
        })
        
        # Should not raise error
        result = TechnicalIndicators.add_all_indicators(data)
        assert result is not None


class TestIndicatorSummary:
    """Test indicator summary function"""
    
    def test_get_indicator_summary(self):
        """Test getting indicator summary"""
        # Create sample data with indicators
        data = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104, 105],
            'MA9': [100.5, 101.5, 102.5, 103.5, 104.5, 105.5],
            'RSI': [50, 55, 60, 65, 70, 75],
        })
        
        summary = TechnicalIndicators.get_indicator_summary(data)
        
        # Check summary has values
        assert summary['Close'] == 105
        assert summary['MA9'] == 105.5
        assert summary['RSI'] == 75
    
    def test_get_indicator_summary_empty_data(self):
        """Test summary with empty DataFrame"""
        data = pd.DataFrame()
        summary = TechnicalIndicators.get_indicator_summary(data)
        
        # Should return empty dict
        assert summary == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
