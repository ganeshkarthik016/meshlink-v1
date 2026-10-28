import socket

import pytest

from p2pchat import config
from p2pchat.discovery import broadcaster
from p2pchat.discovery.broadcaster import find_peers
from p2pchat.discovery.listener import Listener

UDP = 50991                  # not the real port, so tests never clash with a running app
ROOM = b"ROOM-AAA"           # IDs must be exactly 8 bytes
N1 = b"node-001"
N2 = b"node-002"
JOINER = b"joiner00"


@pytest.fixture
def start_listener():
    listeners = []

    def start(node_id, tcp_port, room=ROOM, can_reply=lambda: True):
        listener = Listener(room, node_id, tcp_port, can_reply, UDP)
        listener.start()
        listeners.append(listener)
        return listener

    yield start
    for listener in listeners:
        listener.stop()


def test_listener_answers_same_room(start_listener):
    start_listener(N1, 5555)
    found = find_peers(ROOM, N2, UDP, wait=1)
    # Reachable on 127.0.0.1 and on our network IP: either is fine, so check the port.
    # Asked twice, answered several times, counted once.
    assert [port for _, port in found] == [5555]


def test_other_room_gets_no_answer(start_listener):
    start_listener(N1, 5555, room=b"ROOM-BBB")
    assert find_peers(ROOM, N2, UDP, wait=0.4) == []


def test_own_broadcast_is_ignored(start_listener):
    start_listener(N1, 5555)
    assert find_peers(ROOM, N1, UDP, wait=0.4) == []   # same node id


def test_full_node_stays_quiet(start_listener):
    start_listener(N1, 5555, can_reply=lambda: False)
    assert find_peers(ROOM, N2, UDP, wait=0.4) == []


def test_nobody_around():
    assert find_peers(ROOM, N2, UDP, wait=0.3) == []


def test_limit_stops_early(start_listener):
    for i in range(3):
        start_listener(b"node-00%d" % i, 6000 + i)
    assert len(find_peers(ROOM, JOINER, UDP, wait=1, limit=2)) == 2
    ports = {port for _, port in find_peers(ROOM, JOINER, UDP, wait=1, limit=10)}
    assert ports == {6000, 6001, 6002}


def test_garbage_does_not_break_the_listener(start_listener):
    start_listener(N1, 5555)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(b"junk", ("127.0.0.1", UDP))
    s.sendto(b"x" * 20, ("127.0.0.1", UDP))
    s.close()
    found = find_peers(ROOM, N2, UDP, wait=1)
    assert [port for _, port in found] == [5555]


def test_broadcast_targets_keep_the_defaults_and_are_valid_ips():
    targets = broadcaster.broadcast_targets()
    assert set(config.BROADCAST_ADDRESSES) <= set(targets)
    for address in targets:
        socket.inet_aton(address)        # raises if it is not an IPv4 address


def test_broadcast_targets_include_interface_broadcasts_on_windows(monkeypatch):
    class FakeNetIfaces:
        AF_INET = 2

        @staticmethod
        def interfaces():
            return ["Ethernet", "Wi-Fi"]

        @staticmethod
        def ifaddresses(iface):
            if iface == "Ethernet":
                return {FakeNetIfaces.AF_INET: [{"broadcast": "192.168.1.255"}]}
            if iface == "Wi-Fi":
                return {FakeNetIfaces.AF_INET: [{"broadcast": "10.0.0.255"}]}
            return {}

    monkeypatch.setattr(broadcaster, "fcntl", None)
    monkeypatch.setattr(broadcaster, "netifaces", FakeNetIfaces)

    targets = broadcaster.broadcast_targets()

    assert "192.168.1.255" in targets
    assert "10.0.0.255" in targets


def test_broadcast_targets_include_interface_broadcasts_on_linux(monkeypatch):
    def fake_if_nameindex():
        return [(1, "eth0"), (2, "wlan0")]

    def fake_ioctl(fd, request, data):
        if data.startswith(b"eth0"):
            return b"\x00" * 20 + b"\xc0\xa8\x01\xff"
        return b"\x00" * 20 + b"\x0a\x00\x00\xff"

    monkeypatch.setattr(socket, "if_nameindex", fake_if_nameindex)
    monkeypatch.setattr(broadcaster, "fcntl", type("FakeFcntl", (), {"ioctl": staticmethod(fake_ioctl)}))
    monkeypatch.setattr(broadcaster, "netifaces", None)

    targets = broadcaster.broadcast_targets()

    assert "192.168.1.255" in targets
    assert "10.0.0.255" in targets
