import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from streamlit_autorefresh import st_autorefresh

# 1. Page Configuration & Setup
st.set_page_config(page_title="Rotational Strategy Hub", layout="wide")
st.title("⚡ Dynamic Rotational Growth Screener & Matrix")

# Auto-refresh every 1 HOUR
count = st_autorefresh(interval=3600000, limit=100, key="data_refresh")

# 2. Interactive Strategy & Heatmap Legends
with st.expander("ℹ️ View Strategy Rules & Visual Heatmap Legends", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📋 Core Strategy Rules")
        st.markdown("""
        | Metric | Growth "Green Light" | Value "Safety Net" | The "Eject" Signal |
        | :--- | :--- | :--- | :--- |
        | **Rev. Growth** | **> 20%** | 5% - 10% | Negative / Declining |
        | **PEG Ratio** | **< 1.8** | **< 1.2** | **> 3.0** *(Overhyped)* |
        | **RSI (14-Day)** | 40 - 50 *(Healthy Dip)* | 30 - 40 *(Oversold)* | **> 80** *(Blow-off)* |
        | **200-Day MA** | Trending Up | Acting as Support | Below MA |
        | **FCF Margin** | **> 15%** | > 10% | Burning Cash |
        """)
    with col2:
        st.markdown("### 🎨 Heatmap Color Thresholds")
        st.markdown("""
        | Metric | 🟩 Green (Strong/Pass) | 🟧 Orange (Neutral) | 🟥 Red (Weak/Fail) |
        | :--- | :--- | :--- | :--- |
        | **Rev. Growth** | >= 20% | 5% to 19.9% | < 5% / Negative |
        | **PEG Ratio** | <= 1.8 | 1.81 to 3.0 | > 3.0 |
        | **RSI (14-Day)** | 30 to 50 | < 30 or 51 to 80 | > 80 |
        | **200-Day MA** | Price >= MA | *N/A* | Price < MA |
        | **FCF Margin** | >= 10% | 0% to 9.9% | < 0% *(Negative)* |
        """)

st.markdown("---")

# 3. Watchlists: The Top 50 US Mega-Caps
STOCK_UNIVERSE = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "GOOGL": "Alphabet", "AMZN": "Amazon", "TGT": "Target",
    "META": "Meta", "BRK-B": "Berkshire Hathaway", "LLY": "Eli Lilly", "AVGO": "Broadcom", "TSLA": "Tesla",
    "JPM": "JPMorgan Chase", "WMT": "Walmart", "UNH": "UnitedHealth", "V": "Visa", "XOM": "Exxon Mobil",
    "MA": "Mastercard", "PG": "Procter & Gamble", "JNJ": "Johnson & Johnson", "COST": "Costco", "HD": "Home Depot",
    "ORCL": "Oracle", "ABBV": "AbbVie", "BAC": "Bank of America", "CVX": "Chevron", "CRM": "Salesforce",
    "NFLX": "Netflix", "KO": "Coca-Cola", "MRK": "Merck", "PEP": "PepsiCo", "TMO": "Thermo Fisher",
    "LIN": "Linde", "ADBE": "Adobe", "DIS": "Disney", "WFC": "Wells Fargo", "CSCO": "Cisco",
    "MCD": "McDonald's", "AXP": "American Express", "ABT": "Abbott Labs", "INTU": "Intuit", "IBM": "IBM",
    "QCOM": "Qualcomm", "CAT": "Caterpillar", "TXN": "Texas Instruments", "AMAT": "Applied Materials", "NOW": "ServiceNow",
    "PFE": "Pfizer", "GE": "GE Aerospace", "GS": "Goldman Sachs", "ISRG": "Intuitive Surgical", "SYK": "Stryker"
}

