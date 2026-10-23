"""Encrypt and decrypt with the message key (ChaCha20-Poly1305).
Poly1305 also detects tampering, and a wrong key fails the same way."""
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

NONCE_SIZE = 12   # random, new for every message, sent in front of the ciphertext
TAG_SIZE = 16     # added by Poly1305


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    nonce = os.urandom(NONCE_SIZE)
    return nonce + ChaCha20Poly1305(key).encrypt(nonce, plaintext, None)


def decrypt(key: bytes, data: bytes) -> bytes:
    """Raises ValueError if the key is wrong or the data was changed."""
    if len(data) < NONCE_SIZE + TAG_SIZE:
        raise ValueError("data too short")
    nonce, ciphertext = data[:NONCE_SIZE], data[NONCE_SIZE:]
    try:
        return ChaCha20Poly1305(key).decrypt(nonce, ciphertext, None)
    except InvalidTag as e:
        raise ValueError("wrong key or data was changed") from e