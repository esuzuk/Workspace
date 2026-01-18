from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from .market_data import Candle


@dataclass(frozen=True)
class Signal:
    action: str  # "BUY" | "SELL" | "HOLD"
    reason: str


class SmaCrossoverStrategy:
    """
    短期SMAと長期SMAのクロスで売買する最小戦略。
    - fast > slow にクロスしたら BUY
    - fast < slow にクロスしたら SELL
    """

    def __init__(self, *, fast: int, slow: int) -> None:
        if fast <= 0 or slow <= 0:
            raise ValueError("fast/slow must be > 0")
        if fast >= slow:
            raise ValueError("fast must be < slow")
        self._fast = fast
        self._slow = slow
        self._closes: Deque[float] = deque(maxlen=slow)
        self._last_state: Optional[str] = None  # "fast_above" | "fast_below"

    def on_candle(self, candle: Candle) -> Signal:
        self._closes.append(candle.close)
        if len(self._closes) < self._slow:
            return Signal(action="HOLD", reason="warming_up")

        closes = list(self._closes)
        fast_sma = sum(closes[-self._fast :]) / self._fast
        slow_sma = sum(closes) / self._slow

        state = "fast_above" if fast_sma > slow_sma else "fast_below" if fast_sma < slow_sma else "equal"

        if self._last_state is None:
            self._last_state = state
            return Signal(action="HOLD", reason=f"init_state:{state}")

        if state == self._last_state or state == "equal":
            self._last_state = state
            return Signal(action="HOLD", reason=f"no_cross:{state}")

        # Cross detected
        if self._last_state == "fast_below" and state == "fast_above":
            self._last_state = state
            return Signal(action="BUY", reason=f"bull_cross fast={fast_sma:.5f} slow={slow_sma:.5f}")
        if self._last_state == "fast_above" and state == "fast_below":
            self._last_state = state
            return Signal(action="SELL", reason=f"bear_cross fast={fast_sma:.5f} slow={slow_sma:.5f}")

        prev = self._last_state
        self._last_state = state
        return Signal(action="HOLD", reason=f"state_change:{prev}->{state}")

