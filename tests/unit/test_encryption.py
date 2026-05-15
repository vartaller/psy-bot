"""
Tests for config.py — Fernet encryption helpers.

These catch:
- Roundtrip break (encrypt → decrypt yields different text)
- Decrypt with wrong user_id silently returning plaintext
- safe_decrypt crashing instead of returning the fallback
"""
import pytest

import config


def test_encrypt_decrypt_roundtrip_ascii():
    plain = "hello world"
    cipher = config.encrypt(42, plain)
    assert cipher != plain
    assert config.decrypt(42, cipher) == plain


def test_encrypt_decrypt_roundtrip_cyrillic():
    plain = "Привіт, як справи?"
    cipher = config.encrypt(42, plain)
    assert config.decrypt(42, cipher) == plain


def test_different_users_get_different_ciphertext():
    """User-scoped key: same plaintext under different user_ids must differ."""
    a = config.encrypt(1, "secret")
    b = config.encrypt(2, "secret")
    assert a != b


def test_decrypt_with_wrong_user_id_raises():
    cipher = config.encrypt(1, "hello")
    with pytest.raises(Exception):
        config.decrypt(2, cipher)


def test_safe_decrypt_returns_dash_on_garbage():
    assert config.safe_decrypt(1, "not-a-token") == "—"


def test_safe_decrypt_returns_dash_on_wrong_user():
    cipher = config.encrypt(1, "hello")
    assert config.safe_decrypt(99, cipher) == "—"


def test_safe_decrypt_returns_plaintext_on_correct_token():
    cipher = config.encrypt(7, "valid")
    assert config.safe_decrypt(7, cipher) == "valid"
