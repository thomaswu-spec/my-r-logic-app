import streamlit as st
import pandas as pd
from supabase import create_client, Client
import yfinance as yf
from datetime import datetime

# --- 1. 初始化連線 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Cockpit Pro", layout="wide")

# --- 2. 核心 CSS 樣式 (對齊按鈕與表格) ---
st.markdown("""
    <style>
    /* 強制按鈕對齊輸入框高度 */
    .stButton > button { margin-top: 28px !important; }
    /* 保持監控表字體大小 */
    .monitor-text { font-size: 14px; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函數 ---
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
    sl_price = p * (1 - (r_pc/100))
    tp_price = p * (1 + (r_pc/100 * ra))
    return {"r_amount": r_amount, "profit_amount": profit_amount, "shares": shares, "sl_price": sl_price, "tp_price": tp_price}

# --- 4. 登入系統 (Sidebar) ---
if 'user' not in st.session_state: st.session_state['user'] = None
st.sidebar.title("🔐 R-Logic 登入")
if st.session_state['user'] is None:
    auth_mode = st.sidebar.selectbox("模式", ["登入", "註冊"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("密碼", type="password")
    if st.sidebar.button("確認"):
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

# --- 5. 主介面邏輯 ---
user = st.session_state['user']
if user:
    st.title(f"🚀 {user.email.split('@')[0]} 的投資指揮中心")

    with st.container(border=True):
        st.subheader("📝 交易策劃 (Trade Planner)")
        # 修正按鈕對齊：將 Ticker, Date, Button 擺喺同一排
        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        with c1: tk = st.text_input("🔍 代號", placeholder="例如: 700").upper()
        with c2: trade_date = st.date_input("📅 日期", datetime.now())
        with c3:
            # 抓取現價按鈕對齊
            if tk and st.button("🔍 抓取現價", use_container_width=True):
                st.session_state['tmp_p'] = fetch_live_price(tk)
        
        p_val = st.session_state.get('tmp_p', None)
        c4, c5, c6, c7 = st.columns(4)
        with c4: pr = st.number_input("進場價", value=p_val)
        with c5: bg = st.number_input("預算", value=None)
        with c6: r_pc = st.number_input("R %", value=5.0)
        with c7: r_ratio = st.number_input("Ratio", value=3.0)

        res = calc_trade_logic(pr, bg, r_pc, r_ratio)
        if res:
            st.divider()
            res_c1, res_c2, res_c3, res_c4, res_c5 = st.columns(5)
            res_c1.metric("🔢 建議股數", f"{res['shares']} 股")
            res_c2.metric("📉 止蝕金額", f"HK$ {res['r_amount']:,.0f}")
            res_c3.metric("📈 預期利潤", f"HK$ {res['profit_amount']:,.0f}")
            res_c4.error(f"❌ 止蝕價位\n\n**{res['sl_price']:.2f}**")
            res_c5.success(f"✅ 止盈價位\n\n**{res['tp_price']:.2f}**")
            
            if st.button("📝 紀錄在你的 portfolio", type="primary", use_container_width=True):
                try:
                    supabase.table("trades").insert({
                        "ticker": tk, "currency": "HKD", "entry_price": pr, "purchase_date": str(trade_date),
                        "stop_loss": res['sl_price'], "qty": res['shares'], "risk_mkt": res['r_amount'], "user_id": user.id 
                    }).execute()
                    st.toast("✅ 紀錄成功！")
                    st.rerun()
                except Exception as e: st.error(f"錯誤: {e}")

    # --- 6. 實時持倉監控 (加回損益計算) ---
    st.divider()
    st.header("📊 持倉實時監控 (Live Monitor)")
    
    db_res = supabase.table("trades").select("*").eq("user_id", user.id).execute()
    if db_res.data:
        # 表頭
        h_cols = st.columns([1, 0.8, 0.8, 0.8, 1, 1.2, 0.8, 0.4])
        headers = ["日期/代號", "成本", "止蝕", "現價", "股數", "盈虧 (HKD)", "當前 R", ""]
        for col, head in zip(h_cols, headers): col.write(f"**{head}**")
        st.write("---")

        total_pl = 0
        for trade in db_res.data:
            live_p = fetch_live_price(trade['ticker'])
            entry_p = trade['entry_price']
            sl_p = trade['stop_loss']
            qty = trade['qty']
            
            r_cols = st.columns([1, 0.8, 0.8, 0.8, 1, 1.2, 0.8, 0.4])
            r_cols[0].write(f"{trade['purchase_date']}\n\n**{trade['ticker']}**")
            r_cols[1].write(f"{entry_p}")
            r_cols[2].write(f"{sl_p}")
            
            if live_p:
                r_cols[3].write(f"{live_p}")
                r_cols[4].write(f"{qty}")
                # 盈虧計算
                pl = (live_p - entry_p) * qty
                total_pl += pl
                pl_color = "green" if pl >= 0 else "red"
                r_cols[5].markdown(f":{pl_color}[${pl:,.1f}]")
                # R 數計算
                denom = entry_p - sl_p
                r_val = (live_p - entry_p) / denom if denom != 0 else 0
                r_cols[6].info(f"{r_val:.2f}R")
            else:
                r_cols[3].write("...")
            
            if r_cols[7].button("🗑️", key=f"d_{trade['id']}"):
                supabase.table("trades").delete().eq("id", trade['id']).execute()
                st.rerun()
        
        st.divider()
        st.metric("總未實現盈虧", f"HK$ {total_pl:,.2f}", delta=f"{total_pl:,.2f}")
    else: st.info("目前沒有持倉紀錄。")
else: st.warning("👈 請登入以開始使用。")