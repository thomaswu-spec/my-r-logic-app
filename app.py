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

# --- 2. 核心 CSS 樣式 (針對手機排版與對齊) ---
st.markdown("""
    <style>
    /* 強制監控表橫向滾動，防止手機版換行 */
    .monitor-container {
        overflow-x: auto;
        white-space: nowrap;
        width: 100%;
        border-bottom: 1px solid #444;
        padding-bottom: 10px;
    }
    /* 加大字體與調整按鈕對齊 */
    .stButton > button { margin-top: 0px !important; width: 100%; }
    .stMetric label { font-size: 14px !important; }
    
    /* 針對手機版微調列間距 */
    @media (max-width: 640px) {
        [data-testid="column"] { min-width: 120px !important; }
    }
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

# --- 4. 登入系統 (保持穩定) ---
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
    st.title(f"🚀 {user.email.split('@')[0]} 投資指揮中心")

    with st.container(border=True):
        st.subheader("📝 交易策劃")
        # 手機版對齊優化：代號、日期、按鈕
        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        with c1: tk = st.text_input("🔍 代號", placeholder="例如: 700").upper()
        with c2: trade_date = st.date_input("📅 日期", datetime.now())
        with c3:
            st.write("## ") # 手機版對齊補位
            if tk and st.button("🔍 抓現價"):
                st.session_state['tmp_p'] = fetch_live_price(tk)
        
        p_val = st.session_state.get('tmp_p', None)
        c4, c5 = st.columns(2) # 手機版改為 2 欄一組
        with c4: pr = st.number_input("進場價", value=p_val)
        with c5: bg = st.number_input("預算 (Budget)", value=None, help="數字會自動加逗號顯示在下方")
        
        c6, c7 = st.columns(2)
        with c6: r_pc = st.number_input("R %", value=5.0)
        with c7: r_ratio = st.number_input("Ratio", value=3.0)

        res = calc_trade_logic(pr, bg, r_pc, r_ratio)
        if res:
            st.divider()
            # 顯示計算結果 (加強千分位格式化)
            res_c1, res_c2, res_c3 = st.columns(3)
            res_c1.metric("🔢 建議股數", f"{res['shares']:,} 股")
            res_c2.metric("📉 止蝕金額", f"HK$ {res['r_amount']:,.0f}")
            res_c3.metric("📈 預期利潤", f"HK$ {res['profit_amount']:,.0f}")
            
            res_c4, res_c5 = st.columns(2)
            res_c4.error(f"❌ 止蝕價位\n\n**{res['sl_price']:,.2f}**")
            res_c5.success(f"✅ 止盈價位\n\n**{res['tp_price']:,.2f}**")
            
            if st.button("📝 紀錄在你的 portfolio", type="primary", use_container_width=True):
                try:
                    supabase.table("trades").insert({
                        "ticker": tk, "currency": "HKD", "entry_price": pr, "purchase_date": str(trade_date),
                        "stop_loss": res['sl_price'], "qty": res['shares'], "risk_mkt": res['r_amount'], "user_id": user.id 
                    }).execute()
                    st.toast("✅ 紀錄成功！")
                    st.rerun()
                except Exception as e: st.error(f"錯誤: {e}")

    # --- 6. 實時持倉監控 (手機橫向顯示優化) ---
    st.divider()
    st.header("📊 持倉實時監控 (Live Monitor)")
    
    db_res = supabase.table("trades").select("*").eq("user_id", user.id).order('purchase_date', desc=True).execute()
    
    if db_res.data:
        # 建立一個可滾動的容器
        st.markdown('<div class="monitor-container">', unsafe_allow_html=True)
        
        # 表頭
        h = st.columns([1.2, 0.8, 0.8, 0.8, 1, 1.2, 0.8, 0.4])
        cols_name = ["日期/代號", "成本", "止蝕", "現價", "股數", "盈虧 (HKD)", "R 數", ""]
        for col, name in zip(h, cols_name): col.write(f"**{name}**")
        st.write("---")

        total_pl = 0
        for trade in db_res.data:
            live_p = fetch_live_price(trade['ticker'])
            entry_p = trade['entry_price']
            sl_p = trade['stop_loss']
            qty = trade['qty']
            
            r = st.columns([1.2, 0.8, 0.8, 0.8, 1, 1.2, 0.8, 0.4])
            r[0].write(f"{trade['purchase_date']}\n\n**{trade['ticker']}**")
            r[1].write(f"{entry_p:,.2f}")
            r[2].write(f"{sl_p:,.2f}")
            
            if live_p:
                r[3].write(f"{live_p:,.2f}")
                r[4].write(f"{qty:,}")
                pl = (live_p - entry_p) * qty
                total_pl += pl
                pl_color = "green" if pl >= 0 else "red"
                r[5].markdown(f":{pl_color}[${pl:,.1f}]")
                denom = entry_p - sl_p
                r_val = (live_p - entry_p) / denom if denom != 0 else 0
                r[6].info(f"{r_val:.2f}R")
            else:
                r[3].write("...")
            
            if r[7].button("🗑️", key=f"d_{trade['id']}"):
                supabase.table("trades").delete().eq("id", trade['id']).execute()
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True) # 結束橫向滾動容器
        
        st.divider()
        st.metric("總未實現盈虧", f"HK$ {total_pl:,.2f}", delta=f"{total_pl:,.2f}")
    else: st.info("目前沒有持倉紀錄。")