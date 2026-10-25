"""The UDP discovery packet: 20 bytes, not encrypted.

    version (1) | kind (1) | broadcast_id (8) | node_id (8) | tcp_port (2)

request: "Is anyone from this room here?"
reply:   "Yes, connect to me on this TCP port"
"""
import struct
from dataclasses import dataclass

VERSION = 1
REQUEST = 1
REPLY = 2

_FORMAT = struct.Struct("!BB8s8sH")      # "!" = network byte order


@dataclass
class Packet:
    kind: int
    broadcast_id: bytes      # which room (comes from keys.py)
    node_id: bytes           # who sent it (random, new every run)
    tcp_port: int            # where to connect to the sender


def build(kind: int, broadcast_id: bytes, node_id: bytes, tcp_port: int) -> bytes:
    if len(broadcast_id) != 8 or len(node_id) != 8:
        raise ValueError("broadcast_id and node_id must be exactly 8 bytes")
    return _FORMAT.pack(VERSION, kind, broadcast_id, node_id, tcp_port)


def parse(data: bytes) -> Packet | None:
    """Returns None for anything that is not a valid packet."""
    if len(data) != _FORMAT.size:
        return None
    version, kind, broadcast_id, node_id, tcp_port = _FORMAT.unpack(data)
    if version != VERSION or kind not in (REQUEST, REPLY):
        return None
    return Packet(kind, broadcast_id, node_id, tcp_port)