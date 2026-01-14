import streamlit as st
import pandas as pd
from supabase import create_client, Client
import yfinance as yf
from datetime import datetime

# --- 1. 初始化與連線 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Cockpit", layout="wide")

# --- 2. 核心 CSS 修復 (針對手機排版同單行顯示) ---
st.markdown("""
    <style>
    /* 強制手機版唔好垂直堆疊，保持橫向滾動 */
    [data-testid="column"] {
        min-width: 100px !important;
    }
    
    /* Live Monitor 專用：強制單行唔換行 */
    .monitor-row {
        white-space: nowrap !important;
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 15px;
        overflow-x: auto; /* 手機可以橫向掃 */
        padding: 10px 0;
        border-bottom: 1px solid #444;
    }
    
    .monitor-cell {
        min-width: 80px;
        text-align: left;
        font-size: 14px;
    }

    /* 加大字體方便手機睇 */
    .stMetric label { font-size: 16px !important; }
    .stMetric div { font-size: 20px !important; }
    
    /* 修正手機版表格過窄問題 */
    @media (max-width: 640px) {
        .stMarkdown div { font-size: 13px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函數 ---
def fetch_live_price(ticker):
    try:
        formatted_ticker = f"{int(ticker):04d}.HK" if ticker.isdigit() else ticker
        stock = yf.Ticker(formatted_ticker)
        return round(stock.fast_info['last_price'], 3)
    except:
        return None

def calc_trade_logic(p, b, r_pc, ra):
    if not p or not b: return None
    r_amount = b * (r_pc / 100) 
    shares = int(b / p) if p > 0 else 0
    sl_price = p * (1 - (r_pc/100))
    tp_price = p * (1 + (r_pc/100 * ra))
    return {"r_amount": r_amount, "shares": shares, "sl_price": sl_price, "tp_price": tp_price}

st.title("🚀 R-Logic 投資指揮中心")

# --- 4. 交易策劃 (優化手機佈局) ---
with st.container(border=True):
    st.subheader("📝 交易策劃")
    col1, col2 = st.columns(2) # 手機版改為兩行
    with col1: tk = st.text_input("🔍 代號", placeholder="例如: 700").upper()
    with col2: trade_date = st.date_input("📅 日期", datetime.now())
    
    if tk:
        if st.button("🔍 抓取現價", use_container_width=True):
            live_p = fetch_live_price(tk)
            st.session_state['tmp_price'] = live_p
    
    p_val = st.session_state.get('tmp_price', None)
    
    col3, col4 = st.columns(2)
    with col3: pr = st.number_input("💰 進場價", value=p_val)
    with col4: bg = st.number_input("💼 預算", value=None)
    
    col5, col6 = st.columns(2)
    with col5: r_pc = st.number_input("⚠️ R %", value=5.0)
    with col6: r_ratio = st.number_input("🎯 Ratio", value=3.0)

    res = calc_trade_logic(pr, bg, r_pc, r_ratio)
    if res:
        st.divider()
        # 結果顯示
        m1, m2 = st.columns(2)
        m1.metric("🔢 建議股數", f"{res['shares']} 股")
        m2.metric("📉 止蝕金額", f"HK$ {res['r_amount']:,.0f}")
        
        m3, m4 = st.columns(2)
        m3.error(f"❌ 止蝕價: **{res['sl_price']:.2f}**")
        m4.success(f"✅ 止盈價: **{res['tp_price']:.2f}**")
        
        if st.button("📥 存入雲端", type="primary", use_container_width=True):
            supabase.table("trades").insert({
                "ticker": tk, "entry_price": pr, "stop_loss": res['sl_price'],
                "qty": res['shares'], "risk_mkt": res['r_amount'],
                "purchase_date": str(trade_date), "currency": "HKD"
            }).execute()
            st.rerun()

# --- 5. 持倉實時監控 (強制單行橫向顯示) ---
st.divider()
st.header("📊 持倉實時監控 (Live Monitor)")

try:
    db_res = supabase.table("trades").select("*").order("purchase_date", desc=True).execute()
    if db_res.data:
        total_pl = 0
        
        # 顯示表頭 (強制橫向)
        st.markdown("""
            <div class="monitor-row" style="font-weight:bold; border-bottom:2px solid #666;">
                <div class="monitor-cell" style="min-width:100px;">日期/代號</div>
                <div class="monitor-cell">成本</div>
                <div class="monitor-cell">現價</div>
                <div class="monitor-cell">股數</div>
                <div class="monitor-cell" style="min-width:110px;">盈虧</div>
                <div class="monitor-cell">R 數</div>
                <div class="monitor-cell" style="min-width:40px;">操作</div>
            </div>
        """, unsafe_allow_html=True)

        for trade in db_res.data:
            curr_p = fetch_live_price(trade['ticker'])
            entry_p = trade['entry_price']
            qty = trade['qty']
            
            if curr_p:
                pl = (curr_p - entry_p) * qty
                total_pl += pl
                denom = entry_p - trade['stop_loss']
                r_now = (curr_p - entry_p) / denom if denom != 0 else 0
                pl_color = "#00ff00" if pl >= 0 else "#ff4b4b"
                
                # 使用 HTML 組合確保「絕對單行」
                st.markdown(f"""
                    <div class="monitor-row">
                        <div class="monitor-cell" style="min-width:100px;">{trade['purchase_date']}<br><b>{trade['ticker']}</b></div>
                        <div class="monitor-cell">{entry_p}</div>
                        <div class="monitor-cell">{curr_p}</div>
                        <div class="monitor-cell">{qty}</div>
                        <div class="monitor-cell" style="min-width:110px; color:{pl_color}; font-weight:bold;">${pl:,.1f}</div>
                        <div class="monitor-cell">{r_now:.2f}R</div>
                        <div class="monitor-cell" style="min-width:40px;">
                            <a href="#" onclick="return false;">🗑️</a>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # 雖然 HTML 顯示靚，但刪除功能仲係要用返 Streamlit Button 先做到
                if st.button(f"刪除 {trade['ticker']} #{trade['id']}", key=f"d_{trade['id']}", size="small"):
                    supabase.table("trades").delete().eq("id", trade['id']).execute()
                    st.rerun()

        st.divider()
        st.metric("總未實現盈虧", f"HK$ {total_pl:,.2f}", delta=f"{total_pl:,.2f}")
    else:
        st.info("目前雲端沒有持倉紀錄。")
except Exception as e:
    st.error(f"資料庫錯誤: {e}")