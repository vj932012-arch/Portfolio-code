import os
import time
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

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

def send_telegram_alert(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing Telegram credentials.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def calculate_rsi(data, window=14):
    if len(data) < window + 1:
        return 50.0 
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def run_rotation_scan():
    print(f"Running Rotational Screener on {len(STOCK_UNIVERSE)} Mega-Caps...")
    processed_data = []
    
    for i, (ticker_symbol, name) in enumerate(STOCK_UNIVERSE.items()):
        try:
            time.sleep(0.4) 
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="1y", interval="1d")
            
            if hist.empty or len(hist) < 200: continue
            
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
            if rev_growth <= 0: is_ejected = True
            if pd.notnull(peg_ratio) and peg_ratio > 3.0: is_ejected = True
            if rsi_14 > 80: is_ejected = True
            if current_price < ma_200: is_ejected = True
            if fcf_margin < 0: is_ejected = True
                
            if is_ejected: continue

            green_lights = 0
            safety_nets = 0
            
            if rev_growth > 20: green_lights += 1
            if pd.notnull(peg_ratio) and peg_ratio < 1.8: green_lights += 1
            if 40 <= rsi_14 <= 50: green_lights += 1
            if ma_200 > ma_200_prev: green_lights += 1
            if fcf_margin > 15: green_lights += 1
            
            if 5 <= rev_growth <= 10: safety_nets += 1
            if pd.notnull(peg_ratio) and peg_ratio < 1.2: safety_nets += 1
            if 30 <= rsi_14 <= 40: safety_nets += 1
            if 0 <= (current_price - ma_200) / ma_200 <= 0.05: safety_nets += 1
            if 10 <= fcf_margin <= 15: safety_nets += 1
            
            processed_data.append({
                "Ticker": ticker_symbol,
                "Price": current_price,
                "RSI": rsi_14,
                "Rank Score": (green_lights * 2) + safety_nets
            })
        except Exception:
            continue
            
    df = pd.DataFrame(processed_data)
    if df.empty:
        print("No eligible stocks found.")
        return
        
    # Sort and grab top 5
    df = df.sort_values(by="Rank Score", ascending=False).head(5)
    
    # Format the Telegram Alert
    message = f"<b>🌎 Rotational Strategy: Top 5 Picks</b>\n<i>{datetime.datetime.now().strftime('%b %d, %Y')}</i>\n\n"
    for index, row in df.iterrows():
        message += f"• <b>{row['Ticker']}</b> | Price: ${row['Price']:.2f} | RSI: {row['RSI']:.1f} | Score: {row['Rank Score']}\n"
        
    send_telegram_alert(message)

if __name__ == "__main__":
    run_rotation_scan()
