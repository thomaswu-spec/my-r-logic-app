import streamlit as st
import pandas as pd
from supabase import create_client, Client
import yfinance as yf
from datetime import datetime
import extra_streamlit_components as stx

# --- 1. 初始化連線 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Cockpit Pro", layout="wide")

# --- 2. 核心 CSS 樣式 ---
st.markdown("""
    <style>
    .big-price { font-size: 32px !important; font-weight: 800 !important; line-height: 1.1; }
    div[data-testid="column"] button { margin-top: -10px !important; }
    .live-ref-text { font-size: 18px; color: #3498db; font-weight: bold; margin-left: 10px; padding-top: 5px; }
    .monitor-wrapper {
        overflow-x: auto;
        white-space: nowrap;
        display: block;
        width: 100%;
        padding: 10px 0;
    }
    @media (max-width: 640px) {
        .stMetric div { font-size: 18px !important; }
        .big-price { font-size: 24px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函數 ---
@st.cache_data(ttl=60)
def get_live_info(ticker):
    try:
        # 自動識別港股/美股/加密貨幣
        if ticker.isdigit():
            formatted = f"{int(ticker):04d}.HK"
        else:
            formatted = ticker
            
        stock = yf.Ticker(formatted)
        
        # 修正：改用 history 確保在非開盤時間也能拿到最後收盤價
        hist = stock.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
        else:
            # 備用方案：fast_info
            price = stock.fast_info.get('last_price', None)
            
        return {
            "name": stock.info.get('shortName') or stock.info.get('longName') or ticker,
            "price": round(price, 3) if price else None
        }
    except Exception as e:
        return {"name": f"Error: {str(e)}", "price": None}

def calc_trade_logic(p, b, r_pc, ra):
    if not p or not b: return None
    r_amt = b * (r_pc / 100) 
    g_amt = r_amt * ra
    shares = int(b / p) if p > 0 else 0
    sl_p = p * (1 - (r_pc/100))
    tp_p = p * (1 + (r_pc/100 * ra))
    return {"r": r_amt, "g": g_amt, "s": shares, "sl": sl_p, "tp": tp_p}

# --- 4. 自動登入邏輯 (Cookie) ---
cookie_manager = stx.CookieManager()
if 'user' not in st.session_state: st.session_state['user'] = None

saved_token = cookie_manager.get("sb-access-token")
if not st.session_state['user'] and saved_token:
    try:
        res = supabase.auth.get_user(saved_token)
        if res.user: st.session_state['user'] = res.user
    except: pass

# --- 5. 側邊欄：登入系統 ---
st.sidebar.title("🔐 R-Logic 帳戶")
if st.session_state['user'] is None:
    auth_mode = st.sidebar.selectbox("模式", ["登入", "註冊新帳號"])
    email = st.sidebar.text_input("Email")
    pw = st.sidebar.text_input("密碼", type="password")
    if st.sidebar.button("確認執行", use_container_width=True):
        try:
            if auth_mode == "登入":
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state['user'] = res.user
                cookie_manager.set("sb-access-token", res.session.access_token, expires_at=datetime.now().timestamp() + 604800)
            else:
                supabase.auth.sign_up({"email": email, "password": pw})
                st.sidebar.success("註冊成功！")
            st.rerun()
        except: st.sidebar.error("驗證失敗")
else:
    st.sidebar.write(f"當前用戶: {st.session_state['user'].email}")
    if st.sidebar.button("登出帳戶", use_container_width=True):
        cookie_manager.delete("sb-access-token")
        supabase.auth.sign_out()
        st.session_state['user'] = None
        st.rerun()

# --- 6. 主程式內容 ---
user = st.session_state['user']
if user:
    st.title(f"🚀 {user.email.split('@')[0]} 的投資指揮中心")

    with st.container(border=True):
        st.subheader("📝 交易策劃 (Planner)")
        r1_c1, r1_c2 = st.columns(2)
        with r1_c1: tk = st.text_input("🔍 股票代號", placeholder="例如: 700").upper()
        with r1_c2: trade_date = st.date_input("📅 交易日期", datetime.now())
        
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
        with r2_c1:
            p_val = st.session_state.get('tmp_p', 0.0)
            pr = st.number_input("💰 進場價格", value=float(p_val) if p_val else 0.0, format="%.3f")
            btn_col, ref_col = st.columns([1, 1.5])
            with btn_col:
                if tk and st.button("🔍 抓取現價", use_container_width=True):
                    info = get_live_info(tk)
                    st.session_state['tmp_p'] = info['price']
                    st.session_state['tmp_n'] = info['name']
                    st.rerun()
            with ref_col:
                if st.session_state.get('tmp_p'):
                    st.markdown(f'<div class="live-ref-text">Ref: {st.session_state["tmp_p"]}</div>', unsafe_allow_html=True)
        
        with r2_c2: bg = st.number_input("💼 預算 (Budget)", value=0.0)
        with r2_c3: r_pc = st.number_input("⚠️ 風險 (R %)", value=5.0)
        with r2_c4: r_ratio = st.number_input("🎯 Ratio", value=3.0)

        res = calc_trade_logic(pr, bg, r_pc, r_ratio)
        if res and pr > 0:
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("🔢 建議股數", f"{res['s']:,} 股")
            m2.metric("📈 預期利潤", f"HK$ {res['g']:,.0f}")
            m3.metric("📉 止蝕金額 (1R)", f"HK$ {res['r']:,.0f}")
            
            v_tp, v_sl = st.columns(2)
            with v_tp:
                st.markdown(f'''<div style="background-color:#dcfce7; padding:15px; border-radius:10px; border-left:5px solid #22c55e;">
                    <span style="color:#15803d; font-size:14px;">✅ 止盈價位 (Target)</span><br>
                    <span class="big-price" style="color:#22c55e;">{res['tp']:,.2f}</span>
                </div>''', unsafe_allow_html=True)
            with v_sl:
                st.markdown(f'''<div style="background-color:#fee2e2; padding:15px; border-radius:10px; border-left:5px solid #ef4444;">
                    <span style="color:#b91c1c; font-size:14px;">❌ 止蝕價位 (Cut Loss)</span><br>
                    <span class="big-price" style="color:#ef4444;">{res['sl']:,.2f}</span>
                </div>''', unsafe_allow_html=True)
            
            st.write("## ")
            if st.button("📝 紀錄在你的 portfolio", type="primary", use_container_width=True):
                try:
                    supabase.table("trades").insert({
                        "ticker": tk, "currency": "HKD", "entry_price": pr, "purchase_date": str(trade_date),
                        "stop_loss": res['sl'], "target_price": res['tp'], "qty": res['s'], "risk_mkt": res['r'], "user_id": user.id 
                    }).execute()
                    st.toast("✅ 紀錄成功！")
                    st.rerun()
                except Exception as e: st.error(f"存檔失敗: {e}")
        else:
            st.info("💡 請輸入代號、價格及預算以顯示策劃詳情。")

    # --- 7. 實時持倉監控 ---
    st.divider()
    st.header("📊 持倉實時監控 (Live Monitor)")
    db_res = supabase.table("trades").select("*").eq("user_id", user.id).order('purchase_date', desc=True).execute()
    
    if db_res.data:
        st.markdown('<div class="monitor-wrapper">', unsafe_allow_html=True)
        # 調整列寬分配
        h = st.columns([1.5, 0.8, 0.8, 0.8, 0.8, 0.8, 1.2, 0.8, 0.4])
        cols_name = ["股票/名稱", "現價", "目標", "止蝕", "股數", "成本", "盈虧(HKD)", "R 數", "操作"]
        for col, name in zip(h, cols_name): col.write(f"**{name}**")
        
        total_pl = 0
        for trade in db_res.data:
            info = get_live_info(trade['ticker'])
            lp, en, sl, tp, qty = info['price'], trade['entry_price'], trade['stop_loss'], trade.get('target_price',0), trade['qty']
            
            r = st.columns([1.5, 0.8, 0.8, 0.8, 0.8, 0.8, 1.2, 0.8, 0.4])
            r[0].markdown(f"**{trade['ticker']}**<br><span style='font-size:11px; color:#888;'>{info['name']}</span>", unsafe_allow_html=True)
            
            # 修正變量名稱：將原來的 entry_p 改為 en
            if lp:
                r[1].write(f"**{lp:,.2f}**")
                r[2].write(f"{tp:,.2f}")
                r[3].write(f"{sl:,.2f}")
                r[4].write(f"{qty:,}")
                r[5].write(f"{en:,.2f}") # 這裡修正了 Bug
                pl = (lp - en) * qty
                total_pl += pl
                r[6].markdown(f":{'green' if pl>=0 else 'red'}[${pl:,.1f}]")
                denom = en - sl
                r[7].info(f"{(lp-en)/denom if denom!=0 else 0:.2f}R")
            else:
                # 如果沒有現價，顯示基礎數據，避免整行空白
                r[1].write("N/A")
                r[2].write(f"{tp:,.2f}")
                r[3].write(f"{sl:,.2f}")
                r[4].write(f"{qty:,}")
                r[5].write(f"{en:,.2f}")
                r[6].write("--")
                r[7].write("--")
            
            if r[8].button("🗑️", key=f"d_{trade['id']}"):
                supabase.table("trades").delete().eq("id", trade['id']).execute()
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()
        st.metric("總未實現盈虧", f"HK$ {total_pl:,.2f}", delta=f"{total_pl:,.2f}")
    else: 
        st.info("目前沒有持倉紀錄。")
else:
    st.warning("👈 請在側邊欄登入以開始使用。")