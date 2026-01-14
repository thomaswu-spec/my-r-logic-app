import streamlit as st
import pandas as pd
from supabase import create_client, Client
import yfinance as yf # 新增實時股價工具

# --- 1. 初始化與連線 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Cockpit Pro", layout="wide")

# --- 2. 專業 CSS 樣式 (解決對齊、字體、提示問題) ---
st.markdown("""
    <style>
    /* 加大字體 */
    html, body, [class*="css"] { font-size: 18px !important; }
    /* 強制標籤行高與輸入框對齊 */
    .row-label {
        height: 65px; 
        display: flex; 
        align-items: center; 
        font-weight: bold;
        font-size: 16px;
    }
    .output-label {
        height: 48px;
        display: flex;
        align-items: center;
        font-weight: bold;
    }
    /* 調整間距 */
    [data-testid="stVerticalBlock"] { gap: 0rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函數 ---
def fetch_live_price(ticker, market="HK"):
    try:
        # 轉換代號格式 (例如 700 -> 0700.HK)
        formatted_ticker = f"{int(ticker):04d}.HK" if market == "HK" else ticker
        stock_info = yf.Ticker(formatted_ticker)
        return stock_info.fast_info['last_price']
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

st.title("🚀 R-Logic 投資指揮中心 (專業對齊版)")

# --- 4. 策劃器與對比 (5個場景) ---
# 佈局比例：左邊標籤佔 1.8，右邊每個場景佔 2
main_cols = st.columns([1.8, 2, 2, 2, 2, 2], gap="small")

with main_cols[0]:
    st.write("### ") # 對齊頂部
    st.write("---")
    st.markdown('<div class="row-label">🔍 代號 (Stock)</div>', unsafe_allow_html=True)
    st.markdown('<div class="row-label">💰 進場價 (Price)</div>', unsafe_allow_html=True)
    st.markdown('<div class="row-label">💼 預算 (Budget)</div>', unsafe_allow_html=True)
    st.markdown('<div class="row-label">⚠️ 風險 (R %)</div>', unsafe_allow_html=True)
    st.markdown('<div class="row-label">🎯 比例 (Ratio)</div>', unsafe_allow_html=True)
    st.write("---")
    st.markdown('<div class="output-label">📈 預計回報</div>', unsafe_allow_html=True)
    st.markdown('<div class="output-label">📉 預計虧損</div>', unsafe_allow_html=True)
    st.markdown('<div class="output-label">🔢 建議股數</div>', unsafe_allow_html=True)
    st.markdown('<div class="output-label">✅ 目標價</div>', unsafe_allow_html=True)
    st.markdown('<div class="output-label">❌ 止蝕價</div>', unsafe_allow_html=True)

for i in range(1, 6):
    with main_cols[i]:
        st.write(f"### {i}")
        with st.container(border=True):
            # 1. 代號輸入 (使用 placeholder，不再預設 700)
            tk = st.text_input(f"tk{i}", placeholder="請輸入代號", key=f"tk_{i}", label_visibility="collapsed").upper()
            
            # 2. 獲取實時股價按鈕
            live_p = None
            if tk:
                if st.button(f"抓取現價", key=f"fetch_{i}", use_container_width=True):
                    live_p = fetch_live_price(tk)
                    if live_p: st.toast(f"已獲取 {tk} 現價: {live_p:.2f}")
            
            # 3. 價格與預算輸入 (若抓到現價則預填)
            pr = st.number_input(f"pr{i}", value=live_p, placeholder="輸入進場價", key=f"pr_{i}", label_visibility="collapsed")
            bg = st.number_input(f"bg{i}", value=None, placeholder="輸入預算", key=f"bg_{i}", label_visibility="collapsed")
            rpc = st.number_input(f"r{i}", value=5.0, step=0.1, key=f"rpc_{i}", label_visibility="collapsed")
            rat = st.number_input(f"ra{i}", value=3.0, step=0.5, key=f"rat_{i}", label_visibility="collapsed")
            
            res = calc_logic(pr, bg, rpc, rat)
            st.write("---")
            if res:
                st.write(f"HK${res['gain']:,.0f}")
                st.write(f"HK${res['loss']:,.0f}")
                st.write(f"**{res['shares']}**")
                st.success(f"{res['target']:.2f}")
                st.error(f"{res['sl']:.2f}")
                
                if st.button(f"📥 存入 {i}", key=f"s{i}", use_container_width=True):
                    # 移除 id 欄位，讓 Supabase 自動生成
                    supabase.table("trades").insert({
                        "ticker": tk, "entry_price": pr, "stop_loss": res['sl'],
                        "qty": res['shares'], "currency": "HKD", "risk_mkt": res['loss']
                    }).execute()
                    st.rerun()
            else:
                st.info("等待數據...")

# --- 5. 底部總覽 ---
st.divider()
st.header("📊 全局持倉總覽")
db_res = supabase.table("trades").select("*").execute()
if db_res.data:
    df = pd.DataFrame(db_res.data)
    st.dataframe(df[['ticker', 'qty', 'entry_price', 'stop_loss', 'risk_mkt']], use_container_width=True)