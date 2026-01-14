import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- 初始化連線 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Planner", layout="wide")

# --- 核心計算 (根據 R Logic Google Sheet) ---
def excel_calc(price, budget, r_pc, r_ratio):
    r_budget = budget * (r_pc / 100)
    shares = int(budget / price) if price > 0 else 0
    target = price * (1 + (r_pc/100 * r_ratio))
    sl = price * (1 - (r_pc/100))
    return {"r": r_budget, "g": r_budget * r_ratio, "shares": shares, "target": target, "sl": sl}

st.title("📑 R-Logic 專業交易模擬策劃")

cols = st.columns([1.2, 2, 2, 2], gap="medium")
# (這裡省略標籤顯示代碼，保持簡潔)

for i in range(1, 4):
    with cols[i]:
        st.subheader(f"場景 {i}")
        with st.container(border=True):
            stock = st.text_input(f"S{i}", placeholder="please input here", key=f"tk_{i}", label_visibility="collapsed").upper()
            price = st.number_input(f"P{i}", value=None, placeholder="please input here", key=f"pr_{i}", label_visibility="collapsed")
            budget = st.number_input(f"B{i}", value=None, placeholder="please input here", key=f"bg_{i}", label_visibility="collapsed")
            r_pc = st.number_input(f"R{i}", value=5.0, key=f"rpc_{i}", label_visibility="collapsed")
            r_ratio = st.number_input(f"Ratio{i}", value=3.0, key=f"ra_{i}", label_visibility="collapsed")
            
            if price and budget:
                res = excel_calc(price, budget, r_pc, r_ratio)
                st.write("---")
                st.success(f"目標: {res['target']:.2f}")
                st.error(f"止蝕: {res['sl']:.2f}")
                
                if st.button(f"📥 存入持倉 {i}", key=f"btn_{i}", use_container_width=True):
                    try:
                        # 準備資料，這裡的 key 必須完全對應 image_e31367.png 的欄位
                        save_data = {
                            "ticker": stock if stock else "N/A",
                            "currency": "HKD",
                            "qty": res['shares'],
                            "entry_price": price,
                            "stop_loss": res['sl'],
                            "risk_mkt": res['r']
                        }
                        # 發送
                        supabase.table("trades").insert(save_data).execute()
                        st.toast(f"✅ {stock} 存檔成功！")
                    except Exception as e:
                        st.error(f"❌ 錯誤：{str(e)}")