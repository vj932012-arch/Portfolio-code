import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 1. Page Configuration & Setup
st.set_page_config(page_title="Rotational Strategy Hub", layout="wide")
st.title("⚡ Dynamic Rotational Growth Screener & Matrix")
st.markdown("Scans the market universe, flags disqualifications, and outputs exact buy triggers with live conditional formatting.")

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

# 3. Screening Pool
STOCK_UNIVERSE = {
    "NVDA": "NVIDIA Corporation", "PLTR": "Palantir Technologies Inc", 
    "VRT": "Vertiv Holdings Co", "LLY": "Eli Lilly & Co", 
    "CEG": "Constellation Energy Corp", "NET": "Cloudflare Inc", 
    "CRWD": "CrowdStrike Holdings Inc", "SQ": "Block Inc", 
    "ANET": "Arista Networks Inc", "VST": "Vistra Corp",
    "GOOGL": "Alphabet Inc", "TGT": "Target Corp", 
    "MSFT": "Microsoft Corporation", "AMZN": "Amazon.com Inc",
    "META": "Meta Platforms Inc", "AMD": "Advanced Micro Devices Inc", 
    "AVGO": "Broadcom Inc", "NEE": "NextEra Energy Inc",
    "XOM": "Exxon Mobil Corp", "FSLR": "First Solar Inc",
    "PANW": "Palo Alto Networks Inc", "MU": "Micron Technology Inc",
    "JPM": "JPMorgan Chase & Co", "V": "Visa Inc", "AAPL": "Apple Inc"
}

# 4. Technical Calculation Helpers
def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# 5. Core Screening & Reasoning Engine
@st.cache_data(ttl=3600)
def execute_screener():
    processed_data = []
    
    for ticker_symbol, name in STOCK_UNIVERSE.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="1y")
            if hist.empty or len(hist) < 200:
                continue
            
            # Gather Technicals
            current_price = hist['Close'].iloc[-1]
            ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            ma_200_prev = hist['Close'].rolling(window=200).mean().iloc[-20]
            rsi_14 = calculate_rsi(hist)
            
            # Gather Fundamentals
            info = ticker.info
            rev_growth = info.get('revenueGrowth', 0.0)
            rev_growth = rev_growth * 100 if rev_growth is not None else 0.0
            peg_ratio = info.get('pegRatio', np.nan)
            
            fcf = info.get('freeCashflow', 0)
            total_rev = info.get('totalRevenue', 1)
            fcf_margin = (fcf / total_rev) * 100 if total_rev and fcf else 0.0
            
            # --- EVALUATE RULES ---
            is_ejected = False
            eject_reasons = []
            
            if rev_growth < 0:
                is_ejected = True
                eject_reasons.append("Negative Growth")
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
                
            # Define Buy Strengths
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
                
            # THIS IS THE BLOCK THAT WAS MISSING THE CLOSING BRACKETS!
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
            
    return pd.DataFrame(processed_data)

df = execute_screener()

# Segment the Boards
eligible_pool = df[df["Eligible"] == True].sort_values(by="Rank Score", ascending=False)
ejected_pool = df[df["Eligible"] == False]

# Extract exact Top 10 Picks
top_10_picks = eligible_pool.head(10)

# 6. Heatmap Styling Engine
def apply_heatmap_styling(target_df):
    display_cols = ["Ticker", "Name", "Price", "Category", "Buy Triggers / Reasons", "Rev Growth", "PEG", "RSI", "200-Day MA", "FCF Margin"]
    df_vis = target_df[display_cols].copy()
    
    def row_style(row):
        styles = [''] * len(row)
        
        # Color Palettes
        green = 'background-color: #c6f6d5; color: #1f462f;'
        orange = 'background-color: #feebc8; color: #744210;'
        red = 'background-color: #fed7d7; color: #742a2a;'
        
        # Apply logic to Rev Growth
        val = row['Rev Growth']
        idx = row.index.get_loc('Rev Growth')
        if val >= 20: styles[idx] = green
        elif val >= 5: styles[idx] = orange
        else: styles[idx] = red
        
        # Apply logic to PEG
        val = row['PEG']
        idx = row.index.get_loc('PEG')
        if pd.notnull(val):
            if val <= 1.8: styles[idx] = green
            elif val <= 3.0: styles[idx] = orange
            else: styles[idx] = red
            
        # Apply logic to RSI
        val = row['RSI']
        idx = row.index.get_loc('RSI')
        if 30 <= val <= 50: styles[idx] = green
        elif val > 80: styles[idx] = red
        else: styles[idx] = orange
            
        # Apply logic to 200-Day MA
        ma_val = row['200-Day MA']
        price_val = row['Price']
        idx = row.index.get_loc('200-Day MA')
        if price_val >= ma_val: styles[idx] = green
        else: styles[idx] = red
        
        # Apply logic to FCF Margin
        val = row['FCF Margin']
        idx = row.index.get_loc('FCF Margin')
        if val >= 10: styles[idx] = green
        elif val >= 0: styles[idx] = orange
        else: styles[idx] = red
            
        return styles

    # Apply the conditional colors
    styled = df_vis.style.apply(row_style, axis=1)
    
    # Finally, format the text appearance natively
    styled = styled.format({
        "Price": "${:,.2f}",
        "Rev Growth": "{:,.1f}%",
        "PEG": lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A",
        "RSI": "{:,.1f}",
        "200-Day MA": "${:,.2f}",
        "FCF Margin": "{:,.1f}%"
    })
    
    return styled

# UI Render Logic Block
st.subheader("🏆 Top 10 Rotational Picks (Ranked by Matrix Score)")

if not top_10_picks.empty:
    styled_top_10 = apply_heatmap_styling(top_10_picks)
    st.dataframe(styled_top_10, use_container_width=True, hide_index=True)
else:
    st.warning("No stocks currently meet the structural eligibility parameters.")

st.markdown("---")
st.subheader("⛔ Active Disqualification Log")

if not ejected_pool.empty:
    ejected_vis = ejected_pool[["Ticker", "Name", "Price", "RSI", "Eject Reason"]].copy()
    
    def color_rejections(val):
        return 'background-color: #fce8e6; color: #a51d24; font-weight: bold;'
        
    styled_ejected = ejected_vis.style.format({
        "Price": "${:,.2f}",
        "RSI": "{:,.1f}"
    }).map(color_rejections, subset=['Ticker'])
    
    st.dataframe(styled_ejected, use_container_width=True, hide_index=True)