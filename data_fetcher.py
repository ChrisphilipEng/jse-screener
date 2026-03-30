"""
Data Fetcher Module
-------------------
Pulls live and cached data from Yahoo Finance for JSE-listed equities.
Handles:
  - Batch downloading of price/fundamental data
  - Caching to avoid hitting rate limits
  - Derived metric calculations (RSI, moving averages, etc.)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 900  # 15-minute cache


def _cache_key(tickers: list[str]) -> str:
    """Generate a cache key from ticker list."""
    key = hashlib.md5("_".join(sorted(tickers)).encode()).hexdigest()
    return key


def _is_cache_valid(cache_file: Path) -> bool:
    """Check if cache file exists and is fresh."""
    if not cache_file.exists():
        return False
    mtime = cache_file.stat().st_mtime
    return (time.time() - mtime) < CACHE_TTL_SECONDS


def fetch_single_ticker(symbol: str) -> dict | None:
    """Fetch data for a single ticker. Returns dict or None on failure."""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        if not info or info.get("regularMarketPrice") is None:
            return None

        # Get historical data for technical calculations
        hist = stock.history(period="1y")

        if hist.empty or len(hist) < 20:
            return None

        close = hist["Close"]
        volume = hist["Volume"]

        # ── PRICE & MARKET DATA ──
        current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        market_cap = info.get("marketCap")

        # ── VALUATION METRICS ──
        pe_trailing = info.get("trailingPE")
        pe_forward = info.get("forwardPE")
        pb_ratio = info.get("priceToBook")
        ps_ratio = info.get("priceToSalesTrailing12Months")
        ev_ebitda = info.get("enterpriseToEbitda")
        ev_revenue = info.get("enterpriseToRevenue")
        peg_ratio = info.get("pegRatio")

        # ── DIVIDEND / INCOME ──
        div_yield = info.get("dividendYield")
        if div_yield is not None and div_yield != 0:
            div_yield = div_yield * 100  # Convert to percentage
        div_rate = info.get("dividendRate")
        payout_ratio = info.get("payoutRatio")
        if payout_ratio is not None and payout_ratio != 0:
            payout_ratio = payout_ratio * 100

        # ── PROFITABILITY / QUALITY ──
        roe = info.get("returnOnEquity")
        if roe and abs(roe) < 1:  # Likely a decimal
            roe = roe * 100
        roa = info.get("returnOnAssets")
        if roa and abs(roa) < 1:
            roa = roa * 100
        profit_margin = info.get("profitMargins")
        if profit_margin and abs(profit_margin) < 1:
            profit_margin = profit_margin * 100
        operating_margin = info.get("operatingMargins")
        if operating_margin and abs(operating_margin) < 1:
            operating_margin = operating_margin * 100
        debt_to_equity = info.get("debtToEquity")
        current_ratio = info.get("currentRatio")
        quick_ratio = info.get("quickRatio")
        gross_margins = info.get("grossMargins")
        if gross_margins and abs(gross_margins) < 1:
            gross_margins = gross_margins * 100

        # ── EARNINGS / GROWTH ──
        earnings_growth = info.get("earningsGrowth")
        if earnings_growth and abs(earnings_growth) < 1:
            earnings_growth = earnings_growth * 100
        revenue_growth = info.get("revenueGrowth")
        if revenue_growth and abs(revenue_growth) < 1:
            revenue_growth = revenue_growth * 100
        eps_trailing = info.get("trailingEps")
        eps_forward = info.get("forwardEps")

        # ── TECHNICAL / MOMENTUM ──
        # Moving averages
        sma_20 = float(close.tail(20).mean()) if len(close) >= 20 else None
        sma_50 = float(close.tail(50).mean()) if len(close) >= 50 else None
        sma_200 = float(close.tail(200).mean()) if len(close) >= 200 else None

        # Price changes
        price_1d = _pct_change(close, 1)
        price_5d = _pct_change(close, 5)
        price_1m = _pct_change(close, 21)
        price_3m = _pct_change(close, 63)
        price_6m = _pct_change(close, 126)
        price_1y = _pct_change(close, 252)

        # RSI (14-day)
        rsi_14 = _calculate_rsi(close, 14)

        # Average volume
        avg_vol_20 = float(volume.tail(20).mean()) if len(volume) >= 20 else None

        # 52-week high/low
        high_52w = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
        low_52w = float(close.tail(252).min()) if len(close) >= 252 else float(close.min())
        pct_from_52w_high = ((current_price - high_52w) / high_52w * 100) if high_52w and current_price else None

        # Volatility (annualized)
        daily_returns = close.pct_change().dropna()
        volatility = float(daily_returns.std() * np.sqrt(252) * 100) if len(daily_returns) > 20 else None

        # Beta
        beta = info.get("beta")

        # ── ANALYST RECOMMENDATIONS & TARGET PRICE ──
        analyst_rec = info.get("recommendationKey")  # e.g. "buy", "hold", "sell"
        analyst_rec_label = _format_recommendation(analyst_rec)
        analyst_mean_score = info.get("recommendationMean")  # 1=Strong Buy, 5=Sell
        num_analysts = info.get("numberOfAnalystOpinions")
        target_high = info.get("targetHighPrice")
        target_low = info.get("targetLowPrice")
        target_mean = info.get("targetMeanPrice")
        target_median = info.get("targetMedianPrice")

        # Upside/downside from current price to mean target
        upside_pct = None
        if target_mean and current_price and current_price > 0:
            upside_pct = round((target_mean - current_price) / current_price * 100, 2)

        return {
            "Symbol": symbol,
            "Price": current_price,
            "Prev_Close": prev_close,
            "Market_Cap": market_cap,
            "Market_Cap_Bn": round(market_cap / 1e9, 2) if market_cap and market_cap > 0 else None,
            # Valuation
            "PE_Trailing": pe_trailing,
            "PE_Forward": pe_forward,
            "PB_Ratio": pb_ratio,
            "PS_Ratio": ps_ratio,
            "EV_EBITDA": ev_ebitda,
            "EV_Revenue": ev_revenue,
            "PEG_Ratio": peg_ratio,
            # Income
            "Div_Yield_Pct": div_yield,
            "Div_Rate": div_rate,
            "Payout_Ratio_Pct": payout_ratio,
            # Quality
            "ROE_Pct": roe,
            "ROA_Pct": roa,
            "Profit_Margin_Pct": profit_margin,
            "Operating_Margin_Pct": operating_margin,
            "Gross_Margin_Pct": gross_margins,
            "Debt_to_Equity": debt_to_equity,
            "Current_Ratio": current_ratio,
            "Quick_Ratio": quick_ratio,
            # Growth
            "Earnings_Growth_Pct": earnings_growth,
            "Revenue_Growth_Pct": revenue_growth,
            "EPS_Trailing": eps_trailing,
            "EPS_Forward": eps_forward,
            # Momentum / Technical
            "SMA_20": sma_20,
            "SMA_50": sma_50,
            "SMA_200": sma_200,
            "RSI_14": rsi_14,
            "Price_1D_Pct": price_1d,
            "Price_5D_Pct": price_5d,
            "Price_1M_Pct": price_1m,
            "Price_3M_Pct": price_3m,
            "Price_6M_Pct": price_6m,
            "Price_1Y_Pct": price_1y,
            "Avg_Vol_20D": avg_vol_20,
            "High_52W": high_52w,
            "Low_52W": low_52w,
            "Pct_From_52W_High": pct_from_52w_high,
            "Volatility_Ann_Pct": volatility,
            "Beta": beta,
            # Analyst data
            "Analyst_Rec": analyst_rec_label,
            "Analyst_Score": analyst_mean_score,
            "Num_Analysts": num_analysts,
            "Target_High": target_high,
            "Target_Low": target_low,
            "Target_Mean": target_mean,
            "Target_Median": target_median,
            "Upside_Pct": upside_pct,
        }

    except Exception as e:
        logger.warning(f"Failed to fetch {symbol}: {e}")
        return None


def _format_recommendation(rec_key: str | None) -> str | None:
    """Convert yfinance recommendation key to display label."""
    if not rec_key:
        return None
    mapping = {
        "strongBuy": "Strong Buy",
        "strong_buy": "Strong Buy",
        "buy": "Buy",
        "overweight": "Overweight",
        "hold": "Hold",
        "neutral": "Hold",
        "underweight": "Underweight",
        "sell": "Sell",
        "strongSell": "Strong Sell",
        "strong_sell": "Strong Sell",
    }
    return mapping.get(rec_key, rec_key.replace("_", " ").title())


def _pct_change(series: pd.Series, periods: int) -> float | None:
    """Calculate percentage change over N periods."""
    if len(series) < periods + 1:
        return None
    current = float(series.iloc[-1])
    past = float(series.iloc[-(periods + 1)])
    if past == 0:
        return None
    return round((current - past) / past * 100, 2)


def _calculate_rsi(prices: pd.Series, period: int = 14) -> float | None:
    """Calculate RSI indicator."""
    if len(prices) < period + 1:
        return None
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 2) if pd.notna(val) else None


def fetch_all_data(
    tickers: list[str],
    progress_callback=None,
    max_workers: int = 5,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Fetch data for all tickers using thread pool.
    Returns a DataFrame with all screening metrics.

    Args:
        tickers: List of Yahoo Finance ticker symbols
        progress_callback: Optional callable(current, total) for progress updates
        max_workers: Number of parallel threads
        use_cache: Whether to use file cache
    """
    cache_file = CACHE_DIR / f"screener_{_cache_key(tickers)}.parquet"

    if use_cache and _is_cache_valid(cache_file):
        logger.info("Loading from cache...")
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            pass

    results = []
    completed = 0
    total = len(tickers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(fetch_single_ticker, t): t for t in tickers
        }
        for future in as_completed(future_to_ticker):
            completed += 1
            ticker = future_to_ticker[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Error fetching {ticker}: {e}")

            if progress_callback:
                progress_callback(completed, total)

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)

    # Save to cache
    try:
        df.to_parquet(cache_file, index=False)
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")

    return df


