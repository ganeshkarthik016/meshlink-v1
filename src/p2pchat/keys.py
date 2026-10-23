"""Turn room ID + password into the two secrets the app needs."""
import hashlib


def derive_keys(room_id: str, password: str) -> tuple[bytes, bytes]:
    """Return (broadcast_id, message_key).

    broadcast_id (8 bytes): goes in the UDP broadcast, so peers know we're in the same room.
    message_key (32 bytes): encrypts messages, never leaves the device.
    """
    output = hashlib.scrypt(
        password.encode(),
        salt=("p2pchat:" + room_id).encode(),
        n=2**14, r=8, p=1,
        dklen=40,
    )
    return output[:8], output[8:]