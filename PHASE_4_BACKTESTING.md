# Phase 4: Strategy & Backtesting

Phase 4 turns the market analysis (Phase 2) and risk rules (Phase 3) into a strategy, and tests that strategy on historical data.

## Run a backtest

```bash
python run_backtest.py                                  # EURUSD, 1h candles, last 12 months
python run_backtest.py --symbol GBPUSD --interval 4h --period 2y
python run_backtest.py --symbol all --interval 1d --period 5y   # every pair in settings.yaml
python run_backtest.py --csv data/raw/EURUSD_1h.csv --symbol EURUSD
```

Yahoo Finance only keeps about the last 730 days of 1h/4h data. Use `--interval 1d` for longer history. Each run writes `results/<PAIR>_<interval>_trades.csv` (every trade, with entry/exit, pips, P&L, R-multiple, costs and the signal reasons) and `results/<PAIR>_<interval>_equity.csv`.

## The strategy (`src/strategy/confirmation_strategy.py`)

| Step | Rule |
|---|---|
| Entry | `MarketAnalyzer.generate_signals()` gives BUY or SELL with at least `entry_confirmation_count` agreeing signals (trend, RSI, MACD, divergence) |
| Trend filter | No buys while the trend is down, no sells while it is up |
| Stop loss | 1.5 × ATR from the signal bar's close (`--atr-multiplier`) |
| Take profit | `min_risk_reward_ratio` × the stop distance (1.5R by default) |
| Size | `risk_per_trade_percent` of the current balance at risk (1%) |

To try your own idea, subclass `Strategy` and implement `generate_signal(history)`. The backtester runs any strategy.

## How the backtester avoids fooling you (`src/backtest/engine.py`)

- **No look-ahead.** A signal from bar *i*'s close is filled at bar *i+1*'s **open**. The strategy only ever sees data up to the current bar, and a test checks this.
- **Pessimistic fills.** If one candle touches both the stop and the target, the stop counts. A gap through the stop fills at the (worse) open price.
- **Trading costs** from `settings.yaml`: half the spread on every fill, slippage on entries and stop exits, and commission on entry and exit (as a fraction of the position's USD value).
- **Risk limits use historical dates:**
  - the daily loss limit blocks the rest of that day
  - the losing-streak limit pauses trading until the next day
  - breaching `max_drawdown_percent` stops all trading for the rest of the test
- **Correct pip values per pair.** EURUSD is $10/pip per lot. USDJPY is about $6.67 at 150. Cross pairs such as EURGBP are approximated, with a warning.

## Reading the report

- **Expectancy / trade** is the average profit per trade, also shown in R (multiples of the amount risked). It must be positive before anything else matters.
- **Profit factor** is gross profit ÷ gross loss. Below 1.0 loses money.
- **Max drawdown** is the worst peak-to-trough fall of the equity curve.
- **PASS/FAIL** lines compare the result with the `performance:` thresholds in `settings.yaml`.

## Cost settings: check these

The default `commission: 0.0005` means 0.05% of position value **each side**, about $54 per standard lot per side on EURUSD. Typical ECN accounts charge $3–4 per lot per side, about 0.0035%. With $100 risked per trade, the default costs alone take around 0.4R per trade. Set the values to match your broker's real spread and commission before judging a strategy.

## Tests

`tests/test_backtest.py` checks the engine with hand-built candles:
- fills, stops, targets, gaps, shorts and end-of-data exits
- costs, the no-look-ahead rule, and the daily-loss, losing-streak and drawdown limits
- pip maths, metrics and the strategy's signal levels

```bash
pytest tests/test_backtest.py -v
```

## Next: Phase 5

Paper trading means running the strategy live against a demo broker account (e.g. OANDA practice) with no real money, and comparing live fills with the backtest.
