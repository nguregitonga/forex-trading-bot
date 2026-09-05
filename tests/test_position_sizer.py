"""
Unit tests for position sizer
"""

import pytest
from src.risk.position_sizer import PositionSizer


class TestPositionSizer:
    """Test PositionSizer functionality"""
    
    def test_position_sizer_initialization(self):
        """Test sizer initializes correctly"""
        sizer = PositionSizer(account_size=10000, risk_percent=1.0)
        assert sizer.account_size == 10000
        assert sizer.risk_percent == 1.0
    
    def test_get_risk_amount(self):
        """Test risk amount calculation"""
        sizer = PositionSizer(account_size=10000, risk_percent=1.0)
        risk = sizer.get_risk_amount()
        assert risk == 100  # 1% of 10000
    
    def test_calculate_position_size_long(self):
        """Test position size for long trade"""
        sizer = PositionSizer(account_size=10000, risk_percent=1.0)
        
        position = sizer.calculate_position_size(
            entry_price=1.0950,
            stop_loss_price=1.0940,  # 10 pips
            pip_value=0.0001
        )
        
        assert position['valid'] == True
        assert position['pips'] == 10
        assert position['lot_size'] > 0
    
    def test_calculate_position_size_short(self):
        """Test position size for short trade"""
        sizer = PositionSizer(account_size=10000, risk_percent=1.0)
        
        position = sizer.calculate_position_size(
            entry_price=1.0940,
            stop_loss_price=1.0950,  # 10 pips
            pip_value=0.0001
        )
        
        assert position['valid'] == True
        assert position['pips'] == 10
    
    def test_calculate_position_size_zero_pips(self):
        """Test position size with zero pips (invalid)"""
        sizer = PositionSizer(account_size=10000)
        
        position = sizer.calculate_position_size(
            entry_price=1.0950,
            stop_loss_price=1.0950,  # 0 pips
            pip_value=0.0001
        )
        
        assert position['valid'] == False
    
    def test_calculate_take_profit_long(self):
        """Test take profit for long trade"""
        sizer = PositionSizer(account_size=10000)
        
        tp = sizer.calculate_take_profit(
            entry_price=1.0950,
            stop_loss_price=1.0940,
            risk_reward_ratio=1.5,
            direction='long'
        )
        
        # Risk 10 pips, reward should be 15 pips
        assert tp == pytest.approx(1.0965, abs=0.0001)
    
    def test_calculate_take_profit_short(self):
        """Test take profit for short trade"""
        sizer = PositionSizer(account_size=10000)
        
        tp = sizer.calculate_take_profit(
            entry_price=1.0950,
            stop_loss_price=1.0960,
            risk_reward_ratio=2.0,
            direction='short'
        )
        
        # Risk 10 pips, reward should be 20 pips
        assert tp == pytest.approx(1.0930, abs=0.0001)
    
    def test_calculate_trailing_stop(self):
        """Test trailing stop calculation"""
        sizer = PositionSizer(account_size=10000)
        
        trailing = sizer.calculate_trailing_stop(
            entry_price=1.0950,
            current_price=1.1000,
            trailing_pips=10,
            direction='long'
        )
        
        # Should be current_price - 10 pips
        assert trailing == pytest.approx(1.0990, abs=0.0001)
    
    def test_calculate_breakeven_stop(self):
        """Test break-even stop calculation"""
        sizer = PositionSizer(account_size=10000)
        
        be = sizer.calculate_breakeven_stop(
            entry_price=1.0950,
            current_price=1.1000,
            commission_pips=2,
            direction='long'
        )
        
        # Should be entry + commission
        assert be == pytest.approx(1.0952, abs=0.0001)
    
    def test_calculate_pyramid_sizes(self):
        """Test pyramid sizing"""
        sizer = PositionSizer(
            account_size=10000,
            max_position_size=1.0
        )
        
        pyramid = sizer.calculate_pyramid_sizes(
            base_lot_size=0.10,
            pyramiding_levels=3,
            scale_factor=0.8
        )
        
        # Should have multiple levels
        assert len(pyramid) > 1
        # Should be decreasing
        assert pyramid[0] > pyramid[1]
    
    def test_validate_position_valid(self):
        """Test validation with valid position"""
        sizer = PositionSizer(account_size=10000)
        
        is_valid, reason = sizer.validate_position(
            lot_size=0.05,
            entry_price=1.0950,
            stop_loss_price=1.0940,
            take_profit_price=1.0975,
            account_balance=10000
        )
        
        assert is_valid == True
    
    def test_validate_position_stop_too_close(self):
        """Test validation with stop loss too close"""
        sizer = PositionSizer(account_size=10000)
        
        is_valid, reason = sizer.validate_position(
            lot_size=0.05,
            entry_price=1.0950,
            stop_loss_price=1.0948,  # Only 2 pips
            take_profit_price=1.0975,
            account_balance=10000
        )
        
        assert is_valid == False
        assert "too close" in reason.lower()
    
    def test_validate_position_tp_below_sl(self):
        """Test validation with TP closer than SL"""
        sizer = PositionSizer(account_size=10000)
        
        is_valid, reason = sizer.validate_position(
            lot_size=0.05,
            entry_price=1.0950,
            stop_loss_price=1.0940,  # 10 pips
            take_profit_price=1.0945,  # Only 5 pips
            account_balance=10000
        )
        
        assert is_valid == False
        assert "closer" in reason.lower()
    
    def test_update_account_size(self):
        """Test account size update"""
        sizer = PositionSizer(account_size=10000)
        sizer.update_account_size(15000)
        
        assert sizer.account_size == 15000
        assert sizer.get_risk_amount() == 150  # 1% of 15000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
