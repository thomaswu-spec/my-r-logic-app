import streamlit as st
import pandas as pd
import requests # 這是用來跟外界 API 溝通的工具

# --- 配置區 ---
API_KEY = "Y054666acb08cd2dfb7de2023" # 👈 請在此處貼上你的 API Key

# 獲取匯率的函數
def get_fx_rate(base, target):
    try:
        url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/pair/{base}/{target}"
        response = requests.get(url).json()
        return response['conversion_rate']
    except:
        return 7.8 # 若 API 失敗，使用預設匯率 (USD/HKD)

st.set_page_config(page_title="R-Logic Pro Global", layout="wide")

if 'trades' not in st.session_state:
    st.session_state.trades = []

st.title("🌍 R-Logic 跨市場持倉管理")

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 全局設定")
    base_currency = st.selectbox("基準貨幣 (Base)", ["USD", "HKD"])
    equity = st.number_input(f"總資產 ({base_currency})", value=100000.0)
    
    # 自動抓取匯率
    if base_currency == "HKD":
        usd_to_base = get_fx_rate("USD", "HKD")
        st.write(f"目前匯率: 1 USD = {usd_to_base:.4f} HKD")
    else:
        usd_to_base = 1.0

# --- 交易策劃 ---
st.header("📝 交易策劃")
c1, c2, c3, c4 = st.columns(4)
with c1: ticker = st.text_input("標的代號").upper()
with c2: mkt_currency = st.selectbox("市場幣別", ["USD", "HKD"])
with c3: entry = st.number_input("進場價", value=150.0)
with c4: sl = st.number_input("止蝕價", value=145.0)

# 核心邏輯：換算 1R 為市場幣別
# 1R = 總資產(Base) * 1% / 匯率
r_in_base = equity * 0.01
# 如果我的資產是 HKD，但買美股，計算時需要把 1R 換成 USD
r_in_mkt = r_in_base / usd_to_base if (base_currency == "HKD" and mkt_currency == "USD") else r_in_base

if entry > sl:
    qty = int(r_in_mkt / (entry - sl))
    st.success(f"建議股數: {qty} | 1R 風險 ({mkt_currency}): ${r_in_mkt:.2f}")
    
    if st.button("➕ 轉為持倉"):
        st.session_state.trades.append({
            "Ticker": ticker, "Currency": mkt_currency, 
            "Qty": qty, "Entry": entry, "Risk_Mkt": r_in_mkt
        })
        st.rerun()

# --- 持倉與總風險 ---
st.divider()
st.header("📊 全局持倉儀表板")
if st.session_state.trades:
    df = pd.DataFrame(st.session_state.trades)
    st.dataframe(df)
    
    # FS 3.B：計算 Total Open Risk
    total_risk = sum(t['Risk_Mkt'] * (usd_to_base if t['Currency'] == "USD" and base_currency == "HKD" else 1) for t in st.session_state.trades)
    st.metric(f"當前總風險 (Total Open Risk in {base_currency})", f"${total_risk:.2f}")