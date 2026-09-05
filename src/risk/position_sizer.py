"""
Position sizer for calculating correct trade position sizes
Ensures risk is controlled per trade based on account percentage
"""

import pandas as pd
from typing import Optional, Dict, Tuple
from src.logger import get_logger

logger = get_logger(__name__)


class PositionSizer:
    """Calculate position size based on risk management rules"""
    
    def __init__(
        self,
        account_size: float,
        risk_percent: float = 1.0,
        min_position_size: float = 0.01,
        max_position_size: float = 10.0
    ):
        """
        Initialize position sizer
        
        Args:
            account_size: Total trading account size (USD)
            risk_percent: Percentage of account to risk per trade (default 1%)
            min_position_size: Minimum lot size (default 0.01 micro lots)
            max_position_size: Maximum lot size (default 10 standard lots)
        """
        self.account_size = account_size
        self.risk_percent = risk_percent
        self.min_position_size = min_position_size
        self.max_position_size = max_position_size
        
        logger.info(
            f"PositionSizer initialized: Account=${account_size:.2f}, "
            f"Risk={risk_percent}%, Min={min_position_size}, Max={max_position_size}"
        )
    
    def get_risk_amount(self) -> float:
        """
        Calculate the dollar amount to risk on this trade
        
        Returns:
            Amount in USD to risk
        """
        risk_amount = self.account_size * (self.risk_percent / 100)
        return risk_amount
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        pip_value: float = 0.0001
    ) -> Dict[str, float]:
        """
        Calculate position size based on entry and stop loss
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            pip_value: Pip value for the currency pair (default 0.0001 for most pairs)
        
        Returns:
            Dictionary with lot_size, risk_amount, pips
        """
        # Calculate pips (distance from entry to stop loss)
        pips = abs(entry_price - stop_loss_price) / pip_value
        
        if pips == 0:
            logger.error("Stop loss distance is zero - invalid calculation")
            return {
                'lot_size': 0,
                'risk_amount': 0,
                'pips': 0,
                'valid': False
            }
        
        # Calculate risk amount
        risk_amount = self.get_risk_amount()
        
        # Calculate lot size
        # For 1 micro lot (0.01): 1 pip = $0.10
        # For 1 mini lot (0.1): 1 pip = $1.00
        # For 1 standard lot (1.0): 1 pip = $10.00
        
        # Formula: Position Size = Risk Amount / (Pips * Pip Value in Account Currency)
        # For USD account with EUR/USD: pip value per lot = 10
        lot_size = risk_amount / (pips * 10)
        
        # Enforce position size limits
        if lot_size < self.min_position_size:
            lot_size = self.min_position_size
            logger.warning(
                f"Position size {lot_size:.4f} below minimum {self.min_position_size}, "
                f"setting to minimum"
            )
        
        if lot_size > self.max_position_size:
            lot_size = self.max_position_size
            logger.warning(
                f"Position size {lot_size:.4f} exceeds maximum {self.max_position_size}, "
                f"capping at maximum"
            )
        
        result = {
            'lot_size': lot_size,
            'risk_amount': risk_amount,
            'pips': pips,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'valid': True
        }
        
        logger.info(f"Position size calculated: {lot_size:.4f} lots for {pips:.0f} pips")
        return result
    
    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss_price: float,
        risk_reward_ratio: float = 1.5,
        direction: str = 'long'
    ) -> float:
        """
        Calculate take profit price based on risk-reward ratio
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            risk_reward_ratio: Desired risk:reward ratio (default 1.5)
            direction: 'long' or 'short'
        
        Returns:
            Take profit price
        """
        risk_distance = abs(entry_price - stop_loss_price)
        reward_distance = risk_distance * risk_reward_ratio
        
        if direction.lower() == 'long':
            take_profit = entry_price + reward_distance
        else:  # short
            take_profit = entry_price - reward_distance
        
        logger.info(
            f"Take profit calculated: {take_profit:.5f} "
            f"(Risk:Reward = 1:{risk_reward_ratio})"
        )
        
        return take_profit
    
    def calculate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        trailing_pips: float = 10.0,
        direction: str = 'long',
        pip_value: float = 0.0001
    ) -> float:
        """
        Calculate trailing stop loss
        
        Args:
            entry_price: Initial entry price
            current_price: Current market price
            trailing_pips: Number of pips to trail stop (default 10)
            direction: 'long' or 'short'
            pip_value: Pip value
        
        Returns:
            Trailing stop loss price
        """
        trailing_distance = trailing_pips * pip_value
        
        if direction.lower() == 'long':
            trailing_stop = current_price - trailing_distance
        else:  # short
            trailing_stop = current_price + trailing_distance
        
        return trailing_stop
    
    def calculate_breakeven_stop(
        self,
        entry_price: float,
        current_price: float,
        commission_pips: float = 1.0,
        direction: str = 'long',
        pip_value: float = 0.0001
    ) -> float:
        """
        Calculate break-even stop loss (accounting for commission)
        
        Args:
            entry_price: Entry price
            current_price: Current price
            commission_pips: Commission cost in pips (default 1 pip)
            direction: 'long' or 'short'
            pip_value: Pip value
        
        Returns:
            Break-even stop loss price
        """
        commission_distance = commission_pips * pip_value
        
        if direction.lower() == 'long':
            # Move stop up to cover commission
            breakeven = entry_price + commission_distance
        else:  # short
            breakeven = entry_price - commission_distance
        
        return breakeven
    
    def calculate_pyramid_sizes(
        self,
        base_lot_size: float,
        pyramiding_levels: int = 3,
        scale_factor: float = 0.8
    ) -> list:
        """
        Calculate position sizes for pyramiding (adding to winning positions)
        
        Args:
            base_lot_size: Initial position size
            pyramiding_levels: Number of additional entries
            scale_factor: How much to reduce each level (0.8 = 80% of previous)
        
        Returns:
            List of lot sizes for each pyramid level
        """
        sizes = [base_lot_size]
        
        for i in range(1, pyramiding_levels):
            next_size = base_lot_size * (scale_factor ** i)
            # Enforce position limits
            if next_size < self.min_position_size:
                break
            if sum(sizes) + next_size > self.max_position_size:
                break
            sizes.append(next_size)
        
        logger.info(f"Pyramid sizes calculated: {[f'{s:.4f}' for s in sizes]}")
        return sizes
    
    def validate_position(
        self,
        lot_size: float,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: float,
        account_balance: float
    ) -> Tuple[bool, str]:
        """
        Validate a position before execution
        
        Args:
            lot_size: Position size
            entry_price: Entry price
            stop_loss_price: Stop loss price
            take_profit_price: Take profit price
            account_balance: Current account balance
        
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check position size limits
        if lot_size < self.min_position_size:
            return False, f"Position {lot_size:.4f} below minimum {self.min_position_size}"
        
        if lot_size > self.max_position_size:
            return False, f"Position {lot_size:.4f} exceeds maximum {self.max_position_size}"
        
        # Check risk amount
        pips = abs(entry_price - stop_loss_price) / 0.0001
        risk_amount = pips * 10 * lot_size
        
        if risk_amount > account_balance * 0.05:  # Max 5% per trade
            return False, f"Risk amount ${risk_amount:.2f} exceeds 5% of balance"
        
        # Check stop loss distance
        if pips < 3:
            return False, "Stop loss too close (minimum 3 pips)"
        
        if pips > 1000:
            return False, "Stop loss too far (maximum 1000 pips)"
        
        # Check take profit vs stop loss
        if take_profit_price == entry_price:
            return False, "Take profit equals entry price"
        
        tp_distance = abs(take_profit_price - entry_price)
        sl_distance = abs(stop_loss_price - entry_price)
        
        if tp_distance < sl_distance:
            return False, "Take profit closer than stop loss"
        
        return True, "Position valid"
    
    def update_account_size(self, new_size: float):
        """Update account size after trading"""
        self.account_size = new_size
        logger.info(f"Account size updated to ${new_size:.2f}")
    
    def get_position_summary(self, position: Dict) -> str:
        """Get human-readable position summary"""
        summary = f"""
