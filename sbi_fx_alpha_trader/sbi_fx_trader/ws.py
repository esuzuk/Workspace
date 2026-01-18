from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Optional

import websockets

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class WsConfig:
    url: str
    subscribe_message: dict[str, Any]


class SbiFxWebSocketClient:
    """
    WebSocket wrapper (最小雛形).
    実際のSBI公式APIの購読形式/メッセージ形式に合わせて調整してください。
    """

    def __init__(self, *, config: WsConfig) -> None:
        self._config = config

    async def messages(self, *, stop_event: asyncio.Event) -> AsyncIterator[dict[str, Any]]:
        backoff = 1.0
        while not stop_event.is_set():
            try:
                async with websockets.connect(self._config.url, ping_interval=20, ping_timeout=20) as ws:
                    backoff = 1.0
                    sub = json.dumps(self._config.subscribe_message, ensure_ascii=False)
                    await ws.send(sub)
                    log.info("WS subscribed: %s", sub)

                    while not stop_event.is_set():
                        raw = await asyncio.wait_for(ws.recv(), timeout=60)
                        if raw is None:
                            break
                        if isinstance(raw, (bytes, bytearray)):
                            raw = raw.decode("utf-8", errors="replace")
                        try:
                            msg = json.loads(raw)
                        except Exception:
                            msg = {"raw": raw}
                        yield msg
            except asyncio.TimeoutError:
                log.warning("WS timeout; reconnecting...")
            except Exception as e:  # noqa: BLE001
                log.warning("WS error; reconnecting... (%s)", e)

            # reconnect backoff
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)


def extract_bid_ask(message: dict[str, Any]) -> Optional[tuple[float, float]]:
    """
    受信メッセージからBid/Askを抜き出すためのヘルパ（汎用）。
    実際のSBI仕様に合わせて調整してください。
    """
    # Common shapes:
    # {"bid": 150.123, "ask": 150.125}
    # {"data":{"bid":..,"ask":..}}
    candidates = []
    if "bid" in message and "ask" in message:
        candidates.append(message)
    if isinstance(message.get("data"), dict) and "bid" in message["data"] and "ask" in message["data"]:
        candidates.append(message["data"])

    for c in candidates:
        try:
            return float(c["bid"]), float(c["ask"])
        except Exception:
            continue
    return None

