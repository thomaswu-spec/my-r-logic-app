import streamlit as st
import pandas as pd
import plotly.express as px # 新增圖表庫

# ... (保留之前的 get_fx_rate 和初始化邏輯) ...

st.title("📊 R-Logic 專業風險儀表板")

# --- 持倉紀錄區 ---
st.header("現有持倉狀態")
if st.session_state.trades:
    # 將資料轉為表格
    df = pd.DataFrame(st.session_state.trades)
    
    # 為了計算 Current R，我們讓用戶可以手動更新現價 (模擬功能)
    st.subheader("更新現價與計算 R 數")
    
    # 建立一個動態更新的列表
    updated_trades = []
    for i, row in df.iterrows():
        with st.expander(f"📈 {row['Ticker']} ({row['Currency']})"):
            c1, c2 = st.columns(2)
            cur_price = c1.number_input(f"{row['Ticker']} 當前價格", value=row['Entry'], key=f"p_{i}")
            
            # 計算 Current R (規格書 2.2)
            # 公式: (現價 - 成本) / (成本 - 止蝕)
            denom = row['Entry'] - row['StopLoss']
            current_r = (cur_price - row['Entry']) / denom if denom != 0 else 0
            
            # 標示顏色：正數綠色，負數紅色 (規格書 6)
            r_color = "green" if current_r >= 0 else "red"
            c2.markdown(f"### 當前回報: :{r_color}[{current_r:.2f} R]")
            
            # 存回更新後的數據
            row['Current_Price'] = cur_price
            row['Current_R'] = current_r
            updated_trades.append(row)

    df_final = pd.DataFrame(updated_trades)

    # --- 視覺化圖表 (FS 3.B) ---
    st.divider()
    st.subheader("🎯 R-Distribution 風險分佈圖")
    
    fig = px.bar(
        df_final, 
        x='Ticker', 
        y='Current_R',
        color='Current_R',
        color_continuous_scale=['red', 'gray', 'green'],
        title="各持倉 R-倍數 分佈"
    )
    # 加上一條 0 的基準線
    fig.add_hline(y=0, line_dash="dash", line_color="white")
    st.plotly_chart(fig, use_container_width=True)

    # 顯示總表
    st.write("詳細持倉清單：")
    st.dataframe(df_final[['Ticker', 'Qty', 'Entry', 'Current_Price', 'Current_R']])