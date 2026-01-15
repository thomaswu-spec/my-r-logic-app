import streamlit as st
import pandas as pd
from supabase import create_client, Client
import yfinance as yf
from datetime import datetime
import extra_streamlit_components as stx

# --- 1. 初始化連線 (完全保留你的 Secrets 設定) ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Cockpit Pro v4.2", layout="wide")

# --- 2. 核心 CSS 樣式 (保留你原本所有字體、顏色、手機對齊設定) ---
st.markdown("""
    <style>
    /* 1. 加大止盈止蝕數字 */
    .big-price { font-size: 32px !important; font-weight: 800 !important; line-height: 1.1; }
    
    /* 2. 修正抓取現價按鈕位置 */
    div[data-testid="column"] button { margin-top: -10px !important; }

    /* 3. 藍色現價參考文字 */
    .live-ref-text { font-size: 18px; color: #3498db; font-weight: bold; margin-left: 10px; padding-top: 5px; }

    /* 4. 強制 Live Monitor 保持單行 */
    .monitor-wrapper {
        overflow-x: auto;
        white-space: nowrap;
        display: block;
        width: 100%;
        padding: 10px 0;
    }
    
    /* 5. 門衛警告樣式 (新加) */
    .gatekeeper-warn { 
        color: #e74c3c; 
        background-color: #fff5f5; 
        padding: 15px; 
        border: 1px solid #e74c3c; 
        border-radius: 10px; 
        margin-top: 10px;
        font-weight: bold;
    }

    /* 6. 手機版微調 */
    @media (max-width: 640px) {
        .stMetric div { font-size: 18px !important; }
        .big-price { font-size: 24px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函數 (升級 v4.2 邏輯) ---
@st.cache_data(ttl=60)
def get_live_info(ticker):
    """抓取報價，解決『收唔到 Show』的問題"""
    try:
        formatted = f"{int(ticker):04d}.HK" if ticker.isdigit() else ticker
        stock = yf.Ticker(formatted)
        # 改用 history 確保喺非交易時間都拎到最後價
        hist = stock.history(period="1d")
        price = hist['Close'].iloc[-1] if not hist.empty else None
        return {
            "name": stock.info.get('shortName') or stock.info.get('longName') or ticker,
            "price": round(price, 3) if price else None
        }
    except: return {"name": "N/A", "price": None}

def calc_trade_logic(p, b, r_pc, ra):
    """符合 Spec 2.1 & 2.2: 以損定倉公式"""
    if not p or not b or p <= 0: return None
    # 2.1 風險單位 (1R) 定義
    r_amt = b * (r_pc / 100) 
    g_amt = r_amt * ra
    # 2.2 建議注碼 (考慮 1R 承受度)
    risk_per_share = p * (r_pc / 100)
    shares = int(r_amt / risk_per_share) if risk_per_share > 0 else 0
    # 止盈止蝕位計算
    sl_p = p * (1 - (r_pc/100))
    tp_p = p * (1 + (r_pc/100 * ra))
    return {"r": r_amt, "g": g_amt, "s": shares, "sl": sl_p, "tp": tp_p}

# --- 4. 自動登入邏輯 (保留 Cookie Manager) ---
cookie_manager = stx.CookieManager()
if 'user' not in st.session_state: st.session_state['user'] = None

saved_token = cookie_manager.get("sb-access-token")
if not st.session_state['user'] and saved_token:
    try:
        res = supabase.auth.get_user(saved_token)
        if res.user: st.session_state['user'] = res.user
    except: pass

# --- 5. 側邊欄：登入系統 (完全保留) ---
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

    # --- 交易策劃器 (Planner) ---
    with st.container(border=True):
        st.subheader("📝 交易策劃與 M.E.T.S. 門衛")
        r1_c1, r1_c2 = st.columns(2)
        with r1_c1: tk = st.text_input("🔍 股票代號", placeholder="例如: 700").upper()
        with r1_c2: trade_date = st.date_input("📅 交易日期", datetime.now())
        
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
        with r2_c1:
            p_val = st.session_state.get('tmp_p', None)
            pr = st.number_input("💰 進場價格", value=p_val, format="%.3f")
            btn_col, ref_col = st.columns([1, 1.5])
            with btn_col:
                if tk and st.button("🔍 抓取現價", use_container_width=True):
                    info = get_live_info(tk)
                    st.session_state['tmp_p'] = info['price']
                    st.rerun()
            with ref_col:
                if st.session_state.get('tmp_p'):
                    st.markdown(f'<div class="live-ref-text">Ref: {st.session_state["tmp_p"]}</div>', unsafe_allow_html=True)
        
        with r2_c2: bg = st.number_input("💼 總權益 (Equity)", value=1000000.0)
        with r2_c3: r_pc = st.number_input("⚠️ 風險 (1R %)", value=1.0)
        with r2_c4: r_ratio = st.number_input("🎯 Reward/Risk Ratio", value=3.0)

        res = calc_trade_logic(pr, bg, r_pc, r_ratio)
        if res:
            st.divider()
            # 指標顯示 (賣點 1, 2)
            m1, m2, m3 = st.columns(3)
            m1.metric("🔢 建議股數 (Max Size)", f"{res['s']:,} 股")
            m2.metric("📈 預期利潤", f"HK$ {res['g']:,.0f}")
            m3.metric("📉 止蝕金額 (1R)", f"HK$ {res['r']:,.0f}")
            
            # 價位顯示大字體
            v_tp, v_sl = st.columns(2)
            with v_tp:
                st.markdown(f'''<div style="background-color:#dcfce7; padding:15px; border-radius:10px; border-left:5px solid #22c55e;">
                    <span style="color:#15803d; font-size:14px;">✅ 止盈價位 ({r_ratio}R)</span><br>
                    <span class="big-price" style="color:#22c55e;">{res['tp']:,.2f}</span>
                </div>''', unsafe_allow_html=True)
            with v_sl:
                st.markdown(f'''<div style="background-color:#fee2e2; padding:15px; border-radius:10px; border-left:5px solid #ef4444;">
                    <span style="color:#b91c1c; font-size:14px;">❌ 止蝕價位 (1R Cut Loss)</span><br>
                    <span class="big-price" style="color:#ef4444;">{res['sl']:,.2f}</span>
                </div>''', unsafe_allow_html=True)
            
            # --- M.E.T.S. 門衛檢查 (賣點 3) ---
            st.write("## ")
            st.markdown("#### 🛡️ M.E.T.S. 紀律檢查點")
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1: chk_market = st.checkbox("📈 Market: 大盤趨勢向上")
            with col_m2: chk_entry = st.checkbox("✨ Entry: 符合 2 個以上進場訊號")
            with col_m3: chk_exit = st.checkbox("🎯 Reward: R:R 比例 >= 3:1")
            
            # 門衛邏輯：必須全選才能解鎖 Save 按鈕
            gate_passed = chk_market and chk_entry and chk_exit
            
            if not gate_passed:
                st.markdown('<div class="gatekeeper-warn">🔒 系統鎖定：請完成 M.E.T.S. 檢查以執行紀錄</div>', unsafe_allow_html=True)

            if st.button("📝 紀錄在你的 portfolio", type="primary", use_container_width=True, disabled=not gate_passed):
                try:
                    supabase.table("trades").insert({
                        "ticker": tk, "currency": "HKD", "entry_price": pr, "purchase_date": str(trade_date),
                        "stop_loss": res['sl'], "target_price": res['tp'], "qty": res['s'], "risk_mkt": res['r'], "user_id": user.id 
                    }).execute()
                    st.toast("✅ 紀錄成功！符合紀律！")
                    st.rerun()
                except Exception as e: st.error(f"存檔失敗: {e}")
        else:
            st.info("💡 請輸入代號、價格及預算以顯示策劃詳情。")

    # --- 7. 實時持倉監控 (Live R-Monitor) ---
    st.divider()
    st.header("📊 持倉實時監控 (R-Multiple Monitor)")
    db_res = supabase.table("trades").select("*").eq("user_id", user.id).order('purchase_date', desc=True).execute()
    
    if db_res.data:
        # 賣點 6: 總曝險預警
        total_r_exposure = len(db_res.data) * r_pc
        if total_r_exposure > 5.0:
            st.error(f"⚠️ 總曝險 ({total_r_exposure:.1f}%) 已超過總資產 5%！請停止開新倉。")

        st.markdown('<div class="monitor-wrapper">', unsafe_allow_html=True)
        h = st.columns([1.5, 0.8, 0.8, 0.8, 0.8, 0.8, 1.2, 1.0, 0.4])
        cols_name = ["股票/名稱", "現價", "目標", "止蝕", "股數", "成本", "盈虧(HKD)", "當前 R 數", "操作"]
        for col, name in zip(h, cols_name): col.write(f"**{name}**")
        
        total_pl = 0
        for trade in db_res.data:
            info = get_live_info(trade['ticker'])
            lp, en, sl, tp, qty = info['price'], trade['entry_price'], trade['stop_loss'], trade.get('target_price',0), trade['qty']
            
            r = st.columns([1.5, 0.8, 0.8, 0.8, 0.8, 0.8, 1.2, 1.0, 0.4])
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
                
                # 賣點 5: 即時 R-倍數監控
                denom = abs(en - sl)
                curr_r = (lp - en) / denom if denom != 0 else 0
                
                # 賣點 7: 利潤狀態顏色
                if curr_r >= 1.0:
                    r[7].success(f"{curr_r:+.2f}R (保本)")
                elif curr_r >= 3.0:
                    r[7].warning(f"{curr_r:+.2f}R (收割)")
                else:
                    r[7].info(f"{curr_r:+.2f}R")
            
            if r[8].button("🗑️", key=f"d_{trade['id']}"):
                supabase.table("trades").delete().eq("id", trade['id']).execute()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()
        st.metric("總未實現盈虧", f"HK$ {total_pl:,.2f}", delta=f"{total_pl:,.2f}")
    else: st.info("目前沒有持倉紀錄。")
else:
    st.warning("👈 請在側邊欄登入以開始使用。")