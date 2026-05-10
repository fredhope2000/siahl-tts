from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import quote_plus


EMPTY_BODY_MD5 = "d41d8cd98f00b204e9800998ecf8427e"


def canonical_query(params: dict[str, str]) -> str:
    return "&".join(
        f"{quote_plus(key)}={quote_plus(value)}"
        for key, value in sorted(params.items(), key=lambda item: item[0])
    )


def build_signed_query(
    endpoint: str,
    api_key: str,
    api_secret: str,
    params: dict[str, str | int | None],
    timestamp: int | None = None,
) -> str:
    signed_params: dict[str, str] = {
        "auth_key": api_key,
        "auth_timestamp": str(timestamp or int(time.time())),
        "body_md5": EMPTY_BODY_MD5,
    }

    for key, value in params.items():
        if value in (None, "", -1):
            continue
        signed_params[key] = str(value)

    query = canonical_query(signed_params)
    string_to_sign = f"GET /{endpoint} {query}"
    signature = hmac.new(
        api_secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{query}&auth_signature={signature}"
