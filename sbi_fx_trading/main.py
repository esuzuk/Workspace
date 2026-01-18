#!/usr/bin/env python3
"""
FX自動売買システム - メインエントリーポイント

複数のFXブローカーに対応した自動売買システムです。
デモモード、バックテストモード、ライブトレードモードに対応しています。

対応ブローカー:
    - Saxo Bank (サクソバンク証券) - 推奨
    - SBI証券 (SBI FXトレード) - API未公開

使用方法:
    # デモモードで実行（Saxo Bank）
    python main.py --mode demo --broker saxo
    
    # バックテストを実行
    python main.py --mode backtest --strategy combined
    
    # ライブトレード（要認証設定）
    python main.py --mode live --broker saxo

注意:
    ライブトレードを行う前に必ずバックテストとデモモードで
    十分な検証を行ってください。
"""

import argparse
import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional

# ローカルモジュール
from api_client import (
    CurrencyPair, FXBrokerClient, MockBrokerClient, Order, OrderSide,
    OrderType, SBIFXClient, Tick, create_broker_client
)
from backtester import BacktestConfig, BacktestEngine, generate_sample_data
from config import Broker, TradingConfig, TradingMode, config
from indicators import TechnicalIndicators, calculate_all_indicators, ohlcv_to_dataframe
from risk_management import RiskManager, TradeRecord
from strategy import (
    BollingerBandStrategy, CombinedStrategy, MACDStrategy,
    MovingAverageCrossStrategy, RSIMeanReversionStrategy,
    TradingSignal, TradingStrategy, TrendFollowingStrategy, get_strategy
)

# ロギング設定
def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None) -> None:
    """ロギングをセットアップ"""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )

logger = logging.getLogger(__name__)


