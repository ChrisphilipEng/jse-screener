# JSE Equity Screener

A professional-grade listed equity screening tool for the Johannesburg Stock Exchange (JSE), built with Python and Streamlit.

## Features

- **Full JSE Universe**: ~130+ pre-loaded JSE tickers covering all major sectors
- **Live Data**: Pulls real-time price and fundamental data from Yahoo Finance
- **7 Strategy Presets**: Deep Value, High Dividend Income, Momentum Leaders, Quality Compounders, Oversold Bounce, Small Cap Growth, Low Volatility
- **40+ Screening Metrics**: Valuation (P/E, P/B, EV/EBITDA), Momentum (RSI, price changes, moving averages), Income (dividend yield, payout ratio), Quality (ROE, ROA, margins, D/E), Growth (earnings/revenue growth)
- **Interactive Charts**: Sector distribution, valuation scatter, performance heatmaps, candlestick charts with overlays
- **Stock Comparison**: Side-by-side comparison with normalized price charts and radar plots
- **Composite Scoring**: Build custom weighted scores to rank stocks
- **Export**: CSV and Excel export of all screener results
- **Custom Universes**: Upload your own ticker list via CSV

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`.

## Usage

1. **Select Universe**: Choose Full JSE, Top 40, or upload a custom CSV
2. **Filter Sectors**: Pick the sectors you want to screen
3. **Choose Strategy**: Use a preset (e.g., Deep Value, Momentum Leaders) or set manual filters
4. **Fetch Data**: Click the "Fetch / Refresh Data" button to pull live data
5. **Explore**: Use the tabs to view results, charts, comparisons, and export

## Custom CSV Format

To use a custom universe, upload a CSV with these columns:

| Column   | Required | Example     |
|----------|----------|-------------|
| Symbol   | Yes      | SBK.JO     |
| Company  | No       | Standard Bank |
| Sector   | No       | Financials  |

Symbols must use the Yahoo Finance `.JO` suffix for JSE shares.

## Project Structure

```
jse-screener/
├── app.py              # Main Streamlit application
├── jse_universe.py     # JSE ticker list and universe management
├── data_fetcher.py     # Yahoo Finance data fetching + caching
├── screener_engine.py  # Filtering, strategies, composite scoring
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Strategy Presets

| Strategy | Description |
|----------|-------------|
| Deep Value | Low P/E, low P/B, dividend paying, low leverage |
| High Dividend Income | 4%+ yield, sustainable payout, large cap |
| Momentum Leaders | Positive price momentum across timeframes, RSI 50-80 |
| Quality Compounders | High ROE, good margins, low debt, growing revenue |
| Oversold Bounce | RSI < 35, >25% off 52-week high, mid/large cap |
| Small Cap Growth | R0.5-20B market cap, strong growth, reasonable P/E |
| Low Volatility | Low beta, low volatility, dividend paying, large cap |

## Notes

- Yahoo Finance data may have delays or gaps for some JSE tickers
- The 15-minute cache helps avoid rate limiting; disable it for real-time data
- For production use, consider a paid data provider (Bloomberg, Refinitiv, IRESS)
- The screener is for informational purposes only — not investment advice

## License

Internal use only. Proprietary and confidential.
