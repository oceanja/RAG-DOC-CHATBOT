"""Admin token signing/verification.

A token is `b64(expiry_ts).b64(hmac_sha256(expiry_ts))`, signed with a key
derived from the admin password. No JWT dependency. Changing the admin
password invalidates all existing tokens (desirable).
"""

import base64
import hashlib
import hmac
import time

from app.config import settings


def _signing_key() -> bytes:
    return hashlib.sha256(settings.admin_password.encode()).digest()


def hash_ip(ip: str | None) -> str | None:
    """SHA256(salt + ip) — never store raw visitor IPs."""
    if not ip:
        return None
    return hashlib.sha256(f"{settings.ip_hash_salt}:{ip}".encode()).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text.encode())


def verify_password(candidate: str) -> bool:
    return hmac.compare_digest(candidate, settings.admin_password)


def create_admin_token(ttl_days: int | None = None) -> str:
    ttl_days = ttl_days if ttl_days is not None else settings.admin_token_ttl_days
    expiry = int(time.time()) + ttl_days * 86400
    payload = str(expiry).encode()
    sig = hmac.new(_signing_key(), payload, hashlib.sha256).digest()
    return f"{_b64(payload)}.{_b64(sig)}"


def verify_admin_token(token: str) -> bool:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        payload = _unb64(payload_b64)
        sig = _unb64(sig_b64)
    except Exception:
        return False

    expected = hmac.new(_signing_key(), payload, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        return time.time() < int(payload.decode())
    except ValueError:
        return False
