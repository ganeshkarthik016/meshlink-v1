import os

import pytest

from p2pchat.comms.crypto import encrypt, decrypt


def test_round_trip():
    key = os.urandom(32)
    assert decrypt(key, encrypt(key, b"hello")) == b"hello"


def test_wrong_key_fails():
    data = encrypt(os.urandom(32), b"hello")
    with pytest.raises(ValueError):
        decrypt(os.urandom(32), data)


def test_tampered_data_fails():
    key = os.urandom(32)
    data = bytearray(encrypt(key, b"hello"))
    data[-1] ^= 1                       # flip one bit
    with pytest.raises(ValueError):
        decrypt(key, bytes(data))


def test_same_message_encrypts_differently():
    key = os.urandom(32)
    assert encrypt(key, b"hello") != encrypt(key, b"hello")


def test_too_short_fails():
    with pytest.raises(ValueError):
        decrypt(os.urandom(32), b"abc")