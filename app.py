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

# --- 2. 核心計算與抓取功能 ---
def fetch_live_price(ticker):
    try:
        formatted_ticker = f"{int(ticker):04d}.HK" if ticker.isdigit() else ticker
        stock = yf.Ticker(formatted_ticker)
        return round(stock.fast_info['last_price'], 3)
    except: return None

def calc_trade_logic(p, b, r_pc, ra):
    if not p or not b: return None
    r_amount = b * (r_pc / 100) 
    profit_amount = r_amount * ra
    shares = int(b / p) if p > 0 else 0
    # 止蝕位：Entry Price 跌 R%
    sl_price = p * (1 - (r_pc/100))
    # 止盈位：Entry Price 升 (R% * Ratio)
    tp_price = p * (1 + (r_pc/100 * ra))
    return {
        "r_amount": r_amount, 
        "profit_amount": profit_amount,
        "shares": shares, 
        "sl_price": sl_price, 
        "tp_price": tp_price
    }

# --- 3. 登入系統 (保持穩定) ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

st.sidebar.title("🔐 R-Logic 登入")
if st.session_state['user'] is None:
    auth_mode = st.sidebar.selectbox("模式", ["登入", "新用戶註冊"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("密碼", type="password")
    if st.sidebar.button("確認", use_container_width=True):
        try:
            if auth_mode == "登入":
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state['user'] = res.user
            else:
                supabase.auth.sign_up({"email": email, "password": password})
                st.sidebar.success("註冊成功！")
            st.rerun()
        except: st.sidebar.error("驗證失敗")
else:
    st.sidebar.write(f"用戶: {st.session_state['user'].email}")
    if st.sidebar.button("登出"):
        st.session_state['user'] = None
        st.rerun()

# --- 4. 主介面邏輯 ---
user = st.session_state['user']

if user:
    st.title(f"🚀 {user.email.split('@')[0]} 的投資指揮中心")

    with st.container(border=True):
        st.subheader("📝 交易策劃 (Trade Planner)")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1: tk = st.text_input("🔍 代號", placeholder="例如: 700").upper()
        with c2: trade_date = st.date_input("📅 日期", datetime.now())
        with c3:
            st.write("## ")
            if tk and st.button("🔍 抓取現價", use_container_width=True):
                st.session_state['tmp_p'] = fetch_live_price(tk)
        
        p_val = st.session_state.get('tmp_p', None)
        c4, c5, c6, c7 = st.columns(4)
        with c4: pr = st.number_input("進場價", value=p_val)
        with c5: bg = st.number_input("預算", value=None)
        with c6: r_pc = st.number_input("R %", value=5.0)
        with c7: r_ratio = st.number_input("Ratio", value=3.0)

        # --- 重要：加返之前消失咗嘅計算結果顯示 ---
        res = calc_trade_logic(pr, bg, r_pc, r_ratio)
        if res:
            st.divider()
            res_c1, res_c2, res_c3, res_c4, res_c5 = st.columns(5)
            res_c1.metric("🔢 建議股數", f"{res['shares']} 股")
            res_c2.metric("📉 止蝕金額", f"HK$ {res['r_amount']:,.0f}")
            res_c3.metric("📈 預期利潤", f"HK$ {res['profit_amount']:,.0f}")
            # 用紅色同綠色標出價位
            res_c4.error(f"❌ 止蝕價位\n\n**{res['sl_price']:.2f}**")
            res_c5.success(f"✅ 止盈價位\n\n**{res['tp_price']:.2f}**")
            
            # --- 修正後的存檔按鈕 ---
            if st.button("📝 紀錄在你的 portfolio", type="primary", use_container_width=True):
                try:
                    supabase.table("trades").insert({
                        "ticker": tk, 
                        "currency": "HKD", # 補返呢行解決 Error
                        "entry_price": pr, 
                        "stop_loss": res['sl_price'],
                        "qty": res['shares'], 
                        "risk_mkt": res['r_amount'],
                        "purchase_date": str(trade_date), 
                        "user_id": user.id 
                    }).execute()
                    st.toast("✅ 紀錄成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"存檔失敗: {e}")
        else:
            st.info("💡 請輸入進場價與預算以顯示策劃詳情。")

    # --- 5. 持倉實時監控 ---
    st.divider()
    st.header("📊 持倉實時監控")
    db_res = supabase.table("trades").select("*").eq("user_id", user.id).execute()
    if db_res.data:
        df = pd.DataFrame(db_res.data)
        st.dataframe(df[['purchase_date', 'ticker', 'qty', 'entry_price', 'stop_loss']], use_container_width=True)
        for trade in db_res.data:
            if st.button(f"🗑️ 刪除 {trade['ticker']} (ID:{trade['id']})", key=f"d_{trade['id']}"):
                supabase.table("trades").delete().eq("id", trade['id']).execute()
                st.rerun()
else:
    st.warning("👈 請喺左邊側邊欄登入以開始使用。")