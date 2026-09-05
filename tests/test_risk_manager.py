"""
Unit tests for risk manager
"""

import pytest
from src.risk.risk_manager import RiskManager


class TestRiskManager:
    """Test RiskManager functionality"""
    
    def test_risk_manager_initialization(self):
        """Test risk manager initializes correctly"""
        rm = RiskManager(
            account_size=10000,
            max_daily_loss_percent=5.0,
            max_consecutive_losses=3
        )
        
        assert rm.account_size == 10000
        assert rm.current_balance == 10000
        assert rm.max_daily_loss_percent == 5.0
    
    def test_can_trade_initially(self):
        """Test can trade returns True initially"""
        rm = RiskManager(account_size=10000)
        can_trade, reason = rm.can_trade()
        
        assert can_trade == True
    
    def test_record_winning_trade(self):
        """Test recording winning trade"""
        rm = RiskManager(account_size=10000)
        
        rm.record_trade(
            symbol='EURUSD',
            entry_price=1.0950,
            exit_price=1.0960,
            lot_size=0.1,
            pnl=100,
            is_winning=True
        )
        
        assert rm.current_balance == 10100
        assert len(rm.trades) == 1
        assert rm.consecutive_losses == 0
    
    def test_record_losing_trade(self):
        """Test recording losing trade"""
        rm = RiskManager(account_size=10000)
        
        rm.record_trade(
            symbol='EURUSD',
            entry_price=1.0950,
            exit_price=1.0940,
            lot_size=0.1,
            pnl=-50,
            is_winning=False
        )
        
        assert rm.current_balance == 9950
        assert len(rm.trades) == 1
        assert rm.consecutive_losses == 1
    
    def test_consecutive_losses_reset(self):
        """Test consecutive losses reset on win"""
        rm = RiskManager(account_size=10000)
        
        # 2 losses
        rm.record_trade('EURUSD', 1.0950, 1.0940, 0.1, -50, False)
        rm.record_trade('GBPUSD', 1.2750, 1.2740, 0.1, -50, False)
        assert rm.consecutive_losses == 2
        
        # Win resets
        rm.record_trade('USDJPY', 150, 151, 0.1, 100, True)
        assert rm.consecutive_losses == 0
    
    def test_win_rate_calculation(self):
        """Test win rate calculation"""
        rm = RiskManager(account_size=10000)
        
        rm.record_trade('EURUSD', 1.0950, 1.0960, 0.1, 100, True)
        rm.record_trade('GBPUSD', 1.2750, 1.2740, 0.1, -50, False)
        
        assert rm.get_win_rate() == 50.0  # 1 win out of 2 trades
    
    def test_profit_factor_calculation(self):
        """Test profit factor calculation"""
        rm = RiskManager(account_size=10000)
        
        rm.record_trade('EURUSD', 1.0950, 1.0960, 0.1, 100, True)
        rm.record_trade('GBPUSD', 1.2750, 1.2740, 0.1, -50, False)
        
        # Profit factor = 100 / 50 = 2.0
        assert rm.get_profit_factor() == 2.0
    
    def test_average_win_calculation(self):
        """Test average win calculation"""
        rm = RiskManager(account_size=10000)
        
        rm.record_trade('EURUSD', 1.0950, 1.0960, 0.1, 100, True)
        rm.record_trade('GBPUSD', 1.2750, 1.2760, 0.1, 50, True)
        
        assert rm.get_average_win() == 75.0  # (100 + 50) / 2
    
    def test_average_loss_calculation(self):
        """Test average loss calculation"""
        rm = RiskManager(account_size=10000)
        
        rm.record_trade('EURUSD', 1.0950, 1.0940, 0.1, -50, False)
        rm.record_trade('GBPUSD', 1.2750, 1.2730, 0.1, -100, False)
        
        assert rm.get_average_loss() == 75.0  # (50 + 100) / 2
    
    def test_expectancy_calculation(self):
        """Test expectancy calculation"""
        rm = RiskManager(account_size=10000)
        
        rm.record_trade('EURUSD', 1.0950, 1.0960, 0.1, 100, True)
        rm.record_trade('GBPUSD', 1.2750, 1.2740, 0.1, -50, False)
        
        # Expectancy = (100 - 50) / 2 = 25 per trade
        assert rm.get_expectancy() == 25.0
    
    def test_open_positions_tracking(self):
        """Test open positions tracking"""
        rm = RiskManager(account_size=10000, max_open_positions=5)
        
        rm.open_position('EURUSD', 0.1)
        assert rm.open_positions == 1
        
        rm.open_position('GBPUSD', 0.1)
        assert rm.open_positions == 2
        
        rm.close_position('EURUSD')
        assert rm.open_positions == 1
    
    def test_max_open_positions_limit(self):
        """Test max open positions limit"""
        rm = RiskManager(account_size=10000, max_open_positions=2)
        
        rm.open_position('EURUSD', 0.1)
        rm.open_position('GBPUSD', 0.1)
        
        can_trade, reason = rm.can_trade()
        assert can_trade == False
        assert "max open positions" in reason.lower()
    
    def test_consecutive_losses_limit(self):
        """Test max consecutive losses limit"""
        rm = RiskManager(account_size=10000, max_consecutive_losses=2)
        
        rm.record_trade('EURUSD', 1.0950, 1.0940, 0.1, -50, False)
        rm.record_trade('GBPUSD', 1.2750, 1.2740, 0.1, -50, False)
        
        can_trade, reason = rm.can_trade()
        assert can_trade == False
        assert "consecutive losses" in reason.lower()
    
    def test_get_statistics(self):
        """Test statistics calculation"""
        rm = RiskManager(account_size=10000)
        
        rm.record_trade('EURUSD', 1.0950, 1.0960, 0.1, 100, True)
        rm.record_trade('GBPUSD', 1.2750, 1.2740, 0.1, -50, False)
        
        stats = rm.get_statistics()
        
        assert stats['total_trades'] == 2
        assert stats['winning_trades'] == 1
        assert stats['losing_trades'] == 1
        assert stats['current_balance'] == 10050


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
