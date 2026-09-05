# Quick Start Guide - Phase 2: Market Analysis

## Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/nguregitonga/forex-trading-bot.git
cd forex-trading-bot
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
python -c "from src.market.data_fetcher import DataFetcher; print('✅ Installation successful')"
```

---

## Tutorial 1: Download Market Data

### Basic Data Download
```python
from src.market.data_fetcher import DataFetcher
import pandas as pd

# Initialize fetcher
fetcher = DataFetcher()

# Download 6 months of hourly EURUSD data
data = fetcher.fetch_forex_data(
    symbol='EURUSD',
    interval='1h',      # 1m, 5m, 15m, 1h, 4h, 1d
    period='6mo'        # 1d, 5d, 1mo, 3mo, 6mo, 1y, 5y
)

print(f"Downloaded {len(data)} candles")
print(data.head())
print(data.tail())
```

### Validate & Save Data
```python
# Check data quality
is_valid, message = fetcher.validate_data(data)
print(f"Valid: {is_valid} - {message}")

# Save to CSV
fetcher.save_data(data, 'EURUSD', '1h')
print("Data saved to data/raw/EURUSD_1h.csv")

# Load later
data = fetcher.load_data('EURUSD', '1h')
```

### Download Multiple Pairs
```python
symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'NZDUSD']
all_data = fetcher.fetch_multiple_symbols(
    symbols=symbols,
    interval='1h',
    period='3mo'
)

for symbol, data in all_data.items():
    print(f"{symbol}: {len(data)} candles")
    fetcher.save_data(data, symbol, '1h')
```

---

## Tutorial 2: Calculate Technical Indicators

### Add All Indicators
```python
from src.market.indicators import TechnicalIndicators

# Add all indicators automatically
data = TechnicalIndicators.add_all_indicators(data)

# Check what was added
print(data.columns)
```

### Individual Indicators
```python
# Moving Average
data['MA9'] = TechnicalIndicators.moving_average(data['Close'], 9)
data['MA21'] = TechnicalIndicators.moving_average(data['Close'], 21)
data['MA50'] = TechnicalIndicators.moving_average(data['Close'], 50)

# RSI
data['RSI'] = TechnicalIndicators.rsi(data['Close'], period=14)

# MACD
data['MACD'], data['Signal'], data['Histogram'] = TechnicalIndicators.macd(
    data['Close'],
    fast=12,
    slow=26,
    signal=9
)

# Bollinger Bands
data['BB_Upper'], data['BB_Middle'], data['BB_Lower'] = TechnicalIndicators.bollinger_bands(
    data['Close'],
    period=20,
    std_dev=2.0
)

# ATR
data['ATR'] = TechnicalIndicators.atr(
    data['High'],
    data['Low'],
    data['Close'],
    period=14
)

# Stochastic
data['Stoch_K'], data['Stoch_D'] = TechnicalIndicators.stochastic(
    data['High'],
    data['Low'],
    data['Close'],
    period=14
)
```

### Get Current Values
```python
summary = TechnicalIndicators.get_indicator_summary(data)

print("Current Indicator Values:")
for indicator, value in summary.items():
    if value is not None:
        if isinstance(value, float):
            print(f"  {indicator}: {value:.4f}")
        else:
            print(f"  {indicator}: {value}")
```

### View Recent Candles
```python
# Last 5 candles with indicators
print(data[['Close', 'MA9', 'MA21', 'RSI', 'MACD']].tail())
```

---

## Tutorial 3: Analyze Market & Generate Signals

### Simple Market Analysis
```python
from src.market.market_analyzer import MarketAnalyzer

# Initialize analyzer
analyzer = MarketAnalyzer(min_confirmation_signals=2)

# Get complete market summary
summary = analyzer.get_market_summary(data)

# Print summary
print("\n" + "="*60)
print("MARKET ANALYSIS")
print("="*60)
print(f"Time: {summary['timestamp']}")
print(f"Price: {summary['close_price']:.5f}")
print(f"Trend: {summary['trend']}")
print(f"Market Condition: {summary['condition']}")
print(f"\nRSI: {summary['rsi']['value']:.2f} ({summary['rsi']['condition']})")
print(f"MACD: {summary['macd']['signal']}")
print(f"\nSupport: {summary['support_resistance'][0]:.5f}")
print(f"Resistance: {summary['support_resistance'][1]:.5f}")
print(f"\nDivergence: {summary['divergence']}")
print(f"\nSignal: {summary['signals']['signal']}")
print(f"Confidence: {summary['signals']['confidence']:.0%}")
print(f"Reasons:")
for reason in summary['signals']['reasons']:
    print(f"  - {reason}")
