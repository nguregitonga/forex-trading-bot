# Phase 3: Risk Management System

## Overview

Phase 3 implements the **core risk management system** that protects your trading account from catastrophic losses. This phase is critical because no matter how good your trading strategy is, poor risk management will destroy your account.

**Key principle:** Risk management is MORE important than profits. A disciplined trader with a mediocre strategy will outperform a trader with a great strategy but poor risk management.

## What Was Built

### 1. Position Sizer (`src/risk/position_sizer.py`)

Calculates the correct trade size based on your risk tolerance.

**Key Methods:**

```python
# Initialize
sizer = PositionSizer(
    account_size=10000,      # Total account
    risk_percent=1.0,        # Risk 1% per trade
    min_position_size=0.01,  # Minimum 0.01 lots
    max_position_size=10.0   # Maximum 10 lots
)

# Calculate position size
position = sizer.calculate_position_size(
    entry_price=1.0950,
    stop_loss_price=1.0940,  # 10 pips risk
    pip_value=0.0001
)
# Returns: lot_size, risk_amount, pips, etc.

# Calculate take profit (1.5:1 reward)
tp = sizer.calculate_take_profit(
    entry_price=1.0950,
    stop_loss_price=1.0940,
    risk_reward_ratio=1.5,
    direction='long'
)

# Trailing stop
trailing = sizer.calculate_trailing_stop(
    entry_price=1.0950,
    current_price=1.1000,
    trailing_pips=10,
    direction='long'
)
```

**Why It Matters:**
- Ensures risk is proportional to account size
- Prevents over-leveraging
- Automatically calculates correct lot sizes
- Enforces minimum and maximum position limits

### 2. Risk Manager (`src/risk/risk_manager.py`)

Tracks and enforces risk limits in real-time.

**Key Features:**

```python
rm = RiskManager(
    account_size=10000,
    max_daily_loss_percent=5.0,        # Stop if lose 5% in a day
    max_drawdown_percent=10.0,         # Stop if 10% drawdown
    max_consecutive_losses=3,          # Stop after 3 losses
    max_open_positions=5               # Max 5 trades at once
)

# Check if trading is allowed
can_trade, reason = rm.can_trade()
if not can_trade:
    print(f"Trading blocked: {reason}")
    # E.g., "Daily loss limit exceeded"

# Record completed trades
rm.record_trade(
    symbol='EURUSD',
    entry_price=1.0950,
    exit_price=1.0960,
    lot_size=0.1,
    pnl=100,  # Profit
    is_winning=True
)

# Get statistics
stats = rm.get_statistics()
print(f"Win Rate: {stats['win_rate']:.1f}%")
print(f"Profit Factor: {stats['profit_factor']:.2f}")
print(f"Expectancy: ${stats['expectancy']:.2f} per trade")
```

**Key Statistics Calculated:**
- **Win Rate**: Percentage of winning trades
- **Profit Factor**: Gross Profit / Gross Loss (should be > 1.5 for viability)
- **Average Win/Loss**: Mean profit of winners vs losers
- **Expectancy**: Expected profit per trade
- **Risk:Reward Ratio**: How much you make vs risk
- **Max Consecutive Wins/Losses**: Streaks in performance

### 3. Drawdown Monitor (`src/risk/drawdown_monitor.py`)

Monitors peak-to-valley decline in account equity.

```python
dm = DrawdownMonitor(
    account_size=10000,
    max_drawdown_percent=15.0  # Stop if 15% drawdown
)

# Update with each trade
is_valid, reason = dm.update_equity(10500)  # After profit

# Or with trade PnL directly
is_valid, reason = dm.update_with_trade(pnl=100)  # Trade profit/loss

# Monitor drawdown
current_dd = dm.get_current_drawdown_percent()      # Current drawdown
max_dd = dm.get_max_drawdown_percent()              # Max ever experienced
recovery = dm.get_recovery_percentage()             # Progress to recovery

# Check if recovering
if dm.is_in_drawdown():
    print(f"In drawdown: {current_dd:.2f}%")
    print(f"Need {recovery_info['recovery_trades_needed']} wins to recover")
```

## Risk Management Rules Explained

### Rule 1: Risk Only a Small Percentage Per Trade

**The Problem:**
- Risking 5% per trade = 4 losses in a row wipes out 20% of your account
- Risking 10% per trade = 3 losses wipes out 30%

**The Solution:**
```python
# Risk only 1-2% per trade
risk_percent = 1.0  # 1% of account
risk_amount = account_size * (risk_percent / 100)
# On $10,000 account = $100 per trade maximum
```

**Why 1-2%?**
- Allows 10+ losses before losing 20% of account
- Gives strategy time to work
- Reduces emotional decision-making
- Sustainable long-term

### Rule 2: Always Use a Stop Loss

