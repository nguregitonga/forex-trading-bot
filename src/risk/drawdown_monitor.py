"""
Drawdown monitor for tracking peak-to-valley decline
Protects account from excessive losses
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Tuple, List
from src.logger import get_logger

logger = get_logger(__name__)


class DrawdownMonitor:
    """Monitor and track drawdown in account equity"""
    
    def __init__(
        self,
        account_size: float,
        max_drawdown_percent: float = 10.0,
        max_loss_per_trade: float = None
    ):
        """
        Initialize drawdown monitor
        
        Args:
            account_size: Starting account size
            max_drawdown_percent: Maximum allowed drawdown percentage
            max_loss_per_trade: Maximum loss on single trade (None = unlimited)
        """
        self.account_size = account_size
        self.current_equity = account_size
        self.peak_equity = account_size
        self.max_drawdown_percent = max_drawdown_percent
        self.max_loss_per_trade = max_loss_per_trade
        
        # Tracking
        self.equity_history: List[Tuple[datetime, float]] = [
            (datetime.now(), account_size)
        ]
        self.drawdown_history: List[Tuple[datetime, float]] = [
            (datetime.now(), 0)
        ]
        
        logger.info(
            f"DrawdownMonitor initialized: Account=${account_size:.2f}, "
            f"Max Drawdown={max_drawdown_percent}%"
        )
    
    def update_equity(self, new_equity: float) -> Tuple[bool, str]:
        """
        Update current equity and check drawdown limits
        
        Args:
            new_equity: Updated account equity
        
        Returns:
            Tuple of (is_within_limits, reason)
        """
        # Update equity
        self.current_equity = new_equity
        self.equity_history.append((datetime.now(), new_equity))
        
        # Update peak if new high
        if new_equity > self.peak_equity:
            self.peak_equity = new_equity
        
        # Calculate current drawdown
        current_dd = self.get_current_drawdown_percent()
        self.drawdown_history.append((datetime.now(), current_dd))
        
        # Check drawdown limit
        if current_dd > self.max_drawdown_percent:
            logger.warning(
                f"DRAWDOWN LIMIT EXCEEDED: {current_dd:.2f}% > {self.max_drawdown_percent}%"
            )
            return False, f"Drawdown {current_dd:.2f}% exceeds limit {self.max_drawdown_percent}%"
        
        return True, f"Drawdown OK: {current_dd:.2f}%"
    
    def update_with_trade(self, pnl: float) -> Tuple[bool, str]:
        """
        Update equity with trade result and check limits
        
        Args:
            pnl: Trade profit/loss
        
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check individual trade loss limit
        if self.max_loss_per_trade and pnl < -self.max_loss_per_trade:
            return False, f"Trade loss ${-pnl:.2f} exceeds limit ${self.max_loss_per_trade:.2f}"
        
        # Update equity
        new_equity = self.current_equity + pnl
        return self.update_equity(new_equity)
    
    def get_current_drawdown_percent(self) -> float:
        """
        Calculate current drawdown percentage
        
        Returns:
            Drawdown as percentage (0-100)
        """
        if self.peak_equity == 0:
            return 0
        
        drawdown = ((self.peak_equity - self.current_equity) / self.peak_equity) * 100
        return max(0, drawdown)
    
    def get_current_drawdown_dollars(self) -> float:
        """
        Calculate current drawdown in dollar amount
        
        Returns:
            Drawdown amount
        """
        return self.peak_equity - self.current_equity
    
    def get_max_drawdown_percent(self) -> float:
        """
        Calculate maximum drawdown experienced
        
        Returns:
            Maximum drawdown percentage
        """
        if not self.equity_history:
            return 0
        
        max_dd = 0
        peak = self.equity_history[0][1]
        
        for timestamp, equity in self.equity_history:
            if equity > peak:
                peak = equity
            
            dd = ((peak - equity) / peak) * 100
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def get_max_drawdown_dollars(self) -> float:
        """
        Calculate maximum drawdown in dollars
        
        Returns:
            Maximum drawdown amount
        """
        if not self.equity_history:
            return 0
        
        max_dd = 0
        peak = self.equity_history[0][1]
        
        for timestamp, equity in self.equity_history:
            if equity > peak:
                peak = equity
            
            dd = peak - equity
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def get_recovery_time(self) -> Dict:
        """
        Calculate time to recover from drawdown
        
        Returns:
            Dictionary with recovery info
        """
        if self.current_equity >= self.peak_equity:
            return {
                'recovered': True,
                'time_to_recovery': 0,
                'recovery_trades_needed': 0
            }
        
        # Calculate approximate trades needed to recover
        current_dd = self.get_current_drawdown_dollars()
        avg_win = self._get_average_win()
        
        if avg_win <= 0:
            trades_needed = float('inf')
        else:
            trades_needed = int(current_dd / avg_win) + 1
        
        return {
            'recovered': False,
            'drawdown_amount': current_dd,
            'recovery_trades_needed': trades_needed
        }
    
    def _get_average_win(self) -> float:
        """Helper to get average trade profit from history"""
        if len(self.equity_history) < 2:
            return 0
        
        profits = []
        for i in range(1, len(self.equity_history)):
            change = self.equity_history[i][1] - self.equity_history[i-1][1]
            if change > 0:
                profits.append(change)
        
        return sum(profits) / len(profits) if profits else 0
    
    def get_recovery_percentage(self) -> float:
        """
        Get recovery progress (0-100)
        
        Returns:
            Recovery percentage
        """
        if self.current_equity >= self.peak_equity:
            return 100
        
        total_dd = self.peak_equity - self.account_size
        current_recovery = self.current_equity - self.account_size
        
        if total_dd == 0:
            return 100
        
        return max(0, (current_recovery / total_dd) * 100)
    
    def is_in_drawdown(self) -> bool:
        """Check if currently in drawdown"""
        return self.current_equity < self.peak_equity
    
    def get_statistics(self) -> Dict:
        """
        Get comprehensive drawdown statistics
        
        Returns:
            Dictionary with drawdown stats
        """
        return {
            'current_equity': self.current_equity,
            'peak_equity': self.peak_equity,
            'account_size': self.account_size,
            'current_drawdown_percent': self.get_current_drawdown_percent(),
            'current_drawdown_dollars': self.get_current_drawdown_dollars(),
            'max_drawdown_percent': self.get_max_drawdown_percent(),
            'max_drawdown_dollars': self.get_max_drawdown_dollars(),
            'recovery_percentage': self.get_recovery_percentage(),
            'is_in_drawdown': self.is_in_drawdown(),
            'total_gain': self.current_equity - self.account_size,
            'total_return_percent': ((self.current_equity - self.account_size) / self.account_size) * 100
        }
    
    def print_statistics(self):
        """
        Print formatted drawdown statistics
        """
        stats = self.get_statistics()
        
        logger.info("\n" + "="*60)
        logger.info("DRAWDOWN STATISTICS")
        logger.info("="*60)
        logger.info(f"Starting Equity: ${stats['account_size']:.2f}")
        logger.info(f"Peak Equity: ${stats['peak_equity']:.2f}")
        logger.info(f"Current Equity: ${stats['current_equity']:.2f}")
        logger.info(f"\nCurrent Drawdown:")
        logger.info(f"  Percentage: {stats['current_drawdown_percent']:.2f}%")
        logger.info(f"  Amount: ${stats['current_drawdown_dollars']:.2f}")
        logger.info(f"\nMaximum Drawdown:")
        logger.info(f"  Percentage: {stats['max_drawdown_percent']:.2f}%")
        logger.info(f"  Amount: ${stats['max_drawdown_dollars']:.2f}")
        logger.info(f"\nRecovery:")
        logger.info(f"  In Drawdown: {stats['is_in_drawdown']}")
        logger.info(f"  Recovery Progress: {stats['recovery_percentage']:.2f}%")
        logger.info(f"\nPerformance:")
        logger.info(f"  Total Gain: ${stats['total_gain']:.2f}")
        logger.info(f"  Return: {stats['total_return_percent']:.2f}%")
        logger.info("="*60 + "\n")


def demo_drawdown_monitor():
    """Demo drawdown monitor functionality"""
    
    dm = DrawdownMonitor(
        account_size=10000,
        max_drawdown_percent=15.0
    )
    
    logger.info("\n" + "="*60)
    logger.info("DRAWDOWN MONITOR DEMO")
    logger.info("="*60)
    
    # Simulate equity changes
    equity_changes = [100, -50, 200, -75, 150, -200, 100, 50, -30]
    
    for change in equity_changes:
        is_valid, reason = dm.update_with_trade(change)
        logger.info(f"Trade PnL: {change:+.2f} | {reason} | Valid: {is_valid}")
    
    # Print statistics
    dm.print_statistics()


if __name__ == "__main__":
    demo_drawdown_monitor()
