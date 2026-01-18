"""
日本株分析アプリ - Streamlit UI
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from data_fetcher import JapaneseStockDataFetcher
from backtester import Backtester
from strategy_optimizer import StrategyOptimizer
import warnings
warnings.filterwarnings('ignore')

# ページ設定
st.set_page_config(
    page_title="日本株分析アプリ",
    page_icon="📈",
    layout="wide"
)

st.title("📈 日本株分析・バックテストアプリ")
st.markdown("Yahooファイナンスから日本株データを取得し、バックテストと戦略最適化を行います")

# サイドバー
st.sidebar.header("設定")

# ティッカー入力
ticker_input = st.sidebar.text_input(
    "ティッカーシンボル",
    value="7203",
    help="例: 7203 (トヨタ自動車), 6758 (ソニーグループ), 9984 (ソフトバンクグループ)"
)

# 期間選択
period = st.sidebar.selectbox(
    "データ取得期間",
    options=["6mo", "1y", "2y", "5y"],
    index=1
)

# 初期資金
initial_capital = st.sidebar.number_input(
    "初期資金（円）",
    min_value=100000,
    max_value=100000000,
    value=1000000,
    step=100000
)

# タブ
tab1, tab2, tab3, tab4 = st.tabs(["📊 データ表示", "🔍 バックテスト", "⚙️ 戦略最適化", "📋 利益条件分析"])

# データ取得
@st.cache_data(ttl=3600)
def fetch_stock_data(ticker: str, period: str):
    """株価データを取得（キャッシュ付き）"""
    fetcher = JapaneseStockDataFetcher()
    data = fetcher.get_stock_data(ticker, period)
    data = fetcher.add_technical_indicators(data)
    return data

# タブ1: データ表示
with tab1:
    st.header("株価データとテクニカル指標")
    
    try:
        with st.spinner("データを取得中..."):
            data = fetch_stock_data(ticker_input, period)
        
        st.success(f"データ取得成功: {len(data)}件のデータ")
        
        # 基本情報
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("現在価格", f"¥{data['Close'].iloc[-1]:,.0f}")
        with col2:
            price_change = data['Close'].iloc[-1] - data['Close'].iloc[-2]
            st.metric("前日比", f"¥{price_change:,.0f}", delta=f"{(price_change/data['Close'].iloc[-2]*100):.2f}%")
        with col3:
            st.metric("最高値", f"¥{data['High'].max():,.0f}")
        with col4:
            st.metric("最安値", f"¥{data['Low'].min():,.0f}")
        
        # チャート表示
        fig = go.Figure()
        
        # ローソク足
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name="価格"
        ))
        
        # 移動平均線
        if 'MA5' in data.columns:
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MA5'],
                name="MA5",
                line=dict(color='blue', width=1)
            ))
        if 'MA25' in data.columns:
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MA25'],
                name="MA25",
                line=dict(color='orange', width=1)
            ))
        if 'MA75' in data.columns:
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MA75'],
                name="MA75",
                line=dict(color='red', width=1)
            ))
        
        fig.update_layout(
            title="株価チャート",
            xaxis_title="日付",
            yaxis_title="価格（円）",
            height=500,
            xaxis_rangeslider_visible=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # RSIチャート
        if 'RSI' in data.columns:
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(
                x=data.index,
                y=data['RSI'],
                name="RSI",
                line=dict(color='purple', width=2)
            ))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="売られすぎ (70)")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="買われすぎ (30)")
            fig_rsi.update_layout(
                title="RSI（相対力指数）",
                xaxis_title="日付",
                yaxis_title="RSI",
                height=300
            )
            st.plotly_chart(fig_rsi, use_container_width=True)
        
        # データテーブル
        st.subheader("データテーブル")
        st.dataframe(data.tail(20), use_container_width=True)
        
    except Exception as e:
        st.error(f"エラー: {str(e)}")

# タブ2: バックテスト
with tab2:
    st.header("バックテスト")
    
    try:
        data = fetch_stock_data(ticker_input, period)
        
        # 戦略選択
        strategy_type = st.selectbox(
            "戦略タイプ",
            options=["移動平均クロス", "RSI戦略", "MACD戦略"]
        )
        
        if strategy_type == "移動平均クロス":
            col1, col2 = st.columns(2)
            with col1:
                short_ma = st.number_input("短期移動平均", min_value=3, max_value=50, value=5)
            with col2:
                long_ma = st.number_input("長期移動平均", min_value=10, max_value=200, value=25)
            
            # 買い・売り条件
            def buy_condition(row):
                if pd.isna(row[f'MA{short_ma}']) or pd.isna(row[f'MA{long_ma}']):
                    return False
                return row[f'MA{short_ma}'] > row[f'MA{long_ma}']
            
            def sell_condition(row):
                if pd.isna(row[f'MA{short_ma}']) or pd.isna(row[f'MA{long_ma}']):
                    return False
                return row[f'MA{short_ma}'] < row[f'MA{long_ma}']
            
            # 移動平均を計算
            data[f'MA{short_ma}'] = data['Close'].rolling(window=short_ma).mean()
            data[f'MA{long_ma}'] = data['Close'].rolling(window=long_ma).mean()
        
        elif strategy_type == "RSI戦略":
            col1, col2 = st.columns(2)
            with col1:
                rsi_oversold = st.number_input("RSI買いシグナル", min_value=10, max_value=40, value=30)
            with col2:
                rsi_overbought = st.number_input("RSI売りシグナル", min_value=60, max_value=90, value=70)
            
            def buy_condition(row):
                if pd.isna(row['RSI']):
                    return False
                return row['RSI'] < rsi_oversold
            
            def sell_condition(row):
                if pd.isna(row['RSI']):
                    return False
                return row['RSI'] > rsi_overbought
        
        else:  # MACD戦略
            def buy_condition(row):
                if pd.isna(row['MACD']) or pd.isna(row['MACD_signal']):
                    return False
                return (row['MACD'] > row['MACD_signal']) and (row['MACD_hist'] > 0)
            
            def sell_condition(row):
                if pd.isna(row['MACD']) or pd.isna(row['MACD_signal']):
                    return False
                return (row['MACD'] < row['MACD_signal']) and (row['MACD_hist'] < 0)
        
        # バックテスト実行
        if st.button("バックテスト実行", type="primary"):
            with st.spinner("バックテスト実行中..."):
                backtester = Backtester(initial_capital)
                results = backtester.run_backtest(data, buy_condition, sell_condition)
            
            # 結果表示
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("総リターン", f"¥{results['total_return']:,.0f}", f"{results['total_return_pct']:.2f}%")
            with col2:
                st.metric("勝率", f"{results['win_rate']:.1f}%")
            with col3:
                st.metric("取引回数", f"{results['num_trades']}回")
            with col4:
                st.metric("シャープレシオ", f"{results['sharpe_ratio']:.2f}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("平均利益", f"¥{results['avg_profit']:,.0f}")
            with col2:
                st.metric("平均損失", f"¥{results['avg_loss']:,.0f}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("プロフィットファクター", f"{results['profit_factor']:.2f}")
            with col2:
                st.metric("最大ドローダウン", f"{results['max_drawdown']:.2f}%")
            
            # エクイティカーブ
            if results['equity_curve']:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=results['dates'],
                    y=results['equity_curve'],
                    name="エクイティ",
                    line=dict(color='blue', width=2)
                ))
                fig.add_hline(y=initial_capital, line_dash="dash", line_color="gray", annotation_text="初期資金")
                fig.update_layout(
                    title="エクイティカーブ",
                    xaxis_title="日付",
                    yaxis_title="資産（円）",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # 取引履歴
            if results['trades']:
                st.subheader("取引履歴")
                trades_df = pd.DataFrame([
                    {
                        'エントリー日': t.entry_date.strftime('%Y-%m-%d'),
                        '決済日': t.exit_date.strftime('%Y-%m-%d') if t.exit_date else '-',
                        'エントリー価格': f"¥{t.entry_price:,.0f}",
                        '決済価格': f"¥{t.exit_price:,.0f}" if t.exit_price else '-',
                        '数量': t.shares,
                        '利益': f"¥{t.profit:,.0f}" if t.profit else '-',
                        '利益率': f"{t.profit_pct:.2f}%" if t.profit_pct else '-'
                    }
                    for t in results['trades']
                ])
                st.dataframe(trades_df, use_container_width=True)
    
    except Exception as e:
        st.error(f"エラー: {str(e)}")

# タブ3: 戦略最適化
with tab3:
    st.header("戦略最適化")
    
    try:
        data = fetch_stock_data(ticker_input, period)
        
        optimization_type = st.selectbox(
            "最適化タイプ",
            options=["移動平均クロス", "RSI戦略"]
        )
        
        if st.button("最適化実行", type="primary"):
            with st.spinner("最適化実行中...（時間がかかる場合があります）"):
                optimizer = StrategyOptimizer(initial_capital)
                
                if optimization_type == "移動平均クロス":
                    results = optimizer.optimize_ma_cross_strategy(data)
                else:
                    results = optimizer.optimize_rsi_strategy(data)
            
            if not results.empty:
                st.success(f"最適化完了: {len(results)}件の利益が出る戦略が見つかりました")
                
                # トップ10を表示
                st.subheader("トップ10の戦略")
                display_cols = [col for col in results.columns if col not in ['equity_curve', 'dates', 'trades']]
                st.dataframe(results.head(10)[display_cols], use_container_width=True)
                
                # 最適化結果をセッション状態に保存
                st.session_state['optimization_results'] = results
            else:
                st.warning("利益が出る戦略が見つかりませんでした")
    
    except Exception as e:
        st.error(f"エラー: {str(e)}")

# タブ4: 利益条件分析
with tab4:
    st.header("利益条件分析")
    
    if 'optimization_results' not in st.session_state or st.session_state['optimization_results'].empty:
        st.info("まず「戦略最適化」タブで最適化を実行してください")
    else:
        try:
            results = st.session_state['optimization_results']
            optimizer = StrategyOptimizer(initial_capital)
            analysis = optimizer.analyze_profitable_conditions(results)
            
            st.subheader("最良の戦略")
            if analysis['best_strategy']:
                best = analysis['best_strategy']
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**パラメータ:**")
                    for key, value in best.items():
                        if key not in ['total_return', 'total_return_pct', 'num_trades', 'win_rate', 
                                      'avg_profit', 'avg_loss', 'profit_factor', 'max_drawdown', 'sharpe_ratio',
                                      'equity_curve', 'dates', 'trades']:
                            st.write(f"- {key}: {value}")
                
                with col2:
                    st.write("**パフォーマンス:**")
                    st.metric("総リターン", f"{best['total_return_pct']:.2f}%")
                    st.metric("勝率", f"{best['win_rate']:.1f}%")
                    st.metric("取引回数", f"{best['num_trades']}回")
                    st.metric("プロフィットファクター", f"{best['profit_factor']:.2f}")
            
            st.subheader("利益が出る条件の統計")
            st.write(f"**テストした戦略数:** {analysis['total_tested_strategies']}")
            st.write(f"**利益が出た戦略数:** {analysis['total_profitable_strategies']}")
            st.write(f"**利益率:** {analysis['total_profitable_strategies']/analysis['total_tested_strategies']*100:.1f}%")
            
            if analysis['parameter_ranges']:
                st.subheader("パラメータ範囲")
                param_df = pd.DataFrame(analysis['parameter_ranges']).T
                st.dataframe(param_df, use_container_width=True)
        
        except Exception as e:
            st.error(f"エラー: {str(e)}")
