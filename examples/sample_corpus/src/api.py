"""HTTP API.

The important part for demo is how retry is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from retry_policy import DEFAULT_RETRY_POLICY, with_retries

@dataclass
class PaymentClient:
    def charge(self, amount_cents: int, token: str) -> dict[str, Any]:
        # In real life, this would call an external provider.
        # For demo, we simulate transient failure.
        raise RuntimeError("transient upstream 503")

def charge_with_retry(amount_cents: int, token: str) -> dict[str, Any]:
    client = PaymentClient()
    return with_retries(lambda: client.charge(amount_cents, token), DEFAULT_RETRY_POLICY)

