"""
JSE Equity Screener — Streamlit Application
=============================================
A professional-grade listed equity screening tool for the
Johannesburg Stock Exchange (JSE).

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io

from jse_universe import get_universe_df, get_sectors, load_custom_universe
from data_fetcher import fetch_all_data, fetch_price_history, get_company_info, get_stock_research
from screener_engine import (
    FILTER_GROUPS,
    STRATEGIES,
    apply_filters,
    apply_strategy,
    compute_composite_score,
    get_all_filter_columns,
)

# ──────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JSE Equity Screener",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Global tweaks */
    .block-container { padding-top: 1rem; }
    .stMetric { background: #0e1117; border-radius: 8px; padding: 12px; border: 1px solid #262730; }

    /* Header */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid #1a3a5c;
    }
    .main-header h1 { color: #e94560; margin: 0; font-size: 2rem; }
    .main-header p { color: #a8b2d1; margin: 0.3rem 0 0 0; font-size: 0.95rem; }

    /* Positive/negative colors */
    .positive { color: #00d26a; font-weight: 600; }
    .negative { color: #f44336; font-weight: 600; }

    /* Table styling */
    .dataframe th { background-color: #1a1a2e !important; color: #e94560 !important; }

    /* Strategy cards */
    .strategy-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .strategy-card h4 { color: #e94560; margin: 0 0 0.3rem 0; }
    .strategy-card p { color: #8b949e; margin: 0; font-size: 0.85rem; }

    /* Sidebar section headers */
    .sidebar-section {
        color: #e94560;
        font-weight: 700;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #e94560;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────────────────────────────
if "screener_data" not in st.session_state:
    st.session_state.screener_data = None
if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = None
if "last_fetch_time" not in st.session_state:
    st.session_state.last_fetch_time = None
if "research_view" not in st.session_state:
    st.session_state.research_view = None  # Symbol to deep-dive into


# ──────────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>JSE Equity Screener</h1>
    <p>Live screening of Johannesburg Stock Exchange listed equities &bull; Powered by Yahoo Finance</p>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Configuration")

    # ── Universe Selection ──
    st.markdown('<div class="sidebar-section">Universe</div>', unsafe_allow_html=True)
    universe_option = st.radio(
        "Stock Universe",
        ["Full JSE", "Top 40 / Large Cap", "Custom CSV"],
        label_visibility="collapsed",
    )

    universe_df = get_universe_df()

    if universe_option == "Top 40 / Large Cap":
        # Select well-known large caps
        top40_symbols = [
            "NPN.JO", "PRX.JO", "CFR.JO", "BTI.JO", "AGL.JO", "BHP.JO",
            "GLN.JO", "SOL.JO", "MTN.JO", "SHP.JO", "FSR.JO", "SBK.JO",
            "ABG.JO", "NED.JO", "CPI.JO", "SLM.JO", "DSY.JO", "OMU.JO",
            "AMS.JO", "IMP.JO", "SSW.JO", "ANG.JO", "GFI.JO", "KIO.JO",
            "EXX.JO", "MNP.JO", "VOD.JO", "CLS.JO", "WHL.JO", "BID.JO",
            "BVT.JO", "MRP.JO", "TFG.JO", "REM.JO", "APN.JO", "NPH.JO",
            "MCG.JO", "ARI.JO", "N91.JO", "INL.JO",
        ]
        universe_df = universe_df[universe_df["Symbol"].isin(top40_symbols)]
    elif universe_option == "Custom CSV":
        uploaded_file = st.file_uploader("Upload ticker CSV", type=["csv"])
        if uploaded_file:
            try:
                universe_df = load_custom_universe(uploaded_file)
                st.success(f"Loaded {len(universe_df)} tickers from CSV")
            except Exception as e:
                st.error(f"CSV Error: {e}")

    st.caption(f"Universe: **{len(universe_df)}** shares")

    # ── Sector Filter ──
    st.markdown('<div class="sidebar-section">Sectors</div>', unsafe_allow_html=True)
    available_sectors = sorted(universe_df["Sector"].unique())
    selected_sectors = st.multiselect(
        "Filter by sector",
        available_sectors,
        default=available_sectors,
        label_visibility="collapsed",
    )

    # ── Strategy Presets ──
    st.markdown('<div class="sidebar-section">Strategy Presets</div>', unsafe_allow_html=True)
    strategy_names = ["Custom (Manual Filters)"] + list(STRATEGIES.keys())
    selected_strategy = st.selectbox(
        "Select a strategy",
        strategy_names,
        label_visibility="collapsed",
    )

    if selected_strategy != "Custom (Manual Filters)":
        strat = STRATEGIES[selected_strategy]
        st.markdown(f"""
        <div class="strategy-card">
            <h4>{selected_strategy}</h4>
            <p>{strat['description']}</p>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Filters below are overridden by the strategy preset.")

    # ── Manual Filters ──
    st.markdown('<div class="sidebar-section">Screening Filters</div>', unsafe_allow_html=True)

    manual_filters = {}
    for group_name, group_filters in FILTER_GROUPS.items():
        with st.expander(group_name, expanded=False):
            for display_name, col_name in group_filters.items():
                col1, col2 = st.columns(2)
                with col1:
                    min_val = st.number_input(
                        f"Min {display_name}",
                        value=None,
                        key=f"min_{col_name}",
                        label_visibility="collapsed",
                        placeholder=f"Min",
                    )
                with col2:
                    max_val = st.number_input(
                        f"Max {display_name}",
                        value=None,
                        key=f"max_{col_name}",
                        label_visibility="collapsed",
                        placeholder=f"Max",
                    )
                if min_val is not None or max_val is not None:
                    manual_filters[col_name] = (min_val, max_val)

    # ── Data Controls ──
    st.markdown('<div class="sidebar-section">Data Controls</div>', unsafe_allow_html=True)
    max_workers = st.slider("Parallel threads", 1, 10, 5, help="Higher = faster but more API load")
    use_cache = st.checkbox("Use cache (15 min)", value=True)

    # Fetch Button
    st.markdown("---")
    fetch_btn = st.button("🔄 Fetch / Refresh Data", use_container_width=True, type="primary")


