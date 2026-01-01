"""Prometheus metrics for Identity service flows."""

from __future__ import annotations

from prometheus_client import Counter

registration_total = Counter(
    "identity_registration_total",
    "Number of registration attempts grouped by outcome",
    ["outcome"],
)

login_attempt_total = Counter(
    "identity_login_attempt_total",
    "Number of login attempts grouped by outcome",
    ["outcome"],
)

token_refresh_total = Counter(
    "identity_token_refresh_total",
    "Refresh token exchanges grouped by outcome",
    ["outcome"],
)

verification_request_total = Counter(
    "identity_verification_request_total",
    "Verification token requests grouped by outcome",
    ["outcome"],
)

verification_confirm_total = Counter(
    "identity_verification_confirm_total",
    "Verification confirmations grouped by outcome",
    ["outcome"],
)

password_reset_request_total = Counter(
    "identity_password_reset_request_total",
    "Password reset token requests grouped by outcome",
    ["outcome"],
)

password_reset_confirm_total = Counter(
    "identity_password_reset_confirm_total",
    "Password reset confirmations grouped by outcome",
    ["outcome"],
)
