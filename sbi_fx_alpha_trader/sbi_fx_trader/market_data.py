from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class Tick:
    ts: datetime  # UTC
    bid: float
    ask: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0


@dataclass(frozen=True)
class Candle:
    start_ts: datetime  # UTC bucket start
    end_ts: datetime  # UTC bucket end (exclusive)
    open: float
    high: float
    low: float
    close: float


class CandleBuilder:
    def __init__(self, *, timeframe_seconds: int) -> None:
        if timeframe_seconds <= 0:
            raise ValueError("timeframe_seconds must be > 0")
        self._tf = timeframe_seconds
        self._current: Optional[Candle] = None

    def update(self, tick: Tick) -> Optional[Candle]:
        """
        Returns a completed candle when a new bucket starts; otherwise None.
        """
        ts = tick.ts
        if ts.tzinfo is None:
            raise ValueError("Tick.ts must be timezone-aware")
        epoch = int(ts.timestamp())
        bucket_start_epoch = epoch - (epoch % self._tf)
        bucket_start = datetime.fromtimestamp(bucket_start_epoch, tz=timezone.utc)
        bucket_end = datetime.fromtimestamp(bucket_start_epoch + self._tf, tz=timezone.utc)

        price = tick.mid
        if self._current is None:
            self._current = Candle(
                start_ts=bucket_start,
                end_ts=bucket_end,
                open=price,
                high=price,
                low=price,
                close=price,
            )
            return None

        # Same bucket
        if bucket_start == self._current.start_ts:
            c = self._current
            self._current = Candle(
                start_ts=c.start_ts,
                end_ts=c.end_ts,
                open=c.open,
                high=max(c.high, price),
                low=min(c.low, price),
                close=price,
            )
            return None

        # New bucket => finalize previous, start new
        finished = self._current
        self._current = Candle(
            start_ts=bucket_start,
            end_ts=bucket_end,
            open=price,
            high=price,
            low=price,
            close=price,
        )
        return finished


class PaperTickFeed:
    """
    擬似ティック生成（ランダムウォーク）。
    """

    def __init__(
        self,
        *,
        start_price: float = 150.0,
        spread: float = 0.01,
        step_std: float = 0.02,
        seed: int = 42,
    ) -> None:
        self._rng = random.Random(seed)
        self._mid = start_price
        self._spread = spread
        self._step_std = step_std

    def next_tick(self) -> Tick:
        step = self._rng.gauss(0.0, self._step_std)
        self._mid = max(0.0001, self._mid + step)
        bid = self._mid - self._spread / 2.0
        ask = self._mid + self._spread / 2.0
        return Tick(ts=datetime.now(timezone.utc), bid=bid, ask=ask)

