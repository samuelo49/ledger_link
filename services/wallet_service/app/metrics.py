from prometheus_client import Counter

wallet_credit_total = Counter("wallet_credit_total", "Number of successful wallet credit operations", ["currency"])
wallet_debit_total = Counter("wallet_debit_total", "Number of successful wallet debit operations", ["currency"])
wallet_idempotency_replay_total = Counter(
    "wallet_idempotency_replay_total", "Number of idempotent replays detected for wallet operations", ["currency", "type"]
)
wallet_insufficient_funds_total = Counter(
    "wallet_insufficient_funds_total", "Number of debit attempts failed due to insufficient funds", ["currency"]
)
