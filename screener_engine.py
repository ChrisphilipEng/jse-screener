"""
Screening Engine
----------------
Applies user-defined filters to the fetched data.
Supports:
  - Range filters (min/max) for all numeric fields
  - Sector/industry filters
  - Pre-built strategy screens (value, momentum, income, quality)
  - Custom composite scoring
"""

import pandas as pd
import numpy as np


# ──────────────────────────────────────────────────────────────────────
# FILTER DEFINITIONS
# Each filter group maps display names to DataFrame column names
# ──────────────────────────────────────────────────────────────────────

FILTER_GROUPS = {
    "Valuation": {
        "P/E Ratio (Trailing)": "PE_Trailing",
        "P/E Ratio (Forward)": "PE_Forward",
        "Price/Book": "PB_Ratio",
        "Price/Sales": "PS_Ratio",
        "EV/EBITDA": "EV_EBITDA",
        "EV/Revenue": "EV_Revenue",
        "PEG Ratio": "PEG_Ratio",
    },
    "Momentum & Technical": {
        "RSI (14-day)": "RSI_14",
        "Price Change 1D (%)": "Price_1D_Pct",
        "Price Change 5D (%)": "Price_5D_Pct",
        "Price Change 1M (%)": "Price_1M_Pct",
        "Price Change 3M (%)": "Price_3M_Pct",
        "Price Change 6M (%)": "Price_6M_Pct",
        "Price Change 1Y (%)": "Price_1Y_Pct",
        "% From 52W High": "Pct_From_52W_High",
        "Volatility (Ann. %)": "Volatility_Ann_Pct",
        "Beta": "Beta",
    },
    "Income & Dividends": {
        "Dividend Yield (%)": "Div_Yield_Pct",
        "Payout Ratio (%)": "Payout_Ratio_Pct",
    },
    "Quality & Profitability": {
        "ROE (%)": "ROE_Pct",
        "ROA (%)": "ROA_Pct",
        "Profit Margin (%)": "Profit_Margin_Pct",
        "Operating Margin (%)": "Operating_Margin_Pct",
        "Gross Margin (%)": "Gross_Margin_Pct",
        "Debt/Equity": "Debt_to_Equity",
        "Current Ratio": "Current_Ratio",
    },
    "Growth": {
        "Earnings Growth (%)": "Earnings_Growth_Pct",
        "Revenue Growth (%)": "Revenue_Growth_Pct",
    },
    "Analyst & Target": {
        "Analyst Score (1=Strong Buy)": "Analyst_Score",
        "# Analysts Covering": "Num_Analysts",
        "Target Price (Mean)": "Target_Mean",
        "Upside to Target (%)": "Upside_Pct",
    },
    "Size & Liquidity": {
        "Market Cap (Bn ZAR)": "Market_Cap_Bn",
        "Avg Volume (20D)": "Avg_Vol_20D",
    },
}


def get_all_filter_columns() -> dict[str, str]:
    """Return flat dict of display_name -> column_name."""
    result = {}
    for group in FILTER_GROUPS.values():
        result.update(group)
    return result


def apply_filters(
    df: pd.DataFrame,
    filters: dict[str, tuple[float | None, float | None]],
    sectors: list[str] | None = None,
) -> pd.DataFrame:
    """
    Apply range filters to the DataFrame.

    Args:
        df: Full screener DataFrame
        filters: dict mapping column names to (min_val, max_val) tuples
                 None means no bound on that side
        sectors: Optional list of sectors to include

    Returns:
        Filtered DataFrame
    """
    filtered = df.copy()

    # Sector filter
    if sectors and len(sectors) > 0:
        if "Sector" in filtered.columns:
            filtered = filtered[filtered["Sector"].isin(sectors)]

    # Range filters — preserve rows where the column is NaN
    # (NaN means data not available, not that it fails the filter)
    for col, (min_val, max_val) in filters.items():
        if col not in filtered.columns:
            continue
        is_nan = filtered[col].isna()
        if min_val is not None:
            filtered = filtered[is_nan | (filtered[col] >= min_val)]
        if max_val is not None:
            is_nan = filtered[col].isna()  # Recompute after potential row removal
            filtered = filtered[is_nan | (filtered[col] <= max_val)]

    return filtered.reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────
# PRE-BUILT STRATEGY SCREENS
# ──────────────────────────────────────────────────────────────────────

