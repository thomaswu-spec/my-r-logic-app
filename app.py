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
    /* 1. 加大止蝕止盈數字 */
    .big-price { font-size: 32px !important; font-weight: 800 !important; line-height: 1.1; }
    
    /* 2. 抓取現價按鈕樣式 - 貼近輸入框 */
    div[data-testid="column"] button { margin-top: -5px !important; }

    /* 3. 藍色現價 Reference 文字 */
    .live-ref-text { font-size: 18px; color: #3498db; font-weight: bold; margin-left: 10px; padding-top: 5px; }

    /* 4. 強制 Live Monitor 保持單行，手機版可橫向捲動 */
    .monitor-wrapper {
        overflow-x: auto;
        white-space: nowrap;
        display: block;
        width: 100%;
        padding: 10px 0;
    }
    
    /* 5. 手機版微調 */
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

# --- 4. 登入系統 (Sidebar) ---
if 'user' not in st.session_state: st.session_state['user'] = None
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
            else:
                supabase.auth.sign_up({"email": email, "password": pw})
                st.sidebar.success("註冊成功！")
            st.rerun()
        except: st.sidebar.error("驗證失敗，請檢查輸入")
else:
    st.sidebar.write(f"當前用戶: {st.session_state['user'].email}")
    if st.sidebar.button("登出帳戶", use_container_width=True):
        st.session_state['user'] = None
        st.rerun()

# --- 5. 主程式 ---
user = st.session_state['user']
if user:
    st.title(f"🚀 {user.email.split('@')[0]} 的投資指揮中心")

    with st.container(border=True):
        st.subheader("📝 交易策劃 (Planner)")
        # 第一排：代號同日期
        r1_c1, r1_c2 = st.columns(2)
        with r1_c1: tk = st.text_input("🔍 股票代號", placeholder="例如: 700").upper()
        with r1_c2: trade_date = st.date_input("📅 交易日期", datetime.now())
        
        # 第二排：進場價(連按鈕)、預算、R%、Ratio
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
        with r2_c1:
            p_val = st.session_state.get('tmp_p', None)
            pr = st.number_input("💰 進場價格", value=p_val, format="%.3f")
            
            # 按鈕位執正：擺喺進場價下面
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
        
        with r2_c2: bg = st.number_input("💼 預算 (Budget)", value=None)
        with r2_c3: r_pc = st.number_input("⚠️ 風險 (R %)", value=5.0)
        with r2_c4: r_ratio = st.number_input("🎯 Ratio", value=3.0)

        res = calc_trade_logic(pr, bg, r_pc, r_ratio)
        if res:
            st.divider()
            # 指標顯示 (左：利潤 | 右：止蝕)
            m1, m2, m3 = st.columns(3)
            m1.metric("🔢 建議股數", f"{res['s']:,} 股")
            m2.metric("📈 預期利潤", f"HK$ {res['g']:,.0f}")
            m3.metric("📉 止蝕金額 (1R)", f"HK$ {res['r']:,.0f}")
            
            # 價位顯示 (左：止盈 | 右：止蝕)
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
                except Exception as e: st.error(f"存檔失敗 (請確保 Supabase 已加 target_price 欄位): {e}")

    # --- 6. 實時持倉監控 (重點：排版順序) ---
    st.divider()
    st.header("📊 持倉實時監控 (Live Monitor)")
    
    db_res = supabase.table("trades").select("*").eq("user_id", user.id).order('purchase_date', desc=True).execute()
    
    if db_res.data:
        st.markdown('<div class="monitor-wrapper">', unsafe_allow_html=True)
        # 排序：名稱 -> 現價 -> 目標 -> 止蝕 -> 股數 -> 成本 -> 盈虧 -> R 數
        h = st.columns([1.8, 0.8, 0.8, 0.8, 0.8, 0.8, 1.2, 0.8, 0.4])
        cols_name = ["股票/名稱", "現價", "目標", "止蝕", "股數", "成本", "盈虧(HKD)", "R 數", ""]
        for col, name in zip(h, cols_name): col.write(f"**{name}**")
        
        total_pl = 0
        for trade in db_res.data:
            info = get_live_info(trade['ticker'])
            lp, en, sl, tp, qty = info['price'], trade['entry_price'], trade['stop_loss'], trade.get('target_price',0), trade['qty']
            
            r = st.columns([1.8, 0.8, 0.8, 0.8, 0.8, 0.8, 1.2, 0.8, 0.4])
            r[0].markdown(f"**{trade['ticker']}**<br><span style='font-size:12px; color:#888;'>{info['name']}</span>", unsafe_allow_html=True)
            
            if lp:
                r[1].write(f"**{lp:,.2f}**")
                r[2].write(f"{tp:,.2f}")
                r[3].write(f"{sl:,.2f}")
                r[4].write(f"{qty:,}")
                r[5].write(f"{en:,.2f}")
                pl = (lp - en) * qty
                total_pl += pl
                r[6].markdown(f":{'green' if pl>=0 else 'red'}[${pl:,.1f}]")
                denom = en - sl
                r[7].info(f"{(lp-en)/denom if denom!=0 else 0:.2f}R")
            else:
                for i in range(1, 8): r[i].write("...")
            
            if r[8].button("🗑️", key=f"d_{trade['id']}"):
                supabase.table("trades").delete().eq("id", trade['id']).execute()
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()
        st.metric("總未實現盈虧", f"HK$ {total_pl:,.2f}", delta=f"{total_pl:,.2f}")
    else: st.info("目前沒有持倉紀錄。")