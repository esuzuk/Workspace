from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import requests

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RestEndpoints:
    base_url: str
    order_path: str
    positions_path: str


class SbiFxRestClient:
    """
    REST wrapper (最小雛形).
    実際のSBI公式APIのパス/ボディ/フィールド名に合わせて調整してください。
    """

    def __init__(
        self,
        *,
        endpoints: RestEndpoints,
        access_token: str,
        token_type: str = "Bearer",
        timeout_seconds: int = 15,
    ) -> None:
        self._endpoints = endpoints
        self._timeout = timeout_seconds
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"{token_type} {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _url(self, path: str) -> str:
        return self._endpoints.base_url.rstrip("/") + "/" + path.lstrip("/")

    def get_positions(self) -> dict[str, Any]:
        url = self._url(self._endpoints.positions_path)
        r = self._session.get(url, timeout=self._timeout)
        r.raise_for_status()
        return r.json()

    def place_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: int,
        client_order_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        side: "BUY" or "SELL"
        """
        url = self._url(self._endpoints.order_path)
        body: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "type": "MARKET",
        }
        if client_order_id:
            body["clientOrderId"] = client_order_id

        log.info("Sending order: %s", body)
        r = self._session.post(url, json=body, timeout=self._timeout)
        r.raise_for_status()
        return r.json()

