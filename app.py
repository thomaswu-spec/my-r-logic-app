import streamlit as st
import pandas as pd
from supabase import create_client, Client
import yfinance as yf

# --- 1. 初始化與連線 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Cockpit Pro", layout="wide")

# --- 2. CSS 樣式修正 (對齊與字體) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 16px !important; }
    .row-label { height: 65px; display: flex; align-items: center; font-weight: bold; }
    .metric-card { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4255; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函數 ---
def fetch_live_price(ticker):
    try:
        # 簡單判斷：純數字視為港股，否則視為美股
        formatted_ticker = f"{int(ticker):04d}.HK" if ticker.isdigit() else ticker
        stock = yf.Ticker(formatted_ticker)
        # 抓取最新成交價
        price = stock.fast_info['last_price']
        return round(price, 3)
    except:
        return None

def calc_logic(p, b, r, ra):
    if not p or not b: return None
    r_val = b * (r / 100)
    return {
        "shares": int(b / p),
        "target": p * (1 + (r/100 * ra)),
        "sl": p * (1 - (r/100)),
        "gain": r_val * ra,
        "loss": r_val
    }

st.title("🚀 R-Logic 投資指揮中心")

# --- 4. 策劃器 (維持 5 個場景，代碼同前，略過以縮短長度但功能保留) ---
# ... (此處保留之前的 Scenario Planner 5 欄代碼) ...

# --- 5. 全局持倉總覽 (新增實時損益與刪除) ---
st.divider()
st.header("📊 全局持倉監控 (Live Portfolio)")

# 從雲端抓取最新數據
db_res = supabase.table("trades").select("*").execute()
if db_res.data:
    trades_list = db_res.data
    
    # 建立統計變數
    total_pl = 0
    total_risk = 0
    
    # 顯示表頭
    h1, h2, h3, h4, h5, h6, h7 = st.columns([1, 1, 1, 1, 1.5, 1.2, 0.5])
    h1.write("**代號**")
    h2.write("**股數**")
    h3.write("**成本**")
    h4.write("**現價**")
    h5.write("**盈虧 (HKD)**")
    h6.write("**當前 R 數**")
    h7.write("")

    st.write("---")

    for trade in trades_list:
        # 實時抓取價格
        curr_price = fetch_live_price(trade['ticker'])
        entry_price = trade['entry_price']
        stop_loss = trade['stop_loss']
        qty = trade['qty']
        
        # 計算損益
        if curr_price:
            pl_amount = (curr_price - entry_price) * qty
            # 當前 R 數公式：(現價 - 成本) / (成本 - 止蝕)
            denom = entry_price - stop_loss
            curr_r = (curr_price - entry_price) / denom if denom != 0 else 0
            
            total_pl += pl_amount
            total_risk += trade['risk_mkt']
            
            # 顯示每一行
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 1, 1, 1, 1.5, 1.2, 0.5])
            c1.write(trade['ticker'])
            c2.write(f"{qty}")
            c3.write(f"{entry_price}")
            c4.write(f"{curr_price}")
            
            # 盈虧顏色標示
            pl_color = "green" if pl_amount >= 0 else "red"
            c5.markdown(f":{pl_color}[${pl_amount:,.2f}]")
            
            # R 數視覺化
            r_color = "inverse" if curr_r >= 2 else "normal"
            c6.info(f"{curr_r:.2f} R")