# ──────────────────────────────────────────────────────────────────────
# DATA FETCHING
# ──────────────────────────────────────────────────────────────────────
if fetch_btn:
    # Filter tickers by selected sectors
    filtered_universe = universe_df[universe_df["Sector"].isin(selected_sectors)]
    tickers = filtered_universe["Symbol"].tolist()

    if len(tickers) == 0:
        st.error("No tickers selected. Please adjust your sector filters.")
    else:
        progress_bar = st.progress(0, text="Fetching data from Yahoo Finance...")
        status_text = st.empty()

        def update_progress(current, total):
            pct = current / total
            progress_bar.progress(pct, text=f"Fetching data... {current}/{total} tickers")

        with st.spinner("Pulling live data..."):
            data = fetch_all_data(
                tickers,
                progress_callback=update_progress,
                max_workers=max_workers,
                use_cache=use_cache,
            )

        progress_bar.empty()
        status_text.empty()

        if data.empty:
            st.warning("No data returned. Yahoo Finance may be rate-limiting. Try again in a few minutes.")
        else:
            # Merge with universe metadata
            data = data.merge(
                universe_df[["Symbol", "Company", "Sector"]],
                on="Symbol",
                how="left",
                suffixes=("", "_universe"),
            )
            # Use universe sector if yfinance didn't return one
            if "Sector_universe" in data.columns:
                data["Sector"] = data["Sector"].fillna(data["Sector_universe"])
                data.drop(columns=["Sector_universe"], inplace=True, errors="ignore")
            if "Company_universe" in data.columns:
                data["Company"] = data["Company"].fillna(data["Company_universe"])
                data.drop(columns=["Company_universe"], inplace=True, errors="ignore")

            st.session_state.screener_data = data
            st.session_state.last_fetch_time = datetime.now()
            st.success(f"✅ Loaded {len(data)} stocks | {datetime.now().strftime('%H:%M:%S')}")


