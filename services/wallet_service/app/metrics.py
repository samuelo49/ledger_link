from prometheus_client import Counter, Histogram

wallet_credit_total = Counter("wallet_credit_total", "Number of successful wallet credit operations", ["currency"])
wallet_debit_total = Counter("wallet_debit_total", "Number of successful wallet debit operations", ["currency"])
wallet_idempotency_replay_total = Counter(
    "wallet_idempotency_replay_total", "Number of idempotent replays detected for wallet operations", ["currency", "type"]
)
wallet_insufficient_funds_total = Counter(
    "wallet_insufficient_funds_total", "Number of debit attempts failed due to insufficient funds", ["currency"]
)
wallet_transfer_created_total = Counter(
    "wallet_transfer_created_total", "Number of transfer objects created", ["currency"]
)
wallet_transfer_completed_total = Counter(
    "wallet_transfer_completed_total", "Number of transfers completed successfully", ["currency"]
)
wallet_transfer_failed_total = Counter(
    "wallet_transfer_failed_total", "Number of transfers that failed", ["currency", "reason"]
)
wallet_transfer_idempotent_total = Counter(
    "wallet_transfer_idempotent_total", "Number of transfer requests treated as idempotent replays", ["currency"]
)
wallet_transfer_latency_seconds = Histogram(
    "wallet_transfer_latency_seconds",
    "Latency of wallet transfer processing",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
