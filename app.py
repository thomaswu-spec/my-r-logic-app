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

# --- 2. 核心計算與抓取函數 ---
def fetch_live_price(ticker):
    try:
        # 自動判斷港股或美股格式
        formatted_ticker = f"{int(ticker):04d}.HK" if ticker.isdigit() else ticker
        stock = yf.Ticker(formatted_ticker)
        # 獲取最新成交價
        return round(stock.fast_info['last_price'], 3)
    except:
        return None

def calc_trade_logic(p, b, r_pc, ra):
    if not p or not b: return None
    # 根據 Budget 同 R% 計出風險金額 (R budget) 
    r_amount = b * (r_pc / 100) 
    shares = int(b / p) if p > 0 else 0
    # 止蝕價位 
    sl_price = p * (1 - (r_pc/100))
    # 止盈目標價位 
    tp_price = p * (1 + (r_pc/100 * ra))
    
    return {
        "r_amount": r_amount,
        "shares": shares,
        "sl_price": sl_price,
        "tp_price": tp_price
    }

st.title("🚀 R-Logic 投資指揮中心")

# --- 3. 交易策劃器 (維持單一輸入) ---
with st.container(border=True):
    st.subheader("📝 交易策劃")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1: tk = st.text_input("🔍 股票代號", placeholder="例如: 700").upper()
    with c2: trade_date = st.date_input("📅 買入日期", datetime.now())
    with c3:
        st.write("## ")
        live_p = None
        if tk and st.button("🔍 抓取現價", use_container_width=True):
            live_p = fetch_live_price(tk)

    c4, c5, c6, c7 = st.columns(4)
    with c4: pr = st.number_input("💰 進場價格", value=live_p)
    with c5: bg = st.number_input("💼 投入預算", value=None)
    with c6: r_pc = st.number_input("⚠️ 風險比例 (R %)", value=5.0)
    with c7: r_ratio = st.number_input("🎯 風險回報比", value=3.0)

    res = calc_trade_logic(pr, bg, r_pc, r_ratio)
    if res:
        st.divider()
        res_c1, res_c2, res_c3, res_c4, res_c5 = st.columns(5)
        res_c1.metric("🔢 建議股數", f"{res['shares']} 股")
        res_c2.metric("📉 止蝕金額", f"HK$ {res['r_amount']:,.0f}")
        res_c4.error(f"❌ 止蝕價位\n\n**{res['sl_price']:.2f}**")
        res_c5.success(f"✅ 止盈價位\n\n**{res['tp_price']:.2f}**")
        
        if st.button("📥 存入雲端", type="primary", use_container_width=True):
            supabase.table("trades").insert({
                "ticker": tk, "entry_price": pr, "stop_loss": res['sl_price'],
                "qty": res['shares'], "risk_mkt": res['r_amount'],
                "purchase_date": str(trade_date), "currency": "HKD"
            }).execute()
            st.rerun()

# --- 4. 持倉實時監控 (重點更新區) ---
st.divider()
st.header("📊 持倉實時監控 (Live Monitor)")

db_res = supabase.table("trades").select("*").execute()
if db_res.data:
    total_unrealized_pl = 0
    
    # 建立表頭
    h_cols = st.columns([1, 1, 1, 1, 1, 1, 0.5])
    h_cols[0].write("**日期/代號**")
    h_cols[1].write("**成本**")
    h_cols[2].write("**現價**")
    h_cols[3].write("**股數**")
    h_cols[4].write("**盈虧 (HKD)**")
    h_cols[5].write("**當前 R 數**")
    st.write("---")

    for trade in db_res.data:
        curr_p = fetch_live_price(trade['ticker'])
        entry_p = trade['entry_price']
        qty = trade['qty']
        
        row = st.columns([1, 1, 1, 1, 1, 1, 0.5])
        row[0].write(f"{trade['purchase_date']}\n\n**{trade['ticker']}**")
        row[1].write(f"{entry_p}")
        
        if curr_p:
            # 計算損益：(現價 - 成本) * 股數 
            pl = (curr_p - entry_p) * qty
            total_unrealized_pl += pl
            
            # 當前 R 數 = (現價 - 成本) / (成本 - 止蝕)
            denom = entry_p - trade['stop_loss']
            r_now = (curr_p - entry_p) / denom if denom != 0 else 0
            
            row[2].write(f"{curr_p}")
            row[3].write(f"{qty}")
            
            # 盈虧變色標示
            pl_color = "green" if pl >= 0 else "red"
            row[4].markdown(f":{pl_color}[${pl:,.2f}]")
            
            # R 數背景顯示
            row[5].info(f"{r_now:.2f} R")
        else:
            row[2].write("Loading...")
        
        # 刪除功能
        if row[6].button("🗑️", key=f"del_{trade['id']}"):
            supabase.table("trades").delete().eq("id", trade['id']).execute()
            st.rerun()

    # 底部彙總
    st.divider()
    m1, m2 = st.columns(2)
    m1.metric("總未實現盈虧", f"HK$ {total_unrealized_pl:,.2f}", delta=f"{total_unrealized_pl:,.2f}")
else:
    st.info("目前雲端沒有持倉紀錄。")