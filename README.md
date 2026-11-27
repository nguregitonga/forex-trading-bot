# forex-trading-bot

A disciplined, risk-managed Forex trading bot with market analysis and risk management, built in phases toward backtesting and automated trading.

> **Status:** Phases 1–3 done (data, market analysis, risk management). No strategy, backtester or broker execution yet. The bot does not place trades. `config/settings.yaml` defaults to paper mode with trading disabled.

## Features

- **Market data** (`src/market/data_fetcher.py`): downloads Forex OHLCV from Yahoo Finance (EURUSD, GBPUSD, USDJPY…), validates it, resamples timeframes (1h → 4h) and saves/loads CSV.
- **Technical indicators** (`src/market/indicators.py`): moving averages, RSI, MACD, Bollinger Bands, ATR and Stochastic.
- **Market analysis** (`src/market/market_analyzer.py`): trend direction (MA order plus slope), RSI and MACD conditions, support/resistance, and confirmed entry signals.
- **Risk management** (`src/risk/`):
  - position sizing by % risk, with take-profit, trailing and break-even stops
  - daily loss, drawdown and consecutive-loss limits
  - win rate, profit factor and expectancy

## Setup

```bash
git clone https://github.com/nguregitonga/forex-trading-bot.git
cd forex-trading-bot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Quick example

```python
from src.market.data_fetcher import DataFetcher
from src.market.indicators import TechnicalIndicators
from src.market.market_analyzer import MarketAnalyzer
from src.risk.position_sizer import PositionSizer

data = DataFetcher().fetch_forex_data("EURUSD", interval="1h", period="3mo")
data = TechnicalIndicators.add_all_indicators(data)
print(MarketAnalyzer().get_market_summary(data))

sizer = PositionSizer(account_size=10000, risk_percent=1.0)
print(sizer.calculate_position_size(entry_price=1.0850, stop_loss_price=1.0830))
```

## Tests

```bash
pytest
```

Data-download tests pass offline, because a failed download returns an empty DataFrame. Logs go to `logs/forex_bot.log`. Set `FOREX_BOT_LOG_LEVEL=DEBUG` for more detail.

## Project structure

```
config/settings.yaml      trading, risk, strategy and backtest settings
src/logger.py             shared logging (console + rotating file)
src/market/               data fetching, indicators, market analysis
src/risk/                 position sizing, risk limits, drawdown monitor
tests/                    unit tests
```

Detailed guides: [Phase 2 quick start](QUICK_START_PHASE_2.md), [Phase 2 completion](PHASE_2_COMPLETION.md), [Phase 3 risk management](PHASE_3_RISK_MANAGEMENT.md), [Phase 3 checklist](PHASE_3_CHECKLIST.md).

## Roadmap

- [x] Phase 1–2: data and market analysis
- [x] Phase 3: risk management
- [ ] Phase 4: strategy and backtesting engine (with trading costs from `settings.yaml`)
- [ ] Phase 5: paper trading against a demo broker account
- [ ] Phase 6: notifications (Telegram/email)

## Disclaimer

This project is for education and research only. It is not financial advice. Forex trading carries a high risk of loss. Test only on paper or demo accounts.

## License

MIT. See [LICENSE](LICENSE).
