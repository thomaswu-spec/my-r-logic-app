import streamlit as st
import math
import pandas as pd # 這是處理表格的神器

st.set_page_config(page_title="R-Logic Pro", layout="wide")

# --- 1. 初始化筆記本 (Session State) ---
# 如果筆記本裡還沒有「trades」這頁，我們就建立一個空的清單
if 'trades' not in st.session_state:
    st.session_state.trades = []

st.title("🛡️ R-Logic 交易策劃與持倉管理")

# --- 側邊欄：全局設定 ---
with st.sidebar:
    st.header("⚙️ 全局設定")
    equity = st.number_input("總資產 (Base Currency)", value=10000.0)
    default_risk = st.slider("預設風險 %", 0.1, 5.0, 1.0, 0.1)
    commission = st.number_input("每筆固定手續費", value=5.0)
    slippage = st.number_input("預期滑價", value=0.01)

# --- 主畫面：交易策劃器 ---
st.header("📝 第一步：策劃交易")
c1, c2, c3 = st.columns(3)
with c1: ticker = st.text_input("標的代號", value="AAPL").upper()
with c2: entry = st.number_input("進場價", value=150.0)
with c3: sl = st.number_input("止蝕價", value=145.0)

# 核心計算
r_amount = equity * (default_risk / 100)
risk_per_share = (entry - sl) + slippage

if entry > sl:
    qty = math.floor((r_amount - commission) / risk_per_share)
    total_cost = qty * entry
    
    # 顯示計算結果
    st.info(f"建議股數: {qty} | 預算: ${total_cost:.2f}")

    # --- 2. 轉為持倉按鈕 (User Story 實現) ---
    if st.button("➕ 轉為持倉 (Add to Positions)"):
        # 建立一筆交易紀錄
        new_trade = {
            "Ticker": ticker,
            "Entry": entry,
            "StopLoss": sl,
            "Qty": qty,
            "TotalCost": total_cost,
            "RiskAmount": r_amount
        }
        # 把這筆紀錄寫進「白板」
        st.session_state.trades.append(new_trade)
        st.success(f"已將 {ticker} 加入持倉列表！")
else:
    st.error("止蝕價須低於進場價")

st.divider()

# --- 3. 持倉儀表板 (Dashboard MVP) ---
st.header("📊 第二步：我的持倉 (Positions)")

if len(st.session_state.trades) > 0:
    # 把白板上的紀錄變成漂亮表格
    df = pd.DataFrame(st.session_state.trades)
    st.table(df) # 顯示表格
    
    # 計算全域指標 (FS 3.B)
    total_open_risk = df["RiskAmount"].sum()
    st.metric("當前總風險 (Total Open Risk)", f"${total_open_risk:.2f}")
    
    if st.button("🗑️ 清空所有紀錄"):
        st.session_state.trades = []
        st.rerun() # 重新整理頁面
else:
    st.write("目前沒有持倉紀錄，請從上方新增。")