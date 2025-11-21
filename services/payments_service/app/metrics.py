from __future__ import annotations

from prometheus_client import Counter

payment_intent_created_total = Counter(
    "payment_intent_created_total",
    "Total number of payment intents created",
    ["currency"],
)

payment_intent_confirmed_total = Counter(
    "payment_intent_confirmed_total",
    "Total number of payment intents confirmed",
    ["currency"],
)
