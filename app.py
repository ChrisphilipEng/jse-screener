"""
JSE Research Terminal — Streamlit Application
===============================================
A comprehensive equity research platform for the
Johannesburg Stock Exchange (JSE).
Apple-inspired dark mode UI with full navigation.

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io
import json
from pathlib import Path

from jse_universe import get_universe_df, get_sectors, load_custom_universe
from data_fetcher import (
    fetch_all_data, fetch_price_history, get_company_info,
    get_stock_research, fetch_single_ticker,
)
from screener_engine import (
    FILTER_GROUPS, STRATEGIES, apply_filters, apply_strategy,
    compute_composite_score, get_all_filter_columns,
)

# ──────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JSE Research Terminal",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────────────
# APPLE-STYLE DARK MODE CSS
# ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── APPLE DESIGN SYSTEM — DARK MODE ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Root variables */
    :root {
        --bg-primary: #000000;
        --bg-secondary: #1c1c1e;
        --bg-tertiary: #2c2c2e;
        --bg-card: #1c1c1e;
        --text-primary: #f5f5f7;
        --text-secondary: #86868b;
        --text-tertiary: #6e6e73;
        --accent-blue: #0a84ff;
        --accent-green: #30d158;
        --accent-red: #ff453a;
        --accent-orange: #ff9f0a;
        --accent-yellow: #ffd60a;
        --accent-purple: #bf5af2;
        --border-color: #38383a;
        --border-subtle: #2c2c2e;
        --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
    }

    /* Global */
    .stApp { background-color: var(--bg-primary) !important; font-family: var(--font-family); }
    .block-container { padding-top: 0.5rem !important; max-width: 1400px; }
    h1, h2, h3, h4, h5 { font-family: var(--font-family) !important; font-weight: 600 !important; color: var(--text-primary) !important; letter-spacing: -0.02em; }
    p, span, li, label, div { font-family: var(--font-family) !important; }

    /* Hide default Streamlit header/footer */
    header[data-testid="stHeader"] { background: transparent !important; }
    .stDeployButton { display: none; }

    /* ── TOP NAVIGATION BAR ── */
    .nav-bar {
        display: flex;
        align-items: center;
        gap: 0;
        background: rgba(28, 28, 30, 0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-bottom: 1px solid var(--border-color);
        padding: 0 24px;
        margin: -1rem -1rem 1.5rem -1rem;
        position: sticky;
        top: 0;
        z-index: 999;
        border-radius: 0;
    }
    .nav-brand {
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--text-primary);
        padding: 14px 20px 14px 0;
        border-right: 1px solid var(--border-color);
        margin-right: 4px;
        letter-spacing: -0.03em;
        white-space: nowrap;
    }
    .nav-item {
        padding: 14px 18px;
        color: var(--text-secondary);
        font-size: 0.85rem;
        font-weight: 500;
        cursor: pointer;
        transition: color 0.2s;
        border-bottom: 2px solid transparent;
        text-decoration: none;
        white-space: nowrap;
    }
    .nav-item:hover { color: var(--text-primary); }
    .nav-item.active {
        color: var(--accent-blue);
        border-bottom: 2px solid var(--accent-blue);
    }

    /* ── CARDS ── */
    .apple-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .apple-card-sm {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }

    /* ── METRICS ── */
    .metric-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 16px 20px;
        text-align: left;
    }
    .metric-label {
        font-size: 0.72rem;
        font-weight: 500;
        color: var(--text-tertiary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.03em;
    }
    .metric-value.positive { color: var(--accent-green); }
    .metric-value.negative { color: var(--accent-red); }
    .metric-delta {
        font-size: 0.78rem;
        font-weight: 500;
        margin-top: 2px;
    }
    .metric-delta.up { color: var(--accent-green); }
    .metric-delta.down { color: var(--accent-red); }

    /* ── STOCK ROW (clickable list item) ── */
    .stock-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 20px;
        border-bottom: 1px solid var(--border-subtle);
        transition: background 0.15s;
        cursor: pointer;
    }
    .stock-row:hover { background: var(--bg-tertiary); }
    .stock-row:last-child { border-bottom: none; }
    .stock-name { font-weight: 600; color: var(--text-primary); font-size: 0.9rem; }
    .stock-symbol { color: var(--text-tertiary); font-size: 0.78rem; margin-top: 1px; }
    .stock-price { font-weight: 600; color: var(--text-primary); font-size: 0.95rem; text-align: right; }
    .stock-change { font-size: 0.8rem; font-weight: 500; text-align: right; }
    .stock-change.up { color: var(--accent-green); }
    .stock-change.down { color: var(--accent-red); }

    /* ── BADGE ── */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .badge-buy { background: rgba(48, 209, 88, 0.15); color: var(--accent-green); }
    .badge-hold { background: rgba(255, 159, 10, 0.15); color: var(--accent-orange); }
    .badge-sell { background: rgba(255, 69, 58, 0.15); color: var(--accent-red); }

    /* ── SECTION HEADERS ── */
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 24px 0 16px 0;
        letter-spacing: -0.02em;
    }
    .section-sub {
        font-size: 0.82rem;
        color: var(--text-tertiary);
        margin: -12px 0 16px 0;
    }

    /* ── STREAMLIT OVERRIDES ── */
    .stMetric { background: var(--bg-secondary) !important; border-radius: 12px !important; padding: 16px !important; border: 1px solid var(--border-subtle) !important; }
    .stMetric label { color: var(--text-tertiary) !important; font-size: 0.72rem !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }
    .stMetric [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700 !important; letter-spacing: -0.03em !important; }

    div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid var(--border-color); }

    .stTabs [data-baseweb="tab-list"] { gap: 0; background: var(--bg-secondary); border-radius: 10px; padding: 3px; border: 1px solid var(--border-color); }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; font-weight: 500; font-size: 0.82rem; color: var(--text-secondary); padding: 8px 16px; }
    .stTabs [aria-selected="true"] { background: var(--bg-tertiary) !important; color: var(--text-primary) !important; }

    .stSelectbox > div > div { background: var(--bg-secondary) !important; border-color: var(--border-color) !important; border-radius: 10px !important; }
    .stMultiSelect > div > div { background: var(--bg-secondary) !important; border-color: var(--border-color) !important; border-radius: 10px !important; }
    .stNumberInput > div > div > input { background: var(--bg-secondary) !important; border-color: var(--border-color) !important; border-radius: 10px !important; }

    button[kind="primary"] { background: var(--accent-blue) !important; border: none !important; border-radius: 10px !important; font-weight: 600 !important; }
    button[kind="secondary"] { border-color: var(--border-color) !important; border-radius: 10px !important; }

    .stExpander { border: 1px solid var(--border-color) !important; border-radius: 12px !important; background: var(--bg-secondary) !important; }

    .stDownloadButton > button { border-radius: 10px !important; }

    /* Plotly chart backgrounds */
    .js-plotly-plot .plotly .bg { fill: var(--bg-secondary) !important; }

    /* Watchlist / Portfolio buttons */
    .action-btn {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 0.82rem;
        font-weight: 600;
        cursor: pointer;
        border: 1px solid var(--border-color);
        background: var(--bg-tertiary);
        color: var(--text-primary);
        transition: all 0.15s;
    }
    .action-btn:hover { background: var(--accent-blue); border-color: var(--accent-blue); }
    .action-btn-danger:hover { background: var(--accent-red); border-color: var(--accent-red); }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────────────────────────────
defaults = {
    "screener_data": None,
    "last_fetch_time": None,
    "active_page": "Home",
    "research_symbol": None,
    "watchlist": ["NPN.JO", "SBK.JO", "CPI.JO", "SHP.JO", "MTN.JO"],
    "portfolio": [
        {"symbol": "SBK.JO", "shares": 100, "avg_price": 145.00},
        {"symbol": "CPI.JO", "shares": 50, "avg_price": 2100.00},
        {"symbol": "SHP.JO", "shares": 200, "avg_price": 220.00},
    ],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

WATCHLIST_FILE = Path(".watchlist.json")
PORTFOLIO_FILE = Path(".portfolio.json")

# Persist watchlist/portfolio
def _save_watchlist():
    WATCHLIST_FILE.write_text(json.dumps(st.session_state.watchlist))
def _save_portfolio():
    PORTFOLIO_FILE.write_text(json.dumps(st.session_state.portfolio))
def _load_persisted():
    if WATCHLIST_FILE.exists():
        try: st.session_state.watchlist = json.loads(WATCHLIST_FILE.read_text())
        except: pass
    if PORTFOLIO_FILE.exists():
        try: st.session_state.portfolio = json.loads(PORTFOLIO_FILE.read_text())
        except: pass
_load_persisted()


# ──────────────────────────────────────────────────────────────────────
# NAVIGATION
# ──────────────────────────────────────────────────────────────────────
PAGES = ["Home", "Screener", "Research", "Watchlist", "Portfolio", "Sectors", "News"]

def _nav_class(page):
    return "nav-item active" if st.session_state.active_page == page else "nav-item"

# Render navigation bar using Streamlit columns (clickable)
nav_cols = st.columns([2] + [1] * len(PAGES))
with nav_cols[0]:
    st.markdown('<div style="font-size:1.15rem;font-weight:700;color:#f5f5f7;padding:8px 0;letter-spacing:-0.03em;">JSE Research Terminal</div>', unsafe_allow_html=True)
for i, page in enumerate(PAGES):
    with nav_cols[i + 1]:
        if st.button(page, key=f"nav_{page}", use_container_width=True):
            st.session_state.active_page = page
            st.rerun()

st.markdown('<div style="border-bottom:1px solid #38383a;margin:-0.5rem 0 1.5rem 0;"></div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# HELPER: Plotly dark theme
# ──────────────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#1c1c1e",
    plot_bgcolor="#1c1c1e",
    font=dict(family="Inter, -apple-system, sans-serif", color="#f5f5f7"),
    margin=dict(t=30, b=40, l=50, r=20),
)

def _metric_html(label, value, delta=None, delta_dir=None):
    """Render an Apple-style metric card."""
    val_class = ""
    if delta_dir == "up": val_class = "positive"
    elif delta_dir == "down": val_class = "negative"
    delta_html = ""
    if delta:
        d_class = "up" if delta_dir == "up" else "down" if delta_dir == "down" else ""
        delta_html = f'<div class="metric-delta {d_class}">{delta}</div>'
    return f'''
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {val_class}">{value}</div>
        {delta_html}
    </div>'''

def _rec_badge(rec):
    """Return HTML badge for analyst recommendation."""
    if not rec or rec == "N/A":
        return '<span class="badge" style="background:#38383a;color:#86868b;">N/A</span>'
    rec_lower = rec.lower()
    if "buy" in rec_lower or "overweight" in rec_lower:
        return f'<span class="badge badge-buy">{rec}</span>'
    elif "sell" in rec_lower or "underweight" in rec_lower:
        return f'<span class="badge badge-sell">{rec}</span>'
    else:
        return f'<span class="badge badge-hold">{rec}</span>'


# ──────────────────────────────────────────────────────────────────────
# DATA LOADING (shared across pages)
# ──────────────────────────────────────────────────────────────────────
universe_df = get_universe_df()


# ══════════════════════════════════════════════════════════════════════
#  PAGE: HOME — MARKET DASHBOARD
# ══════════════════════════════════════════════════════════════════════
if st.session_state.active_page == "Home":

    st.markdown('<div class="section-header">Market Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Johannesburg Stock Exchange — Live Data</div>', unsafe_allow_html=True)

    # Quick load button
    if st.session_state.screener_data is None:
        st.info("No data loaded yet. Fetch data to populate the dashboard.")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            if st.button("Load Top 40", type="primary", use_container_width=True):
                top40 = ["NPN.JO","PRX.JO","CFR.JO","BTI.JO","AGL.JO","BHP.JO",
                         "GLN.JO","SOL.JO","MTN.JO","SHP.JO","FSR.JO","SBK.JO",
                         "ABG.JO","NED.JO","CPI.JO","SLM.JO","DSY.JO","OMU.JO",
                         "AMS.JO","IMP.JO","SSW.JO","ANG.JO","GFI.JO","KIO.JO",
                         "EXX.JO","MNP.JO","VOD.JO","CLS.JO","WHL.JO","BID.JO",
                         "BVT.JO","MRP.JO","TFG.JO","REM.JO","APN.JO","NPH.JO",
                         "MCG.JO","ARI.JO","N91.JO","INL.JO"]
                prog = st.progress(0, "Loading Top 40...")
                def _upd(c, t): prog.progress(c/t, f"Fetching {c}/{t}...")
                data = fetch_all_data(top40, progress_callback=_upd, max_workers=5)
                prog.empty()
                if not data.empty:
                    data = data.merge(universe_df[["Symbol","Company","Sector"]], on="Symbol", how="left", suffixes=("","_u"))
                    for col in ["Sector","Company"]:
                        if f"{col}_u" in data.columns:
                            data[col] = data[col].fillna(data[f"{col}_u"])
                            data.drop(columns=[f"{col}_u"], inplace=True, errors="ignore")
                    st.session_state.screener_data = data
                    st.session_state.last_fetch_time = datetime.now()
                    st.rerun()
        with c2:
            if st.button("Load Full JSE", use_container_width=True):
                tickers = universe_df["Symbol"].tolist()
                prog = st.progress(0, "Loading full universe...")
                def _upd2(c, t): prog.progress(c/t, f"Fetching {c}/{t}...")
                data = fetch_all_data(tickers, progress_callback=_upd2, max_workers=5)
                prog.empty()
                if not data.empty:
                    data = data.merge(universe_df[["Symbol","Company","Sector"]], on="Symbol", how="left", suffixes=("","_u"))
                    for col in ["Sector","Company"]:
                        if f"{col}_u" in data.columns:
                            data[col] = data[col].fillna(data[f"{col}_u"])
                            data.drop(columns=[f"{col}_u"], inplace=True, errors="ignore")
                    st.session_state.screener_data = data
                    st.session_state.last_fetch_time = datetime.now()
                    st.rerun()

    else:
        data = st.session_state.screener_data
        ts = st.session_state.last_fetch_time
        st.caption(f"Data loaded: {len(data)} stocks | Last refresh: {ts.strftime('%H:%M:%S') if ts else 'N/A'}")

        # ── Summary Row ──
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Stocks Loaded", f"{len(data)}")
        avg_pe = data["PE_Trailing"].median()
        m2.metric("Median P/E", f"{avg_pe:.1f}" if pd.notna(avg_pe) else "N/A")
        avg_dy = data["Div_Yield_Pct"].median()
        m3.metric("Median Div Yield", f"{avg_dy:.2f}%" if pd.notna(avg_dy) else "N/A")
        total_mcap = data["Market_Cap_Bn"].sum()
        m4.metric("Total Mkt Cap", f"R{total_mcap:,.0f}B" if pd.notna(total_mcap) else "N/A")
        gainers = len(data[data["Price_1D_Pct"] > 0]) if "Price_1D_Pct" in data.columns else 0
        losers = len(data[data["Price_1D_Pct"] < 0]) if "Price_1D_Pct" in data.columns else 0
        m5.metric("Gainers", f"{gainers}", delta=f"{gainers}/{gainers+losers}")
        m6.metric("Losers", f"{losers}")

        st.markdown("---")

        # ── Top Movers ──
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown('<div class="section-header">Top Gainers</div>', unsafe_allow_html=True)
            if "Price_1D_Pct" in data.columns:
                top_gain = data.nlargest(8, "Price_1D_Pct")[["Symbol","Company","Price","Price_1D_Pct","Market_Cap_Bn"]].copy()
                for _, row in top_gain.iterrows():
                    sym = row["Symbol"]
                    name = row.get("Company", sym)
                    price = row["Price"]
                    chg = row["Price_1D_Pct"]
                    st.markdown(f'''
                    <div class="stock-row">
                        <div><div class="stock-name">{name}</div><div class="stock-symbol">{sym}</div></div>
                        <div><div class="stock-price">R{price:,.2f}</div><div class="stock-change up">+{chg:.2f}%</div></div>
                    </div>''', unsafe_allow_html=True)

        with col_right:
            st.markdown('<div class="section-header">Top Losers</div>', unsafe_allow_html=True)
            if "Price_1D_Pct" in data.columns:
                top_lose = data.nsmallest(8, "Price_1D_Pct")[["Symbol","Company","Price","Price_1D_Pct"]].copy()
                for _, row in top_lose.iterrows():
                    sym = row["Symbol"]
                    name = row.get("Company", sym)
                    price = row["Price"]
                    chg = row["Price_1D_Pct"]
                    st.markdown(f'''
                    <div class="stock-row">
                        <div><div class="stock-name">{name}</div><div class="stock-symbol">{sym}</div></div>
                        <div><div class="stock-price">R{price:,.2f}</div><div class="stock-change down">{chg:.2f}%</div></div>
                    </div>''', unsafe_allow_html=True)

        st.markdown("---")

        # ── Sector Heatmap ──
        st.markdown('<div class="section-header">Sector Performance</div>', unsafe_allow_html=True)
        if "Sector" in data.columns and "Price_1D_Pct" in data.columns:
            sector_perf = data.groupby("Sector").agg(
                Avg_1D=("Price_1D_Pct", "mean"),
                Avg_1M=("Price_1M_Pct", "mean"),
                Avg_6M=("Price_6M_Pct", "mean"),
                Count=("Symbol", "count"),
                Mkt_Cap=("Market_Cap_Bn", "sum"),
            ).round(2)
            sector_perf = sector_perf.sort_values("Mkt_Cap", ascending=False)

            fig_sector = go.Figure(data=go.Heatmap(
                z=[sector_perf["Avg_1D"].values, sector_perf["Avg_1M"].values, sector_perf["Avg_6M"].values],
                x=sector_perf.index,
                y=["1 Day", "1 Month", "6 Months"],
                colorscale=[[0, "#ff453a"], [0.5, "#1c1c1e"], [1, "#30d158"]],
                zmid=0,
                text=np.array([sector_perf["Avg_1D"].values, sector_perf["Avg_1M"].values, sector_perf["Avg_6M"].values]).round(1),
                texttemplate="%{text}%",
                textfont={"size": 12, "color": "#f5f5f7"},
            ))
            fig_sector.update_layout(**PLOTLY_LAYOUT, height=220, margin=dict(t=10, b=30, l=80, r=20))
            st.plotly_chart(fig_sector, use_container_width=True)

        # ── Top Analyst Picks ──
        st.markdown('<div class="section-header">Top Analyst Picks</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Stocks with highest analyst upside and strong buy ratings</div>', unsafe_allow_html=True)
        if "Upside_Pct" in data.columns and "Analyst_Rec" in data.columns:
            picks = data.dropna(subset=["Upside_Pct", "Analyst_Rec"])
            picks = picks[picks["Analyst_Rec"].isin(["Strong Buy", "Buy"])]
            picks = picks.nlargest(10, "Upside_Pct")
            if len(picks) > 0:
                for _, row in picks.iterrows():
                    rec_html = _rec_badge(row.get("Analyst_Rec"))
                    upside = row["Upside_Pct"]
                    up_color = "#30d158" if upside > 0 else "#ff453a"
                    st.markdown(f'''
                    <div class="stock-row">
                        <div style="display:flex;align-items:center;gap:12px;">
                            {rec_html}
                            <div><div class="stock-name">{row.get("Company", row["Symbol"])}</div><div class="stock-symbol">{row["Symbol"]}</div></div>
                        </div>
                        <div style="display:flex;align-items:center;gap:24px;">
                            <div style="text-align:right;"><div class="stock-price">R{row["Price"]:,.2f}</div><div style="font-size:0.78rem;color:#86868b;">Target: R{row.get("Target_Mean",0):,.2f}</div></div>
                            <div style="font-size:1.1rem;font-weight:700;color:{up_color};min-width:70px;text-align:right;">{upside:+.1f}%</div>
                        </div>
                    </div>''', unsafe_allow_html=True)
            else:
                st.caption("No stocks with Buy/Strong Buy rating found in current data.")

        # Refresh button
        st.markdown("---")
        if st.button("Refresh Data", use_container_width=True):
            st.session_state.screener_data = None
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  PAGE: SCREENER
# ══════════════════════════════════════════════════════════════════════
elif st.session_state.active_page == "Screener":

    st.markdown('<div class="section-header">Equity Screener</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Filter and rank JSE-listed shares across 30+ metrics</div>', unsafe_allow_html=True)

    if st.session_state.screener_data is None:
        st.warning("No data loaded. Go to **Home** and load data first.")
    else:
        data = st.session_state.screener_data.copy()

        # ── Screener Controls ──
        ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
        with ctrl1:
            strategy_names = ["No Preset (Manual)"] + list(STRATEGIES.keys())
            selected_strategy = st.selectbox("Strategy Preset", strategy_names)
        with ctrl2:
            available_sectors = sorted(data["Sector"].dropna().unique()) if "Sector" in data.columns else []
            selected_sectors = st.multiselect("Sectors", available_sectors, default=available_sectors)
        with ctrl3:
            sort_by = st.selectbox("Sort by", ["Market_Cap_Bn", "Upside_Pct", "Div_Yield_Pct", "PE_Trailing", "ROE_Pct", "Price_1M_Pct", "Price_6M_Pct", "RSI_14"])

        # Manual filters
        with st.expander("Advanced Filters", expanded=False):
            manual_filters = {}
            filter_cols = st.columns(3)
            for idx, (group_name, group_filters) in enumerate(FILTER_GROUPS.items()):
                with filter_cols[idx % 3]:
                    st.markdown(f"**{group_name}**")
                    for display_name, col_name in group_filters.items():
                        fc1, fc2 = st.columns(2)
                        min_val = fc1.number_input(f"Min", value=None, key=f"s_min_{col_name}", placeholder="Min", label_visibility="collapsed")
                        max_val = fc2.number_input(f"Max", value=None, key=f"s_max_{col_name}", placeholder="Max", label_visibility="collapsed")
                        if min_val is not None or max_val is not None:
                            manual_filters[col_name] = (min_val, max_val)
                        st.caption(display_name)

        # Apply filters
        if selected_strategy != "No Preset (Manual)":
            filtered = apply_strategy(data, selected_strategy)
            strat_info = STRATEGIES[selected_strategy]
            st.info(f"**{selected_strategy}** — {strat_info['description']}")
        else:
            filtered = apply_filters(data, manual_filters, selected_sectors)

        if sort_by in filtered.columns:
            asc = sort_by in ["PE_Trailing", "Analyst_Score"]
            filtered = filtered.sort_values(sort_by, ascending=asc, na_position="last")

        # ── Summary ──
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Results", len(filtered))
        s2.metric("Pass Rate", f"{len(filtered)/max(len(data),1)*100:.0f}%")
        avg_up = filtered["Upside_Pct"].median() if "Upside_Pct" in filtered.columns else None
        s3.metric("Median Upside", f"{avg_up:+.1f}%" if pd.notna(avg_up) else "N/A")
        avg_yield = filtered["Div_Yield_Pct"].median() if "Div_Yield_Pct" in filtered.columns else None
        s4.metric("Median Yield", f"{avg_yield:.2f}%" if pd.notna(avg_yield) else "N/A")

        # ── Results Table ──
        display_cols = ["Symbol", "Company", "Sector", "Price", "Analyst_Rec", "Target_Mean",
                       "Upside_Pct", "Market_Cap_Bn", "PE_Trailing", "Div_Yield_Pct",
                       "ROE_Pct", "Price_1M_Pct", "Price_6M_Pct", "RSI_14", "Beta"]
        available = [c for c in display_cols if c in filtered.columns]
        st.dataframe(
            filtered[available],
            use_container_width=True,
            height=500,
            column_config={
                "Price": st.column_config.NumberColumn(format="R %.2f"),
                "Market_Cap_Bn": st.column_config.NumberColumn("Mkt Cap (Bn)", format="R %.2f"),
                "PE_Trailing": st.column_config.NumberColumn("P/E", format="%.1f"),
                "Div_Yield_Pct": st.column_config.NumberColumn("Div Yield %", format="%.2f%%"),
                "ROE_Pct": st.column_config.NumberColumn("ROE %", format="%.1f%%"),
                "Price_1M_Pct": st.column_config.NumberColumn("1M %", format="%.2f%%"),
                "Price_6M_Pct": st.column_config.NumberColumn("6M %", format="%.2f%%"),
                "RSI_14": st.column_config.NumberColumn("RSI", format="%.1f"),
                "Beta": st.column_config.NumberColumn("Beta", format="%.2f"),
                "Analyst_Rec": st.column_config.TextColumn("Analyst"),
                "Target_Mean": st.column_config.NumberColumn("Target", format="R %.2f"),
                "Upside_Pct": st.column_config.NumberColumn("Upside %", format="%.1f%%"),
            },
        )

        # ── Quick Research Buttons ──
        st.markdown("---")
        st.markdown("**Open Research** — click a stock below:")
        btn_cols = st.columns(10)
        for idx, sym in enumerate(filtered["Symbol"].tolist()[:30]):
            with btn_cols[idx % 10]:
                label = sym.replace(".JO", "")
                if st.button(label, key=f"scr_{sym}"):
                    st.session_state.research_symbol = sym
                    st.session_state.active_page = "Research"
                    st.rerun()

        # ── Export ──
        st.markdown("---")
        ex1, ex2 = st.columns(2)
        with ex1:
            csv = filtered.to_csv(index=False)
            st.download_button("Download CSV", csv, f"jse_screen_{datetime.now():%Y%m%d_%H%M}.csv", "text/csv", use_container_width=True)
        with ex2:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                filtered.to_excel(w, sheet_name="Results", index=False)
            st.download_button("Download Excel", buf.getvalue(), f"jse_screen_{datetime.now():%Y%m%d_%H%M}.xlsx", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
#  PAGE: RESEARCH — STOCK DEEP DIVE
# ══════════════════════════════════════════════════════════════════════
elif st.session_state.active_page == "Research":

    st.markdown('<div class="section-header">Stock Research</div>', unsafe_allow_html=True)

    # Stock picker
    all_symbols = universe_df["Symbol"].tolist()
    default_idx = 0
    if st.session_state.research_symbol and st.session_state.research_symbol in all_symbols:
        default_idx = all_symbols.index(st.session_state.research_symbol)

    pick1, pick2 = st.columns([3, 1])
    with pick1:
        research_sym = st.selectbox("Search for a stock", all_symbols, index=default_idx, key="research_pick")
    with pick2:
        if st.button("Add to Watchlist", use_container_width=True):
            if research_sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(research_sym)
                _save_watchlist()
                st.success(f"Added {research_sym}")

    if research_sym:
        with st.spinner(f"Loading research for {research_sym}..."):
            research = get_stock_research(research_sym)

        ov = research.get("overview", {})
        an = research.get("analyst", {})

        # ── Header ──
        st.markdown(f'<div style="font-size:2rem;font-weight:700;color:#f5f5f7;letter-spacing:-0.03em;margin-top:8px;">{ov.get("name", research_sym)}</div>', unsafe_allow_html=True)
        st.caption(f'{ov.get("sector","N/A")} | {ov.get("industry","N/A")} | {ov.get("currency","ZAR")}')

        if ov.get("description"):
            with st.expander("About", expanded=False):
                st.write(ov["description"])

        # ── Analyst Consensus ──
        st.markdown("---")
        ac1, ac2, ac3, ac4, ac5 = st.columns(5)
        rec = an.get("recommendation", "N/A")
        ac1.markdown(f"**Recommendation**\n\n{_rec_badge(rec)}", unsafe_allow_html=True)
        ac2.metric("Score (1-5)", f'{an.get("mean_score","N/A")}')
        ac3.metric("# Analysts", f'{an.get("num_analysts","N/A")}')
        price = an.get("current_price")
        target = an.get("target_mean")
        ac4.metric("Price", f"R{price:,.2f}" if price else "N/A")
        ac5.metric("Target", f"R{target:,.2f}" if target else "N/A")

        # ── Upside Banner ──
        upside = an.get("upside_pct")
        if upside is not None:
            up_color = "#30d158" if upside > 0 else "#ff453a"
            up_label = "UPSIDE" if upside > 0 else "DOWNSIDE"
            st.markdown(f'''
            <div style="text-align:center;padding:20px;margin:16px 0;background:#1c1c1e;border-radius:16px;border:1px solid #38383a;">
                <div style="font-size:2.5rem;font-weight:700;color:{up_color};letter-spacing:-0.04em;">{upside:+.1f}%</div>
                <div style="font-size:0.85rem;color:#86868b;font-weight:500;">{up_label} TO ANALYST TARGET</div>
            </div>''', unsafe_allow_html=True)

        # ── Target Range ──
        if all(an.get(k) for k in ["target_low","target_mean","target_high","current_price"]):
            t_low, t_mean, t_high, c_price = an["target_low"], an["target_mean"], an["target_high"], an["current_price"]
            t_median = an.get("target_median", t_mean)

            fig_t = go.Figure()
            fig_t.add_trace(go.Bar(x=[t_high-t_low], y=[""], base=[t_low], orientation="h",
                                   marker=dict(color="rgba(10,132,255,0.25)"), name="Range",
                                   hovertemplate=f"Low: R{t_low:,.2f}<br>High: R{t_high:,.2f}<extra></extra>"))
            fig_t.add_vline(x=c_price, line=dict(color="#ff453a", width=3),
                           annotation_text=f"Current: R{c_price:,.2f}", annotation_position="top")
            fig_t.add_vline(x=t_mean, line=dict(color="#30d158", width=3, dash="dash"),
                           annotation_text=f"Target: R{t_mean:,.2f}", annotation_position="bottom")
            fig_t.update_layout(**PLOTLY_LAYOUT, height=130, showlegend=False,
                               xaxis=dict(range=[min(t_low,c_price)*0.93, max(t_high,c_price)*1.07]),
                               yaxis=dict(visible=False))
            st.plotly_chart(fig_t, use_container_width=True)

            tc1, tc2, tc3, tc4 = st.columns(4)
            tc1.metric("Target Low", f"R{t_low:,.2f}")
            tc2.metric("Target Mean", f"R{t_mean:,.2f}")
            tc3.metric("Target Median", f"R{t_median:,.2f}")
            tc4.metric("Target High", f"R{t_high:,.2f}")

        # ── Key Metrics ──
        st.markdown("---")
        st.markdown("**Key Metrics**")
        row = st.session_state.screener_data
        if row is not None:
            row = row[row["Symbol"] == research_sym]
        if row is not None and len(row) > 0:
            r = row.iloc[0]
            km1, km2, km3, km4, km5, km6 = st.columns(6)
            km1.metric("P/E", f"{r.get('PE_Trailing','N/A')}" if pd.notna(r.get('PE_Trailing')) else "N/A")
            km2.metric("P/B", f"{r.get('PB_Ratio','N/A')}" if pd.notna(r.get('PB_Ratio')) else "N/A")
            km3.metric("Div Yield", f"{r.get('Div_Yield_Pct',0):.2f}%" if pd.notna(r.get('Div_Yield_Pct')) else "N/A")
            km4.metric("ROE", f"{r.get('ROE_Pct',0):.1f}%" if pd.notna(r.get('ROE_Pct')) else "N/A")
            km5.metric("D/E", f"{r.get('Debt_to_Equity','N/A')}" if pd.notna(r.get('Debt_to_Equity')) else "N/A")
            km6.metric("Mkt Cap", f"R{r.get('Market_Cap_Bn',0):,.1f}B" if pd.notna(r.get('Market_Cap_Bn')) else "N/A")

        # ── Price Chart ──
        st.markdown("---")
        st.markdown("**Price Chart**")
        rp = st.selectbox("Period", ["1mo","3mo","6mo","1y","2y","5y"], index=3, key="rp")
        hist = fetch_price_history(research_sym, period=rp)
        if not hist.empty:
            fig_pc = go.Figure()
            fig_pc.add_trace(go.Candlestick(x=hist.index, open=hist["Open"], high=hist["High"],
                                            low=hist["Low"], close=hist["Close"], name="Price"))
            if len(hist) >= 20:
                fig_pc.add_trace(go.Scatter(x=hist.index, y=hist["Close"].rolling(20).mean(),
                                            mode="lines", name="SMA 20", line=dict(color="#ff9f0a", width=1)))
            if len(hist) >= 50:
                fig_pc.add_trace(go.Scatter(x=hist.index, y=hist["Close"].rolling(50).mean(),
                                            mode="lines", name="SMA 50", line=dict(color="#0a84ff", width=1)))
            if an.get("target_mean"):
                fig_pc.add_hline(y=an["target_mean"], line=dict(color="#30d158", width=2, dash="dash"),
                                 annotation_text=f"Target: R{an['target_mean']:,.2f}")
            fig_pc.update_layout(**PLOTLY_LAYOUT, height=450, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_pc, use_container_width=True)

            fig_v = px.bar(x=hist.index, y=hist["Volume"], color_discrete_sequence=["#38383a"])
            fig_v.update_layout(**PLOTLY_LAYOUT, height=150, margin=dict(t=5,b=30,l=50,r=20))
            st.plotly_chart(fig_v, use_container_width=True)

        # ── Financials ──
        st.markdown("---")
        st.markdown("**Financial Statements**")
        ft1, ft2, ft3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
        for tab, key in [(ft1,"income_statement"),(ft2,"balance_sheet"),(ft3,"cash_flow")]:
            with tab:
                fdata = research.get(key, {})
                if fdata:
                    fdf = pd.DataFrame(fdata)
                    st.dataframe(fdf.style.format(lambda x: f"R{x:,.0f}" if isinstance(x,(int,float)) and pd.notna(x) else ""),
                                use_container_width=True, height=400)
                else:
                    st.caption("Not available for this stock.")

        # ── Holders ──
        holders = research.get("institutional_holders", [])
        if holders:
            st.markdown("---")
            st.markdown("**Top Institutional Holders**")
            st.dataframe(pd.DataFrame(holders), use_container_width=True)

        # ── Dividends ──
        divs = research.get("dividends", [])
        if divs:
            st.markdown("---")
            st.markdown("**Dividend History**")
            div_df = pd.DataFrame(divs)
            if "Date" in div_df.columns:
                fig_d = px.bar(div_df, x="Date", y="Dividends", color_discrete_sequence=["#30d158"])
                fig_d.update_layout(**PLOTLY_LAYOUT, height=250)
                st.plotly_chart(fig_d, use_container_width=True)

        # ── News ──
        news = research.get("news", [])
        if news:
            st.markdown("---")
            st.markdown("**Recent News**")
            for article in news:
                link = article.get("link", "")
                title = article.get("title", "Untitled")
                pub = article.get("publisher", "")
                if link:
                    st.markdown(f'- [{title}]({link}) — *{pub}*')
                else:
                    st.markdown(f'- {title} — *{pub}*')

        # ── External Links ──
        st.markdown("---")
        clean = research_sym.replace(".JO","")
        lc1, lc2, lc3, lc4 = st.columns(4)
        lc1.markdown(f"[Yahoo Finance](https://finance.yahoo.com/quote/{research_sym}/)")
        lc2.markdown(f"[TradingView](https://www.tradingview.com/symbols/JSE-{clean}/)")
        lc3.markdown(f"[ShareNet](https://www.sharenet.co.za/v3/q.php?scode={clean})")
        lc4.markdown(f"[Google Finance](https://www.google.com/finance/quote/{clean}:JSE)")


# ══════════════════════════════════════════════════════════════════════
#  PAGE: WATCHLIST
# ══════════════════════════════════════════════════════════════════════
elif st.session_state.active_page == "Watchlist":

    st.markdown('<div class="section-header">Watchlist</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Track your favourite stocks</div>', unsafe_allow_html=True)

    # Add stock
    add1, add2 = st.columns([3, 1])
    with add1:
        new_sym = st.selectbox("Add a stock", universe_df["Symbol"].tolist(), key="wl_add")
    with add2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Add", use_container_width=True, type="primary"):
            if new_sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_sym)
                _save_watchlist()
                st.rerun()

    st.markdown("---")

    if not st.session_state.watchlist:
        st.caption("Your watchlist is empty. Add stocks above.")
    else:
        data = st.session_state.screener_data
        for sym in st.session_state.watchlist:
            row = data[data["Symbol"] == sym] if data is not None else pd.DataFrame()
            name = sym
            price_str = "—"
            change_str = ""
            change_class = ""
            rec_html = ""
            upside_html = ""

            if len(row) > 0:
                r = row.iloc[0]
                name = r.get("Company", sym)
                price_str = f"R{r['Price']:,.2f}" if pd.notna(r.get("Price")) else "—"
                chg = r.get("Price_1D_Pct")
                if pd.notna(chg):
                    change_class = "up" if chg > 0 else "down"
                    change_str = f"{chg:+.2f}%"
                rec_html = _rec_badge(r.get("Analyst_Rec"))
                up = r.get("Upside_Pct")
                if pd.notna(up):
                    up_c = "#30d158" if up > 0 else "#ff453a"
                    upside_html = f'<span style="color:{up_c};font-weight:600;font-size:0.85rem;">{up:+.1f}% upside</span>'

            wc1, wc2, wc3 = st.columns([5, 1, 1])
            with wc1:
                st.markdown(f'''
                <div class="stock-row">
                    <div style="display:flex;align-items:center;gap:12px;">
                        {rec_html}
                        <div><div class="stock-name">{name}</div><div class="stock-symbol">{sym} {upside_html}</div></div>
                    </div>
                    <div><div class="stock-price">{price_str}</div><div class="stock-change {change_class}">{change_str}</div></div>
                </div>''', unsafe_allow_html=True)
            with wc2:
                if st.button("Research", key=f"wl_r_{sym}", use_container_width=True):
                    st.session_state.research_symbol = sym
                    st.session_state.active_page = "Research"
                    st.rerun()
            with wc3:
                if st.button("Remove", key=f"wl_del_{sym}", use_container_width=True):
                    st.session_state.watchlist.remove(sym)
                    _save_watchlist()
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  PAGE: PORTFOLIO
# ══════════════════════════════════════════════════════════════════════
elif st.session_state.active_page == "Portfolio":

    st.markdown('<div class="section-header">Portfolio Tracker</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Track your holdings and P&L</div>', unsafe_allow_html=True)

    # Add holding
    with st.expander("Add Holding", expanded=False):
        pa1, pa2, pa3, pa4 = st.columns([3, 1, 1, 1])
        with pa1:
            p_sym = st.selectbox("Stock", universe_df["Symbol"].tolist(), key="pf_sym")
        with pa2:
            p_shares = st.number_input("Shares", min_value=1, value=100, key="pf_shares")
        with pa3:
            p_price = st.number_input("Avg Price (R)", min_value=0.01, value=100.0, key="pf_price")
        with pa4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Add", type="primary", use_container_width=True, key="pf_add"):
                st.session_state.portfolio.append({"symbol": p_sym, "shares": p_shares, "avg_price": p_price})
                _save_portfolio()
                st.rerun()

    st.markdown("---")

    if not st.session_state.portfolio:
        st.caption("No holdings. Add your first position above.")
    else:
        data = st.session_state.screener_data
        total_cost = 0
        total_value = 0
        portfolio_rows = []

        for i, holding in enumerate(st.session_state.portfolio):
            sym = holding["symbol"]
            shares = holding["shares"]
            avg_p = holding["avg_price"]
            cost = shares * avg_p
            total_cost += cost

            current_p = None
            name = sym
            if data is not None:
                row = data[data["Symbol"] == sym]
                if len(row) > 0:
                    current_p = row.iloc[0].get("Price")
                    name = row.iloc[0].get("Company", sym)

            mkt_val = shares * current_p if current_p else 0
            total_value += mkt_val
            pnl = mkt_val - cost
            pnl_pct = (pnl / cost * 100) if cost > 0 else 0

            portfolio_rows.append({
                "idx": i, "symbol": sym, "name": name, "shares": shares,
                "avg_price": avg_p, "current_price": current_p,
                "cost": cost, "value": mkt_val, "pnl": pnl, "pnl_pct": pnl_pct,
            })

        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        # Summary
        ps1, ps2, ps3, ps4 = st.columns(4)
        ps1.metric("Total Cost", f"R{total_cost:,.2f}")
        ps2.metric("Market Value", f"R{total_value:,.2f}")
        pnl_color = "normal" if total_pnl >= 0 else "inverse"
        ps3.metric("Total P&L", f"R{total_pnl:,.2f}", delta=f"{total_pnl_pct:+.2f}%")
        ps4.metric("Holdings", f"{len(st.session_state.portfolio)}")

        st.markdown("---")

        # Portfolio allocation pie
        if total_value > 0:
            alloc_df = pd.DataFrame(portfolio_rows)
            fig_alloc = px.pie(alloc_df, values="value", names="symbol", hole=0.5,
                              color_discrete_sequence=px.colors.qualitative.Set2)
            fig_alloc.update_layout(**PLOTLY_LAYOUT, height=300, showlegend=True)
            st.plotly_chart(fig_alloc, use_container_width=True)

        # Holdings table
        for pr in portfolio_rows:
            pnl_c = "up" if pr["pnl"] >= 0 else "down"
            pnl_sign = "+" if pr["pnl"] >= 0 else ""
            curr_p = f"R{pr['current_price']:,.2f}" if pr["current_price"] else "N/A"

            hc1, hc2, hc3 = st.columns([5, 1, 1])
            with hc1:
                st.markdown(f'''
                <div class="stock-row">
                    <div>
                        <div class="stock-name">{pr["name"]}</div>
                        <div class="stock-symbol">{pr["symbol"]} | {pr["shares"]} shares @ R{pr["avg_price"]:,.2f}</div>
                    </div>
                    <div style="display:flex;gap:24px;align-items:center;">
                        <div style="text-align:right;">
                            <div class="stock-price">{curr_p}</div>
                            <div style="font-size:0.78rem;color:#86868b;">Value: R{pr["value"]:,.2f}</div>
                        </div>
                        <div style="text-align:right;min-width:90px;">
                            <div class="stock-change {pnl_c}">{pnl_sign}R{abs(pr["pnl"]):,.2f}</div>
                            <div class="stock-change {pnl_c}">{pnl_sign}{abs(pr["pnl_pct"]):.1f}%</div>
                        </div>
                    </div>
                </div>''', unsafe_allow_html=True)
            with hc2:
                if st.button("Research", key=f"pf_r_{pr['idx']}", use_container_width=True):
                    st.session_state.research_symbol = pr["symbol"]
                    st.session_state.active_page = "Research"
                    st.rerun()
            with hc3:
                if st.button("Remove", key=f"pf_del_{pr['idx']}", use_container_width=True):
                    st.session_state.portfolio.pop(pr["idx"])
                    _save_portfolio()
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  PAGE: SECTORS
# ══════════════════════════════════════════════════════════════════════
elif st.session_state.active_page == "Sectors":

    st.markdown('<div class="section-header">Sector Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Performance breakdown by JSE sector</div>', unsafe_allow_html=True)

    if st.session_state.screener_data is None:
        st.warning("No data loaded. Go to **Home** and load data first.")
    else:
        data = st.session_state.screener_data.copy()

        if "Sector" in data.columns:
            # Sector summary table
            sector_stats = data.groupby("Sector").agg(
                Stocks=("Symbol", "count"),
                Mkt_Cap_Bn=("Market_Cap_Bn", "sum"),
                Avg_PE=("PE_Trailing", "median"),
                Avg_DY=("Div_Yield_Pct", "median"),
                Avg_ROE=("ROE_Pct", "median"),
                Avg_1D=("Price_1D_Pct", "mean"),
                Avg_1M=("Price_1M_Pct", "mean"),
                Avg_6M=("Price_6M_Pct", "mean"),
                Avg_Upside=("Upside_Pct", "median"),
            ).round(2).sort_values("Mkt_Cap_Bn", ascending=False)

            st.dataframe(sector_stats, use_container_width=True, height=400)

            st.markdown("---")

            # Sector comparison charts
            ch1, ch2 = st.columns(2)

            with ch1:
                st.markdown("**Market Cap by Sector**")
                fig_mc = px.bar(sector_stats.reset_index(), x="Sector", y="Mkt_Cap_Bn",
                               color_discrete_sequence=["#0a84ff"])
                fig_mc.update_layout(**PLOTLY_LAYOUT, height=350)
                st.plotly_chart(fig_mc, use_container_width=True)

            with ch2:
                st.markdown("**Median Upside by Sector**")
                if "Avg_Upside" in sector_stats.columns:
                    colors = ["#30d158" if v > 0 else "#ff453a" for v in sector_stats["Avg_Upside"]]
                    fig_up = go.Figure(go.Bar(x=sector_stats.index, y=sector_stats["Avg_Upside"],
                                             marker_color=colors))
                    fig_up.update_layout(**PLOTLY_LAYOUT, height=350)
                    st.plotly_chart(fig_up, use_container_width=True)

            # Drill into sector
            st.markdown("---")
            selected_sector = st.selectbox("Drill into sector", sorted(data["Sector"].dropna().unique()))
            if selected_sector:
                sector_df = data[data["Sector"] == selected_sector].sort_values("Market_Cap_Bn", ascending=False)
                display = ["Symbol","Company","Price","Market_Cap_Bn","PE_Trailing","Div_Yield_Pct","ROE_Pct","Analyst_Rec","Upside_Pct","Price_6M_Pct"]
                avail = [c for c in display if c in sector_df.columns]
                st.dataframe(sector_df[avail], use_container_width=True, height=400)


# ══════════════════════════════════════════════════════════════════════
#  PAGE: NEWS
# ══════════════════════════════════════════════════════════════════════
elif st.session_state.active_page == "News":

    st.markdown('<div class="section-header">News & Events</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Latest news for your watchlist and top JSE stocks</div>', unsafe_allow_html=True)

    # Which stocks to fetch news for
    news_sources = st.session_state.watchlist[:5] if st.session_state.watchlist else ["NPN.JO","SBK.JO","MTN.JO","AGL.JO","SHP.JO"]
    news_pick = st.multiselect("Select stocks for news", universe_df["Symbol"].tolist(), default=news_sources, key="news_pick")

    if news_pick:
        for sym in news_pick:
            st.markdown(f"---")
            st.markdown(f'**{sym.replace(".JO","")}**')
            with st.spinner(f"Loading news for {sym}..."):
                try:
                    stock = __import__("yfinance").Ticker(sym)
                    news_items = stock.news or []
                except Exception:
                    news_items = []

            if news_items:
                for article in news_items[:5]:
                    title = article.get("title", "Untitled")
                    publisher = article.get("publisher", "")
                    link = article.get("link", "")
                    if link:
                        st.markdown(f'- [{title}]({link}) — *{publisher}*')
                    else:
                        st.markdown(f'- {title} — *{publisher}*')
            else:
                st.caption("No recent news available.")

    # ── Earnings Calendar placeholder ──
    st.markdown("---")
    st.markdown('<div class="section-header">Earnings Calendar</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Upcoming reporting dates for JSE-listed companies</div>', unsafe_allow_html=True)

    if st.session_state.screener_data is not None:
        st.caption("Earnings dates are sourced from Yahoo Finance when available. Not all JSE companies report earnings dates.")
        cal_stocks = st.session_state.watchlist if st.session_state.watchlist else ["NPN.JO","SBK.JO","CPI.JO"]
        earnings_data = []
        for sym in cal_stocks[:10]:
            try:
                stock = __import__("yfinance").Ticker(sym)
                cal = stock.calendar
                if cal is not None and not (isinstance(cal, pd.DataFrame) and cal.empty):
                    if isinstance(cal, dict):
                        earnings_date = cal.get("Earnings Date", [None])
                        if isinstance(earnings_date, list) and earnings_date:
                            earnings_data.append({"Symbol": sym, "Earnings Date": str(earnings_date[0])})
                    elif isinstance(cal, pd.DataFrame):
                        earnings_data.append({"Symbol": sym, "Earnings Date": str(cal.iloc[0, 0]) if len(cal) > 0 else "N/A"})
            except Exception:
                pass
        if earnings_data:
            st.dataframe(pd.DataFrame(earnings_data), use_container_width=True)
        else:
            st.caption("No upcoming earnings dates found for tracked stocks.")
    else:
        st.caption("Load data from the Home page to see earnings calendar.")


# ──────────────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f'<div style="text-align:center;color:#6e6e73;font-size:0.75rem;padding:8px 0;">JSE Research Terminal | Data via Yahoo Finance | {datetime.now().strftime("%Y")}</div>', unsafe_allow_html=True)
