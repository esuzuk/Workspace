from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Optional

from .rest import SbiFxRestClient
from .strategy import Signal

log = logging.getLogger(__name__)


@dataclass
class PositionState:
    net_position: int = 0  # +long, -short


class OrderExecutor:
    """
    paper/live を抽象化して「シグナル→注文」を実行する。
    """

    def __init__(
        self,
        *,
        mode: str,
        symbol: str,
        order_qty: int,
        max_net_position: int,
        rest_client: Optional[SbiFxRestClient] = None,
    ) -> None:
        self._mode = mode
        self._symbol = symbol
        self._qty = order_qty
        self._max = max_net_position
        self._rest = rest_client
        self.position = PositionState()

    def _can_increase(self, delta: int) -> bool:
        nxt = self.position.net_position + delta
        return abs(nxt) <= self._max

    def on_signal(self, signal: Signal) -> None:
        if signal.action not in {"BUY", "SELL"}:
            return

        delta = self._qty if signal.action == "BUY" else -self._qty
        if not self._can_increase(delta):
            log.warning(
                "Risk guard: blocked order. net=%s delta=%s max=%s",
                self.position.net_position,
                delta,
                self._max,
            )
            return

        client_order_id = str(uuid.uuid4())
        if self._mode == "paper":
            self.position.net_position += delta
            log.info(
                "[PAPER] %s %s qty=%s net=%s reason=%s",
                signal.action,
                self._symbol,
                self._qty,
                self.position.net_position,
                signal.reason,
            )
            return

        if self._mode == "live":
            if self._rest is None:
                raise RuntimeError("live mode requires rest_client")
            resp = self._rest.place_market_order(
                symbol=self._symbol,
                side=signal.action,
                quantity=self._qty,
                client_order_id=client_order_id,
            )
            # NOTE: 約定/建玉反映は本来、約定通知や建玉照会に同期させるべき。
            self.position.net_position += delta
            log.info(
                "[LIVE] order_sent id=%s action=%s symbol=%s qty=%s net=%s resp=%s",
                client_order_id,
                signal.action,
                self._symbol,
                self._qty,
                self.position.net_position,
                resp,
            )
            return

        raise ValueError(f"Unknown mode: {self._mode}")

