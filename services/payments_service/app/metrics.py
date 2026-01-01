from __future__ import annotations

from prometheus_client import Counter, Histogram

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

payment_intent_wallet_debit_failures_total = Counter(
    "payment_intent_wallet_debit_failures_total",
    "Failed downstream wallet debits while confirming a payment intent",
    ["reason"],
)

wallet_debit_latency_seconds = Histogram(
    "payment_intent_wallet_debit_latency_seconds",
    "Latency of downstream wallet debit calls during confirmation",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