**Stop Loss Placement:**
```python
# Based on chart support/resistance, NOT arbitrary
# Example: EUR/USD daily chart
entry_price = 1.0950
nearest_support = 1.0940  # 10 pips
stop_loss = nearest_support - 0.0005  # 5 pips below support

# Calculate position size from stop distance
risk_amount = 100  # Risk $100
stop_distance_pips = (entry_price - stop_loss) / 0.0001  # Convert to pips
lot_size = risk_amount / (stop_distance_pips * 10)  # For EUR/USD
```

**Never:**
- Trade without a stop loss
- Use "mental stops" (doesn't work)
- Place stops < 3 pips (too tight, gets stopped out)
- Place stops > 1000 pips (too loose, risks too much)

### Rule 3: Use Risk-to-Reward Ratios

**Why 1:1.5 Minimum?**

With 50% win rate:
- Avg Win: $150 (1.5 risk units)
- Avg Loss: $100 (1 risk unit)
- Per trade: (150 × 0.5) - (100 × 0.5) = +$25
- On 100 trades: +$2,500 profit

```python
# Entry: 1.0950, Stop: 1.0940 (10 pips)
# Risk: $100, Want 1.5:1 reward

risk_distance = 10 pips
reward_distance = risk_distance * 1.5  # 15 pips
take_profit = 1.0950 + (15 * 0.0001)  # 1.0965
```

### Rule 4: Maximum Daily Loss Limit

**Purpose:** Stop trading after losing money on a bad day

```python
# If account = $10,000
max_daily_loss_percent = 5.0  # Max $500 loss per day

# After $500 loss today, stop trading
# Wait until next day to continue
```

**Why?**
- Bad market conditions exist (news, illiquidity)
- Prevents revenge trading (doubling down after losses)
- Preserves capital for next opportunities

### Rule 5: Maximum Consecutive Losses

**Purpose:** Stop trading after repeated losses

```python
max_consecutive_losses = 3

# After 3 losses in a row:
# 1. Stop trading
# 2. Review what went wrong
# 3. Check if market conditions changed
# 4. Only resume if fix is identified
```

**Why?**
- If strategy loses 3 times, something is wrong
- Market conditions may have changed
- Prevents "fighting the market"
- Time to re-evaluate

### Rule 6: Maximum Drawdown Protection

**Drawdown = Peak-to-Valley Decline**

```python
# Account peaks at $12,000
# Market downturn, account falls to $10,800
# Drawdown = (12,000 - 10,800) / 12,000 = 10%

max_drawdown_percent = 15.0  # Stop if 15% drawdown
```

**Why 15%?**
- High enough to not over-constrain
- Low enough to protect capital
- Allows profitable strategies to work
- Prevents catastrophic losses

## How to Use These Modules

### Step 1: Initialize All Modules

```python
from src.risk.position_sizer import PositionSizer
from src.risk.risk_manager import RiskManager
from src.risk.drawdown_monitor import DrawdownMonitor

# Set up
account_size = 10000

position_sizer = PositionSizer(
    account_size=account_size,
    risk_percent=1.0
)

risk_manager = RiskManager(
    account_size=account_size,
    max_daily_loss_percent=5.0,
    max_consecutive_losses=3
)

drawdown_monitor = DrawdownMonitor(
    account_size=account_size,
    max_drawdown_percent=15.0
)
```

### Step 2: Before Opening a Trade

```python
# 1. Check if trading is allowed
can_trade, reason = risk_manager.can_trade()
if not can_trade:
    print(f"Cannot trade: {reason}")
    exit()

# 2. Calculate position size
position = position_sizer.calculate_position_size(
    entry_price=1.0950,
    stop_loss_price=1.0940,
    pip_value=0.0001
)

if not position['valid']:
    print(f"Position invalid")
    exit()

lot_size = position['lot_size']

# 3. Calculate take profit
take_profit = position_sizer.calculate_take_profit(
    entry_price=1.0950,
    stop_loss_price=1.0940,
    risk_reward_ratio=1.5,
    direction='long'
)

# 4. Validate before executing
is_valid, reason = position_sizer.validate_position(
    lot_size=lot_size,
    entry_price=1.0950,
    stop_loss_price=1.0940,
    take_profit_price=take_profit,
    account_balance=risk_manager.current_balance
)

if is_valid:
    # Open trade with broker API
    broker.open_trade(
        symbol='EURUSD',
        direction='buy',
        lot_size=lot_size,
        entry=1.0950,
        stop_loss=1.0940,
        take_profit=take_profit
    )
```

### Step 3: After Trade Closes

```python
# Record the trade
risk_manager.record_trade(
    symbol='EURUSD',
    entry_price=1.0950,
    exit_price=1.0960,
    lot_size=0.1,
    pnl=100,  # Profit
    is_winning=True
)

# Update drawdown monitor
new_balance = risk_manager.current_balance
is_valid, reason = drawdown_monitor.update_equity(new_balance)

if not is_valid:
    print(f"Drawdown limit exceeded: {reason}")
    # Stop all trading
```

### Step 4: Monitor Statistics

```python
# Get stats regularly
stats = risk_manager.get_statistics()

print(f"Total Trades: {stats['total_trades']}")
print(f"Win Rate: {stats['win_rate']:.1f}%")
print(f"Profit Factor: {stats['profit_factor']:.2f}")
print(f"Expectancy: ${stats['expectancy']:.2f} per trade")
print(f"Current Balance: ${stats['current_balance']:.2f}")
print(f"Drawdown: {stats['current_drawdown_percent']:.2f}%")
```

## Testing

All three modules have comprehensive test coverage:

```bash
# Run all risk management tests
pytest tests/test_position_sizer.py -v
pytest tests/test_risk_manager.py -v
pytest tests/test_drawdown_monitor.py -v

# Or all at once
pytest tests/ -k "risk" -v
```

**Test Coverage:**
- 13 tests for position sizer
- 15 tests for risk manager
- 14 tests for drawdown monitor
- **Total: 42 tests**

## Common Mistakes to Avoid

### ❌ Mistake 1: Ignoring Stop Losses
```python
# BAD: No stop loss
broker.open_trade(symbol='EURUSD', direction='buy', lot_size=1.0)

# GOOD: Always have stop loss
broker.open_trade(
    symbol='EURUSD',
    direction='buy',
    lot_size=0.1,
    stop_loss=1.0940,
    take_profit=1.0965
)
```

### ❌ Mistake 2: Risking Too Much Per Trade
```python
# BAD: Risking 10% per trade
risk_manager = RiskManager(
    account_size=10000,
    max_daily_loss_percent=50.0  # Too high!
)

# GOOD: Risk 1-2% maximum
risk_manager = RiskManager(
    account_size=10000,
    max_daily_loss_percent=5.0  # 5% = 1% avg per trade
)
```

### ❌ Mistake 3: Moving Stop Losses Against You
```python
# BAD: Loosening stop loss after loss
# Trade EUR/USD, enter at 1.0950, stop at 1.0940
# Price moves to 1.0935, losing $100
# Move stop to 1.0930 to "give it more room" ❌

# GOOD: Keep stop loss fixed
# Let the trade play out
# If it hits stop, accept the loss
```

### ❌ Mistake 4: Not Using Risk-to-Reward Ratios
```python
# BAD: No take profit target
broker.open_trade(symbol='EURUSD', direction='buy')
# Just hope price goes up

# GOOD: Define take profit based on risk:reward
position_sizer.calculate_take_profit(
    entry_price=1.0950,
    stop_loss_price=1.0940,
    risk_reward_ratio=1.5,
    direction='long'
)
# Exit at 1.0965 for 15 pips profit (1.5x 10 pip risk)
```

### ❌ Mistake 5: Revenge Trading After Losses
```python
# BAD: After 3 losses, double lot size to "make it back"
rm.record_trade(..., pnl=-50, is_winning=False)
rm.record_trade(..., pnl=-50, is_winning=False)
rm.record_trade(..., pnl=-50, is_winning=False)
# Now opening with 2x lot size ❌

# GOOD: Stop trading after max consecutive losses
if rm.consecutive_losses >= rm.max_consecutive_losses:
    # Stop trading
    # Review what went wrong
    # Don't resume until fix found
```

## Key Metrics to Track

### 1. Win Rate
- **What:** % of trades that make money
- **Target:** 50%+ (even 40% is OK with good risk:reward)
- **Reality:** Most traders have 40-60%

### 2. Profit Factor
- **What:** Total Wins / Total Losses
- **Target:** 1.5+ (earning $1.50 per $1 risked)
- **Reality:** 1.3-2.0 is good for most systems

### 3. Expectancy
- **What:** Average profit per trade
- **Target:** Positive (makes money over time)
- **Formula:** (Win Rate × Avg Win) - (Loss Rate × Avg Loss)

### 4. Risk-to-Reward Ratio
- **What:** Average profit / Average loss
- **Target:** 1.5+ or higher
- **Protects against:** Low win rates

### 5. Maximum Drawdown
- **What:** Peak-to-valley decline
- **Target:** < 20% for any system
- **Reality:** Even good systems can have 15-20% drawdowns

## What's Next

Phase 3 completes the **risk management foundation**. Now you have:

✅ Position sizing (correct trade size)
✅ Risk limits (daily, drawdown, consecutive losses)
✅ Drawdown monitoring (capital protection)
✅ Trade statistics (measure performance)

**Next Phase (Phase 4):** Market Analysis & Signals
- Read price action
- Identify support/resistance
- Calculate technical indicators
- Generate trading signals

## Summary

**Remember:** The goal is NOT to make money on every trade. The goal is to:
1. Manage risk ruthlessly
2. Win more than you lose
3. Make bigger profits on wins than losses
4. Repeat 100+ times
5. Watch small gains compound into large returns

Phase 3 provides all the tools to enforce this discipline.
