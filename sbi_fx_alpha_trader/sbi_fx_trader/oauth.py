from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class OAuthToken:
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None


def fetch_access_token(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    grant_type: str = "client_credentials",
    scope: str = "",
    timeout_seconds: int = 15,
) -> OAuthToken:
    """
    OAuth2 token fetch (generic).
    SBI公式APIの実際のパラメータ/ヘッダ要件に合わせて調整してください。
    """
    data = {"grant_type": grant_type}
    if scope:
        data["scope"] = scope

    # Basic auth is common for client_credentials
    log.info("Fetching access token...")
    r = requests.post(
        token_url,
        data=data,
        auth=(client_id, client_secret),
        timeout=timeout_seconds,
    )
    r.raise_for_status()
    payload = r.json()

    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError(f"Token response missing access_token: {payload}")

    return OAuthToken(
        access_token=access_token,
        token_type=payload.get("token_type", "Bearer"),
        expires_in=payload.get("expires_in"),
    )

