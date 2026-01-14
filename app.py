import streamlit as st
import pandas as pd
from supabase import create_client, Client
import yfinance as yf
from datetime import datetime

# --- 1. 初始化連線 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Cockpit", layout="wide")

# --- 2. 核心功能函數 ---
def fetch_live_price(ticker):
    try:
        formatted_ticker = f"{int(ticker):04d}.HK" if ticker.isdigit() else ticker
        stock = yf.Ticker(formatted_ticker)
        return round(stock.fast_info['last_price'], 3)
    except: return None

def calc_trade_logic(p, b, r_pc, ra):
    if not p or not b: return None
    r_amount = b * (r_pc / 100) 
    shares = int(b / p) if p > 0 else 0
    sl_price = p * (1 - (r_pc/100))
    tp_price = p * (1 + (r_pc/100 * ra))
    return {"r_amount": r_amount, "shares": shares, "sl_price": sl_price, "tp_price": tp_price}

# --- 3. 多用戶登入系統 (Login System) ---
st.sidebar.title("🔐 R-Logic 登入")
auth_mode = st.sidebar.selectbox("模式", ["登入", "新用戶註冊"])
email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("密碼", type="password")

user = None

if auth_mode == "登入":
    if st.sidebar.button("登入"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state['user'] = res.user
            st.sidebar.success("登入成功！")
            st.rerun()
        except: st.sidebar.error("登入失敗，請檢查 Email 或密碼")
else:
    if st.sidebar.button("註冊"):
        try:
            supabase.auth.sign_up({"email": email, "password": password})
            st.sidebar.info("註冊信已寄出，請檢查 Email 驗證。")
        except: st.sidebar.error("註冊失敗")

# 檢查 Session 狀態
if 'user' in st.session_state:
    user = st.session_state['user']
    if st.sidebar.button("登出"):
        del st.session_state['user']
        st.rerun()

# --- 4. 主程式邏輯 (只有登入後才顯示) ---
if user:
    st.title(f"🚀 {email.split('@')[0]} 的投資指揮中心")

    with st.container(border=True):
        st.subheader("📝 交易策劃")
        col1, col2 = st.columns(2)
        with col1: tk = st.text_input("🔍 代號", placeholder="例如: 700").upper()
        with col2: trade_date = st.date_input("📅 日期", datetime.now())
        
        # 抓取現價邏輯
        if tk and st.button("🔍 抓取現價", use_container_width=True):
            st.session_state['tmp_p'] = fetch_live_price(tk)
        
        p_val = st.session_state.get('tmp_p', None)
        c3, c4, c5, c6 = st.columns(4)
        with c3: pr = st.number_input("進場價", value=p_val)
        with c4: bg = st.number_input("預算", value=None)
        with c5: r_pc = st.number_input("R %", value=5.0)
        with c6: r_ratio = st.number_input("Ratio", value=3.0)

        res = calc_trade_logic(pr, bg, r_pc, r_ratio)
        if res:
            st.divider()
            # 顯示計算結果
            st.button("📝 紀錄在你的 portfolio", type="primary", use_container_width=True, on_click=lambda: 
                supabase.table("trades").insert({
                    "ticker": tk, "entry_price": pr, "stop_loss": res['sl_price'],
                    "qty": res['shares'], "risk_mkt": res['r_amount'],
                    "purchase_date": str(trade_date), "user_id": user.id # 儲存用戶 ID
                }).execute()
            )

    # --- 5. 持倉實時監控 (只睇返自己嘅 record) ---
    st.divider()
    st.header("📊 持倉實時監控 (Live Monitor)")
    
    # 呢度係關鍵：只 select 屬於目前 user.id 嘅資料
    db_res = supabase.table("trades").select("*").eq("user_id", user.id).execute()
    
    if db_res.data:
        # (呢度保留之前嘅 HTML/CSS 橫向排版代碼，為咗簡潔省略，但記得功能要齊)
        for trade in db_res.data:
            # 修復咗嘅刪除掣 (拎走咗 size 參數)
            if st.button(f"🗑️ 刪除 {trade['ticker']}", key=f"d_{trade['id']}"):
                supabase.table("trades").delete().eq("id", trade['id']).execute()
                st.rerun()
else:
    st.warning("👈 請喺側邊欄登入以查看你的 Portfolio。")