"""
FX自動売買システム - リスク管理モジュール

ポジションサイズの計算、損切り・利確の設定、
資金管理ルールの適用を行います。

リスク管理の原則:
1. 1トレードあたりのリスクは口座残高の1-2%以下
2. 最大ドローダウンを制限
3. 複数ポジションのリスク分散
4. レバレッジの適切な管理
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple
import logging

from api_client import AccountInfo, CurrencyPair, Order, OrderSide, Position
from config import RiskConfig

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """リスクレベル"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PositionSizeResult:
    """ポジションサイズ計算結果"""
    recommended_size: int  # 推奨ポジションサイズ（通貨単位）
    max_size: int  # 最大許容サイズ
    risk_amount: Decimal  # リスク金額（円）
    stop_loss_pips: float  # 損切り幅（pips）
    risk_reward_ratio: float  # リスクリワード比
    leverage_used: float  # 使用レバレッジ
    
    def to_dict(self) -> Dict:
        return {
            "recommended_size": self.recommended_size,
            "max_size": self.max_size,
            "risk_amount": float(self.risk_amount),
            "stop_loss_pips": self.stop_loss_pips,
            "risk_reward_ratio": self.risk_reward_ratio,
            "leverage_used": self.leverage_used
        }


@dataclass
class RiskAssessment:
    """リスク評価結果"""
    level: RiskLevel
    current_drawdown: float  # 現在のドローダウン（%）
    open_position_risk: Decimal  # オープンポジションのリスク金額
    daily_loss: Decimal  # 本日の損失額
    warnings: List[str] = field(default_factory=list)
    can_trade: bool = True
    reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "level": self.level.value,
            "current_drawdown": self.current_drawdown,
            "open_position_risk": float(self.open_position_risk),
            "daily_loss": float(self.daily_loss),
            "warnings": self.warnings,
            "can_trade": self.can_trade,
            "reason": self.reason
        }


@dataclass
class TradeRecord:
    """取引記録"""
    timestamp: datetime
    currency_pair: CurrencyPair
    side: OrderSide
    entry_price: Decimal
    exit_price: Optional[Decimal]
    quantity: int
    pnl: Optional[Decimal]
    pnl_pips: Optional[float]