class TradingBot:
    """
    FX自動売買ボット
    
    戦略に基づいて自動的にトレードを実行します。
    """
    
    def __init__(
        self,
        broker_client: FXBrokerClient,
        strategy: TradingStrategy,
        risk_manager: RiskManager,
        trading_config: TradingConfig
    ):
        self.client = broker_client
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.config = trading_config
        self.is_running = False
        self._stop_event = asyncio.Event()
    
    async def start(self) -> None:
        """ボットを開始"""
        broker_names = {
            Broker.SBI: "SBI証券",
            Broker.SAXO: "サクソバンク証券 (Saxo Bank)",
            Broker.MOCK: "モック"
        }
        
        logger.info("=" * 60)
        logger.info("FX自動売買ボット 起動")
        logger.info("=" * 60)
        logger.info(f"ブローカー: {broker_names.get(self.config.api.broker, 'Unknown')}")
        logger.info(f"戦略: {self.strategy.name}")
        logger.info(f"モード: {self.config.api.mode.value}")
        logger.info(f"通貨ペア: {[p.value for p in self.config.strategy.currency_pairs]}")
        
        # API接続
        try:
            connected = await self.client.connect()
            if not connected:
                logger.error("API接続に失敗しました")
                return
        except NotImplementedError as e:
            logger.error(f"API接続エラー: {e}")
            return
        
        self.is_running = True
        logger.info("ボット稼働中... (Ctrl+C で停止)")
        
        try:
            await self._trading_loop()
        except asyncio.CancelledError:
            logger.info("ボット停止リクエストを受信")
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """ボットを停止"""
        logger.info("ボットを停止中...")
        self.is_running = False
        self._stop_event.set()
        
        # オープンポジションを確認
        positions = await self.client.get_positions()
        if positions:
            logger.warning(f"オープンポジション: {len(positions)}件")
            for pos in positions:
                logger.warning(f"  {pos.currency_pair.value}: {pos.side.value} "
                             f"{pos.quantity:,}通貨 @ {pos.entry_price}")
        
        await self.client.disconnect()
        logger.info("ボットを停止しました")
    
    async def _trading_loop(self) -> None:
        """メイントレードループ"""
        poll_interval = 60  # 1分間隔でチェック
        
        while self.is_running and not self._stop_event.is_set():
            try:
                await self._execute_trading_cycle()
            except Exception as e:
                logger.error(f"トレードサイクルでエラー: {e}", exc_info=True)
            
            # 次のサイクルまで待機
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=poll_interval
                )
            except asyncio.TimeoutError:
                pass  # タイムアウトは正常（次のサイクルへ）
    
    async def _execute_trading_cycle(self) -> None:
        """1回のトレードサイクルを実行"""
        # 口座情報を取得
        account = await self.client.get_account_info()
        logger.debug(f"口座残高: ¥{account.balance:,.0f}")
        
        # 現在のポジションを取得
        positions = await self.client.get_positions()
        
        # リスク評価
        risk_assessment = self.risk_manager.assess_risk(account, positions)
        
        if risk_assessment.warnings:
            for warning in risk_assessment.warnings:
                logger.warning(f"リスク警告: {warning}")
        
        if not risk_assessment.can_trade:
            logger.warning(f"取引停止: {risk_assessment.reason}")
            return
        
        # 各通貨ペアをチェック
        for currency_pair in self.config.strategy.currency_pairs:
            await self._check_currency_pair(currency_pair, account, positions)
    
    async def _check_currency_pair(
        self,
        currency_pair: CurrencyPair,
        account,
        positions
    ) -> None:
        """通貨ペアをチェックしてシグナルを処理"""
        # ティックデータを取得
        tick = await self.client.get_tick(currency_pair)
        
        # ローソク足データを取得
        ohlcv_data = await self.client.get_ohlcv(
            currency_pair,
            self.config.strategy.primary_timeframe.value,
            count=200
        )
        
        if not ohlcv_data:
            logger.warning(f"{currency_pair.value}: ローソク足データなし")
            return
        
        # シグナルを生成
        signal = self.strategy.generate_signal(currency_pair, ohlcv_data, tick)
        
        # シグナルを処理
        if signal.is_buy_signal or signal.is_sell_signal:
            await self._process_signal(signal, tick, account)
        
        # 既存ポジションの管理
        for pos in positions:
            if pos.currency_pair == currency_pair:
                should_close, reason = self.risk_manager.should_close_position(
                    pos,
                    tick.bid if pos.side == OrderSide.BUY else tick.ask
                )
                if should_close:
                    logger.info(f"ポジション決済: {pos.position_id} - {reason}")
                    await self.client.close_position(pos.position_id)
    
    async def _process_signal(
        self,
        signal: TradingSignal,
        tick: Tick,
        account
    ) -> None:
        """シグナルを処理して注文を実行"""
        logger.info(f"シグナル検出: {signal.currency_pair.value} "
                   f"{signal.signal_type.value} (信頼度: {signal.confidence:.2f})")
        logger.info(f"  理由: {signal.reason}")
        
        # 信頼度が低すぎる場合はスキップ
        if signal.confidence < 0.5:
            logger.debug("信頼度が低いためスキップ")
            return
        
        # エントリー価格を決定
        entry_price = signal.entry_price or (
            tick.ask if signal.is_buy_signal else tick.bid
        )
        
        # ストップロス・テイクプロフィットを計算
        stop_loss = signal.stop_loss
        take_profit = signal.take_profit
        
        if not stop_loss:
            stop_loss = self.risk_manager.calculate_stop_loss(
                entry_price, signal.order_side, currency_pair=signal.currency_pair
            )
        
        if not take_profit:
            take_profit = self.risk_manager.calculate_take_profit(
                entry_price, stop_loss, signal.order_side
            )
        
        # ポジションサイズを計算
        size_result = self.risk_manager.calculate_position_size(
            account, entry_price, stop_loss, take_profit, signal.currency_pair
        )
        
        logger.info(f"  ポジションサイズ: {size_result.recommended_size:,}通貨")
        logger.info(f"  損切り: {stop_loss} ({size_result.stop_loss_pips:.1f}pips)")
        logger.info(f"  利確: {take_profit}")
        
        # 注文を作成
        order = Order(
            order_id="",  # APIで割り当て
            currency_pair=signal.currency_pair,
            side=signal.order_side,
            order_type=OrderType.MARKET,
            quantity=size_result.recommended_size,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        # 注文を発注
        try:
            filled_order = await self.client.place_order(order)
            logger.info(f"注文約定: {filled_order.order_id} @ {filled_order.filled_price}")
            
            # 取引を記録
            self.risk_manager.record_trade(TradeRecord(
                timestamp=datetime.now(),
                currency_pair=signal.currency_pair,
                side=signal.order_side,
                entry_price=filled_order.filled_price,
                exit_price=None,
                quantity=filled_order.quantity,
                pnl=None,
                pnl_pips=None
            ))
        except Exception as e:
            logger.error(f"注文エラー: {e}")


async def run_demo_mode(args: argparse.Namespace) -> None:
    """デモモードで実行"""
    logger.info("デモモードで実行中...")
    
    # 設定をデモモードに
    config.api.mode = TradingMode.DEMO
    
    # コンポーネントを初期化
    client = create_broker_client(config)
    strategy = get_strategy(args.strategy, config.strategy)
    risk_manager = RiskManager(config.risk)
    
    # ボットを起動
    bot = TradingBot(client, strategy, risk_manager, config)
    
    # シグナルハンドラー設定
    def signal_handler(sig, frame):
        logger.info("停止シグナルを受信...")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await bot.start()


async def run_backtest_mode(args: argparse.Namespace) -> None:
    """バックテストモードで実行"""
    logger.info("バックテストモードで実行中...")
    
    # 戦略を取得
    strategy = get_strategy(args.strategy, config.strategy)
    
    # サンプルデータを生成（実際の運用では過去データを読み込む）
    logger.info("テストデータを生成中...")
    data = generate_sample_data(
        currency_pair=CurrencyPair.USDJPY,
        bars=args.bars or 2000,
        timeframe_hours=1,
        trend=0.00002,
        volatility=0.0006
    )
    
    logger.info(f"データ期間: {data[0].timestamp.date()} 〜 {data[-1].timestamp.date()}")
    logger.info(f"バー数: {len(data)}")
    
    # バックテスト設定
    backtest_config = BacktestConfig(
        initial_balance=Decimal(str(args.balance or 1000000)),
        spread_pips=0.3,
        slippage_pips=0.1
    )
    
    # バックテスト実行
    engine = BacktestEngine(strategy, config.risk, backtest_config)
    result = engine.run(data, CurrencyPair.USDJPY)
    
    # 結果を表示
    result.print_summary()
    
    # 取引詳細を表示（オプション）
    if args.verbose:
        print("\n【取引詳細】")
        for trade in result.trades[:20]:  # 最初の20件
            print(f"  {trade.entry_time.strftime('%Y-%m-%d %H:%M')} "
                  f"{trade.side.value} @ {trade.entry_price} → "
                  f"{trade.exit_price} ({trade.pnl_pips:+.1f}pips) "
                  f"[{trade.exit_reason}]")
        
        if len(result.trades) > 20:
            print(f"  ... 他 {len(result.trades) - 20} 件")


async def run_live_mode(args: argparse.Namespace) -> None:
    """ライブトレードモードで実行"""
    logger.warning("=" * 50)
    logger.warning("⚠️  ライブトレードモード")
    logger.warning("⚠️  実際のお金でトレードします")
    logger.warning("=" * 50)
    
    # 確認
    if not args.force:
        confirm = input("本当にライブトレードを開始しますか？ (yes/no): ")
        if confirm.lower() != "yes":
            logger.info("キャンセルしました")
            return
    
    # 認証情報チェック
    if not config.api.user_id or not config.api.password:
        logger.error("認証情報が設定されていません。.envファイルを確認してください。")
        return
    
    config.api.mode = TradingMode.LIVE
    
    # コンポーネントを初期化
    client = create_broker_client(config)
    strategy = get_strategy(args.strategy, config.strategy)
    risk_manager = RiskManager(config.risk)
    
    # ボットを起動
    bot = TradingBot(client, strategy, risk_manager, config)
    
    # シグナルハンドラー設定
    def signal_handler(sig, frame):
        logger.info("停止シグナルを受信...")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await bot.start()


def show_strategies() -> None:
    """利用可能な戦略を表示"""
    print("\n利用可能な戦略:")
    print("-" * 40)
    strategies = {
        "ma_cross": "移動平均線クロス戦略",
        "rsi_reversal": "RSI平均回帰戦略",
        "bollinger": "ボリンジャーバンド戦略",
        "macd": "MACD戦略",
        "trend_following": "トレンドフォロー戦略",
        "combined": "複合戦略（推奨）",
    }
    for name, description in strategies.items():
        print(f"  {name:20} - {description}")
    print()


def show_brokers() -> None:
    """利用可能なブローカーを表示"""
    print("\n利用可能なブローカー:")
    print("-" * 50)
    brokers = {
        "saxo": "サクソバンク証券 (Saxo Bank) - 推奨",
        "sbi": "SBI証券 (SBI FXトレード) - API未公開",
        "mock": "モック（バックテスト用）",
    }
    for name, description in brokers.items():
        print(f"  {name:10} - {description}")
    print()


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="FX自動売買システム（Saxo Bank / SBI証券対応）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  # Saxo Bankでデモ実行
  python main.py --mode demo --broker saxo --strategy combined
  
  # バックテストを実行
  python main.py --mode backtest --strategy ma_cross --bars 3000
  
  # Saxo Bankでライブトレード
  python main.py --mode live --broker saxo
  
  # 利用可能な戦略・ブローカーを表示
  python main.py --list-strategies
  python main.py --list-brokers
"""
    )
    
    parser.add_argument(
        "--mode", "-m",
        choices=["demo", "backtest", "live"],
        default="demo",
        help="実行モード (default: demo)"
    )
    
    parser.add_argument(
        "--broker",
        choices=["saxo", "sbi", "mock"],
        default=None,
        help="使用するブローカー (default: 環境変数から読み込み)"
    )
    
    parser.add_argument(
        "--strategy", "-s",
        default="combined",
        help="使用する戦略 (default: combined)"
    )
    
    parser.add_argument(
        "--list-strategies",
        action="store_true",
        help="利用可能な戦略を表示"
    )
    
    parser.add_argument(
        "--list-brokers",
        action="store_true",
        help="利用可能なブローカーを表示"
    )
    
    parser.add_argument(
        "--bars", "-b",
        type=int,
        default=2000,
        help="バックテストのバー数 (default: 2000)"
    )
    
    parser.add_argument(
        "--balance",
        type=int,
        default=1000000,
        help="初期資金（円） (default: 1000000)"
    )
    
    parser.add_argument(
        "--log-level", "-l",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="ログレベル (default: INFO)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="詳細出力"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="確認なしで実行（ライブモード用）"
    )
    
    args = parser.parse_args()
    
    # 戦略リスト表示
    if args.list_strategies:
        show_strategies()
        return
    
    # ブローカーリスト表示
    if args.list_brokers:
        show_brokers()
        return
    
    # ブローカー設定を上書き
    if args.broker:
        config.api.broker = Broker(args.broker)
    
    # ロギング設定
    log_file = config.log.file_path if args.mode == "live" else None
    setup_logging(args.log_level, log_file)
    
    # 設定を表示
    if args.verbose:
        config.display()
    
    # モードに応じて実行
    if args.mode == "demo":
        asyncio.run(run_demo_mode(args))
    elif args.mode == "backtest":
        asyncio.run(run_backtest_mode(args))
    elif args.mode == "live":
        asyncio.run(run_live_mode(args))


if __name__ == "__main__":
    main()
