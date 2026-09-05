"""
Unit tests for drawdown monitor
"""

import pytest
from src.risk.drawdown_monitor import DrawdownMonitor


class TestDrawdownMonitor:
    """Test DrawdownMonitor functionality"""
    
    def test_drawdown_monitor_initialization(self):
        """Test monitor initializes correctly"""
        dm = DrawdownMonitor(
            account_size=10000,
            max_drawdown_percent=10.0
        )
        
        assert dm.account_size == 10000
        assert dm.current_equity == 10000
        assert dm.peak_equity == 10000
    
    def test_update_equity_increase(self):
        """Test equity increase updates peak"""
        dm = DrawdownMonitor(account_size=10000)
        
        is_valid, reason = dm.update_equity(11000)
        
        assert is_valid == True
        assert dm.current_equity == 11000
        assert dm.peak_equity == 11000  # Peak should update
    
    def test_update_equity_decrease(self):
        """Test equity decrease creates drawdown"""
        dm = DrawdownMonitor(account_size=10000)
        
        is_valid, reason = dm.update_equity(9500)
        
        assert is_valid == True
        assert dm.current_equity == 9500
        dd = dm.get_current_drawdown_percent()
        assert dd == pytest.approx(5.0, abs=0.1)  # 5% drawdown
    
    def test_drawdown_limit_exceeded(self):
        """Test drawdown limit enforcement"""
        dm = DrawdownMonitor(account_size=10000, max_drawdown_percent=5.0)
        
        # Create 10% drawdown
        is_valid, reason = dm.update_equity(9000)
        
        assert is_valid == False
        assert "drawdown" in reason.lower()
    
    def test_get_current_drawdown_percent(self):
        """Test current drawdown percentage calculation"""
        dm = DrawdownMonitor(account_size=10000)
        
        dm.update_equity(11000)  # Peak up
        dm.update_equity(10450)  # Down from peak
        
        dd = dm.get_current_drawdown_percent()
        # (11000 - 10450) / 11000 = 5%
        assert dd == pytest.approx(5.0, abs=0.1)
    
    def test_get_current_drawdown_dollars(self):
        """Test current drawdown dollar calculation"""
        dm = DrawdownMonitor(account_size=10000)
        
        dm.update_equity(11000)  # Peak
        dm.update_equity(10500)  # Down
        
        dd_dollars = dm.get_current_drawdown_dollars()
        assert dd_dollars == 500
    
    def test_get_max_drawdown_percent(self):
        """Test maximum drawdown percentage"""
        dm = DrawdownMonitor(account_size=10000)
        
        # Simulate equity changes
        dm.update_equity(12000)  # Up
        dm.update_equity(10800)  # Down 10%
        dm.update_equity(11500)  # Partial recovery
        dm.update_equity(10350)  # Down further
        
        max_dd = dm.get_max_drawdown_percent()
        # Max drawdown from 12000 to 10350 = 13.75%
        assert max_dd > 10
    
    def test_get_max_drawdown_dollars(self):
        """Test maximum drawdown in dollars"""
        dm = DrawdownMonitor(account_size=10000)
        
        dm.update_equity(12000)  # Up
        dm.update_equity(10000)  # Down 2000
        
        max_dd_dollars = dm.get_max_drawdown_dollars()
        assert max_dd_dollars == 2000
    
    def test_is_in_drawdown(self):
        """Test in drawdown detection"""
        dm = DrawdownMonitor(account_size=10000)
        
        assert dm.is_in_drawdown() == False  # At equity = peak
        
        dm.update_equity(11000)  # New peak
        assert dm.is_in_drawdown() == False
        
        dm.update_equity(10500)  # Below peak
        assert dm.is_in_drawdown() == True
    
    def test_update_with_trade_positive(self):
        """Test update with positive trade"""
        dm = DrawdownMonitor(account_size=10000)
        
        is_valid, reason = dm.update_with_trade(100)
        
        assert is_valid == True
        assert dm.current_equity == 10100
    
    def test_update_with_trade_negative_within_limit(self):
        """Test update with loss within limit"""
        dm = DrawdownMonitor(
            account_size=10000,
            max_loss_per_trade=500
        )
        
        is_valid, reason = dm.update_with_trade(-200)
        
        assert is_valid == True
        assert dm.current_equity == 9800
    
    def test_update_with_trade_exceeds_loss_limit(self):
        """Test update with loss exceeding limit"""
        dm = DrawdownMonitor(
            account_size=10000,
            max_loss_per_trade=500
        )
        
        is_valid, reason = dm.update_with_trade(-1000)
        
        assert is_valid == False
        assert "loss" in reason.lower()
    
    def test_get_recovery_percentage(self):
        """Test recovery percentage calculation"""
        dm = DrawdownMonitor(account_size=10000)
        
        dm.update_equity(12000)  # Peak
        dm.update_equity(10600)  # Down 1400 from peak
        
        recovery = dm.get_recovery_percentage()
        # From 10000, loss was 1400 (to 10600), so 0% recovery
        assert 0 <= recovery <= 100
    
    def test_get_statistics(self):
        """Test statistics calculation"""
        dm = DrawdownMonitor(account_size=10000)
        
        dm.update_equity(11000)  # Peak
        dm.update_equity(10500)  # Drawdown
        
        stats = dm.get_statistics()
        
        assert stats['current_equity'] == 10500
        assert stats['peak_equity'] == 11000
        assert 'current_drawdown_percent' in stats
        assert 'is_in_drawdown' in stats
        assert stats['is_in_drawdown'] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