class RiskManager:
    """リスク管理クラス"""
    
    def __init__(self, config: RiskConfig):
        self.config = config
        self.trade_history: List[TradeRecord] = []
        self.daily_trades: int = 0
        self.daily_loss: Decimal = Decimal("0")
        self.peak_balance: Decimal = Decimal("0")
        self.last_reset_date: datetime = datetime.now().date()
    
    def calculate_position_size(
        self,
        account_info: AccountInfo,
        entry_price: Decimal,
        stop_loss_price: Decimal,
        take_profit_price: Optional[Decimal] = None,
        currency_pair: CurrencyPair = CurrencyPair.USDJPY
    ) -> PositionSizeResult:
        """
        適切なポジションサイズを計算
        
        Kelly Criterion をベースに、リスク許容度に応じたサイズを算出します。
        
        Args:
            account_info: 口座情報
            entry_price: エントリー価格
            stop_loss_price: 損切り価格
            take_profit_price: 利確価格（オプション）
            currency_pair: 通貨ペア
        
        Returns:
            PositionSizeResult
        """
        # 損切り幅を計算（pips）
        pip_value = Decimal("0.01") if "JPY" in currency_pair.value else Decimal("0.0001")
        stop_loss_pips = abs(float(entry_price - stop_loss_price) / float(pip_value))
        
        # リスク金額を計算
        risk_amount = account_info.balance * Decimal(str(self.config.risk_per_trade))
        
        # ポジションサイズを計算
        # リスク金額 = ポジションサイズ × 損切り幅 × pip価値
        # JPY通貨ペアの場合、1pip = 0.01円 × ポジションサイズ
        if "JPY" in currency_pair.value:
            # 例: USD/JPY 10,000通貨で1pip動くと100円の損益
            pip_value_per_lot = Decimal("0.01") * 1000  # 1000通貨あたりの1pip = 10円
        else:
            # 非JPYペアの場合（例: EUR/USD）
            pip_value_per_lot = Decimal("0.0001") * 1000 * entry_price
        
        # 推奨ポジションサイズ
        if stop_loss_pips > 0:
            position_size = int(risk_amount / (Decimal(str(stop_loss_pips)) * pip_value_per_lot / 1000))
            position_size = (position_size // 1000) * 1000  # 1000通貨単位に丸める
        else:
            position_size = self.config.default_lot_size
        
        # 最大サイズ制限を適用
        max_size = min(position_size, self.config.max_position_size)
        
        # 証拠金チェック（レバレッジ25倍）
        required_margin = entry_price * max_size / 25
        if required_margin > account_info.margin_available:
            max_size = int(account_info.margin_available * 25 / entry_price)
            max_size = (max_size // 1000) * 1000
        
        # レバレッジ計算
        leverage_used = float(entry_price * max_size / account_info.balance)
        
        # リスクリワード比
        if take_profit_price:
            take_profit_pips = abs(float(take_profit_price - entry_price) / float(pip_value))
            risk_reward_ratio = take_profit_pips / stop_loss_pips if stop_loss_pips > 0 else 0
        else:
            risk_reward_ratio = 2.0  # デフォルト
        
        return PositionSizeResult(
            recommended_size=max_size,
            max_size=self.config.max_position_size,
            risk_amount=risk_amount,
            stop_loss_pips=stop_loss_pips,
            risk_reward_ratio=risk_reward_ratio,
            leverage_used=leverage_used
        )
    
    def assess_risk(
        self,
        account_info: AccountInfo,
        positions: List[Position]
    ) -> RiskAssessment:
        """
        現在のリスク状況を評価
        
        Args:
            account_info: 口座情報
            positions: 保有ポジション一覧
        
        Returns:
            RiskAssessment
        """
        warnings = []
        can_trade = True
        reason = ""
        
        # 日次リセットチェック
        self._check_daily_reset()
        
        # ドローダウン計算
        if self.peak_balance == Decimal("0"):
            self.peak_balance = account_info.balance
        elif account_info.balance > self.peak_balance:
            self.peak_balance = account_info.balance
        
        current_drawdown = float(
            (self.peak_balance - account_info.equity) / self.peak_balance * 100
        ) if self.peak_balance > 0 else 0
        
        # オープンポジションのリスク計算
        open_position_risk = Decimal("0")
        for position in positions:
            if position.stop_loss:
                pip_value = Decimal("0.01") if "JPY" in position.currency_pair.value else Decimal("0.0001")
                sl_pips = abs(position.entry_price - position.stop_loss) / pip_value
                risk = sl_pips * position.quantity * pip_value
                open_position_risk += risk
        
        # リスクレベル判定
        if current_drawdown >= self.config.max_drawdown_percent:
            level = RiskLevel.CRITICAL
            can_trade = False
            reason = f"最大ドローダウン（{self.config.max_drawdown_percent}%）に到達"
            warnings.append(reason)
        elif current_drawdown >= self.config.max_drawdown_percent * 0.7:
            level = RiskLevel.HIGH
            warnings.append(f"ドローダウン警告: {current_drawdown:.1f}%")
        elif current_drawdown >= self.config.max_drawdown_percent * 0.5:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
        
        # 日次取引回数チェック
        if self.daily_trades >= self.config.max_trades_per_day:
            can_trade = False
            reason = f"本日の最大取引回数（{self.config.max_trades_per_day}回）に到達"
            warnings.append(reason)
        
        # 同時ポジション数チェック
        if len(positions) >= self.config.max_open_positions:
            can_trade = False
            reason = f"最大同時ポジション数（{self.config.max_open_positions}）に到達"
            warnings.append(reason)
        
        # 証拠金維持率チェック
        if account_info.margin_level and account_info.margin_level < Decimal("200"):
            level = RiskLevel.CRITICAL
            warnings.append(f"証拠金維持率低下: {account_info.margin_level:.0f}%")
            if account_info.margin_level < Decimal("150"):
                can_trade = False
                reason = "証拠金維持率が危険水準"
        
        return RiskAssessment(
            level=level,
            current_drawdown=current_drawdown,
            open_position_risk=open_position_risk,
            daily_loss=self.daily_loss,
            warnings=warnings,
            can_trade=can_trade,
            reason=reason
        )
    
    def calculate_stop_loss(
        self,
        entry_price: Decimal,
        side: OrderSide,
        atr: Optional[float] = None,
        currency_pair: CurrencyPair = CurrencyPair.USDJPY
    ) -> Decimal:
        """
        損切り価格を計算
        
        ATRベースまたは固定pipsで計算します。
        
        Args:
            entry_price: エントリー価格
            side: 売買方向
            atr: ATR値（オプション）
            currency_pair: 通貨ペア
        
        Returns:
            損切り価格
        """
        if atr:
            # ATRベースの損切り（ATRの2倍）
            stop_distance = Decimal(str(atr * 2))
        else:
            # 固定pipsの損切り
            pip_value = Decimal("0.01") if "JPY" in currency_pair.value else Decimal("0.0001")
            stop_distance = pip_value * Decimal(str(self.config.default_stop_loss_pips))
        
        if side == OrderSide.BUY:
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance
    
    def calculate_take_profit(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        side: OrderSide,
        risk_reward_ratio: float = 2.0
    ) -> Decimal:
        """
        利確価格を計算
        
        リスクリワード比に基づいて計算します。
        
        Args:
            entry_price: エントリー価格
            stop_loss: 損切り価格
            side: 売買方向
            risk_reward_ratio: リスクリワード比（デフォルト2.0）
        
        Returns:
            利確価格
        """
        stop_distance = abs(entry_price - stop_loss)
        profit_distance = stop_distance * Decimal(str(risk_reward_ratio))
        
        if side == OrderSide.BUY:
            return entry_price + profit_distance
        else:
            return entry_price - profit_distance
    
    def should_close_position(
        self,
        position: Position,
        current_tick_price: Decimal
    ) -> Tuple[bool, str]:
        """
        ポジションを決済すべきか判断
        
        Args:
            position: ポジション
            current_tick_price: 現在価格
        
        Returns:
            (決済すべきか, 理由)
        """
        # 損切りチェック
        if position.stop_loss:
            if position.side == OrderSide.BUY:
                if current_tick_price <= position.stop_loss:
                    return True, "損切りライン到達"
            else:
                if current_tick_price >= position.stop_loss:
                    return True, "損切りライン到達"
        
        # 利確チェック
        if position.take_profit:
            if position.side == OrderSide.BUY:
                if current_tick_price >= position.take_profit:
                    return True, "利確ライン到達"
            else:
                if current_tick_price <= position.take_profit:
                    return True, "利確ライン到達"
        
        return False, ""
    
    def update_trailing_stop(
        self,
        position: Position,
        current_price: Decimal,
        trailing_distance_pips: float = 20.0
    ) -> Optional[Decimal]:
        """
        トレーリングストップを更新
        
        Args:
            position: ポジション
            current_price: 現在価格
            trailing_distance_pips: トレーリング幅（pips）
        
        Returns:
            新しい損切り価格（更新不要の場合はNone）
        """
        pip_value = Decimal("0.01") if "JPY" in position.currency_pair.value else Decimal("0.0001")
        trailing_distance = pip_value * Decimal(str(trailing_distance_pips))
        
        if position.side == OrderSide.BUY:
            # 買いポジション: 価格上昇に合わせて損切りを引き上げ
            new_stop = current_price - trailing_distance
            if position.stop_loss and new_stop > position.stop_loss:
                return new_stop
        else:
            # 売りポジション: 価格下落に合わせて損切りを引き下げ
            new_stop = current_price + trailing_distance
            if position.stop_loss and new_stop < position.stop_loss:
                return new_stop
        
        return None
    
    def record_trade(self, record: TradeRecord) -> None:
        """取引を記録"""
        self.trade_history.append(record)
        self.daily_trades += 1
        
        if record.pnl:
            if record.pnl < 0:
                self.daily_loss += abs(record.pnl)
        
        logger.info(f"取引記録: {record.currency_pair.value} {record.side.value} "
                   f"PnL: {record.pnl if record.pnl else 'N/A'}")
    
    def _check_daily_reset(self) -> None:
        """日次リセットチェック"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_trades = 0
            self.daily_loss = Decimal("0")
            self.last_reset_date = today
            logger.info("日次カウンターをリセットしました")
    
    def get_statistics(self) -> Dict:
        """取引統計を取得"""
        if not self.trade_history:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "average_pnl": 0.0,
                "max_win": 0.0,
                "max_loss": 0.0,
                "profit_factor": 0.0
            }
        
        closed_trades = [t for t in self.trade_history if t.pnl is not None]
        
        if not closed_trades:
            return {
                "total_trades": len(self.trade_history),
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "average_pnl": 0.0,
                "max_win": 0.0,
                "max_loss": 0.0,
                "profit_factor": 0.0
            }
        
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl < 0]
        
        total_profit = sum(t.pnl for t in winning_trades)
        total_loss = abs(sum(t.pnl for t in losing_trades))
        
        return {
            "total_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0,
            "total_pnl": float(sum(t.pnl for t in closed_trades)),
            "average_pnl": float(sum(t.pnl for t in closed_trades) / len(closed_trades)),
            "max_win": float(max((t.pnl for t in winning_trades), default=Decimal("0"))),
            "max_loss": float(min((t.pnl for t in losing_trades), default=Decimal("0"))),
            "profit_factor": float(total_profit / total_loss) if total_loss > 0 else float("inf")
        }


class PartialCloseManager:
    """部分決済マネージャー"""
    
    def __init__(self, close_levels: List[Tuple[float, float]] = None):
        """
        Args:
            close_levels: [(利益pips, 決済割合), ...]
                例: [(30, 0.5), (50, 0.3), (80, 0.2)]
                    30pips で50%、50pipsで30%、80pipsで20%決済
        """
        self.close_levels = close_levels or [
            (30.0, 0.5),  # 30pipsで50%決済
            (60.0, 0.3),  # 60pipsで30%決済
            (100.0, 0.2)  # 100pipsで残り20%決済
        ]
        self.executed_levels: Dict[str, List[int]] = {}
    
    def check_partial_close(
        self,
        position: Position,
        current_price: Decimal
    ) -> Optional[Tuple[int, str]]:
        """
        部分決済が必要か確認
        
        Args:
            position: ポジション
            current_price: 現在価格
        
        Returns:
            (決済数量, 理由) または None
        """
        pip_value = Decimal("0.01") if "JPY" in position.currency_pair.value else Decimal("0.0001")
        
        if position.side == OrderSide.BUY:
            profit_pips = float((current_price - position.entry_price) / pip_value)
        else:
            profit_pips = float((position.entry_price - current_price) / pip_value)
        
        if profit_pips <= 0:
            return None
        
        # 実行済みレベルを取得
        if position.position_id not in self.executed_levels:
            self.executed_levels[position.position_id] = []
        
        for level_idx, (target_pips, close_ratio) in enumerate(self.close_levels):
            if level_idx in self.executed_levels[position.position_id]:
                continue
            
            if profit_pips >= target_pips:
                close_quantity = int(position.quantity * close_ratio)
                close_quantity = (close_quantity // 1000) * 1000  # 1000通貨単位に丸める
                
                if close_quantity > 0:
                    self.executed_levels[position.position_id].append(level_idx)
                    return (
                        close_quantity,
                        f"部分決済: {target_pips}pips到達で{close_ratio*100:.0f}%決済"
                    )
        
        return None


if __name__ == "__main__":
    # テスト
    from config import RiskConfig
    from api_client import CurrencyPair, OrderSide, Position, AccountInfo
    
    config = RiskConfig()
    rm = RiskManager(config)
    
    # テスト用口座情報
    account = AccountInfo(
        account_id="TEST-001",
        balance=Decimal("1000000"),
        equity=Decimal("1000000"),
        margin_used=Decimal("0"),
        margin_available=Decimal("1000000"),
        unrealized_pnl=Decimal("0")
    )
    
    print("=" * 60)
    print("リスク管理テスト")
    print("=" * 60)
    
    # ポジションサイズ計算
    entry = Decimal("150.000")
    stop = Decimal("149.700")  # 30pips
    tp = Decimal("150.600")    # 60pips
    
    result = rm.calculate_position_size(account, entry, stop, tp)
    print(f"\n【ポジションサイズ計算】")
    print(f"  エントリー: {entry}")
    print(f"  損切り: {stop} ({result.stop_loss_pips:.1f}pips)")
    print(f"  利確: {tp}")
    print(f"  推奨サイズ: {result.recommended_size:,}通貨")
    print(f"  リスク金額: {result.risk_amount:,.0f}円")
    print(f"  リスクリワード比: {result.risk_reward_ratio:.2f}")
    print(f"  使用レバレッジ: {result.leverage_used:.1f}倍")
    
    # リスク評価
    positions = [
        Position(
            position_id="POS-001",
            currency_pair=CurrencyPair.USDJPY,
            side=OrderSide.BUY,
            quantity=10000,
            entry_price=Decimal("150.000"),
            current_price=Decimal("150.200"),
            stop_loss=Decimal("149.700")
        )
    ]
    
    assessment = rm.assess_risk(account, positions)
    print(f"\n【リスク評価】")
    print(f"  リスクレベル: {assessment.level.value}")
    print(f"  ドローダウン: {assessment.current_drawdown:.2f}%")
    print(f"  取引可能: {assessment.can_trade}")
    if assessment.warnings:
        print(f"  警告: {', '.join(assessment.warnings)}")