Position Summary:
  Lot Size: {position['lot_size']:.4f}
  Entry: {position['entry_price']:.5f}
  Stop Loss: {position['stop_loss_price']:.5f}
  Pips at Risk: {position['pips']:.0f}
  Amount at Risk: ${position['risk_amount']:.2f}
        """
        return summary


def demo_position_sizer():
    """Demo position sizer functionality"""
    
    # Initialize sizer
    sizer = PositionSizer(
        account_size=10000,
        risk_percent=1.0,  # Risk 1% per trade
        min_position_size=0.01,
        max_position_size=1.0
    )
    
    logger.info("\n" + "="*60)
    logger.info("POSITION SIZING EXAMPLE")
    logger.info("="*60)
    
    # Example 1: Long trade on EURUSD
    logger.info("\nExample 1: EURUSD Long Trade")
    logger.info("-" * 60)
    
    position1 = sizer.calculate_position_size(
        entry_price=1.0950,
        stop_loss_price=1.0940,  # 10 pips
        pip_value=0.0001
    )
    
    logger.info(sizer.get_position_summary(position1))
    
    # Calculate take profit
    tp1 = sizer.calculate_take_profit(
        entry_price=1.0950,
        stop_loss_price=1.0940,
        risk_reward_ratio=1.5,
        direction='long'
    )
    logger.info(f"Take Profit: {tp1:.5f} (Risk:Reward = 1:1.5)")
    
    # Example 2: Short trade on GBPUSD
    logger.info("\n\nExample 2: GBPUSD Short Trade")
    logger.info("-" * 60)
    
    position2 = sizer.calculate_position_size(
        entry_price=1.2750,
        stop_loss_price=1.2770,  # 20 pips
        pip_value=0.0001
    )
    
    logger.info(sizer.get_position_summary(position2))
    
    # Calculate take profit
    tp2 = sizer.calculate_take_profit(
        entry_price=1.2750,
        stop_loss_price=1.2770,
        risk_reward_ratio=2.0,
        direction='short'
    )
    logger.info(f"Take Profit: {tp2:.5f} (Risk:Reward = 1:2.0)")
    
    # Example 3: Trailing stop
    logger.info("\n\nExample 3: Trailing Stop Loss")
    logger.info("-" * 60)
    
    trailing_stop = sizer.calculate_trailing_stop(
        entry_price=1.0950,
        current_price=1.1000,
        trailing_pips=15,
        direction='long'
    )
    logger.info(f"Current Price: 1.1000")
    logger.info(f"Trailing Stop (15 pips): {trailing_stop:.5f}")
    
    # Example 4: Pyramid sizing
    logger.info("\n\nExample 4: Pyramid Sizing")
    logger.info("-" * 60)
    
    pyramid = sizer.calculate_pyramid_sizes(
        base_lot_size=0.10,
        pyramiding_levels=3,
        scale_factor=0.8
    )
    logger.info(f"Pyramid levels: {[f'{s:.4f}' for s in pyramid]}")
    logger.info(f"Total position: {sum(pyramid):.4f}")
    
    # Example 5: Position validation
    logger.info("\n\nExample 5: Position Validation")
    logger.info("-" * 60)
    
    is_valid, reason = sizer.validate_position(
        lot_size=0.05,
        entry_price=1.0950,
        stop_loss_price=1.0940,
        take_profit_price=1.0975,
        account_balance=10000
    )
    logger.info(f"Valid: {is_valid} - {reason}")
    
    logger.info("="*60 + "\n")


if __name__ == "__main__":
    demo_position_sizer()
