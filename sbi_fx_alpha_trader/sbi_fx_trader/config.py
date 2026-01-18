from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import time
from typing import Optional


def _env(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    return int(v) if v is not None and v != "" else default


def _env_str(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


@dataclass(frozen=True)
class MaintenanceWindow:
    start: time
    end: time


def parse_maintenance_windows_jst(spec: str) -> list[MaintenanceWindow]:
    """
    spec: comma-separated "HH:MM-HH:MM"
    Example: "05:55-06:10,23:55-00:10"
    """
    spec = (spec or "").strip()
    if not spec:
        return []

    windows: list[MaintenanceWindow] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            a, b = part.split("-", 1)
            sh, sm = a.split(":")
            eh, em = b.split(":")
            windows.append(
                MaintenanceWindow(
                    start=time(int(sh), int(sm)),
                    end=time(int(eh), int(em)),
                )
            )
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Invalid MAINTENANCE_WINDOWS_JST part: {part}") from e
    return windows


@dataclass(frozen=True)
class TraderConfig:
    mode: str
    symbol: str
    order_qty: int
    timeframe_seconds: int
    fast_sma: int
    slow_sma: int
    max_net_position: int

    # OAuth
    client_id: str
    client_secret: str
    token_url: str
    oauth_grant_type: str
    oauth_scope: str

    # REST
    api_base_url: str
    fx_order_path: str
    fx_positions_path: str

    # WS
    ws_url: str
    ws_subscribe_json: dict

    # Ops
    maintenance_windows_jst: list[MaintenanceWindow]
    log_level: str
    log_path: str

    @staticmethod
    def load_from_env() -> "TraderConfig":
        mode = _env_str("TRADER_MODE", "paper").lower()
        if mode not in {"paper", "live"}:
            raise ValueError("TRADER_MODE must be 'paper' or 'live'")

        subscribe_raw = _env_str("SBI_WS_SUBSCRIBE_JSON", '{"type":"subscribe","symbol":"USDJPY"}')
        try:
            ws_subscribe_json = json.loads(subscribe_raw)
            if not isinstance(ws_subscribe_json, dict):
                raise ValueError("SBI_WS_SUBSCRIBE_JSON must be a JSON object")
        except Exception as e:  # noqa: BLE001
            raise ValueError("Invalid SBI_WS_SUBSCRIBE_JSON (must be JSON object)") from e

        return TraderConfig(
            mode=mode,
            symbol=_env_str("SYMBOL", "USDJPY"),
            order_qty=_env_int("ORDER_QTY", 1000),
            timeframe_seconds=_env_int("TIMEFRAME_SECONDS", 60),
            fast_sma=_env_int("FAST_SMA", 10),
            slow_sma=_env_int("SLOW_SMA", 30),
            max_net_position=_env_int("MAX_NET_POSITION", 1000),
            client_id=_env("SBI_CLIENT_ID", "your_client_id"),
            client_secret=_env("SBI_CLIENT_SECRET", "your_client_secret"),
            token_url=_env("SBI_TOKEN_URL", "https://api.example.com/oauth/token"),
            oauth_grant_type=_env_str("SBI_OAUTH_GRANT_TYPE", "client_credentials"),
            oauth_scope=_env_str("SBI_OAUTH_SCOPE", ""),
            api_base_url=_env("SBI_API_BASE_URL", "https://api.example.com"),
            fx_order_path=_env_str("SBI_FX_ORDER_PATH", "/fx/orders"),
            fx_positions_path=_env_str("SBI_FX_POSITIONS_PATH", "/fx/positions"),
            ws_url=_env("SBI_WS_URL", "wss://stream.example.com"),
            ws_subscribe_json=ws_subscribe_json,
            maintenance_windows_jst=parse_maintenance_windows_jst(
                _env_str("MAINTENANCE_WINDOWS_JST", "")
            ),
            log_level=_env_str("LOG_LEVEL", "INFO"),
            log_path=_env_str("LOG_PATH", "./trader.log"),
        )