def fetch_price_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Fetch historical price data for charting."""
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        return hist
    except Exception as e:
        logger.warning(f"Failed to fetch history for {symbol}: {e}")
        return pd.DataFrame()


def get_company_info(symbol: str) -> dict:
    """Fetch detailed company info for the detail view."""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return {
            "Name": info.get("longName", info.get("shortName", symbol)),
            "Sector": info.get("sector", "N/A"),
            "Industry": info.get("industry", "N/A"),
            "Description": info.get("longBusinessSummary", "No description available."),
            "Website": info.get("website", "N/A"),
            "Employees": info.get("fullTimeEmployees"),
            "Country": info.get("country", "South Africa"),
            "Exchange": info.get("exchange", "JSE"),
            "Currency": info.get("currency", "ZAR"),
        }
    except Exception:
        return {"Name": symbol, "Sector": "N/A", "Industry": "N/A"}


def get_stock_research(symbol: str) -> dict:
    """
    Fetch comprehensive research data for the stock detail deep-dive.
    Includes financials, analyst data, news, and key events.
    """
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        result = {}

        # ── Company Overview ──
        result["overview"] = {
            "name": info.get("longName", info.get("shortName", symbol)),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "description": info.get("longBusinessSummary", ""),
            "website": info.get("website"),
            "employees": info.get("fullTimeEmployees"),
            "country": info.get("country", "South Africa"),
            "currency": info.get("currency", "ZAR"),
        }

        # ── Analyst Recommendations ──
        result["analyst"] = {
            "recommendation": _format_recommendation(info.get("recommendationKey")),
            "mean_score": info.get("recommendationMean"),
            "num_analysts": info.get("numberOfAnalystOpinions"),
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "target_mean": info.get("targetMeanPrice"),
            "target_median": info.get("targetMedianPrice"),
            "current_price": info.get("regularMarketPrice") or info.get("currentPrice"),
        }
        price = result["analyst"]["current_price"]
        tmean = result["analyst"]["target_mean"]
        result["analyst"]["upside_pct"] = (
            round((tmean - price) / price * 100, 2) if tmean and price and price > 0 else None
        )

        # ── Recommendation Trends (quarterly breakdown) ──
        try:
            rec_df = stock.recommendations
            if rec_df is not None and not rec_df.empty:
                result["rec_trends"] = rec_df.tail(8).to_dict("records")
            else:
                result["rec_trends"] = []
        except Exception:
            result["rec_trends"] = []

        # ── Income Statement (annual) ──
        try:
            inc = stock.financials
            if inc is not None and not inc.empty:
                result["income_statement"] = inc.to_dict()
            else:
                result["income_statement"] = {}
        except Exception:
            result["income_statement"] = {}

        # ── Balance Sheet ──
        try:
            bs = stock.balance_sheet
            if bs is not None and not bs.empty:
                result["balance_sheet"] = bs.to_dict()
            else:
                result["balance_sheet"] = {}
        except Exception:
            result["balance_sheet"] = {}

        # ── Cash Flow ──
        try:
            cf = stock.cashflow
            if cf is not None and not cf.empty:
                result["cash_flow"] = cf.to_dict()
            else:
                result["cash_flow"] = {}
        except Exception:
            result["cash_flow"] = {}

        # ── Major Holders ──
        try:
            holders = stock.institutional_holders
            if holders is not None and not holders.empty:
                result["institutional_holders"] = holders.head(10).to_dict("records")
            else:
                result["institutional_holders"] = []
        except Exception:
            result["institutional_holders"] = []

        # ── News ──
        try:
            news = stock.news
            if news:
                result["news"] = [
                    {
                        "title": n.get("title", ""),
                        "publisher": n.get("publisher", ""),
                        "link": n.get("link") or n.get("url", ""),
                        "published": n.get("providerPublishTime", ""),
                    }
                    for n in news[:10]
                ]
            else:
                result["news"] = []
        except Exception:
            result["news"] = []

        # ── Dividend History ──
        try:
            divs = stock.dividends
            if divs is not None and not divs.empty:
                result["dividends"] = divs.tail(20).reset_index().to_dict("records")
            else:
                result["dividends"] = []
        except Exception:
            result["dividends"] = []

        return result

    except Exception as e:
        logger.warning(f"Failed to fetch research for {symbol}: {e}")
        return {"overview": {"name": symbol}, "analyst": {}, "news": []}
