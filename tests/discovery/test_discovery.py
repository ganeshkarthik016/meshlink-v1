import socket

import pytest

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
    assert found == [("127.0.0.1", 5555)]        # asked twice, answered twice, counted once


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
    assert find_peers(ROOM, N2, UDP, wait=1) == [("127.0.0.1", 5555)]