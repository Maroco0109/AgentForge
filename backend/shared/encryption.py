"""AES-256-GCM encryption for API keys at rest."""

import base64
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.shared.config import settings

NONCE_SIZE = 12  # 96 bits, recommended for GCM


@lru_cache(maxsize=1)
def _get_encryption_key() -> bytes:
    """Get and validate the encryption key from settings."""
    raw = settings.ENCRYPTION_KEY
    if not raw:
        raise RuntimeError(
            "ENCRYPTION_KEY is not configured. Generate one with: "
            'python -c "import secrets, base64; '
            'print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"'
        )
    try:
        key = base64.urlsafe_b64decode(raw)
    except Exception as exc:
        raise RuntimeError("ENCRYPTION_KEY is not valid base64") from exc
    if len(key) != 32:
        raise RuntimeError(
            f"ENCRYPTION_KEY must be 32 bytes (got {len(key)}). "
            'Generate with: python -c "import secrets, base64; '
            'print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"'
        )
    return key


def encrypt_api_key(plaintext: str) -> tuple[bytes, bytes]:
    """Encrypt an API key using AES-256-GCM.

    Returns:
        (ciphertext, nonce) tuple.
    """
    key = _get_encryption_key()
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return ciphertext, nonce


def decrypt_api_key(ciphertext: bytes, nonce: bytes) -> str:
    """Decrypt an API key using AES-256-GCM.

    Raises:
        RuntimeError: If decryption fails (wrong key, tampered data).
    """
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as exc:
        raise RuntimeError(
            "Failed to decrypt API key. The encryption key may have changed."
        ) from exc
    return plaintext.decode("utf-8")
