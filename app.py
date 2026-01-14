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

# --- 2. 核心 CSS 樣式 (解決對齊、大字體、手機單行) ---
st.markdown("""
    <style>
    .big-price { font-size: 30px !important; font-weight: 800 !important; line-height: 1.2; }
    div[data-testid="column"]:nth-of-type(3) button { margin-top: 31px !important; }
    
    /* 強制單行顯示並允許橫向捲動 */
    .monitor-wrapper {
        overflow-x: auto;
        white-space: nowrap;
        display: block;
        width: 100%;
        padding: 10px 0;
    }
    
    /* 加大表格字體 */
    .monitor-row { font-size: 15px !important; }

    @media (max-width: 640px) {
        div[data-testid="column"]:nth-of-type(3) button { margin-top: 0px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函數 ---
@st.cache_data(ttl=3600) # 緩存股票名稱，減少 API 請求
def get_stock_details(ticker):
    try:
        formatted = f"{int(ticker):04d}.HK" if ticker.isdigit() else ticker
        stock = yf.Ticker(formatted)
        return {
            "name": stock.info.get('longName', 'Unknown'),
            "price": round(stock.fast_info['last_price'], 3)
        }
    except: return {"name": "N/A", "price": None}

def calc_trade_logic(p, b, r_pc, ra):
    if not p or not b: return None
    r_amt = b * (r_pc / 100) 
    g_amt = r_amt * ra
    shares = int(b / p) if p > 0 else 0
    sl_p = p * (1 - (r_pc/100))
    tp_p = p * (1 + (r_pc/100 * ra))
    return {"r": r_amt, "g": g_amt, "s": shares, "sl": sl_p, "tp": tp_p}

# --- 4. 登入系統 ---
if 'user' not in st.session_state: st.session_state['user'] = None
st.sidebar.title("🔐 R-Logic 登入")
if st.session_state['user'] is None:
    auth_mode = st.sidebar.selectbox("模式", ["登入", "註冊"])
    email = st.sidebar.text_input("Email")
    pw = st.sidebar.text_input("密碼", type="password")
    if st.sidebar.button("確認"):
        try:
            if auth_mode == "登入":
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state['user'] = res.user
            else:
                supabase.auth.sign_up({"email": email, "password": pw})
                st.sidebar.success("註冊成功！")
            st.rerun()
        except: st.sidebar.error("驗證失敗")
else:
    st.sidebar.write(f"用戶: {st.session_state['user'].email}")
    if st.sidebar.button("登出"):
        st.session_state['user'] = None
        st.rerun()

# --- 5. 主程式 ---
user = st.session_state['user']
if user:
    st.title(f"🚀 {user.email.split('@')[0]} 投資指揮中心")

    with st.container(border=True):
        st.subheader("📝 交易策劃")
        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        with c1: tk = st.text_input("🔍 代號", placeholder="例如: 700").upper()
        with c2: trade_date = st.date_input("📅 日期", datetime.now())
        with c3:
            if tk and st.button("🔍 抓取現價", use_container_width=True):
                details = get_stock_details(tk)
                st.session_state['tmp_p'] = details['price']
        
        p_val = st.session_state.get('tmp_p', None)
        c4, c5, c6, c7 = st.columns(4)
        with c4: pr = st.number_input("進場價", value=p_val)
        with c5: bg = st.number_input("預算 (Budget)", value=None)
        with c6: r_pc = st.number_input("R %", value=5.0)
        with c7: r_ratio = st.number_input("Ratio", value=3.0)

        res = calc_trade_logic(pr, bg, r_pc, r_ratio)
        if res:
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("建議股數", f"{res['s']:,} 股")
            m2.metric("止蝕金額", f"HK$ {res['r']:,.0f}")
            m3.metric("預期利潤", f"HK$ {res['g']:,.0f}")
            
            r_sl, r_tp = st.columns(2)
            with r_sl:
                st.markdown(f'''<div style="background-color:#fee2e2; padding:15px; border-radius:10px; border-left:5px solid #ef4444;">
                    <span style="color:#b91c1c; font-size:14px;">❌ 止蝕價位</span><br>
                    <span class="big-price" style="color:#ef4444;">{res['sl']:,.2f}</span>
                </div>''', unsafe_allow_html=True)
            with r_tp:
                st.markdown(f'''<div style="background-color:#dcfce7; padding:15px; border-radius:10px; border-left:5px solid #22c55e;">
                    <span style="color:#15803d; font-size:14px;">✅ 止盈價位</span><br>
                    <span class="big-price" style="color:#22c55e;">{res['tp']:,.2f}</span>
                </div>''', unsafe_allow_html=True)
            
            if st.button("📝 紀錄在你的 portfolio", type="primary", use_container_width=True):
                try:
                    supabase.table("trades").insert({
                        "ticker": tk, "currency": "HKD", "entry_price": pr, "purchase_date": str(trade_date),
                        "stop_loss": res['sl'], "target_price": res['tp'], "qty": res['s'], "risk_mkt": res['r'], "user_id": user.id 
                    }).execute()
                    st.toast("✅ 紀錄成功！")
                    st.rerun()
                except Exception as e: st.error(f"錯誤: {e}")

    # --- 6. 實時持倉監控 (重新排版) ---
    st.divider()
    st.header("📊 持倉實時監控 (Live Monitor)")
    
    db_res = supabase.table("trades").select("*").eq("user_id", user.id).order('purchase_date', desc=True).execute()
    
    if db_res.data:
        st.markdown('<div class="monitor-wrapper">', unsafe_allow_html=True)
        
        # 重新排列標題：股票名稱 -> 現價 -> 目標價 -> 止蝕價 -> 股數 -> 成本 -> 盈虧 -> R 數
        h = st.columns([1.8, 0.8, 0.8, 0.8, 0.6, 0.8, 1, 0.8, 0.4])
        cols_name = ["股票 (名稱)", "現價", "目標", "止蝕", "股數", "成本", "盈虧(HKD)", "R 數", ""]
        for col, name in zip(h, cols_name): col.write(f"**{name}**")
        
        total_pl = 0
        for trade in db_res.data:
            details = get_stock_details(trade['ticker'])
            live_p = details['price']
            entry_p = trade['entry_price']
            sl_p = trade['stop_loss']
            tp_p = trade.get('target_price', 0) # 獲取目標價
            qty = trade['qty']
            
            r = st.columns([1.8, 0.8, 0.8, 0.8, 0.6, 0.8, 1, 0.8, 0.4])
            
            # 1. 股票名稱 + 代號
            r[0].markdown(f"**{trade['ticker']}**<br><span style='font-size:12px; color:#888;'>{details['name']}</span>", unsafe_allow_html=True)
            
            if live_p:
                # 2. 現價
                r[1].write(f"**{live_p:,.2f}**")
                # 3. 目標價
                r[2].write(f"{tp_p:,.2f}")
                # 4. 止蝕價
                r[3].write(f"{sl_p:,.2f}")
                # 5. 股數
                r[4].write(f"{qty:,}")
                # 6. 成本
                r[5].write(f"{entry_p:,.2f}")
                
                # 7. 盈虧
                pl = (live_p - entry_p) * qty
                total_pl += pl
                pl_color = "green" if pl >= 0 else "red"
                r[6].markdown(f":{pl_color}[${pl:,.1f}]")
                
                # 8. R 數
                denom = entry_p - sl_p
                r_val = (live_p - entry_p) / denom if denom != 0 else 0
                r[7].info(f"{r_val:.2f}R")
            else:
                for i in range(1, 8): r[i].write("...")
            
            if r[8].button("🗑️", key=f"d_{trade['id']}"):
                supabase.table("trades").delete().eq("id", trade['id']).execute()
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()
        st.metric("總計未實現盈虧", f"HK$ {total_pl:,.2f}", delta=f"{total_pl:,.2f}")
    else: st.info("目前沒有持倉紀錄。")