"""
FX自動売買システム - 設定管理モジュール

FXトレード向けの設定を一元管理します。
環境変数からの読み込みと、デフォルト値の設定を行います。

対応ブローカー:
- SBI証券（SBI FXトレード）
- Saxo Bank（サクソバンク証券）
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()


class Broker(Enum):
    """対応ブローカー"""
    SBI = "sbi"           # SBI証券
    SAXO = "saxo"         # サクソバンク証券
    MOCK = "mock"         # モック（バックテスト用）


class TradingMode(Enum):
    """トレードモード"""
    DEMO = "demo"
    LIVE = "live"
    BACKTEST = "backtest"


class TimeFrame(Enum):
    """時間足"""
    M1 = "1min"
    M5 = "5min"
    M15 = "15min"
    M30 = "30min"
    H1 = "1hour"
    H4 = "4hour"
    D1 = "daily"
    W1 = "weekly"


class CurrencyPair(Enum):
    """通貨ペア"""
    USDJPY = "USD/JPY"
    EURJPY = "EUR/JPY"
    GBPJPY = "GBP/JPY"
    AUDJPY = "AUD/JPY"
    EURUSD = "EUR/USD"
    GBPUSD = "GBP/USD"
    AUDUSD = "AUD/USD"


@dataclass
class APIConfig:
    """API接続設定"""
    # ブローカー選択
    broker: Broker = field(
        default_factory=lambda: Broker(os.getenv("BROKER", "saxo"))
    )
    
    # トレードモード
    mode: TradingMode = field(
        default_factory=lambda: TradingMode(os.getenv("TRADING_MODE", "demo"))
    )
    
    # === SBI証券設定 ===
    sbi_user_id: str = field(default_factory=lambda: os.getenv("SBI_USER_ID", ""))
    sbi_password: str = field(default_factory=lambda: os.getenv("SBI_PASSWORD", ""))
    sbi_base_url: str = "https://api.sbisec.co.jp/fx"
    sbi_demo_url: str = "https://demo-api.sbisec.co.jp/fx"
    
    # === Saxo Bank設定 ===
    saxo_app_key: str = field(default_factory=lambda: os.getenv("SAXO_APP_KEY", ""))
    saxo_app_secret: str = field(default_factory=lambda: os.getenv("SAXO_APP_SECRET", ""))
    saxo_redirect_uri: str = field(
        default_factory=lambda: os.getenv("SAXO_REDIRECT_URI", "http://localhost:8080/callback")
    )
    saxo_environment: str = field(
        default_factory=lambda: os.getenv("SAXO_ENVIRONMENT", "sim")  # sim or live
    )
    
    # Saxo Bank APIエンドポイント
    saxo_sim_auth_url: str = "https://sim.logonvalidation.net"
    saxo_live_auth_url: str = "https://live.logonvalidation.net"
    saxo_sim_api_url: str = "https://gateway.saxobank.com/sim/openapi"
    saxo_live_api_url: str = "https://gateway.saxobank.com/openapi"
    saxo_sim_ws_url: str = "wss://streaming.saxobank.com/sim/openapi/streamingws"
    saxo_live_ws_url: str = "wss://streaming.saxobank.com/openapi/streamingws"
    
    @property
    def endpoint(self) -> str:
        """現在のモードに応じたエンドポイントを返す"""
        if self.broker == Broker.SAXO:
            if self.saxo_environment == "live":
                return self.saxo_live_api_url
            return self.saxo_sim_api_url
        else:  # SBI
            if self.mode == TradingMode.DEMO:
                return self.sbi_demo_url
            return self.sbi_base_url
    
    @property
    def is_saxo(self) -> bool:
        """Saxo Bankを使用するかどうか"""
        return self.broker == Broker.SAXO
    
    @property
    def is_sbi(self) -> bool:
        """SBI証券を使用するかどうか"""
        return self.broker == Broker.SBI


@dataclass
class RiskConfig:
    """リスク管理設定"""
    # 1トレードあたりのリスク（口座残高に対する割合）
    risk_per_trade: float = field(
        default_factory=lambda: float(os.getenv("RISK_PER_TRADE", "0.02"))
    )
    
    # ポジション設定
    default_lot_size: int = field(
        default_factory=lambda: int(os.getenv("DEFAULT_LOT_SIZE", "1000"))
    )
    max_position_size: int = field(
        default_factory=lambda: int(os.getenv("MAX_POSITION_SIZE", "10000"))
    )
    
    # ストップロス・テイクプロフィット（pips）
    default_stop_loss_pips: float = 30.0
    default_take_profit_pips: float = 60.0
    
    # 最大同時ポジション数
    max_open_positions: int = 3
    
    # 1日の最大取引回数
    max_trades_per_day: int = 10
    
    # 最大ドローダウン（%）- これを超えたら取引停止
    max_drawdown_percent: float = 10.0


@dataclass
class StrategyConfig:
    """トレード戦略設定"""
    # 使用する時間足
    primary_timeframe: TimeFrame = TimeFrame.H1
    secondary_timeframe: TimeFrame = TimeFrame.M15
    
    # 対象通貨ペア
    currency_pairs: List[CurrencyPair] = field(
        default_factory=lambda: [CurrencyPair.USDJPY, CurrencyPair.EURJPY]
    )
    
    # テクニカル指標のパラメータ
    # 移動平均
    sma_short_period: int = 20
    sma_long_period: int = 50
    ema_period: int = 21
    
    # RSI
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    
    # MACD
    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9
    
    # ボリンジャーバンド
    bb_period: int = 20
    bb_std_dev: float = 2.0
    
    # ATR（Average True Range）
    atr_period: int = 14


@dataclass
class NotificationConfig:
    """通知設定"""
    slack_webhook_url: Optional[str] = field(
        default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL")
    )
    line_notify_token: Optional[str] = field(
        default_factory=lambda: os.getenv("LINE_NOTIFY_TOKEN")
    )
    
    # 通知トリガー
    notify_on_trade: bool = True
    notify_on_error: bool = True
    notify_daily_summary: bool = True


@dataclass
class LogConfig:
    """ログ設定"""
    level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    file_path: Path = field(
        default_factory=lambda: Path(os.getenv("LOG_FILE_PATH", "./logs/trading.log"))
    )
    
    # ログローテーション
    max_file_size_mb: int = 10
    backup_count: int = 5


@dataclass
class TradingConfig:
    """統合設定クラス"""
    api: APIConfig = field(default_factory=APIConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    log: LogConfig = field(default_factory=LogConfig)
    
    def validate(self) -> bool:
        """設定の検証"""
        errors = []
        warnings = []
        
        # API認証情報のチェック
        if self.api.mode == TradingMode.LIVE:
            if self.api.broker == Broker.SBI:
                if not self.api.sbi_user_id or not self.api.sbi_password:
                    errors.append("SBI証券: 本番モードではユーザーIDとパスワードが必須です")
            elif self.api.broker == Broker.SAXO:
                if not self.api.saxo_app_key or not self.api.saxo_app_secret:
                    errors.append("Saxo Bank: 本番モードではApp KeyとApp Secretが必須です")
        
        # Saxo Bank 環境チェック
        if self.api.broker == Broker.SAXO:
            if self.api.saxo_environment == "live" and self.api.mode != TradingMode.LIVE:
                warnings.append("Saxo Bank: 本番環境が設定されていますが、トレードモードがLIVEではありません")
        
        # リスク設定のチェック
        if self.risk.risk_per_trade > 0.05:
            warnings.append("1トレードあたりのリスクが5%を超えています（推奨: 1-2%）")
        
        if self.risk.max_drawdown_percent > 20.0:
            warnings.append("最大ドローダウンが20%を超えています")
        
        # 警告の表示
        for warning in warnings:
            print(f"⚠️ 警告: {warning}")
        
        # エラーの表示
        if errors:
            for error in errors:
                print(f"❌ エラー: {error}")
            return False
        
        return True
    
    def display(self) -> None:
        """設定の表示（機密情報は隠す）"""
        print("=" * 60)
        print("FX自動売買システム - 現在の設定")
        print("=" * 60)
        
        # ブローカー情報
        broker_names = {
            Broker.SBI: "SBI証券（SBI FXトレード）",
            Broker.SAXO: "サクソバンク証券（Saxo Bank）",
            Broker.MOCK: "モック（バックテスト用）"
        }
        print(f"ブローカー: {broker_names.get(self.api.broker, self.api.broker.value)}")
        print(f"トレードモード: {self.api.mode.value}")
        
        # ブローカー固有の設定
        if self.api.broker == Broker.SAXO:
            print(f"Saxo環境: {'本番' if self.api.saxo_environment == 'live' else 'シミュレーション'}")
            print(f"App Key: {'*' * 8 + self.api.saxo_app_key[-4:] if len(self.api.saxo_app_key) > 4 else '未設定'}")
        elif self.api.broker == Broker.SBI:
            print(f"ユーザーID: {'*' * len(self.api.sbi_user_id) if self.api.sbi_user_id else '未設定'}")
        
        print(f"\n【リスク管理】")
        print(f"  1トレードリスク: {self.risk.risk_per_trade * 100:.1f}%")
        print(f"  デフォルトロット: {self.risk.default_lot_size:,}通貨")
        print(f"  最大ポジション: {self.risk.max_position_size:,}通貨")
        print(f"  損切り: {self.risk.default_stop_loss_pips} pips")
        print(f"  利確: {self.risk.default_take_profit_pips} pips")
        print(f"\n【戦略設定】")
        print(f"  主時間足: {self.strategy.primary_timeframe.value}")
        print(f"  通貨ペア: {', '.join([p.value for p in self.strategy.currency_pairs])}")
        print("=" * 60)


# グローバル設定インスタンス
config = TradingConfig()


if __name__ == "__main__":
    # 設定のテスト
    config.display()
    config.validate()
