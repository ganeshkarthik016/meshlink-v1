import os
import queue
import time

from p2pchat.comms.crypto import encrypt
from p2pchat.comms.forwarder import Forwarder, SeenSet
from p2pchat.comms.message import make_chat
from p2pchat.comms.peers import PeerTable


class FakePeers:
    """Records what would have been sent."""
    def __init__(self):
        self.sent = []

    def send_all(self, data, skip=None):
        self.sent.append((data, skip))


def setup():
    key = os.urandom(32)
    peers, shown = FakePeers(), []
    return key, peers, shown, Forwarder(key, peers, shown.append)


def wait_for(condition, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_new_message_is_shown_and_forwarded():
    key, peers, shown, fwd = setup()
    msg = make_chat("bob", "1.1.1.1", "hi")
    data = encrypt(key, msg.to_bytes())
    fwd.handle(data, "link1")
    assert shown == [msg]
    assert peers.sent == [(data, "link1")]       # same bytes, skipping where it came from


def test_duplicate_is_dropped():
    key, peers, shown, fwd = setup()
    data = encrypt(key, make_chat("bob", "1.1.1.1", "hi").to_bytes())
    fwd.handle(data, "link1")
    fwd.handle(data, "link2")                    # same message from another peer
    assert len(shown) == 1
    assert len(peers.sent) == 1


def test_wrong_key_is_dropped():
    key, peers, shown, fwd = setup()
    data = encrypt(os.urandom(32), make_chat("eve", "1.1.1.1", "hi").to_bytes())
    fwd.handle(data, "link1")
    assert shown == [] and peers.sent == []


def test_garbage_is_dropped():
    key, peers, shown, fwd = setup()
    fwd.handle(b"garbage", "link1")
    fwd.handle(encrypt(key, b"not a message"), "link1")   # right key, wrong content
    assert shown == [] and peers.sent == []


def test_own_message_coming_back_is_ignored():
    key, peers, shown, fwd = setup()
    msg = make_chat("me", "1.1.1.1", "hello")
    fwd.send(msg)
    assert len(peers.sent) == 1
    fwd.handle(peers.sent[0][0], "link1")        # it travelled around and came back
    assert shown == []
    assert len(peers.sent) == 1


def test_seen_set_forgets_oldest():
    seen = SeenSet(3)
    for i in "abcd":
        assert seen.add(i) is True
    assert seen.add("d") is False                # still remembered
    assert seen.add("a") is True                 # forgotten, so new again


def test_triangle_has_no_loops():
    """a-b, b-c, c-a: a message could circle forever. Each node must get it once."""
    key = os.urandom(32)
    boxes = {n: queue.Queue() for n in "abc"}
    tables, fwds = {}, {}
    for n in "abc":
        tables[n] = PeerTable(lambda data, link, n=n: fwds[n].handle(data, link))
        fwds[n] = Forwarder(key, tables[n], boxes[n].put)
        tables[n].listen(0)
    try:
        tables["a"].connect_to("127.0.0.1", tables["b"].port)
        tables["b"].connect_to("127.0.0.1", tables["c"].port)
        tables["c"].connect_to("127.0.0.1", tables["a"].port)
        assert wait_for(lambda: all(t.count() == 2 for t in tables.values()))
        fwds["a"].send(make_chat("alice", "1.1.1.1", "hi"))
        assert boxes["b"].get(timeout=2).text == "hi"
        assert boxes["c"].get(timeout=2).text == "hi"
        time.sleep(0.3)                          # give any duplicate time to show up
        assert all(box.empty() for box in boxes.values())
    finally:
        for t in tables.values():
            t.close()