import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- 1. 初始化與連線 ---
# 確保你的 Secrets 已經填好 SUPABASE_URL 和 SUPABASE_KEY
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Cockpit", layout="wide")

# 讀取雲端數據
def fetch_data():
    res = supabase.table("trades").select("*").execute()
    return res.data

st.title("🚀 R-Logic 投資指揮中心")

# --- 2. 頂部總覽 (Portfolio Overview) ---
db_data = fetch_data()
df = pd.DataFrame(db_data) if db_data else pd.DataFrame()

m1, m2, m3 = st.columns(3)
if not df.empty:
    m1.metric("總持倉數", f"{len(df)} 筆")
    m2.metric("總未平倉風險", f"HK${df['risk_mkt'].sum():,.0f}")
    m3.metric("資料庫狀態", "已連線", delta="同步中")

st.divider()

# --- 3. 中間層：Excel 風格策劃器 (對標 image_e1be2a.png) ---
st.subheader("📑 交易場景對比 (Scenario Planner)")
input_cols = st.columns([1, 2, 2, 2], gap="medium")

# 最左側標籤
with input_cols[0]:
    st.write("## ") # 留白對齊
    st.write("---")
    st.markdown("**🔍 代號 (Stock)**")
    st.markdown("**💰 進場價 (Price)**")
    st.markdown("**💼 預算 (Budget)**")
    st.markdown("**⚠️ 風險 (R %)**")
    st.markdown("**🎯 比例 (Ratio)**")
    st.write("---")
    st.markdown("🔢 **建議股數**")
    st.markdown("✅ **目標價 (Target)**")
    st.markdown("❌ **止蝕價 (SL)**")

# 三個對比場景
for i in range(1, 4):
    with input_cols[i]:
        st.write(f"### 場景 {i}")
        with st.container(border=True):
            # 輸入區
            s_tk = st.text_input("tk", value="700" if i==1 else "9888", key=f"tk_{i}", label_visibility="collapsed").upper()
            s_pr = st.number_input("pr", value=616.0 if i==1 else 142.8, key=f"pr_{i}", label_visibility="collapsed")
            s_bg = st.number_input("bg", value=123000.0 if i==1 else 100000.0, key=f"bg_{i}", label_visibility="collapsed")
            s_rp = st.slider("rp", 1.0, 10.0, 5.0, 0.1, key=f"rp_{i}", label_visibility="collapsed")
            s_ra = st.number_input("ra", value=3.0 if i==1 else 2.0, key=f"ra_{i}", label_visibility="collapsed")
            
            # 計算公式 (對標你的 Excel)
            r_budget = s_bg * (s_rp / 100)
            shares = int(s_bg / s_pr) if s_pr > 0 else 0
            target = s_pr * (1 + (s_rp/100 * s_ra))
            sl = s_pr * (1 - (s_rp/100))
            
            st.write("---")
            # 輸出區
            st.write(f"**{shares}** 股")
            st.success(f"**{target:,.2f}**")
            st.error(f"**{sl:,.2f}**")
            
            if st.button(f"📥 存入持倉 {i}", key=f"save_{i}", use_container_width=True):
                supabase.table("trades").insert({
                    "ticker": s_tk, "entry_price": s_pr, "stop_loss": sl,
                    "qty": shares, "currency": "HKD", "risk_mkt": r_budget
                }).execute()
                st.rerun()

st.divider()

# --- 4. 底部層：實時監控 (Friendly Input) ---
st.subheader("🔍 持倉管理與現價更新")
if not df.empty:
    for i, row in df.iterrows():
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
            c1.markdown(f"#### {row['ticker']}")
            c1.caption(f"成本: {row['entry_price']}")
            
            # 友好的現價輸入
            curr_p = c2.number_input(f"最新價格", value=float(row['entry_price']), key=f"live_{i}")
            
            # 計算 R 數
            dist = (curr_p - row['entry_price']) / (row['entry_price'] - row['stop_loss'])
            color = "green" if dist >= 0 else "red"
            c3.markdown(f"### 當前進度: :{color}[{dist:.2f} R]")
            
            if c4.button("🗑️", key=f"del_{i}"):
                supabase.table("trades").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.info("尚未有持倉數據，請從上方場景策劃器存入。")