"""Tests for AES-256-GCM encryption module."""

import base64
import secrets

import pytest

# Generate a valid test encryption key
_TEST_KEY = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    """Set a valid encryption key for all tests."""
    monkeypatch.setattr("backend.shared.config.settings.ENCRYPTION_KEY", _TEST_KEY)
    # Clear the lru_cache so each test picks up the new key
    from backend.shared.encryption import _get_encryption_key

    _get_encryption_key.cache_clear()


class TestEncryptDecrypt:
    """Test encrypt/decrypt round-trip."""

    def test_round_trip(self):
        from backend.shared.encryption import decrypt_api_key, encrypt_api_key

        plaintext = "sk-proj-abc123xyz456"
        ciphertext, nonce = encrypt_api_key(plaintext)
        result = decrypt_api_key(ciphertext, nonce)
        assert result == plaintext

    def test_different_keys_produce_different_ciphertext(self):
        from backend.shared.encryption import encrypt_api_key

        plaintext = "sk-proj-abc123xyz456"
        ct1, n1 = encrypt_api_key(plaintext)
        ct2, n2 = encrypt_api_key(plaintext)
        # Nonces should differ (random)
        assert n1 != n2
        # Ciphertexts should differ due to different nonces
        assert ct1 != ct2

    def test_nonce_is_12_bytes(self):
        from backend.shared.encryption import encrypt_api_key

        _, nonce = encrypt_api_key("test-key")
        assert len(nonce) == 12

    def test_decrypt_with_wrong_key_fails(self, monkeypatch):
        from backend.shared.encryption import _get_encryption_key, encrypt_api_key

        plaintext = "sk-proj-secret"
        ciphertext, nonce = encrypt_api_key(plaintext)

        # Change to a different key
        new_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        monkeypatch.setattr("backend.shared.config.settings.ENCRYPTION_KEY", new_key)
        _get_encryption_key.cache_clear()

        from backend.shared.encryption import decrypt_api_key

        with pytest.raises(RuntimeError, match="Failed to decrypt"):
            decrypt_api_key(ciphertext, nonce)

    def test_decrypt_with_tampered_ciphertext_fails(self):
        from backend.shared.encryption import decrypt_api_key, encrypt_api_key

        ciphertext, nonce = encrypt_api_key("sk-proj-abc")
        tampered = bytes([b ^ 0xFF for b in ciphertext])
        with pytest.raises(RuntimeError, match="Failed to decrypt"):
            decrypt_api_key(tampered, nonce)


class TestGetEncryptionKey:
    """Test _get_encryption_key validation."""

    def test_missing_key_raises(self, monkeypatch):
        from backend.shared.encryption import _get_encryption_key

        monkeypatch.setattr("backend.shared.config.settings.ENCRYPTION_KEY", "")
        _get_encryption_key.cache_clear()
        with pytest.raises(RuntimeError, match="ENCRYPTION_KEY is not configured"):
            _get_encryption_key()

    def test_too_long_key_raises(self, monkeypatch):
        from backend.shared.encryption import _get_encryption_key

        long_key = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode()
        monkeypatch.setattr("backend.shared.config.settings.ENCRYPTION_KEY", long_key)
        _get_encryption_key.cache_clear()
        with pytest.raises(RuntimeError, match="must be 32 bytes"):
            _get_encryption_key()

    def test_wrong_length_raises(self, monkeypatch):
        from backend.shared.encryption import _get_encryption_key

        short_key = base64.urlsafe_b64encode(b"tooshort").decode()
        monkeypatch.setattr("backend.shared.config.settings.ENCRYPTION_KEY", short_key)
        _get_encryption_key.cache_clear()
        with pytest.raises(RuntimeError, match="must be 32 bytes"):
            _get_encryption_key()

    def test_valid_key_returns_bytes(self):
        from backend.shared.encryption import _get_encryption_key

        key = _get_encryption_key()
        assert isinstance(key, bytes)
        assert len(key) == 32
