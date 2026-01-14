import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- 1. 初始化 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Cockpit", layout="wide")

# --- 2. CSS 強制對齊工具 ---
st.markdown("""
    <style>
    [data-testid="stVerticalBlock"] { gap: 0rem; }
    .label-font { font-weight: bold; height: 62px; display: flex; align-items: center; }
    .output-font { height: 45px; display: flex; align-items: center; color: #00ff00; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心邏輯 ---
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

# --- 4. 策劃器與對比 (5個場景) ---
tabs = st.columns([1.5, 2, 2, 2, 2, 2], gap="small")

labels = [
    "🔍 交易代號 (Stock)", "💰 進場價格 (Price)", "💼 投入預算 (Budget)", 
    "⚠️ 風險比例 (R %)", "🎯 風險回報比 (Ratio)"
]

with tabs[0]:
    st.write("### ") # 頂部對齊
    st.write("---")
    for lbl in labels:
        st.markdown(f'<div class="label-font">{lbl}</div>', unsafe_allow_html=True)
    st.write("---")
    st.markdown("**預計回報 HK$**")
    st.markdown("**預計虧損 HK$**")
    st.markdown("**建議股數**")
    st.markdown("**目標價 (Target)**")
    st.markdown("**止蝕價 (SL)**")

for i in range(1, 6):
    with tabs[i]:
        st.subheader(f"場景 {i}")
        with st.container(border=True):
            tk = st.text_input(f"tk{i}", placeholder="Input...", key=f"tk_{i}", label_visibility="collapsed").upper()
            pr = st.number_input(f"pr{i}", value=None, placeholder="0.00", key=f"pr_{i}", label_visibility="collapsed")
            bg = st.number_input(f"bg{i}", value=None, placeholder="0.00", key=f"bg_{i}", label_visibility="collapsed")
            rpc = st.number_input(f"r{i}", value=5.0, key=f"rpc_{i}", label_visibility="collapsed")
            rat = st.number_input(f"ra{i}", value=3.0, key=f"rat_{i}", label_visibility="collapsed")
            
            res = calc_logic(pr, bg, rpc, rat)
            st.write("---")
            if res:
                st.write(f"**{res['gain']:,.0f}**")
                st.write(f"**{res['loss']:,.0f}**")
                st.write(f"**{res['shares']}**")
                st.success(f"{res['target']:.2f}")
                st.error(f"{res['sl']:.2f}")
                
                if st.button(f"📥 存入 {i}", key=f"s{i}", use_container_width=True):
                    supabase.table("trades").insert({
                        "ticker": tk if tk else "N/A", "entry_price": pr,
                        "stop_loss": res['sl'], "qty": res['shares'],
                        "currency": "HKD", "risk_mkt": res['loss']
                    }).execute()
                    st.toast("✅ 數據已同步至雲端")
            else:
                st.info("待輸入...")

# --- 5. 持倉總覽 (Summary Section) ---
st.divider()
st.header("📊 全局持倉總覽 (Portfolio Summary)")

try:
    db_res = supabase.table("trades").select("*").execute()
    if db_res.data:
        df = pd.DataFrame(db_res.data)
        
        # 顯示統計卡片
        c1, c2, c3 = st.columns(3)
        c1.metric("總持倉數", f"{len(df)} 筆")
        c2.metric("總未平倉風險", f"HK$ {df['risk_mkt'].sum():,.2f}")
        c3.metric("平均 R 規模", f"HK$ {df['risk_mkt'].mean():,.0f}")
        
        # 顯示清單
        st.dataframe(df[['ticker', 'qty', 'entry_price', 'stop_loss', 'risk_mkt']], use_container_width=True)
    else:
        st.write("📭 目前雲端沒有持倉紀錄。")
except Exception as e:
    st.error(f"無法讀取數據: {e}")