print("="*60)
```

### Individual Analyses
```python
# Trend Analysis
trend = analyzer.analyze_trend(data)
print(f"Trend: {trend.name}")  # UPTREND, DOWNTREND, NEUTRAL, etc.

# RSI Analysis
rsi_analysis = analyzer.analyze_rsi(data)
print(f"RSI: {rsi_analysis['value']:.2f}")
print(f"Condition: {rsi_analysis['condition']}")  # overbought, oversold, neutral

# MACD Analysis
macd_analysis = analyzer.analyze_macd(data)
print(f"MACD Signal: {macd_analysis['signal']}")  # bullish, bearish, neutral
print(f"Momentum: {macd_analysis['momentum']:.6f}")

# Bollinger Bands Analysis
bb_analysis = analyzer.analyze_bollinger_bands(data)
print(f"BB Position: {bb_analysis['position']:.2f}")  # 0=at lower, 1=at upper
print(f"BB Condition: {bb_analysis['condition']}")  # at_upper_band, at_lower_band, in_range

# Support/Resistance
support, resistance = analyzer.detect_support_resistance(data, lookback=20)
print(f"Support: {support:.5f}")
print(f"Resistance: {resistance:.5f}")

# Divergence
divergence = analyzer.detect_divergence(data)
print(f"Divergence: {divergence}")  # bullish_divergence, bearish_divergence, none

# Trading Signals
signals = analyzer.generate_signals(data)
print(f"Signal: {signals['signal']}")  # BUY, SELL, HOLD, NONE
print(f"Confidence: {signals['confidence']:.0%}")
print(f"Confirmation Count: {signals['confirmation_count']}")
print(f"Reasons:")
for reason in signals['reasons']:
    print(f"  - {reason}")
```

---

## Tutorial 4: Working with Different Timeframes

### Download Multiple Timeframes
```python
timeframes = ['1h', '4h', '1d']
all_data = {}

for tf in timeframes:
    data = fetcher.fetch_forex_data('EURUSD', interval=tf, period='1y')
    data = TechnicalIndicators.add_all_indicators(data)
    all_data[tf] = data
    print(f"{tf}: {len(data)} candles")
```

### Compare Signals Across Timeframes
```python
analyzer = MarketAnalyzer()

print("\nSignals Across Timeframes:\n")
for tf, data in all_data.items():
    signals = analyzer.generate_signals(data)
    confidence = signals['confidence']
    print(f"{tf:3s} - Signal: {signals['signal']:5s} | Confidence: {confidence:.0%}")
```

### Resample Data
```python
# Resample 1-hour data to 4-hour
data_1h = all_data['1h']
data_4h = fetcher.resample_data(data_1h, '4h')

print(f"Original 1h data: {len(data_1h)} candles")
print(f"Resampled to 4h: {len(data_4h)} candles")

# Recalculate indicators on resampled data
data_4h = TechnicalIndicators.add_all_indicators(data_4h)
```

---

## Tutorial 5: Analyzing Multiple Pairs

### Quick Dashboard
```python
symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD']
analyzer = MarketAnalyzer()

print("\n" + "="*80)
print("FOREX MARKET DASHBOARD")
print("="*80)
print(f"{'Pair':<10} {'Trend':<15} {'Signal':<8} {'Confidence':<15} {'Support':<10} {'Resistance':<10}")
print("-"*80)

for symbol in symbols:
    data = fetcher.fetch_forex_data(symbol, interval='1h', period='1mo')
    if data.empty:
        continue
    
    data = TechnicalIndicators.add_all_indicators(data)
    summary = analyzer.get_market_summary(data)
    support, resistance = summary['support_resistance']
    signal = summary['signals']['signal']
    confidence = summary['signals']['confidence']
    trend = summary['trend']
    price = summary['close_price']
    
    print(f"{symbol:<10} {trend:<15} {signal:<8} {confidence:>6.0%}          {support:>9.5f} {resistance:>9.5f}")

print("="*80)
```

---

## Tutorial 6: Testing Your Setup

### Run Unit Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_indicators.py -v
pytest tests/test_data_fetcher.py -v
pytest tests/test_market_analyzer.py -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
```

### Quick Verification
```python
# Test data fetcher
from src.market.data_fetcher import DataFetcher
fetcher = DataFetcher()
data = fetcher.fetch_forex_data('EURUSD', interval='1d', period='1mo')
print(f"✅ Fetcher: Downloaded {len(data)} candles")

# Test indicators
from src.market.indicators import TechnicalIndicators
data = TechnicalIndicators.add_all_indicators(data)
print(f"✅ Indicators: Added {len(data.columns)} columns")

# Test analyzer
from src.market.market_analyzer import MarketAnalyzer
analyzer = MarketAnalyzer()
summary = analyzer.get_market_summary(data)
print(f"✅ Analyzer: Generated signal '{summary['signals']['signal']}'")

print("\n✅ All Phase 2 modules working correctly!")
```

