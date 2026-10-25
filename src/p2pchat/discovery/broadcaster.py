"""Shouts "is anyone from my room here?" and collects the answers."""
import socket
import time

from p2pchat import config
from p2pchat.discovery import protocol


def find_peers(broadcast_id: bytes, node_id: bytes,
               udp_port: int = config.UDP_PORT,
               wait: float = config.DISCOVERY_WAIT,
               limit: int = config.MAX_OUT) -> list[tuple[str, int]]:
    """Returns [(ip, tcp_port), ...] for the first `limit` nodes that answer.
    Stops early once it has enough, otherwise waits `wait` seconds."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", 0))                       # any free port: the answers come back here
    try:
        request = protocol.build(protocol.REQUEST, broadcast_id, node_id, 0)
        for _ in range(2):                   # UDP can lose packets, so ask twice
            for address in config.BROADCAST_ADDRESSES:
                try:
                    sock.sendto(request, (address, udp_port))
                except OSError:              # e.g. no network: just skip this address
                    pass

        found = {}                           # node_id -> (ip, tcp_port); keeps arrival order
        end = time.time() + wait
        while len(found) < limit:
            remaining = end - time.time()
            if remaining <= 0:
                break
            sock.settimeout(remaining)
            try:
                data, addr = sock.recvfrom(64)
            except OSError:                  # timeout
                break
            packet = protocol.parse(data)
            if (packet is not None
                    and packet.kind == protocol.REPLY
                    and packet.broadcast_id == broadcast_id
                    and packet.node_id != node_id):
                found[packet.node_id] = (addr[0], packet.tcp_port)   # same node twice counts once
        return list(found.values())
    finally:
        sock.close()