STRATEGIES = {
    "Deep Value": {
        "description": "Low valuation stocks trading below intrinsic value. Classic Graham/Buffett style.",
        "filters": {
            "PE_Trailing": (None, 12),
            "PB_Ratio": (None, 1.5),
            "Div_Yield_Pct": (2.0, None),
            "Debt_to_Equity": (None, 100),
        },
        "sort_by": "PE_Trailing",
        "sort_asc": True,
    },
    "High Dividend Income": {
        "description": "High-yielding stocks with sustainable payouts for income portfolios.",
        "filters": {
            "Div_Yield_Pct": (4.0, None),
            "Payout_Ratio_Pct": (None, 80),
            "Market_Cap_Bn": (5, None),
        },
        "sort_by": "Div_Yield_Pct",
        "sort_asc": False,
    },
    "Momentum Leaders": {
        "description": "Stocks with strong upward price momentum across multiple timeframes.",
        "filters": {
            "Price_1M_Pct": (0, None),
            "Price_3M_Pct": (5, None),
            "Price_6M_Pct": (10, None),
            "RSI_14": (50, 80),
            "Avg_Vol_20D": (100000, None),
        },
        "sort_by": "Price_6M_Pct",
        "sort_asc": False,
    },
    "Quality Compounders": {
        "description": "High-quality businesses with strong returns and growth — long-term compounders.",
        "filters": {
            "ROE_Pct": (15, None),
            "Profit_Margin_Pct": (10, None),
            "Debt_to_Equity": (None, 80),
            "Revenue_Growth_Pct": (0, None),
        },
        "sort_by": "ROE_Pct",
        "sort_asc": False,
    },
    "Oversold Bounce": {
        "description": "Technically oversold stocks that may be due for a rebound. Contrarian play.",
        "filters": {
            "RSI_14": (None, 35),
            "Pct_From_52W_High": (None, -25),
            "Market_Cap_Bn": (2, None),
        },
        "sort_by": "RSI_14",
        "sort_asc": True,
    },
    "Small Cap Growth": {
        "description": "Smaller companies with strong growth and reasonable valuations.",
        "filters": {
            "Market_Cap_Bn": (0.5, 20),
            "Revenue_Growth_Pct": (5, None),
            "PE_Forward": (None, 20),
        },
        "sort_by": "Revenue_Growth_Pct",
        "sort_asc": False,
    },
    "Low Volatility": {
        "description": "Defensive, low-volatility stocks for risk-averse portfolios.",
        "filters": {
            "Beta": (None, 0.8),
            "Volatility_Ann_Pct": (None, 25),
            "Div_Yield_Pct": (1.5, None),
            "Market_Cap_Bn": (10, None),
        },
        "sort_by": "Volatility_Ann_Pct",
        "sort_asc": True,
    },
}


def apply_strategy(df: pd.DataFrame, strategy_name: str) -> pd.DataFrame:
    """Apply a pre-built strategy screen."""
    if strategy_name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    strategy = STRATEGIES[strategy_name]
    filters = {col: bounds for col, bounds in strategy["filters"].items()}
    filtered = apply_filters(df, filters)

    # Sort by the strategy's primary sort column
    sort_col = strategy["sort_by"]
    if sort_col in filtered.columns:
        filtered = filtered.sort_values(
            sort_col, ascending=strategy["sort_asc"], na_position="last"
        )

    return filtered.reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────
# COMPOSITE SCORING
# ──────────────────────────────────────────────────────────────────────

def compute_composite_score(
    df: pd.DataFrame,
    weights: dict[str, tuple[float, bool]],
) -> pd.DataFrame:
    """
    Compute a weighted composite score across multiple metrics.

    Args:
        df: Screener DataFrame
        weights: dict mapping column names to (weight, higher_is_better) tuples

    Returns:
        DataFrame with added 'Composite_Score' column, sorted desc
    """
    scored = df.copy()
    score = pd.Series(0.0, index=scored.index)

    for col, (weight, higher_is_better) in weights.items():
        if col not in scored.columns:
            continue
        series = scored[col].copy()
        # Normalize to 0-100 percentile rank
        ranked = series.rank(pct=True, na_option="bottom") * 100
        if not higher_is_better:
            ranked = 100 - ranked
        score += ranked * weight

    # Normalize total
    total_weight = sum(w for w, _ in weights.values())
    if total_weight > 0:
        score = score / total_weight

    scored["Composite_Score"] = score.round(2)
    scored = scored.sort_values("Composite_Score", ascending=False)
    return scored.reset_index(drop=True)
