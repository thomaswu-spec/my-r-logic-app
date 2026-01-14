import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import math

# --- 1. 基礎配置與 API 設定 ---
API_KEY = "YOUR_API_KEY" # 👈 記得填入你的 ExchangeRate-API Key

def get_fx_rate(base, target):
    try:
        url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/pair/{base}/{target}"
        response = requests.get(url).json()
        return response.get('conversion_rate', 7.8)
    except:
        return 7.8

st.set_page_config(page_title="R-Logic Pro", layout="wide")

# --- 2. 【核心修復】初始化筆記本 ---
# 這段代碼確保 App 啟動時一定會先建立 trades 清單，避免報錯
if 'trades' not in st.session_state:
    st.session_state.trades = []

st.title("🛡️ R-Logic 全能交易管理系統")

# --- 3. 側邊欄：全域設定 ---
with st.sidebar:
    st.header("⚙️ 全局設定")
    base_currency = st.selectbox("基準貨幣", ["USD", "HKD"])
    equity = st.number_input(f"總資產 ({base_currency})", value=10000.0)
    
    usd_to_base = get_fx_rate("USD", base_currency) if base_currency == "HKD" else 1.0
    if base_currency == "HKD":
        st.caption(f"即時匯率: 1 USD = {usd_to_base:.4f} HKD")

# --- 4. 交易策劃器 (Planner) ---
st.header("📝 第一步：策劃交易")
c1, c2, c3, c4 = st.columns(4)
with c1: ticker = st.text_input("標的代號").upper()
with c2: mkt_currency = st.selectbox("市場幣別", ["USD", "HKD"])
with c3: entry = st.number_input("進場價", value=100.0)
with c4: sl = st.number_input("止蝕價", value=95.0)

# 計算邏輯
r_in_base = equity * 0.01
r_in_mkt = r_in_base / usd_to_base if (base_currency == "HKD" and mkt_currency == "USD") else r_in_base

if entry > sl:
    qty = int(r_in_mkt / (entry - sl))
    st.success(f"建議股數: {qty} | 預期風險: {mkt_currency} ${r_in_mkt:.2f}")
    
    if st.button("➕ 轉為持倉"):
        st.session_state.trades.append({
            "Ticker": ticker,
            "Currency": mkt_currency,
            "Qty": qty,
            "Entry": entry,
            "StopLoss": sl,
            "Risk_Mkt": r_in_mkt
        })
        st.toast(f"{ticker} 已加入持倉！")
        st.rerun()
else:
    st.error("止蝕價須低於進場價")

st.divider()

# --- 5. 持倉儀表板 (Dashboard) ---
st.header("📊 第二步：持倉監控與 R-Distribution")

if st.session_state.trades:
    df = pd.DataFrame(st.session_state.trades)
    
    updated_trades = []
    # 使用列來並排顯示現價輸入和 R 數
    for i, row in df.iterrows():
        with st.expander(f"📌 {row['Ticker']} - 成本: {row['Entry']}"):
            col_a, col_b = st.columns(2)
            cur_price = col_a.number_input(f"當前價格 ({row['Ticker']})", value=row['Entry'], key=f"cur_{i}")
            
            # 計算 Current R
            denom = row['Entry'] - row['StopLoss']
            curr_r = (cur_price - row['Entry']) / denom if denom != 0 else 0
            
            color = "green" if curr_r >= 0 else "red"
            col_b.markdown(f"### 回報: :{color}[{curr_r:.2f} R]")
            
            row['Current_Price'] = cur_price
            row['Current_R'] = curr_r
            updated_trades.append(row)
    
    df_final = pd.DataFrame(updated_trades)

    # 繪製圖表
    fig = px.bar(df_final, x='Ticker', y='Current_R', color='Current_R',
                 color_continuous_scale=['red', 'gray', 'green'],
                 title="持倉風險分佈 (R-Units)")
    st.plotly_chart(fig, use_container_width=True)
    
    if st.button("🗑️ 清空數據"):
        st.session_state.trades = []
        st.rerun()
else:
    st.info("目前沒有持倉紀錄。")