# 4. Technical Calculation Helpers
def calculate_rsi(data, window=14):
    if len(data) < window + 1:
        return 50.0 
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# 5. Core Screening Engine
@st.cache_data(ttl=3600)
def execute_screener(ticker_dictionary, show_progress=False):
    processed_data = []
    total_stocks = len(ticker_dictionary)
    
    if show_progress and total_stocks > 10:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    for i, (ticker_symbol, name) in enumerate(ticker_dictionary.items()):
        if show_progress and total_stocks > 10:
            progress_bar.progress((i + 1) / total_stocks)
            status_text.text(f"Scanning Top 50... Fetching {ticker_symbol} ({i+1}/{total_stocks})")
            
        try:
            time.sleep(0.4) 
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="1y", interval="1d")
            
            if hist.empty or len(hist) < 200:
                continue
            
            current_price = hist['Close'].iloc[-1]
            ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            ma_200_prev = hist['Close'].rolling(window=200).mean().iloc[-20]
            rsi_14 = calculate_rsi(hist)
            
            info = ticker.info
            rev_growth = info.get('revenueGrowth', 0.0)
            rev_growth = rev_growth * 100 if rev_growth is not None else 0.0
            peg_ratio = info.get('pegRatio', np.nan)
            
            fcf = info.get('freeCashflow', 0)
            total_rev = info.get('totalRevenue', 1)
            fcf_margin = (fcf / total_rev) * 100 if total_rev and fcf else 0.0
            
            is_ejected = False
            eject_reasons = []
            
            if rev_growth <= 0: 
                is_ejected = True
                eject_reasons.append("Zero/Negative Growth")
            if pd.notnull(peg_ratio) and peg_ratio > 3.0:
                is_ejected = True
                eject_reasons.append("PEG > 3.0")
            if rsi_14 > 80:
                is_ejected = True
                eject_reasons.append("RSI > 80")
            if current_price < ma_200:
                is_ejected = True
                eject_reasons.append("Below 200-Day MA")
            if fcf_margin < 0:
                is_ejected = True
                eject_reasons.append("Negative FCF")
                
            green_lights = 0
            safety_nets = 0
            buy_triggers = []
            classification = "Eligible (Neutral)"
            
            if not is_ejected:
                if rev_growth > 20: 
                    green_lights += 1
                    buy_triggers.append("High Rev Growth (>20%)")
                if pd.notnull(peg_ratio) and peg_ratio < 1.8: 
                    green_lights += 1
                    buy_triggers.append("Attractive Growth PEG (<1.8)")
                if 40 <= rsi_14 <= 50: 
                    green_lights += 1
                    buy_triggers.append("Healthy RSI Dip (40-50)")
                if ma_200 > ma_200_prev: 
                    green_lights += 1
                if fcf_margin > 15: 
                    green_lights += 1
                    buy_triggers.append("Elite FCF Margin (>15%)")
                
                if 5 <= rev_growth <= 10: 
                    safety_nets += 1
                    buy_triggers.append("Defensive Rev Base (5-10%)")
                if pd.notnull(peg_ratio) and peg_ratio < 1.2: 
                    safety_nets += 1
                    buy_triggers.append("Value-Priced PEG (<1.2)")
                if 30 <= rsi_14 <= 40: 
                    safety_nets += 1
                    buy_triggers.append("Oversold RSI Floor (30-40)")
                if 0 <= (current_price - ma_200) / ma_200 <= 0.05: 
                    safety_nets += 1
                    buy_triggers.append("Holding 200-Day MA Support")
                if 10 <= fcf_margin <= 15: 
                    safety_nets += 1
                    buy_triggers.append("Stable FCF Margin (10-15%)")
                
                if green_lights >= 2 and (40 <= rsi_14 <= 50):
                    classification = "🟢 Growth Buy (Healthy Dip)"
                elif green_lights >= 2:
                    classification = "🟢 Growth Green Light"
                elif safety_nets >= 2 and (30 <= rsi_14 <= 40):
                    classification = "🔵 Safety Net (Oversold)"
                elif safety_nets >= 2:
                    classification = "🔵 Value Safety Net"
                
                if not buy_triggers:
                    buy_triggers.append("Stable Baseline Financials")
            else:
                classification = "🔴 Eject Signal Triggered"
                
            processed_data.append({
                "Ticker": ticker_symbol,
                "Name": name, 
                "Price": current_price,
                "Rev Growth": rev_growth,
                "PEG": peg_ratio,
                "RSI": rsi_14,
                "200-Day MA": ma_200,
                "FCF Margin": fcf_margin,
                "Category": classification,
                "Eligible": not is_ejected,
                "Buy Triggers / Reasons": " | ".join(buy_triggers) if not is_ejected else "N/A",
                "Eject Reason": ", ".join(eject_reasons) if eject_reasons else "N/A",
                "Rank Score": (green_lights * 2) + safety_nets
            })
        except Exception:
            continue
            
    if show_progress and total_stocks > 10:
        progress_bar.empty()
        status_text.empty()
        
    return pd.DataFrame(processed_data)

