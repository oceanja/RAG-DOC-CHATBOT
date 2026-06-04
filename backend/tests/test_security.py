import pytest

from app.config import settings
from app.security import (
    create_admin_token,
    hash_ip,
    verify_admin_token,
    verify_password,
)


@pytest.fixture(autouse=True)
def fixed_admin_password(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "fixed-test-password")
    monkeypatch.setattr(settings, "ip_hash_salt", "fixed-test-salt")


def test_verify_password_constant_time_compare():
    assert verify_password("fixed-test-password") is True
    assert verify_password("wrong") is False
    assert verify_password("") is False


def test_token_roundtrip_valid_for_7_days():
    token = create_admin_token(ttl_days=7)
    assert verify_admin_token(token) is True


def test_token_invalid_when_tampered():
    token = create_admin_token(ttl_days=7)
    # flip a character in the signature segment
    payload, sig = token.split(".", 1)
    tampered = f"{payload}.{sig[:-2]}AA"
    assert verify_admin_token(tampered) is False


def test_token_rejected_when_expired():
    # ttl_days=-1 produces an already-expired token
    expired = create_admin_token(ttl_days=-1)
    assert verify_admin_token(expired) is False


def test_token_signing_key_depends_on_admin_password(monkeypatch):
    token = create_admin_token(ttl_days=7)
    monkeypatch.setattr(settings, "admin_password", "different-password")
    assert verify_admin_token(token) is False  # rotating password invalidates tokens


def test_hash_ip_is_deterministic_and_salted():
    h1 = hash_ip("1.2.3.4")
    h2 = hash_ip("1.2.3.4")
    h3 = hash_ip("1.2.3.5")
    assert h1 == h2
    assert h1 != h3
    assert hash_ip(None) is None
    assert hash_ip("") is None
    # never store the raw IP — hash must not contain it
    assert "1.2.3.4" not in h1
    # SHA256 hex
    assert len(h1) == 64
    int(h1, 16)  # parses as hex


def test_hash_ip_changes_with_salt(monkeypatch):
    h_before = hash_ip("1.2.3.4")
    monkeypatch.setattr(settings, "ip_hash_salt", "different-salt")
    assert hash_ip("1.2.3.4") != h_before
