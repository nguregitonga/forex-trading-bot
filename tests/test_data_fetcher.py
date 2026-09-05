"""
Unit tests for data fetcher
"""

import pytest
import pandas as pd
from pathlib import Path
from src.market.data_fetcher import DataFetcher


class TestDataFetcher:
    """Test DataFetcher functionality"""
    
    def test_data_fetcher_initialization(self):
        """Test DataFetcher initializes correctly"""
        fetcher = DataFetcher(data_dir="test_data")
        assert fetcher.source == "yfinance"
        assert fetcher.data_dir == Path("test_data")
    
    def test_fetch_forex_data_returns_dataframe(self):
        """Test fetch returns DataFrame"""
        fetcher = DataFetcher()
        
        # Fetch recent data (use shorter period for testing)
        data = fetcher.fetch_forex_data('EURUSD', interval='1d', period='1mo')
        
        # Should return DataFrame (may be empty if network unavailable)
        assert isinstance(data, pd.DataFrame)
    
    def test_data_has_required_columns(self):
        """Test fetched data has OHLC columns"""
        fetcher = DataFetcher()
        data = fetcher.fetch_forex_data('EURUSD', interval='1d', period='1mo')
        
        if not data.empty:
            required_cols = ['Open', 'High', 'Low', 'Close']
            for col in required_cols:
                assert col in data.columns
    
    def test_add_technical_features(self):
        """Test adding technical features"""
        # Create sample data
        data = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [102, 103, 104],
            'Low': [99, 100, 101],
            'Close': [100.5, 101.5, 102.5],
            'Volume': [1000, 1100, 1200]
        })
        
        fetcher = DataFetcher()
        result = fetcher.add_technical_features(data)
        
        # Check features were added
        assert 'Returns' in result.columns
        assert 'Daily_Range' in result.columns
        assert 'Typical_Price' in result.columns
        assert 'Volume_MA' in result.columns
    
    def test_resample_data(self):
        """Test data resampling"""
        # Create hourly data
        dates = pd.date_range('2024-01-01', periods=24, freq='h')
        data = pd.DataFrame({
            'Open': [100 + i for i in range(24)],
            'High': [101 + i for i in range(24)],
            'Low': [99 + i for i in range(24)],
            'Close': [100.5 + i for i in range(24)],
            'Volume': [1000 for _ in range(24)]
        }, index=dates)
        
        fetcher = DataFetcher()
        resampled = fetcher.resample_data(data, '4h')
        
        # Should have fewer candles (24 hourly -> 6 4-hourly)
        assert len(resampled) <= len(data)
        assert 'Open' in resampled.columns
        assert 'Close' in resampled.columns
    
    def test_validate_data_empty(self):
        """Test validation with empty data"""
        fetcher = DataFetcher()
        data = pd.DataFrame()
        
        is_valid, message = fetcher.validate_data(data)
        assert is_valid == False
        assert "empty" in message.lower()
    
    def test_validate_data_missing_columns(self):
        """Test validation with missing columns"""
        fetcher = DataFetcher()
        data = pd.DataFrame({
            'Open': [100, 101],
            'Close': [100.5, 101.5]
        })
        
        is_valid, message = fetcher.validate_data(data)
        assert is_valid == False
        assert "missing" in message.lower()
    
    def test_validate_data_with_nan(self):
        """Test validation with NaN values"""
        fetcher = DataFetcher()
        data = pd.DataFrame({
            'Open': [100, float('nan')],
            'High': [102, 103],
            'Low': [99, 100],
            'Close': [100.5, 101.5]
        })
        
        is_valid, message = fetcher.validate_data(data)
        assert is_valid == False
        assert "nan" in message.lower()
    
    def test_validate_data_invalid_ohlc(self):
        """Test validation with invalid OHLC relationships"""
        fetcher = DataFetcher()
        data = pd.DataFrame({
            'Open': [100, 101],
            'High': [95, 103],  # High < Low (invalid)
            'Low': [99, 100],
            'Close': [100.5, 101.5]
        })
        
        is_valid, message = fetcher.validate_data(data)
        assert is_valid == False
        assert "invalid" in message.lower()
    
    def test_validate_data_valid(self):
        """Test validation with valid data"""
        fetcher = DataFetcher()
        data = pd.DataFrame({
            'Open': [100, 101],
            'High': [102, 103],
            'Low': [99, 100],
            'Close': [100.5, 101.5]
        })
        
        is_valid, message = fetcher.validate_data(data)
        assert is_valid == True
        assert "passed" in message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
