import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- 1. 連線設定 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Planner", layout="wide")

# --- 2. 核心計算函數 (對接 Google Sheet 公式) ---
def calculate_logic(price, budget, r_pc, r_ratio):
    r_budget = budget * (r_pc / 100)
    shares = int(budget / price) if price > 0 else 0
    target = price * (1 + (r_pc/100 * r_ratio))
    sl = price * (1 - (r_pc/100))
    return {
        "gain": r_budget * r_ratio,
        "loss": r_budget,
        "shares": shares,
        "target": target,
        "sl": sl,
        "r_val": r_budget
    }

st.title("📑 R-Logic 專業交易模擬策劃")
st.caption("根據你的 Excel 邏輯優化：調整數值後自動計算結果")

# --- 3. 介面佈局：修正標籤顯示 ---
# 建立 4 個欄位，給左邊標籤多一點空間 (1.5)
cols = st.columns([1.5, 2, 2, 2], gap="medium")

# --- 第一欄：顯示標籤欄位 ---
with cols[0]:
    st.write("## ") # 標題對齊空間
    st.write("---")
    st.markdown("### ") # 微調對齊
    st.markdown("**🔍 交易代號 (Stock)**")
    st.markdown("**💰 進場價格 (Price)**")
    st.markdown("**💼 投入預算 (Budget)**")
    st.markdown("**⚠️ 風險比例 (R %)**")
    st.markdown("**🎯 風險回報比 (Ratio)**")
    st.write("---")
    st.markdown("📈 **預計回報金額**")
    st.markdown("📉 **預計虧損金額**")
    st.markdown("🔢 **建議買入股數**")
    st.markdown("✅ **目標止盈 (Target)**")
    st.markdown("❌ **止蝕清算 (Cut Loss)**")

# --- 第二、三、四欄：場景輸入區 ---
for i in range(1, 4):
    with cols[i]:
        st.subheader(f"場景 {i}")
        with st.container(border=True):
            # 輸入區：加入 "please input here" 提示
            stock = st.text_input(f"tk{i}", placeholder="please input here", key=f"tk_{i}", label_visibility="collapsed").upper()
            price = st.number_input(f"pr{i}", value=None, placeholder="please input here", key=f"pr_{i}", label_visibility="collapsed")
            budget = st.number_input(f"bg{i}", value=None, placeholder="please input here", key=f"bg_{i}", label_visibility="collapsed")
            r_pc = st.number_input(f"r{i}", value=5.0, placeholder="please input here", key=f"rpc_{i}", label_visibility="collapsed")
            r_ratio = st.number_input(f"ratio{i}", value=3.0, placeholder="please input here", key=f"ratio_{i}", label_visibility="collapsed")
            
            st.write("---")
            
            if price and budget:
                res = calculate_logic(price, budget, r_pc, r_ratio)
                # 輸出區
                st.write(f"HK${res['gain']:,.0f}")
                st.write(f"HK${res['loss']:,.0f}")
                st.write(f"**{res['shares']}** 股")
                st.success(f"**{res['target']:,.2f}**")
                st.error(f"**{res['sl']:,.2f}**")
                
                if st.button(f"📥 存入持倉 {i}", key=f"btn_{i}", use_container_width=True):
                    try:
                        # 存入資料庫，請確保資料庫 ticker 已經不是 Primary Key
                        supabase.table("trades").insert({
                            "ticker": stock if stock else "N/A",
                            "entry_price": price,
                            "stop_loss": res['sl'],
                            "qty": res['shares'],
                            "currency": "HKD