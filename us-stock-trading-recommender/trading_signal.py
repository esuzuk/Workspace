"""
売買タイミングを判定するモジュール
テクニカル分析とファンダメンタル分析を統合
"""
from datetime import datetime
import logging
from data_fetcher import USStockDataFetcher
from fundamental_analyzer import FundamentalAnalyzer
from investment_philosophy import InvestmentPhilosophyAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingSignalGenerator:
    """売買シグナル生成クラス"""
    
    def __init__(self, data_fetcher: USStockDataFetcher):
        """
        初期化
        
        Args:
            data_fetcher: データ取得オブジェクト
        """
        self.data_fetcher = data_fetcher
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.philosophy_analyzer = InvestmentPhilosophyAnalyzer(self.fundamental_analyzer)
        
        # 判定パラメータ（調整可能）
        self.RSI_OVERSOLD = 30  # RSIが30以下で買いシグナル
        self.RSI_OVERBOUGHT = 70  # RSIが70以上で売りシグナル
        self.PROFIT_TARGET = 20.0  # 利益確定目標（%）
        self.STOP_LOSS = -10.0  # 損切りライン（%）
        self.MA_CROSS_UP_THRESHOLD = 0.02  # 短期移動平均が長期移動平均を2%以上上回る
        self.MA_CROSS_DOWN_THRESHOLD = -0.02  # 短期移動平均が長期移動平均を2%以上下回る
    
    def analyze_sell_signal(self, ticker: str, current_price: float, 
                           purchase_price: float, profit_loss_rate: float) -> dict | None:
        """
        売りシグナルを分析（テクニカル + ファンダメンタル統合）
        
        Args:
            ticker: ティッカーシンボル
            current_price: 現在価格
            purchase_price: 取得価格
            profit_loss_rate: 損益率（%）
        
        Returns:
            dict: 売り推奨情報、推奨がない場合はNone
        """
        try:
            indicators = self.data_fetcher.get_latest_indicators(ticker)
            
            reasons = []
            confidence_factors = []
            data_source = {}
            philosopher_advice = []
            
            # ファンダメンタル分析を追加（売り判定用）
            try:
                financial_data = self.fundamental_analyzer.get_financial_data(ticker)
                
                # バフェット哲学: 長期保有推奨の場合は売りを抑制
                buffett_result = self.philosophy_analyzer.analyze_buffett_value(ticker, financial_data)
                if buffett_result['recommendation'] == 'BUY_AND_HOLD' and profit_loss_rate < 50:
                    reasons.append("【バフェット哲学】優良企業のため長期保有を推奨（売り推奨を抑制）")
                    confidence_factors.append(-0.3)  # 売りシグナルを弱める
                    philosopher_advice.append("ウォーレン・バフェット: 優良企業は長期保有を推奨")
                
                # グレアム哲学: 割高になった場合は売り推奨
                graham_result = self.philosophy_analyzer.analyze_graham_value(ticker, financial_data)
                if graham_result['recommendation'] == 'AVOID':
                    reasons.append("【グレアム哲学】割高評価のため売却を検討")
                    confidence_factors.append(0.6)
                    philosopher_advice.append("ベンジャミン・グレアム: 安全余裕がなくなり割高")
                
                data_source['fundamental'] = {
                    'pe_ratio': financial_data.get('pe_ratio'),
                    'pb_ratio': financial_data.get('pb_ratio'),
                    'roe': financial_data.get('roe'),
                }
                
            except Exception as e:
                logger.warning(f"ファンダメンタル分析エラー ({ticker}): {str(e)}")
                # ファンダメンタル分析が失敗してもテクニカル分析は続行
            
            # 1. 利益確定・損切り判定
            if profit_loss_rate >= self.PROFIT_TARGET:
                reasons.append(f"利益確定目標達成（{profit_loss_rate:.2f}%）")
                confidence_factors.append(0.8)
            elif profit_loss_rate <= self.STOP_LOSS:
                reasons.append(f"損切りライン到達（{profit_loss_rate:.2f}%）")
                confidence_factors.append(0.9)
            
            # 2. RSI判定
            rsi = indicators.get('rsi')
            if rsi:
                data_source['rsi'] = rsi
                if rsi >= self.RSI_OVERBOUGHT:
                    reasons.append(f"RSI過買い状態（RSI: {rsi:.2f}）")
                    confidence_factors.append(0.7)
                elif rsi < 50:
                    # RSIが50を下回っている場合は売りシグナルが弱い
                    confidence_factors.append(-0.2)
            
            # 3. MACD判定
            macd = indicators.get('macd')
            macd_signal = indicators.get('macd_signal')
            macd_hist = indicators.get('macd_hist')
            
            if macd and macd_signal and macd_hist:
                data_source['macd'] = macd
                data_source['macd_signal'] = macd_signal
                data_source['macd_hist'] = macd_hist
                
                # MACDがシグナルを下回る（売りシグナル）
                if macd < macd_signal and macd_hist < 0:
                    reasons.append(f"MACD売りシグナル（MACD: {macd:.2f}, Signal: {macd_signal:.2f}）")
                    confidence_factors.append(0.6)
            
            # 4. 移動平均線判定
            ma_20 = indicators.get('ma_20')
            ma_50 = indicators.get('ma_50')
            ma_200 = indicators.get('ma_200')
            
            if ma_20 and ma_50:
                data_source['ma_20'] = ma_20
                data_source['ma_50'] = ma_50
                
                # 短期移動平均が長期移動平均を下回る
                ma_ratio = (ma_20 - ma_50) / ma_50
                if ma_ratio < self.MA_CROSS_DOWN_THRESHOLD:
                    reasons.append(f"移動平均線デッドクロス（MA20: ${ma_20:.2f}, MA50: ${ma_50:.2f}）")
                    confidence_factors.append(0.65)
            
            if ma_200:
                data_source['ma_200'] = ma_200
                # 現在価格が200日移動平均を大きく下回る
                if current_price < ma_200 * 0.95:
                    reasons.append(f"200日移動平均を大きく下回る（現在: ${current_price:.2f}, MA200: ${ma_200:.2f}）")
                    confidence_factors.append(0.5)
            
            # 5. ボリンジャーバンド判定
            bb_upper = indicators.get('bb_upper')
            if bb_upper and current_price >= bb_upper:
                data_source['bb_upper'] = bb_upper
                reasons.append(f"ボリンジャーバンド上限到達（上限: ${bb_upper:.2f}）")
                confidence_factors.append(0.55)
            
            # 信頼度の計算
            if confidence_factors:
                confidence = min(0.95, max(0.3, sum(confidence_factors) / len(confidence_factors)))
            else:
                confidence = 0.0
            
            # 推奨判定（信頼度が0.5以上の場合）
            if confidence >= 0.5 and reasons:
                logic = "以下の複数の指標が売りシグナルを示しています: " + "、".join(reasons)
                
                recommendation = {
                    'ticker': ticker,
                    'recommendation_type': 'SELL',
                    'recommendation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'current_price': current_price,
                    'recommended_price': current_price,  # 現在価格で売却推奨
                    'reason': " | ".join(reasons),
                    'data_source': data_source,
                    'logic': logic,
                    'confidence': confidence,
                    'philosopher_advice': philosopher_advice  # 賢人のアドバイスを追加
                }
                
                return recommendation
            
            return None
            
        except Exception as e:
            logger.error(f"売りシグナル分析エラー ({ticker}): {str(e)}")
            return None
    
    def analyze_buy_signal(self, ticker: str) -> dict | None:
        """
        買いシグナルを分析（テクニカル + ファンダメンタル統合）
        
        Args:
            ticker: ティッカーシンボル
        
        Returns:
            dict: 買い推奨情報、推奨がない場合はNone
        """
        try:
            indicators = self.data_fetcher.get_latest_indicators(ticker)
            current_price = indicators.get('current_price')
            
            if not current_price:
                return None
            
            reasons = []
            confidence_factors = []
            data_source = {}
            philosopher_advice = []
            
            # ファンダメンタル分析を追加
            try:
                financial_data = self.fundamental_analyzer.get_financial_data(ticker)
                philosophy_results = self.philosophy_analyzer.analyze_all_philosophies(
                    ticker, financial_data, indicators
                )
                
                # 投資哲学からの推奨を追加
                if philosophy_results['overall_recommendation'] in ['STRONG_BUY', 'BUY']:
                    reasons.append(f"【ファンダメンタル分析】{philosophy_results['overall_recommendation']}")
                    confidence_factors.append(philosophy_results['overall_confidence'])
                    
                    # 賢人のアドバイスを追加
                    for advice in philosophy_results.get('philosopher_advice', []):
                        philosopher_advice.append(f"{advice['philosopher']}: {advice['advice']}")
                
                data_source['fundamental'] = {
                    'pe_ratio': financial_data.get('pe_ratio'),
                    'pb_ratio': financial_data.get('pb_ratio'),
                    'roe': financial_data.get('roe'),
                    'earnings_growth': financial_data.get('earnings_growth'),
                }
                
            except Exception as e:
                logger.warning(f"ファンダメンタル分析エラー ({ticker}): {str(e)}")
                # ファンダメンタル分析が失敗してもテクニカル分析は続行
            
            # 1. RSI判定
            rsi = indicators.get('rsi')
            if rsi:
                data_source['rsi'] = rsi
                if rsi <= self.RSI_OVERSOLD:
                    reasons.append(f"RSI過売り状態（RSI: {rsi:.2f}）")
                    confidence_factors.append(0.75)
                elif rsi > 50:
                    # RSIが50を上回っている場合は買いシグナルが弱い
                    confidence_factors.append(-0.2)
            
            # 2. MACD判定
            macd = indicators.get('macd')
            macd_signal = indicators.get('macd_signal')
            macd_hist = indicators.get('macd_hist')
            
            if macd and macd_signal and macd_hist:
                data_source['macd'] = macd
                data_source['macd_signal'] = macd_signal
                data_source['macd_hist'] = macd_hist
                
                # MACDがシグナルを上回る（買いシグナル）
                if macd > macd_signal and macd_hist > 0:
                    reasons.append(f"MACD買いシグナル（MACD: {macd:.2f}, Signal: {macd_signal:.2f}）")
                    confidence_factors.append(0.7)
            
            # 3. 移動平均線判定
            ma_20 = indicators.get('ma_20')
            ma_50 = indicators.get('ma_50')
            ma_200 = indicators.get('ma_200')
            
            if ma_20 and ma_50:
                data_source['ma_20'] = ma_20
                data_source['ma_50'] = ma_50
                
                # 短期移動平均が長期移動平均を上回る
                ma_ratio = (ma_20 - ma_50) / ma_50
                if ma_ratio > self.MA_CROSS_UP_THRESHOLD:
                    reasons.append(f"移動平均線ゴールデンクロス（MA20: ${ma_20:.2f}, MA50: ${ma_50:.2f}）")
                    confidence_factors.append(0.7)
            
            if ma_200:
                data_source['ma_200'] = ma_200
                # 現在価格が200日移動平均を上回る
                if current_price > ma_200:
                    reasons.append(f"200日移動平均を上回る（現在: ${current_price:.2f}, MA200: ${ma_200:.2f}）")
                    confidence_factors.append(0.6)
            
            # 4. ボリンジャーバンド判定
            bb_lower = indicators.get('bb_lower')
            if bb_lower and current_price <= bb_lower:
                data_source['bb_lower'] = bb_lower
                reasons.append(f"ボリンジャーバンド下限到達（下限: ${bb_lower:.2f}）")
                confidence_factors.append(0.65)
            
            # 5. 出来高判定
            volume = indicators.get('volume')
            volume_ma = indicators.get('volume_ma')
            if volume and volume_ma and volume > volume_ma * 1.5:
                data_source['volume'] = volume
                data_source['volume_ma'] = volume_ma
                reasons.append(f"出来高急増（現在: {volume:,.0f}, 平均: {volume_ma:,.0f}）")
                confidence_factors.append(0.5)
            
            # 信頼度の計算
            if confidence_factors:
                confidence = min(0.95, max(0.3, sum(confidence_factors) / len(confidence_factors)))
            else:
                confidence = 0.0
            
            # 推奨判定（信頼度が0.5以上の場合）
            if confidence >= 0.5 and reasons:
                logic = "以下の複数の指標が買いシグナルを示しています: " + "、".join(reasons)
                
                recommendation = {
                    'ticker': ticker,
                    'recommendation_type': 'BUY',
                    'recommendation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'current_price': current_price,
                    'recommended_price': current_price,  # 現在価格で購入推奨
                    'reason': " | ".join(reasons),
                    'data_source': data_source,
                    'logic': logic,
                    'confidence': confidence,
                    'philosopher_advice': philosopher_advice  # 賢人のアドバイスを追加
                }
                
                return recommendation
            
            return None
            
        except Exception as e:
            logger.error(f"買いシグナル分析エラー ({ticker}): {str(e)}")
            return None
    
    def check_portfolio_sell_signals(self, portfolio: list[dict]) -> list[dict]:
        """
        保有株式の売りシグナルをチェック
        
        Args:
            portfolio: 保有株式リスト
        
        Returns:
            list[dict]: 売り推奨リスト
        """
        sell_recommendations = []
        
        for stock in portfolio:
            try:
                recommendation = self.analyze_sell_signal(
                    stock['ticker'],
                    stock['current_price'],
                    stock['purchase_price_per_share'],
                    stock['profit_loss_rate']
                )
                
                if recommendation:
                    sell_recommendations.append(recommendation)
            except Exception as e:
                logger.error(f"売りシグナルチェックエラー ({stock.get('ticker', 'Unknown')}): {str(e)}")
                continue
        
        return sell_recommendations
    
    def check_buy_signals(self, tickers: list[str]) -> list[dict]:
        """
        指定銘柄の買いシグナルをチェック
        
        Args:
            tickers: チェックするティッカーシンボルのリスト
        
        Returns:
            list[dict]: 買い推奨リスト
        """
        buy_recommendations = []
        
        for ticker in tickers:
            try:
                recommendation = self.analyze_buy_signal(ticker)
                
                if recommendation:
                    buy_recommendations.append(recommendation)
            except Exception as e:
                logger.error(f"買いシグナルチェックエラー ({ticker}): {str(e)}")
                continue
        
        return buy_recommendations