---

## Common Patterns

### Pattern 1: Daily Analysis
```python
def daily_analysis(symbols):
    """Analyze all symbols every day"""
    fetcher = DataFetcher()
    analyzer = MarketAnalyzer()
    
    for symbol in symbols:
        data = fetcher.fetch_forex_data(symbol, interval='1h', period='1mo')
        data = TechnicalIndicators.add_all_indicators(data)
        summary = analyzer.get_market_summary(data)
        
        if summary['signals']['signal'] == 'BUY':
            print(f"🟢 {symbol}: BUY signal with {summary['signals']['confidence']:.0%} confidence")
        elif summary['signals']['signal'] == 'SELL':
            print(f"🔴 {symbol}: SELL signal with {summary['signals']['confidence']:.0%} confidence")

daily_analysis(['EURUSD', 'GBPUSD', 'USDJPY'])
```

### Pattern 2: Entry Point Validation
```python
def validate_entry(symbol, entry_price):
    """Check if entry is valid for a symbol"""
    fetcher = DataFetcher()
    analyzer = MarketAnalyzer()
    
    data = fetcher.fetch_forex_data(symbol, interval='1h', period='1mo')
    data = TechnicalIndicators.add_all_indicators(data)
    summary = analyzer.get_market_summary(data)
    
    # Entry valid if trend supports the signal
    signal = summary['signals']['signal']
    trend = summary['trend']
    confidence = summary['signals']['confidence']
    
    if signal == 'BUY' and 'UP' in trend and confidence > 0.70:
        return True, f"Strong buy signal in {trend}"
    elif signal == 'SELL' and 'DOWN' in trend and confidence > 0.70:
        return True, f"Strong sell signal in {trend}"
    else:
        return False, f"Signal {signal} doesn't align with {trend}"

valid, reason = validate_entry('EURUSD', 1.0950)
print(f"Entry valid: {valid} - {reason}")
```

### Pattern 3: Multi-Timeframe Confirmation
```python
def get_mtf_signal(symbol):
    """Get signal across multiple timeframes"""
    fetcher = DataFetcher()
    analyzer = MarketAnalyzer()
    
    signals = {}
    
    for tf in ['1h', '4h', '1d']:
        data = fetcher.fetch_forex_data(symbol, interval=tf, period='3mo')
        data = TechnicalIndicators.add_all_indicators(data)
        summary = analyzer.get_market_summary(data)
        signals[tf] = summary['signals']['signal']
    
    # Count signals
    buy_count = sum(1 for s in signals.values() if s == 'BUY')
    sell_count = sum(1 for s in signals.values() if s == 'SELL')
    
    if buy_count == 3:
        return 'STRONG_BUY'
    elif buy_count == 2:
        return 'BUY'
    elif sell_count == 3:
        return 'STRONG_SELL'
    elif sell_count == 2:
        return 'SELL'
    else:
        return 'HOLD'

signal = get_mtf_signal('EURUSD')
print(f"Multi-Timeframe Signal: {signal}")
```

---

## Troubleshooting

### No data downloaded
```python
# Check internet connection
# Try with longer period
data = fetcher.fetch_forex_data('EURUSD', interval='1d', period='1y')

# Or check with different symbol
data = fetcher.fetch_forex_data('GBPUSD=X', interval='1d', period='1mo')
```

### Indicators show NaN
```python
# Normal - indicators need warm-up period
data = data.dropna()  # Remove NaN rows

# Or check data length
print(f"Total rows: {len(data)}")
print(f"Valid rows: {len(data.dropna())}")
```

### Tests failing
```bash
# Check dependencies
pip install --upgrade -r requirements.txt

# Run tests with more detail
pytest tests/ -vv -s
```

---

## Next Steps

1. ✅ **Phase 2 Complete**: Market analysis working
2. 📌 **Phase 3 Next**: Risk management (position sizing, drawdown protection)
3. 📌 **Phase 4**: Trading strategy implementation
4. 📌 **Phase 5**: Backtesting engine
5. 📌 **Phase 6**: Live trading automation

---

## Resources

- **Repository**: https://github.com/nguregitonga/forex-trading-bot
- **Development Guide**: See DEVELOPMENT_GUIDE.md
- **Phase 2 Completion**: See PHASE_2_COMPLETION.md
- **Technical Analysis**: https://www.investopedia.com/terms/t/technicalanalysis.asp

---

**Happy Trading! 🚀**
