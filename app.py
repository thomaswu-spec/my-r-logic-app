import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- 連線設定 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Planner", layout="wide")

st.title("📑 R-Logic 專業交易模擬策劃")

# --- 核心計算引擎 ---
def excel_logic_calc(price, budget, r_pc, r_ratio):
    r_budget = budget * (r_pc / 100)
    shares = int(budget / price) if price > 0 else 0
    target_price = price * (1 + (r_pc/100 * r_ratio))
    cut_loss_price = price * (1 - (r_pc/100))
    return {
        "r_budget": r_budget,
        "gain": r_budget * r_ratio,
        "loss": r_budget,
        "shares": shares,
        "target": target_price,
        "sl": cut_loss_price
    }

# --- 介面佈局 ---
cols = st.columns([1.2, 2, 2, 2], gap="medium")

# 這裡列出標籤 (省略部分重複代碼，保持邏輯一致)
labels = ["🔍 交易代號", "💰 進場價格", "💼 投入預算", "⚠️ 風險比例", "🎯 風險回報比"]
with cols[0]:
    st.write("## ")
    st.write("---")
    for label in labels: st.markdown(f"**{label}**")

# 場景輸入區
for i in range(1, 4):
    with cols[i]:
        st.subheader(f"場景 {i}")
        with st.container(border=True):
            stock = st.text_input(f"S{i}", placeholder="please input here", key=f"tk_{i}", label_visibility="collapsed").upper()
            price = st.number_input(f"P{i}", value=None, placeholder="please input here", key=f"pr_{i}", label_visibility="collapsed")
            budget = st.number_input(f"B{i}", value=None, placeholder="please input here", key=f"bg_{i}", label_visibility="collapsed")
            r_pc = st.number_input(f"R{i}", value=5.0, placeholder="please input here", key=f"rpc_{i}", label_visibility="collapsed")
            r_ratio = st.number_input(f"Ratio{i}", value=3.0, placeholder="please input here", key=f"ratio_{i}", label_visibility="collapsed")
            
            if price and budget:
                res = excel_logic_calc(price, budget, r_pc, r_ratio)
                st.write("---")
                st.write(f"HK${res['gain']:,.0f}")
                st.write(f"HK${res['loss']:,.0f}")
                st.write(f"**{res['shares']}** 股")
                st.success(f"**{res['target']:,.2f}**")
                st.error(f"**{res['sl']:,.2f}**")
                
                # --- 強化的存檔邏輯 ---
                if st.button(f"📥 存入持倉 {i}", key=f"btn_{i}", use_container_width=True):
                    try:
                        # 準備資料，確保名稱與資料庫完全一致
                        # 如果你的 user_id 是必填，請加上 "user_id": "tester"
                        data_to_save = {
                            "ticker": stock,
                            "currency": "HKD",
                            "qty": res['shares'],
                            "entry_price": price,
                            "stop_loss": res['sl'],
                            "risk_mkt": res['r_budget']
                        }
                        
                        supabase.table("trades").insert(data_to_save).execute()
                        st.toast(f"✅ {stock} 存檔成功！", icon="🎉")
                        
                    except Exception as e:
                        # 如果失敗，直接在網頁上噴出真正的錯誤原因
                        st.error(f"❌ 存檔失敗！原因：{str(e)}")
            else:
                st.write("---")
                st.info("請輸入完整參數")