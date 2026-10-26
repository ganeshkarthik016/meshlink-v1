"""Shouts "is anyone from my room here?" and collects the answers."""
import socket
import time
try:
    import fcntl                 # Linux only
except ImportError:              # Windows
    fcntl = None
import struct

from p2pchat import config
from p2pchat.discovery import protocol

def broadcast_targets() -> list[str]:
    """Every address we should shout to: the usual ones, plus the broadcast
    address of each network card (so a laptop with Ethernet AND a hotspot
    reaches both networks)."""
    targets = list(config.BROADCAST_ADDRESSES)
    if fcntl is None:
        return targets           # no per-network-card addresses on this system
    for _, name in socket.if_nameindex():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # 0x8919 = SIOCGIFBRDADDR: "what is this card's broadcast address?"
            reply = fcntl.ioctl(s.fileno(), 0x8919, struct.pack("256s", name.encode()[:15]))
            address = socket.inet_ntoa(reply[20:24])
            if address not in targets:
                targets.append(address)
        except OSError:                  # this card has no broadcast address (e.g. loopback)
            pass
        finally:
            s.close()
    return targets

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
            for address in broadcast_targets():
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