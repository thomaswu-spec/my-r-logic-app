import streamlit as st
import pandas as pd
from supabase import create_client, Client
import yfinance as yf
from datetime import datetime

# --- 1. 初始化與連線 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="R-Logic Cockpit Pro", layout="wide")

# --- 2. 核心功能函數 ---
def fetch_live_price(ticker):
    try:
        formatted_ticker = f"{int(ticker):04d}.HK" if ticker.isdigit() else ticker
        stock = yf.Ticker(formatted_ticker)
        return round(stock.fast_info['last_price'], 3)
    except:
        return None

def calc_trade_logic(p, b, r, ra):
    if not p or not b: return None
    # 核心邏輯：根據 R% 同 Budget 計出風險金額 (1R)
    r_amount = b * (r / 100) 
    # 根據風險金額同 Ratio 計出預期利潤金額
    profit_amount = r_amount * ra
    
    shares = int(b / p) if p > 0 else 0
    # 止蝕位 (Cut Loss Price)：進場價跌 R%
    sl_price = p * (1 - (r/100))
    # 止盈位 (Target Price)：進場價升 (R% * Ratio)
    tp_price = p * (1 + (r/100 * ra))
    
    return {
        "r_amount": r_amount,
        "profit_amount": profit_amount,
        "shares": shares,
        "sl_price": sl_price,
        "tp_price": tp_price
    }

st.title("🚀 R-Logic 專業投資指揮中心")

# --- 3. 單一交易策劃器 (Single Input Interface) ---
with st.container(border=True):
    st.subheader("📝 交易策劃 (Single Trade Entry)")
    
    # 分兩行排列輸入項
    row1_c1, row1_c2, row1_c3 = st.columns(3)
    with row1_c1:
        tk = st.text_input("🔍 股票代號 (Stock)", placeholder="例如: 700 或 TSLA").upper()
    with row1_c2:
        # 新增：買入日期選擇
        trade_date = st.date_input("📅 買入日期", datetime.now())
    with row1_c3:
        # 抓取現價按鈕
        live_p = None
        if tk and st.button("🔍 抓取現價", use_container_width=True):
            live_p = fetch_live_price(tk)
            if live_p: st.toast(f"已獲取 {tk} 最新價格")

    row2_c1, row2_c2, row2_c3, row2_c4 = st.columns(4)
    with row2_c1:
        pr = st.number_input("💰 進場價格 (Entry Price)", value=live_p, placeholder="輸入價格")
    with row2_c2:
        bg = st.number_input("💼 投入預算 (Budget)", value=None, placeholder="輸入總預算")
    with row2_c3:
        r_pc = st.number_input("⚠️ 風險比例 (R %)", value=5.0, help="根據預算計算止蝕百分比")
    with row2_c4:
        r_ratio = st.number_input("🎯 風險回報比 (Ratio)", value=3.0, help="預期盈虧比")

    # --- 自動計算結果顯示 ---
    st.divider()
    res = calc_trade_logic(pr, bg, r_pc, r_ratio)
    
    if res:
        res_c1, res_c2, res_c3, res_c4, res_c5 = st.columns(5)
        res_c1.metric("🔢 建議股數", f"{res['shares']} 股")
        res_c2.metric("📉 止蝕金額 (1R)", f"HK$ {res['r_amount']:,.0f}")
        res_c3.metric("📈 止盈金額", f"HK$ {res['profit_amount']:,.0f}")
        res_c4.error(f"❌ 止蝕位\n\n**{res['sl_price']:.2f}**")
        res_c5.success(f"✅ 止盈位\n\n**{res['tp_price']:.2f}**")
        
        if st.button("📥 正式存入雲端持倉", type="primary", use_container_width=True):
            supabase.table("trades").insert({
                "ticker": tk,
                "entry_price": pr,
                "stop_loss": res['sl_price'],
                "qty": res['shares'],
                "risk_mkt": res['r_amount'],
                "purchase_date": str(trade_date), # 儲存日期
                "currency": "HKD"
            }).execute()
            st.toast("✅ 已成功同步至雲端資料庫！")
            st.rerun()
    else:
        st.info("💡 請輸入進場價同預算，系統會自動幫你計出止蝕同止盈位。")

# --- 4. 全局持倉監控 (Live Portfolio) ---
st.divider()
st.header("📊 持倉實時監控 (Live Monitor)")

db_res = supabase.table("trades").select("*").order("purchase_date", desc=True).execute()
if db_res.data:
    df_display = pd.DataFrame(db_res.data)
    # 這裡可以根據需要美化表格顯示
    st.dataframe(df_display[['purchase_date', 'ticker', 'qty', 'entry_price', 'stop_loss', 'risk_mkt']], use_container_width=True)