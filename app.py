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

# --- 3. 登入系統 (Sidebar) ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

st.sidebar.title("🔐 R-Logic 登入")
if st.session_state['user'] is None:
    auth_mode = st.sidebar.selectbox("模式", ["登入", "新用戶註冊"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("密碼", type="password")

    if auth_mode == "登入":
        if st.sidebar.button("確認登入", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state['user'] = res.user
                st.rerun()
            except: st.sidebar.error("Email 或密碼錯誤")
    else:
        if st.sidebar.button("立即註冊", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.sidebar.success("註冊成功！請檢查 Email 驗證（如已關閉驗證可直接登入）")
            except: st.sidebar.error("註冊失敗")
else:
    st.sidebar.write(f"當前用戶: {st.session_state['user'].email}")
    if st.sidebar.button("登出"):
        supabase.auth.sign_out()
        st.session_state['user'] = None
        st.rerun()

# --- 4. 主程式邏輯 ---
user = st.session_state['user']

if user:
    st.title(f"🚀 {user.email.split('@')[0]} 的投資指揮中心")

    with st.container(border=True):
        st.subheader("📝 交易策劃")
        c1, c2 = st.columns(2)
        with c1: tk = st.text_input("🔍 代號", placeholder="例如: 700").upper()
        with c2: trade_date = st.date_input("📅 日期", datetime.now())
        
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
            # 【修復版代碼：紀錄按鈕】
            if st.button("📝 紀錄在你的 portfolio", type="primary", use_container_width=True):
                try:
                    supabase.table("trades").insert({
                        "ticker": tk, "entry_price": pr, "stop_loss": res['sl_price'],
                        "qty": res['shares'], "risk_mkt": res['r_amount'],
                        "purchase_date": str(trade_date), "user_id": user.id 
                    }).execute()
                    st.toast("✅ 紀錄成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"存檔失敗: {e}")

    # --- 5. 持倉監控 ---
    st.divider()
    st.header("📊 持倉實時監控 (Live Monitor)")
    db_res = supabase.table("trades").select("*").eq("user_id", user.id).execute()
    
    if db_res.data:
        # 顯示表格 (此處簡化處理，你可以套用返之前嘅 HTML CSS 單行排版)
        df = pd.DataFrame(db_res.data)
        st.dataframe(df[['purchase_date', 'ticker', 'qty', 'entry_price', 'stop_loss']], use_container_width=True)
        
        for trade in db_res.data:
            if st.button(f"🗑️ 刪除 {trade['ticker']} (ID:{trade['id']})", key=f"d_{trade['id']}"):
                supabase.table("trades").delete().eq("id", trade['id']).execute()
                st.rerun()
else:
    st.warning("👈 請喺左邊側邊欄登入以開始使用。")