# ──────────────────────────────────────────────────────────────────────
# MAIN CONTENT
# ──────────────────────────────────────────────────────────────────────
if st.session_state.screener_data is not None:
    data = st.session_state.screener_data.copy()

    # ── Apply Strategy or Manual Filters ──
    if selected_strategy != "Custom (Manual Filters)":
        filtered = apply_strategy(data, selected_strategy)
        st.info(f"Strategy: **{selected_strategy}** — {STRATEGIES[selected_strategy]['description']}")
    else:
        filtered = apply_filters(data, manual_filters, selected_sectors)

    # ── TABS ──
    tab_results, tab_charts, tab_compare, tab_research, tab_detail, tab_export = st.tabs([
        "📋 Screening Results",
        "📈 Market Charts",
        "⚖️ Compare Stocks",
        "🔬 Stock Research",
        "🔍 Quick Detail",
        "💾 Export",
    ])

    # ────────────────────────────────────
    # TAB 1: SCREENING RESULTS
    # ────────────────────────────────────
    with tab_results:
        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Stocks Found", len(filtered))
        col2.metric("Universe Size", len(data))
        col3.metric("Pass Rate", f"{len(filtered)/max(len(data),1)*100:.1f}%")
        if "Div_Yield_Pct" in filtered.columns and len(filtered) > 0:
            avg_yield = filtered["Div_Yield_Pct"].mean()
            col4.metric("Avg Div Yield", f"{avg_yield:.2f}%" if pd.notna(avg_yield) else "N/A")
        if "Market_Cap_Bn" in filtered.columns and len(filtered) > 0:
            total_mcap = filtered["Market_Cap_Bn"].sum()
            col5.metric("Total Mkt Cap", f"R{total_mcap:,.0f}B" if pd.notna(total_mcap) else "N/A")

        # Sort options
        st.markdown("---")
        sort_col1, sort_col2 = st.columns([3, 1])
        with sort_col1:
            sortable_cols = [c for c in filtered.columns if filtered[c].dtype in ["float64", "int64", "float32"]]
            sort_by = st.selectbox("Sort by", ["Market_Cap_Bn"] + sortable_cols, key="sort_main")
        with sort_col2:
            sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True, key="sort_order")

        if sort_by in filtered.columns:
            filtered = filtered.sort_values(sort_by, ascending=(sort_order == "Ascending"), na_position="last")

        # Display columns selector — now includes analyst + target columns
        default_display = ["Symbol", "Company", "Sector", "Price",
                          "Analyst_Rec", "Target_Mean", "Upside_Pct",
                          "Market_Cap_Bn", "PE_Trailing", "Div_Yield_Pct",
                          "ROE_Pct", "Price_6M_Pct", "RSI_14"]
        available_display = [c for c in default_display if c in filtered.columns]
        all_cols = filtered.columns.tolist()

        selected_columns = st.multiselect(
            "Display columns",
            all_cols,
            default=available_display,
            key="display_cols",
        )

        if selected_columns:
            display_df = filtered[selected_columns].copy()
        else:
            display_df = filtered.copy()

        # Format and display the main table
        st.dataframe(
            display_df,
            use_container_width=True,
            height=600,
            column_config={
                "Price": st.column_config.NumberColumn(format="R %.2f"),
                "Market_Cap_Bn": st.column_config.NumberColumn("Mkt Cap (Bn)", format="R %.2f"),
                "PE_Trailing": st.column_config.NumberColumn("P/E", format="%.1f"),
                "PE_Forward": st.column_config.NumberColumn("Fwd P/E", format="%.1f"),
                "PB_Ratio": st.column_config.NumberColumn("P/B", format="%.2f"),
                "EV_EBITDA": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
                "Div_Yield_Pct": st.column_config.NumberColumn("Div Yield %", format="%.2f%%"),
                "ROE_Pct": st.column_config.NumberColumn("ROE %", format="%.1f%%"),
                "ROA_Pct": st.column_config.NumberColumn("ROA %", format="%.1f%%"),
                "Profit_Margin_Pct": st.column_config.NumberColumn("Margin %", format="%.1f%%"),
                "Price_1D_Pct": st.column_config.NumberColumn("1D %", format="%.2f%%"),
                "Price_5D_Pct": st.column_config.NumberColumn("5D %", format="%.2f%%"),
                "Price_1M_Pct": st.column_config.NumberColumn("1M %", format="%.2f%%"),
                "Price_3M_Pct": st.column_config.NumberColumn("3M %", format="%.2f%%"),
                "Price_6M_Pct": st.column_config.NumberColumn("6M %", format="%.2f%%"),
                "Price_1Y_Pct": st.column_config.NumberColumn("1Y %", format="%.2f%%"),
                "RSI_14": st.column_config.NumberColumn("RSI", format="%.1f"),
                "Volatility_Ann_Pct": st.column_config.NumberColumn("Vol %", format="%.1f%%"),
                "Debt_to_Equity": st.column_config.NumberColumn("D/E", format="%.1f"),
                "Payout_Ratio_Pct": st.column_config.NumberColumn("Payout %", format="%.1f%%"),
                "Avg_Vol_20D": st.column_config.NumberColumn("Avg Vol", format="%,.0f"),
                "Beta": st.column_config.NumberColumn("Beta", format="%.2f"),
                "Analyst_Rec": st.column_config.TextColumn("Analyst Rec"),
                "Analyst_Score": st.column_config.NumberColumn("Score (1-5)", format="%.1f"),
                "Num_Analysts": st.column_config.NumberColumn("# Analysts", format="%d"),
                "Target_Mean": st.column_config.NumberColumn("Target Price", format="R %.2f"),
                "Target_High": st.column_config.NumberColumn("Target High", format="R %.2f"),
                "Target_Low": st.column_config.NumberColumn("Target Low", format="R %.2f"),
                "Upside_Pct": st.column_config.NumberColumn("Upside %", format="%.1f%%"),
            },
        )

        # ── CLICKABLE STOCK BUTTONS — select a stock for deep-dive research ──
        st.markdown("---")
        st.markdown("#### Click a stock to open deep-dive research")
        button_cols = st.columns(8)
        symbols_list = filtered["Symbol"].tolist()
        for idx, sym in enumerate(symbols_list[:40]):  # Show up to 40 buttons
            col_idx = idx % 8
            company_row = filtered[filtered["Symbol"] == sym]
            label = sym.replace(".JO", "")
            upside = ""
            if len(company_row) > 0 and pd.notna(company_row.iloc[0].get("Upside_Pct")):
                up_val = company_row.iloc[0]["Upside_Pct"]
                upside = f" ({up_val:+.0f}%)"
            if button_cols[col_idx].button(f"{label}{upside}", key=f"btn_{sym}"):
                st.session_state.research_view = sym

    # ────────────────────────────────────
    # TAB 2: MARKET CHARTS
    # ────────────────────────────────────
    with tab_charts:
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader("Sector Distribution")
            if "Sector" in filtered.columns and len(filtered) > 0:
                sector_counts = filtered["Sector"].value_counts()
                fig_sector = px.pie(
                    values=sector_counts.values,
                    names=sector_counts.index,
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig_sector.update_layout(
                    template="plotly_dark",
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20),
                )
                st.plotly_chart(fig_sector, use_container_width=True)

        with chart_col2:
            st.subheader("Valuation Scatter")
            if all(c in filtered.columns for c in ["PE_Trailing", "Div_Yield_Pct"]):
                scatter_df = filtered.dropna(subset=["PE_Trailing", "Div_Yield_Pct"])
                if len(scatter_df) > 0:
                    fig_scatter = px.scatter(
                        scatter_df,
                        x="PE_Trailing",
                        y="Div_Yield_Pct",
                        size="Market_Cap_Bn" if "Market_Cap_Bn" in scatter_df.columns else None,
                        color="Sector" if "Sector" in scatter_df.columns else None,
                        hover_name="Symbol",
                        labels={"PE_Trailing": "P/E Ratio", "Div_Yield_Pct": "Dividend Yield (%)"},
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    fig_scatter.update_layout(
                        template="plotly_dark",
                        height=400,
                        margin=dict(t=20, b=20, l=20, r=20),
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)

        # Histogram
        st.subheader("Distribution Analysis")
        hist_col = st.selectbox(
            "Select metric",
            [c for c in filtered.columns if filtered[c].dtype in ["float64", "int64"]],
            key="hist_metric",
        )
        if hist_col:
            fig_hist = px.histogram(
                filtered.dropna(subset=[hist_col]),
                x=hist_col,
                nbins=30,
                color_discrete_sequence=["#e94560"],
            )
            fig_hist.update_layout(
                template="plotly_dark",
                height=350,
                margin=dict(t=20, b=40, l=40, r=20),
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        # Heatmap of returns
        st.subheader("Performance Heatmap")
        return_cols = ["Price_1D_Pct", "Price_5D_Pct", "Price_1M_Pct",
                       "Price_3M_Pct", "Price_6M_Pct", "Price_1Y_Pct"]
        available_return_cols = [c for c in return_cols if c in filtered.columns]
        if available_return_cols and len(filtered) > 0:
            heatmap_df = filtered.set_index("Symbol")[available_return_cols].dropna(how="all").head(30)
            if len(heatmap_df) > 0:
                fig_heat = go.Figure(data=go.Heatmap(
                    z=heatmap_df.values,
                    x=[c.replace("Price_", "").replace("_Pct", "") for c in heatmap_df.columns],
                    y=heatmap_df.index,
                    colorscale="RdYlGn",
                    zmid=0,
                    text=np.round(heatmap_df.values, 1),
                    texttemplate="%{text}%",
                    textfont={"size": 10},
                ))
                fig_heat.update_layout(
                    template="plotly_dark",
                    height=max(400, len(heatmap_df) * 22),
                    margin=dict(t=20, b=20, l=100, r=20),
                )
                st.plotly_chart(fig_heat, use_container_width=True)

    # ────────────────────────────────────
    # TAB 3: COMPARE STOCKS
    # ────────────────────────────────────
    with tab_compare:
        st.subheader("Side-by-Side Comparison")
        compare_symbols = st.multiselect(
            "Select stocks to compare (max 5)",
            filtered["Symbol"].tolist(),
            max_selections=5,
            key="compare_stocks",
        )

        if compare_symbols:
            compare_df = filtered[filtered["Symbol"].isin(compare_symbols)]
            compare_metrics = ["Price", "Market_Cap_Bn", "PE_Trailing", "PB_Ratio",
                             "Div_Yield_Pct", "ROE_Pct", "Debt_to_Equity",
                             "Price_1M_Pct", "Price_6M_Pct", "RSI_14", "Beta"]
            available_metrics = [m for m in compare_metrics if m in compare_df.columns]

            comparison = compare_df.set_index("Symbol")[available_metrics].T
            comparison.index.name = "Metric"
            st.dataframe(comparison, use_container_width=True)

            # Radar chart
            st.subheader("Radar Comparison")
            radar_metrics = ["PE_Trailing", "Div_Yield_Pct", "ROE_Pct",
                           "Price_6M_Pct", "RSI_14"]
            available_radar = [m for m in radar_metrics if m in compare_df.columns]

            if available_radar and len(compare_symbols) > 0:
                fig_radar = go.Figure()
                for sym in compare_symbols:
                    row = compare_df[compare_df["Symbol"] == sym]
                    if len(row) > 0:
                        values = [float(row[m].iloc[0]) if pd.notna(row[m].iloc[0]) else 0 for m in available_radar]
                        # Normalize to 0-100 for display
                        fig_radar.add_trace(go.Scatterpolar(
                            r=values,
                            theta=available_radar,
                            fill='toself',
                            name=sym,
                        ))
                fig_radar.update_layout(
                    template="plotly_dark",
                    polar=dict(radialaxis=dict(visible=True)),
                    height=500,
                    margin=dict(t=40, b=40, l=80, r=80),
                )
                st.plotly_chart(fig_radar, use_container_width=True)

            # Price history comparison
            st.subheader("Price History Comparison")
            period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=3, key="compare_period")
            fig_price = go.Figure()
            for sym in compare_symbols:
                hist = fetch_price_history(sym, period=period)
                if not hist.empty:
                    # Normalize to 100 at start
                    normalized = hist["Close"] / hist["Close"].iloc[0] * 100
                    fig_price.add_trace(go.Scatter(
                        x=hist.index, y=normalized,
                        mode="lines", name=sym,
                    ))
            fig_price.update_layout(
                template="plotly_dark",
                yaxis_title="Normalized Price (100 = Start)",
                height=450,
                margin=dict(t=20, b=40, l=60, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_price, use_container_width=True)

    # ────────────────────────────────────
    # TAB 4: STOCK RESEARCH (DEEP DIVE)
    # ────────────────────────────────────
    with tab_research:
        # Stock selector — auto-select from button click or manual pick
        research_options = filtered["Symbol"].tolist()
        default_idx = 0
        if st.session_state.research_view and st.session_state.research_view in research_options:
            default_idx = research_options.index(st.session_state.research_view)

        research_symbol = st.selectbox(
            "Select a stock for in-depth research",
            research_options,
            index=default_idx,
            key="research_stock_select",
        )

        if research_symbol:
            with st.spinner(f"Loading research data for {research_symbol}..."):
                research = get_stock_research(research_symbol)

            ov = research.get("overview", {})
            an = research.get("analyst", {})

            # ── HEADER ──
            st.markdown(f"## {ov.get('name', research_symbol)}")
            st.caption(
                f"{ov.get('sector', 'N/A')} | {ov.get('industry', 'N/A')} | "
                f"{ov.get('currency', 'ZAR')} | "
                f"{'[Website](' + ov['website'] + ')' if ov.get('website') else 'No website'}"
            )
            if ov.get("employees"):
                st.caption(f"Employees: {ov['employees']:,}")

            if ov.get("description"):
                with st.expander("Company Description", expanded=False):
                    st.write(ov["description"])

            st.markdown("---")

            # ── ANALYST CONSENSUS SECTION ──
            st.markdown("### Analyst Consensus")

            a1, a2, a3, a4, a5 = st.columns(5)

            # Recommendation badge with color
            rec = an.get("recommendation", "N/A")
            rec_colors = {
                "Strong Buy": "#00d26a", "Buy": "#4caf50", "Overweight": "#8bc34a",
                "Hold": "#ffc107", "Neutral": "#ffc107",
                "Underweight": "#ff9800", "Sell": "#f44336", "Strong Sell": "#d32f2f",
            }
            rec_color = rec_colors.get(rec, "#888")
            a1.markdown(f"""
            <div style="text-align:center; padding:12px; border-radius:8px;
                        background:{rec_color}22; border:2px solid {rec_color};">
                <div style="font-size:0.75rem; color:#aaa;">RECOMMENDATION</div>
                <div style="font-size:1.4rem; font-weight:700; color:{rec_color};">{rec}</div>
            </div>
            """, unsafe_allow_html=True)

            a2.metric("Analyst Score", f"{an.get('mean_score', 'N/A')}" if an.get('mean_score') else "N/A",
                      help="1 = Strong Buy, 5 = Strong Sell")
            a3.metric("# Analysts", f"{an.get('num_analysts', 'N/A')}")

            current_p = an.get("current_price")
            target_m = an.get("target_mean")
            a4.metric("Current Price", f"R{current_p:,.2f}" if current_p else "N/A")
            a5.metric("Mean Target", f"R{target_m:,.2f}" if target_m else "N/A")

            # ── TARGET PRICE VISUAL (gauge-style bar) ──
            if all(an.get(k) for k in ["target_low", "target_mean", "target_high", "current_price"]):
                st.markdown("#### Price vs Analyst Target Range")
                t_low = an["target_low"]
                t_high = an["target_high"]
                t_mean = an["target_mean"]
                t_median = an.get("target_median", t_mean)
                c_price = an["current_price"]
                upside = an.get("upside_pct")

                # Upside/downside display
                if upside is not None:
                    upside_color = "#00d26a" if upside > 0 else "#f44336"
                    upside_label = "UPSIDE" if upside > 0 else "DOWNSIDE"
                    st.markdown(f"""
                    <div style="text-align:center; margin:10px 0 20px 0;">
                        <span style="font-size:2rem; font-weight:700; color:{upside_color};">
                            {upside:+.1f}% {upside_label}
                        </span>
                        <span style="color:#888; font-size:0.9rem;"> to mean analyst target</span>
                    </div>
                    """, unsafe_allow_html=True)

                # Visual target range bar
                bar_min = min(t_low, c_price) * 0.95
                bar_max = max(t_high, c_price) * 1.05
                bar_range = bar_max - bar_min

                fig_target = go.Figure()

                # Target range band
                fig_target.add_trace(go.Bar(
                    x=[t_high - t_low], y=["Target"],
                    base=[t_low], orientation="h",
                    marker=dict(color="rgba(100, 149, 237, 0.3)"),
                    name="Target Range",
                    hovertemplate=f"Low: R{t_low:,.2f}<br>High: R{t_high:,.2f}<extra></extra>",
                ))

                # Current price marker
                fig_target.add_vline(x=c_price, line=dict(color="#e94560", width=3, dash="solid"),
                                     annotation_text=f"Current: R{c_price:,.2f}",
                                     annotation_position="top")
                # Mean target marker
                fig_target.add_vline(x=t_mean, line=dict(color="#00d26a", width=3, dash="dash"),
                                     annotation_text=f"Target: R{t_mean:,.2f}",
                                     annotation_position="bottom")

                fig_target.update_layout(
                    template="plotly_dark",
                    height=150,
                    showlegend=False,
                    xaxis=dict(range=[bar_min, bar_max], title="Price (ZAR)"),
                    yaxis=dict(visible=False),
                    margin=dict(t=40, b=40, l=20, r=20),
                )
                st.plotly_chart(fig_target, use_container_width=True)

                # Target breakdown table
                tc1, tc2, tc3, tc4 = st.columns(4)
                tc1.metric("Target Low", f"R{t_low:,.2f}")
                tc2.metric("Target Mean", f"R{t_mean:,.2f}")
                tc3.metric("Target Median", f"R{t_median:,.2f}")
                tc4.metric("Target High", f"R{t_high:,.2f}")

            st.markdown("---")

            # ── KEY METRICS FROM SCREENER DATA ──
            st.markdown("### Key Metrics")
            row = filtered[filtered["Symbol"] == research_symbol]
            if len(row) > 0:
                r = row.iloc[0]
                km1, km2, km3, km4, km5, km6 = st.columns(6)
                km1.metric("P/E", f"{r.get('PE_Trailing', 'N/A')}" if pd.notna(r.get('PE_Trailing')) else "N/A")
                km2.metric("P/B", f"{r.get('PB_Ratio', 'N/A')}" if pd.notna(r.get('PB_Ratio')) else "N/A")
                km3.metric("Div Yield", f"{r.get('Div_Yield_Pct', 0):.2f}%" if pd.notna(r.get('Div_Yield_Pct')) else "N/A")
                km4.metric("ROE", f"{r.get('ROE_Pct', 0):.1f}%" if pd.notna(r.get('ROE_Pct')) else "N/A")
                km5.metric("D/E", f"{r.get('Debt_to_Equity', 'N/A')}" if pd.notna(r.get('Debt_to_Equity')) else "N/A")
                km6.metric("Beta", f"{r.get('Beta', 'N/A')}" if pd.notna(r.get('Beta')) else "N/A")

                km7, km8, km9, km10, km11, km12 = st.columns(6)
                km7.metric("Mkt Cap", f"R{r.get('Market_Cap_Bn', 0):,.2f}B" if pd.notna(r.get('Market_Cap_Bn')) else "N/A")
                km8.metric("EV/EBITDA", f"{r.get('EV_EBITDA', 'N/A')}" if pd.notna(r.get('EV_EBITDA')) else "N/A")
                km9.metric("RSI (14)", f"{r.get('RSI_14', 'N/A')}" if pd.notna(r.get('RSI_14')) else "N/A")
                km10.metric("1M Return", f"{r.get('Price_1M_Pct', 0):+.1f}%" if pd.notna(r.get('Price_1M_Pct')) else "N/A")
                km11.metric("6M Return", f"{r.get('Price_6M_Pct', 0):+.1f}%" if pd.notna(r.get('Price_6M_Pct')) else "N/A")
                km12.metric("1Y Return", f"{r.get('Price_1Y_Pct', 0):+.1f}%" if pd.notna(r.get('Price_1Y_Pct')) else "N/A")

            st.markdown("---")

            # ── PRICE CHART WITH TARGET OVERLAY ──
            st.markdown("### Price Chart")
            rp = st.selectbox("Period", ["3mo", "6mo", "1y", "2y", "5y"], index=2, key="research_period")
            hist = fetch_price_history(research_symbol, period=rp)
            if not hist.empty:
                fig_pc = go.Figure()
                fig_pc.add_trace(go.Candlestick(
                    x=hist.index, open=hist["Open"], high=hist["High"],
                    low=hist["Low"], close=hist["Close"], name="Price",
                ))
                if len(hist) >= 20:
                    fig_pc.add_trace(go.Scatter(x=hist.index, y=hist["Close"].rolling(20).mean(),
                                                mode="lines", name="SMA 20",
                                                line=dict(color="#ffa500", width=1)))
                if len(hist) >= 50:
                    fig_pc.add_trace(go.Scatter(x=hist.index, y=hist["Close"].rolling(50).mean(),
                                                mode="lines", name="SMA 50",
                                                line=dict(color="#00bfff", width=1)))
                # Overlay analyst target as horizontal line
                if an.get("target_mean"):
                    fig_pc.add_hline(y=an["target_mean"], line=dict(color="#00d26a", width=2, dash="dash"),
                                     annotation_text=f"Target: R{an['target_mean']:,.2f}",
                                     annotation_position="top left")
                if an.get("target_low"):
                    fig_pc.add_hline(y=an["target_low"], line=dict(color="#888", width=1, dash="dot"),
                                     annotation_text="Target Low")
                if an.get("target_high"):
                    fig_pc.add_hline(y=an["target_high"], line=dict(color="#888", width=1, dash="dot"),
                                     annotation_text="Target High")

                fig_pc.update_layout(template="plotly_dark", height=500,
                                     xaxis_rangeslider_visible=False,
                                     margin=dict(t=20, b=40, l=60, r=20))
                st.plotly_chart(fig_pc, use_container_width=True)

                # Volume
                fig_v = px.bar(x=hist.index, y=hist["Volume"],
                              labels={"x": "Date", "y": "Volume"},
                              color_discrete_sequence=["#4a6fa5"])
                fig_v.update_layout(template="plotly_dark", height=180,
                                    margin=dict(t=10, b=30, l=60, r=20))
                st.plotly_chart(fig_v, use_container_width=True)

            st.markdown("---")

            # ── FINANCIAL STATEMENTS ──
            st.markdown("### Financial Statements")
            fin_tab1, fin_tab2, fin_tab3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])

            with fin_tab1:
                inc_data = research.get("income_statement", {})
                if inc_data:
                    inc_df = pd.DataFrame(inc_data)
                    inc_df.index.name = "Item"
                    # Format large numbers
                    st.dataframe(inc_df.style.format(lambda x: f"R{x:,.0f}" if isinstance(x, (int, float)) and pd.notna(x) else ""),
                                use_container_width=True, height=400)
                else:
                    st.info("Income statement data not available for this stock.")

            with fin_tab2:
                bs_data = research.get("balance_sheet", {})
                if bs_data:
                    bs_df = pd.DataFrame(bs_data)
                    bs_df.index.name = "Item"
                    st.dataframe(bs_df.style.format(lambda x: f"R{x:,.0f}" if isinstance(x, (int, float)) and pd.notna(x) else ""),
                                use_container_width=True, height=400)
                else:
                    st.info("Balance sheet data not available for this stock.")

            with fin_tab3:
                cf_data = research.get("cash_flow", {})
                if cf_data:
                    cf_df = pd.DataFrame(cf_data)
                    cf_df.index.name = "Item"
                    st.dataframe(cf_df.style.format(lambda x: f"R{x:,.0f}" if isinstance(x, (int, float)) and pd.notna(x) else ""),
                                use_container_width=True, height=400)
                else:
                    st.info("Cash flow data not available for this stock.")

            st.markdown("---")

            # ── INSTITUTIONAL HOLDERS ──
            holders = research.get("institutional_holders", [])
            if holders:
                st.markdown("### Top Institutional Holders")
                holders_df = pd.DataFrame(holders)
                st.dataframe(holders_df, use_container_width=True)

            # ── DIVIDEND HISTORY ──
            divs = research.get("dividends", [])
            if divs:
                st.markdown("### Dividend History")
                div_df = pd.DataFrame(divs)
                if "Date" in div_df.columns:
                    fig_div = px.bar(div_df, x="Date", y="Dividends",
                                    color_discrete_sequence=["#00d26a"])
                    fig_div.update_layout(template="plotly_dark", height=300,
                                         margin=dict(t=20, b=40, l=60, r=20))
                    st.plotly_chart(fig_div, use_container_width=True)

            # ── NEWS ──
            news = research.get("news", [])
            if news:
                st.markdown("### Recent News")
                for article in news:
                    title = article.get("title", "Untitled")
                    publisher = article.get("publisher", "")
                    link = article.get("link", "")
                    if link:
                        st.markdown(f"- **[{title}]({link})** — *{publisher}*")
                    else:
                        st.markdown(f"- **{title}** — *{publisher}*")

            # ── QUICK LINKS ──
            st.markdown("---")
            st.markdown("### External Research Links")
            clean_sym = research_symbol.replace(".JO", "")
            lc1, lc2, lc3, lc4 = st.columns(4)
            lc1.markdown(f"[Yahoo Finance](https://finance.yahoo.com/quote/{research_symbol}/)")
            lc2.markdown(f"[TradingView](https://www.tradingview.com/symbols/JSE-{clean_sym}/)")
            lc3.markdown(f"[ShareNet](https://www.sharenet.co.za/v3/q.php?scode={clean_sym})")
            lc4.markdown(f"[Google Finance](https://www.google.com/finance/quote/{clean_sym}:JSE)")

    # ────────────────────────────────────
    # TAB 5: QUICK DETAIL (original)
    # ────────────────────────────────────
    with tab_detail:
        selected_detail = st.selectbox(
            "Select a stock for detailed view",
            filtered["Symbol"].tolist(),
            key="detail_stock",
        )

        if selected_detail:
            info = get_company_info(selected_detail)
            row = filtered[filtered["Symbol"] == selected_detail]

            st.markdown(f"### {info.get('Name', selected_detail)}")
            st.caption(f"{info.get('Sector', 'N/A')} | {info.get('Industry', 'N/A')} | {info.get('Currency', 'ZAR')}")

            if info.get("Description") and info["Description"] != "No description available.":
                with st.expander("Company Description", expanded=False):
                    st.write(info["Description"])

            # Key metrics grid
            if len(row) > 0:
                r = row.iloc[0]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Price", f"R{r.get('Price', 0):,.2f}")
                m2.metric("Market Cap", f"R{r.get('Market_Cap_Bn', 0):,.2f}B")
                m3.metric("P/E Ratio", f"{r.get('PE_Trailing', 'N/A')}")
                m4.metric("Div Yield", f"{r.get('Div_Yield_Pct', 'N/A')}%" if pd.notna(r.get('Div_Yield_Pct')) else "N/A")

                m5, m6, m7, m8 = st.columns(4)
                m5.metric("ROE", f"{r.get('ROE_Pct', 'N/A')}%" if pd.notna(r.get('ROE_Pct')) else "N/A")
                m6.metric("D/E Ratio", f"{r.get('Debt_to_Equity', 'N/A')}" if pd.notna(r.get('Debt_to_Equity')) else "N/A")
                m7.metric("RSI (14)", f"{r.get('RSI_14', 'N/A')}" if pd.notna(r.get('RSI_14')) else "N/A")
                m8.metric("Beta", f"{r.get('Beta', 'N/A')}" if pd.notna(r.get('Beta')) else "N/A")

            # Price chart
            st.subheader("Price Chart")
            detail_period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3, key="detail_period")
            hist = fetch_price_history(selected_detail, period=detail_period)
            if not hist.empty:
                fig_detail = go.Figure()

                # Candlestick
                fig_detail.add_trace(go.Candlestick(
                    x=hist.index,
                    open=hist["Open"],
                    high=hist["High"],
                    low=hist["Low"],
                    close=hist["Close"],
                    name="Price",
                ))

                # Moving averages
                if len(hist) >= 20:
                    sma20 = hist["Close"].rolling(20).mean()
                    fig_detail.add_trace(go.Scatter(
                        x=hist.index, y=sma20,
                        mode="lines", name="SMA 20",
                        line=dict(color="#ffa500", width=1),
                    ))
                if len(hist) >= 50:
                    sma50 = hist["Close"].rolling(50).mean()
                    fig_detail.add_trace(go.Scatter(
                        x=hist.index, y=sma50,
                        mode="lines", name="SMA 50",
                        line=dict(color="#00bfff", width=1),
                    ))

                fig_detail.update_layout(
                    template="plotly_dark",
                    height=500,
                    xaxis_rangeslider_visible=False,
                    margin=dict(t=20, b=40, l=60, r=20),
                )
                st.plotly_chart(fig_detail, use_container_width=True)

                # Volume chart
                fig_vol = px.bar(
                    x=hist.index, y=hist["Volume"],
                    labels={"x": "Date", "y": "Volume"},
                    color_discrete_sequence=["#4a6fa5"],
                )
                fig_vol.update_layout(
                    template="plotly_dark",
                    height=200,
                    margin=dict(t=10, b=30, l=60, r=20),
                )
                st.plotly_chart(fig_vol, use_container_width=True)

    # ────────────────────────────────────
    # TAB 5: EXPORT
    # ────────────────────────────────────
    with tab_export:
        st.subheader("Export Screener Results")

        export_option = st.radio(
            "Export format",
            ["CSV", "Excel (XLSX)"],
            horizontal=True,
        )

        if export_option == "CSV":
            csv_data = filtered.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                data=csv_data,
                file_name=f"jse_screen_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                filtered.to_excel(writer, sheet_name="Screener Results", index=False)
                data.to_excel(writer, sheet_name="Full Universe", index=False)
            st.download_button(
                "📥 Download Excel",
                data=buffer.getvalue(),
                file_name=f"jse_screen_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        st.markdown("---")
        st.subheader("Composite Scoring")
        st.caption("Create a custom weighted score to rank stocks across multiple metrics.")

        score_cols = st.multiselect(
            "Select metrics to score",
            ["ROE_Pct", "Div_Yield_Pct", "PE_Trailing", "Price_6M_Pct",
             "Revenue_Growth_Pct", "Debt_to_Equity", "Market_Cap_Bn", "RSI_14"],
            default=["ROE_Pct", "Div_Yield_Pct", "PE_Trailing"],
            key="score_metrics",
        )

        weights = {}
        for col in score_cols:
            sc1, sc2 = st.columns([2, 1])
            with sc1:
                w = st.slider(f"Weight: {col}", 0.0, 5.0, 1.0, 0.5, key=f"w_{col}")
            with sc2:
                higher_better = st.checkbox(
                    "Higher = Better",
                    value=col not in ["PE_Trailing", "Debt_to_Equity"],
                    key=f"hb_{col}",
                )
            weights[col] = (w, higher_better)

        if st.button("Calculate Composite Score", use_container_width=True):
            scored = compute_composite_score(filtered, weights)
            st.dataframe(
                scored[["Symbol", "Company", "Composite_Score"] + score_cols].head(20),
                use_container_width=True,
            )

else:
    # ── Landing page when no data loaded ──
    st.markdown("---")
    st.markdown("### Getting Started")
    st.markdown("""
    1. **Select your universe** in the sidebar (Full JSE, Top 40, or custom CSV)
    2. **Choose sectors** to narrow the search
    3. **Pick a strategy preset** or set manual filters
    4. **Click "Fetch / Refresh Data"** to pull live data from Yahoo Finance
    5. **Explore results** across the tabs: screen, chart, compare, and export
    """)

    # Show strategy overview
    st.markdown("### Available Strategy Presets")
    for name, strat in STRATEGIES.items():
        st.markdown(f"""
        <div class="strategy-card">
            <h4>{name}</h4>
            <p>{strat['description']}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption(f"JSE Equity Screener | Data via Yahoo Finance | Built {datetime.now().strftime('%Y')}")