# 6. Heatmap Styling Engine
def apply_heatmap_styling(target_df):
    display_cols = ["Ticker", "Name", "Price", "Category", "Buy Triggers / Reasons", "Rev Growth", "PEG", "RSI", "200-Day MA", "FCF Margin"]
    if target_df.empty: return target_df
    df_vis = target_df[display_cols].copy()
    
    def row_style(row):
        styles = [''] * len(row)
        green = 'background-color: #c6f6d5; color: #1f462f;'
        orange = 'background-color: #feebc8; color: #744210;'
        red = 'background-color: #fed7d7; color: #742a2a;'
        
        idx_rev = row.index.get_loc('Rev Growth')
        if row['Rev Growth'] >= 20: styles[idx_rev] = green
        elif row['Rev Growth'] >= 5: styles[idx_rev] = orange
        else: styles[idx_rev] = red
        
        idx_peg = row.index.get_loc('PEG')
        if pd.notnull(row['PEG']):
            if row['PEG'] <= 1.8: styles[idx_peg] = green
            elif row['PEG'] <= 3.0: styles[idx_peg] = orange
            else: styles[idx_peg] = red
            
        idx_rsi = row.index.get_loc('RSI')
        if 30 <= row['RSI'] <= 50: styles[idx_rsi] = green
        elif row['RSI'] > 80: styles[idx_rsi] = red
        else: styles[idx_rsi] = orange
            
        idx_ma = row.index.get_loc('200-Day MA')
        if row['Price'] >= row['200-Day MA']: styles[idx_ma] = green
        else: styles[idx_ma] = red
        
        idx_fcf = row.index.get_loc('FCF Margin')
        if row['FCF Margin'] >= 10: styles[idx_fcf] = green
        elif row['FCF Margin'] >= 0: styles[idx_fcf] = orange
        else: styles[idx_fcf] = red
            
        return styles

    styled = df_vis.style.apply(row_style, axis=1)
    styled = styled.format({
        "Price": "${:,.2f}", 
        "Rev Growth": "{:,.1f}%",
        "PEG": lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A",
        "RSI": "{:,.1f}", 
        "200-Day MA": "${:,.2f}", 
        "FCF Margin": "{:,.1f}%"
    })
    
    return styled

# 7. Main Interface Display
st.subheader("🌎 Market Universe: Top 10 Rotational Picks")
st.markdown("Scanning the top 50 U.S. Mega-Cap equities. *Note: Data caches for 1 hour to prevent API limits.*")

df_market = execute_screener(STOCK_UNIVERSE, show_progress=True)

if not df_market.empty:
    eligible_market = df_market[df_market["Eligible"] == True].sort_values(by="Rank Score", ascending=False)
    ejected_market = df_market[df_market["Eligible"] == False]

    if not eligible_market.empty:
        st.dataframe(apply_heatmap_styling(eligible_market.head(10)), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("**⛔ Active Disqualification Log**")
    if not ejected_market.empty:
        def color_rejections(val): return 'background-color: #fce8e6; color: #a51d24; font-weight: bold;'
        st.dataframe(
            ejected_market[["Ticker", "Name", "Price", "RSI", "Eject Reason"]]
            .style.format({"Price": "${:,.2f}", "RSI": "{:,.1f}"})
            .map(color_rejections, subset=['Ticker']), 
            use_container_width=True, hide_index=True
        )
