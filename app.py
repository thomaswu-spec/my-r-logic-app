import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- 1. 初始化與連線 (從保險箱讀取鑰匙) ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Planner", layout="wide")

st.title("📑 R-Logic 專業交易模擬策劃")
st.write("根據你的 Google Sheet 邏輯構建：輸入預算與風險比，自動推算止蝕與目標價。")

# --- 2. 核心計算引擎 (對接 Excel Formula) ---
def excel_logic_calc(price, budget, r_pc, r_ratio):
    # R budget = Buy in budget * R%
    r_budget = budget * (r_pc / 100)
    # Potential Gain = R budget * R Ratio
    potential_gain = r_budget * r_ratio
    # Potential Loss = R budget
    potential_loss = r_budget
    # Shares = Buy in budget / Price (取整數)
    shares = int(budget / price) if price > 0 else 0
    # Target price = Price * (1 + (R% * R Ratio))
    target_price = price * (1 + (r_pc/100 * r_ratio))
    # Cut loss price = Price * (1 - R%)
    cut_loss_price = price * (1 - (r_pc/100))
    
    return {
        "r_budget": r_budget,
        "gain": potential_gain,
        "loss": potential_loss,
        "shares": shares,
        "target": target_price,
        "sl": cut_loss_price
    }

# --- 3. 介面佈局：Excel 風格對比 ---
# 建立 4 欄：標籤, 場景1, 場景2, 場景3
cols = st.columns([1.2, 2, 2, 2], gap="medium")

# 第一欄：固定標籤
with cols[0]:
    st.write("## ") # 對齊空間
    st.write("---")
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

# 第二、三、四欄：輸入與自動計算區
for i in range(1, 4):
    with cols[i]:
        st.subheader(f"場景 {i}")
        with st.container(border=True):
            # --- 輸入區 (依照要求加入 please input here) ---
            stock = st.text_input(f"S{i}", placeholder="please input here", key=f"tk_{i}", label_visibility="collapsed").upper()
            
            # 數值輸入框使用 placeholder
            price = st.number_input(f"P{i}", value=None, placeholder="please input here", key=f"pr_{i}", label_visibility="collapsed")
            budget = st.number_input(f"B{i}", value=None, placeholder="please input here", key=f"bg_{i}", label_visibility="collapsed")
            r_pc = st.number_input(f"R{i}", value=5.0, placeholder="please input here", key=f"rpc_{i}", label_visibility="collapsed")
            r_ratio = st.number_input(f"Ratio{i}", value=3.0, placeholder="please input here", key=f"ratio_{i}", label_visibility="collapsed")
            
            # --- 自動計算邏輯 ---
            if price and budget:
                res = excel_logic_calc(price, budget, r_pc, r_ratio)
                st.write("---")
                # 輸出顯示
                st.write(f"HK${res['gain']:,.0f}")
                st.write(f"HK${res['loss']:,.0f}")
                st.write(f"**{res['shares']}** 股")
                st.success(f"**{res['target']:,.2f}**")
                st.error(f"**{res['sl']:,.2f}**")
                
                # 存入雲端按鈕
                if st.button(f"📥 存入持倉 {i}", key=f"btn_{i}", use_container_width=True):
                    supabase.table("trades").insert({
                        "ticker": stock, "entry_price": price, "stop_loss": res['sl'],
                        "qty": res['shares'], "currency": "HKD", "risk_mkt": res['r_budget']
                    }).execute()
                    st.toast(f"已存入 {stock} 到雲端")
            else:
                st.write("---")
                st.info("請輸入價格與預算以開始計算")