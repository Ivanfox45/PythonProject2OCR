"""Helpers for retrieving a Yandex Cloud IAM token.

The token is requested from the public IAM API using an OAuth token.  The
OAuth token can be supplied explicitly or read from the
``YANDEX_OAUTH_TOKEN`` environment variable.  The :func:`get_iam_token`
function returns the IAM token string or an empty string on failure so the
caller can decide how to handle missing credentials.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import requests

IAM_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"


def get_iam_token(oauth_token: Optional[str] = None, timeout: int = 30) -> str:
    """Fetch a short‑lived IAM token from Yandex Cloud.

    Parameters
    ----------
    oauth_token:
        OAuth token used to authenticate the request.  If omitted, the value
        is read from the ``YANDEX_OAUTH_TOKEN`` environment variable.
    timeout:
        Timeout for the HTTP request in seconds.

    Returns
    -------
    str
        The IAM token if the request succeeds, otherwise an empty string.
    """

    token = oauth_token or os.getenv("YANDEX_OAUTH_TOKEN", "").strip()
    if not token:
        return ""

    headers = {"Content-Type": "application/json"}
    data = {"yandexPassportOauthToken": token}

    try:
        resp = requests.post(IAM_URL, headers=headers, json=data, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("iamToken", "")
    except requests.RequestException:
        return ""


if __name__ == "__main__":
    iam_token = get_iam_token()
    if iam_token:
        print(iam_token)
    else:
        print("Failed to obtain IAM token", file=sys.stderr)
        sys.exit(1)

