"""
Risk manager for tracking and enforcing risk limits
Monitors daily losses, drawdown, and consecutive losses
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import deque
from src.logger import get_logger

logger = get_logger(__name__)


class RiskManager:
    """Manage trading risk and enforce limits"""
    
    def __init__(
        self,
        account_size: float,
        max_daily_loss_percent: float = 5.0,
        max_drawdown_percent: float = 10.0,
        max_consecutive_losses: int = 3,
        max_open_positions: int = 5
    ):
        """
        Initialize risk manager
        
        Args:
            account_size: Starting account size
            max_daily_loss_percent: Stop trading if daily loss exceeds this
            max_drawdown_percent: Stop trading if drawdown exceeds this
            max_consecutive_losses: Stop after N consecutive losses
            max_open_positions: Maximum concurrent open trades
        """
        self.account_size = account_size
        self.current_balance = account_size
        self.peak_balance = account_size
        
        self.max_daily_loss_percent = max_daily_loss_percent
        self.max_drawdown_percent = max_drawdown_percent
        self.max_consecutive_losses = max_consecutive_losses
        self.max_open_positions = max_open_positions
        
        # Trading history
        self.trades: List[Dict] = []
        self.daily_pnl: Dict[str, float] = {}  # Date -> PnL
        self.consecutive_losses = 0
        self.open_positions = 0
        
        # Equity curve tracking
        self.equity_history: List[Tuple[datetime, float]] = [
            (datetime.now(), account_size)
        ]
        
        logger.info(
            f"RiskManager initialized: Account=${account_size:.2f}, "
            f"Max Daily Loss={max_daily_loss_percent}%, "
            f"Max Drawdown={max_drawdown_percent}%"
        )
    
    def can_trade(self) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on risk limits
        
        Returns:
            Tuple of (can_trade, reason)
        """
        # Check daily loss limit
        today = datetime.now().strftime('%Y-%m-%d')
        daily_loss = self.daily_pnl.get(today, 0)
        max_daily_loss = self.account_size * (self.max_daily_loss_percent / 100)
        
        if daily_loss < -max_daily_loss:
            return False, f"Daily loss limit exceeded: ${-daily_loss:.2f} > ${max_daily_loss:.2f}"
        
        # Check drawdown limit
        current_drawdown = self.get_current_drawdown_percent()
        if current_drawdown > self.max_drawdown_percent:
            return False, f"Drawdown limit exceeded: {current_drawdown:.2f}% > {self.max_drawdown_percent}%"
        
        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Max consecutive losses reached: {self.consecutive_losses}"
        
        # Check open positions limit
        if self.open_positions >= self.max_open_positions:
            return False, f"Max open positions reached: {self.open_positions}/{self.max_open_positions}"
        
        return True, "Trading allowed"
    
    def record_trade(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        lot_size: float,
        pnl: float,
        is_winning: bool
    ):
        """
        Record a completed trade
        
        Args:
            symbol: Currency pair traded
            entry_price: Entry price
            exit_price: Exit price
            lot_size: Position size
            pnl: Profit/Loss
            is_winning: True if trade was profitable
        """
        trade = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'lot_size': lot_size,
            'pnl': pnl,
            'is_winning': is_winning
        }
        
        self.trades.append(trade)
        
        # Update balance
        self.current_balance += pnl
        
        # Update peak balance for drawdown calculation
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        # Track daily PnL
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_pnl[today] = self.daily_pnl.get(today, 0) + pnl
        
        # Update consecutive losses
        if is_winning:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        # Add to equity history
        self.equity_history.append((datetime.now(), self.current_balance))
        
        logger.info(
            f"Trade recorded: {symbol} {'+' if is_winning else '-'}${abs(pnl):.2f} "
            f"| Balance: ${self.current_balance:.2f} | Consecutive Losses: {self.consecutive_losses}"
        )
    
    def open_position(self, symbol: str, lot_size: float, pnl: float = 0.0):
        """
        Track opening of a position
        
        Args:
            symbol: Currency pair
            lot_size: Position size
            pnl: Unrealized PnL (if any)
        """
        self.open_positions += 1
        logger.info(f"Position opened: {symbol} ({lot_size} lots) | Open positions: {self.open_positions}")
    
    def close_position(self, symbol: str, pnl: float = 0.0):
        """
        Track closing of a position
        
        Args:
            symbol: Currency pair
            pnl: Realized PnL
        """
        if self.open_positions > 0:
            self.open_positions -= 1
        
        logger.info(f"Position closed: {symbol} | Open positions: {self.open_positions}")
    
    def get_current_drawdown_percent(self) -> float:
        """
        Calculate current drawdown percentage
        
        Returns:
            Drawdown as percentage
        """
        if self.peak_balance == 0:
            return 0
        
        drawdown = ((self.peak_balance - self.current_balance) / self.peak_balance) * 100
        return max(0, drawdown)
    
    def get_daily_pnl(self, date: str = None) -> float:
        """
        Get PnL for a specific day
        
        Args:
            date: Date string (YYYY-MM-DD), defaults to today
        
        Returns:
            Daily PnL
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        return self.daily_pnl.get(date, 0)
    
    def get_win_rate(self) -> float:
        """
        Calculate win rate percentage
        
        Returns:
            Win rate (0-100)
        """
        if not self.trades:
            return 0
        
        winning_trades = sum(1 for t in self.trades if t['is_winning'])
        return (winning_trades / len(self.trades)) * 100
    
    def get_profit_factor(self) -> float:
        """
        Calculate profit factor (gross profit / gross loss)
        
        Returns:
            Profit factor
        """
        if not self.trades:
            return 0
        
        gross_profit = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in self.trades if t['pnl'] < 0))
        
        if gross_loss == 0:
            return 0 if gross_profit == 0 else float('inf')
        
        return gross_profit / gross_loss
    
    def get_average_win(self) -> float:
        """
        Calculate average winning trade
        
        Returns:
            Average win amount
        """
        winning_trades = [t['pnl'] for t in self.trades if t['is_winning']]
        
        if not winning_trades:
            return 0
        
        return sum(winning_trades) / len(winning_trades)
    
    def get_average_loss(self) -> float:
        """
        Calculate average losing trade
        
        Returns:
            Average loss amount (as positive)
        """
        losing_trades = [t['pnl'] for t in self.trades if not t['is_winning']]
        
        if not losing_trades:
            return 0
        
        return abs(sum(losing_trades) / len(losing_trades))
    
    def get_expectancy(self) -> float:
        """
        Calculate expectancy (average profit per trade)
        
        Returns:
            Expected value per trade
        """
        if not self.trades:
            return 0
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        return total_pnl / len(self.trades)
    
    def get_risk_reward_ratio(self) -> float:
        """
        Calculate overall risk-reward ratio
        
        Returns:
            Average reward / average risk
        """
        avg_win = self.get_average_win()
        avg_loss = self.get_average_loss()
        
        if avg_loss == 0:
            return 0 if avg_win == 0 else float('inf')
        
        return avg_win / avg_loss
    
    def get_max_consecutive_wins(self) -> int:
        """
        Calculate maximum consecutive wins
        
        Returns:
            Max consecutive winning trades
        """
        if not self.trades:
            return 0
        
        max_wins = 0
        current_wins = 0
        
        for trade in self.trades:
            if trade['is_winning']:
                current_wins += 1
                max_wins = max(max_wins, current_wins)
            else:
                current_wins = 0
        
        return max_wins
    
    def get_max_consecutive_losses(self) -> int:
        """
        Calculate maximum consecutive losses
        
        Returns:
            Max consecutive losing trades
        """
        if not self.trades:
            return 0
        
        max_losses = 0
        current_losses = 0
        
        for trade in self.trades:
            if not trade['is_winning']:
                current_losses += 1
                max_losses = max(max_losses, current_losses)
            else:
                current_losses = 0
        
        return max_losses
    
    def get_statistics(self) -> Dict:
        """
        Get comprehensive trading statistics
        
        Returns:
            Dictionary with all trading stats
        """
        return {
            'total_trades': len(self.trades),
            'winning_trades': sum(1 for t in self.trades if t['is_winning']),
            'losing_trades': sum(1 for t in self.trades if not t['is_winning']),
            'win_rate': self.get_win_rate(),
            'profit_factor': self.get_profit_factor(),
            'average_win': self.get_average_win(),
            'average_loss': self.get_average_loss(),
            'expectancy': self.get_expectancy(),
            'risk_reward_ratio': self.get_risk_reward_ratio(),
            'max_consecutive_wins': self.get_max_consecutive_wins(),
            'max_consecutive_losses': self.get_max_consecutive_losses(),
            'current_balance': self.current_balance,
            'peak_balance': self.peak_balance,
            'current_drawdown_percent': self.get_current_drawdown_percent(),
            'total_pnl': self.current_balance - self.account_size,
            'return_percent': ((self.current_balance - self.account_size) / self.account_size) * 100
        }
    
    def print_statistics(self):
        """
        Print formatted trading statistics
        """
        stats = self.get_statistics()
        
        logger.info("\n" + "="*60)
        logger.info("TRADING STATISTICS")
        logger.info("="*60)
        logger.info(f"Total Trades: {stats['total_trades']}")
        logger.info(f"  Wins: {stats['winning_trades']} | Losses: {stats['losing_trades']}")
        logger.info(f"Win Rate: {stats['win_rate']:.2f}%")
        logger.info(f"Profit Factor: {stats['profit_factor']:.2f}")
        logger.info(f"Average Win: ${stats['average_win']:.2f}")
        logger.info(f"Average Loss: ${stats['average_loss']:.2f}")
        logger.info(f"Expectancy: ${stats['expectancy']:.2f} per trade")
        logger.info(f"Risk:Reward Ratio: 1:{stats['risk_reward_ratio']:.2f}")
        logger.info(f"Max Consecutive Wins: {stats['max_consecutive_wins']}")
        logger.info(f"Max Consecutive Losses: {stats['max_consecutive_losses']}")
        logger.info(f"\nAccount:")
        logger.info(f"  Starting Balance: ${self.account_size:.2f}")
        logger.info(f"  Current Balance: ${stats['current_balance']:.2f}")
        logger.info(f"  Peak Balance: ${stats['peak_balance']:.2f}")
        logger.info(f"  Drawdown: {stats['current_drawdown_percent']:.2f}%")
        logger.info(f"  Total P&L: ${stats['total_pnl']:.2f}")
        logger.info(f"  Return: {stats['return_percent']:.2f}%")
        logger.info("="*60 + "\n")


def demo_risk_manager():
    """Demo risk manager functionality"""
    
    rm = RiskManager(
        account_size=10000,
        max_daily_loss_percent=5.0,
        max_consecutive_losses=3
    )
    
    logger.info("\n" + "="*60)
    logger.info("RISK MANAGER DEMO")
    logger.info("="*60)
    
    # Simulate some trades
    trades = [
        {'symbol': 'EURUSD', 'pnl': 50, 'is_winning': True},
        {'symbol': 'GBPUSD', 'pnl': -30, 'is_winning': False},
        {'symbol': 'USDJPY', 'pnl': 75, 'is_winning': True},
        {'symbol': 'AUDUSD', 'pnl': 100, 'is_winning': True},
        {'symbol': 'EURUSD', 'pnl': -50, 'is_winning': False},
        {'symbol': 'GBPUSD', 'pnl': 60, 'is_winning': True},
    ]
    
    for trade in trades:
        can_trade, reason = rm.can_trade()
        logger.info(f"Can trade: {can_trade} - {reason}")
        
        if can_trade:
            rm.record_trade(
                symbol=trade['symbol'],
                entry_price=100,
                exit_price=101,
                lot_size=0.1,
                pnl=trade['pnl'],
                is_winning=trade['is_winning']
            )
    
    # Print statistics
    rm.print_statistics()


if __name__ == "__main__":
    demo_risk_manager()
