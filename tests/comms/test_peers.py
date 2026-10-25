import queue
import time

import pytest

from p2pchat import config
from p2pchat.comms.peers import PeerTable


def wait_for(condition, timeout=2.0):
    """Threads need a moment, so check again and again until true or timeout."""
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def make_table():
    tables = []

    def make(on_data=lambda data, link: None):
        table = PeerTable(on_data)
        tables.append(table)
        return table

    yield make
    for table in tables:               # always clean up, even if the test fails
        table.close()


def test_two_tables_exchange_messages(make_table):
    box_a, box_b = queue.Queue(), queue.Queue()
    a = make_table(lambda data, link: box_a.put(data))
    b = make_table(lambda data, link: box_b.put(data))
    a.listen(0)
    assert b.connect_to("127.0.0.1", a.port)
    assert wait_for(lambda: a.count() == 1)
    b.send_all(b"hi a")
    assert box_a.get(timeout=2) == b"hi a"
    a.send_all(b"hi b")
    assert box_b.get(timeout=2) == b"hi b"


def test_send_all_skips_the_sender(make_table):
    box_a, box_b = queue.Queue(), queue.Queue()
    center = make_table(lambda data, link: center.send_all(data, skip=link))  # forward to others
    a = make_table(lambda data, link: box_a.put(data))
    b = make_table(lambda data, link: box_b.put(data))
    center.listen(0)
    a.connect_to("127.0.0.1", center.port)
    b.connect_to("127.0.0.1", center.port)
    assert wait_for(lambda: center.count() == 2)
    a.send_all(b"from a")
    assert box_b.get(timeout=2) == b"from a"     # b got it through the center
    time.sleep(0.2)
    assert box_a.empty()                         # a did not get its own message back


def test_outgoing_limit(make_table):
    listeners = [make_table() for _ in range(config.MAX_OUT + 1)]
    for t in listeners:
        t.listen(0)
    joiner = make_table()
    results = [joiner.connect_to("127.0.0.1", t.port) for t in listeners]
    assert results == [True] * config.MAX_OUT + [False]


def test_incoming_limit(make_table):
    server = make_table()
    server.listen(0)
    clients = [make_table() for _ in range(config.MAX_IN + 1)]
    for client in clients[:config.MAX_IN]:
        assert client.connect_to("127.0.0.1", server.port)
    assert wait_for(lambda: server.count() == config.MAX_IN)
    assert server.can_accept() is False
    extra = clients[-1]
    extra.connect_to("127.0.0.1", server.port)           # server must close this one
    assert wait_for(lambda: extra.count() == 0)
    assert server.count() == config.MAX_IN


def test_can_accept_before_full(make_table):
    server = make_table()
    server.listen(0)
    assert server.can_accept() is True


def test_dead_peer_is_removed(make_table):
    a = make_table()
    b = make_table()
    a.listen(0)
    b.connect_to("127.0.0.1", a.port)
    assert wait_for(lambda: a.count() == 1)
    b.close()
    assert wait_for(lambda: a.count() == 0)


def test_has_ip(make_table):
    a = make_table()
    b = make_table()
    a.listen(0)
    b.connect_to("127.0.0.1", a.port)
    assert b.has_ip("127.0.0.1")
    assert not b.has_ip("10.0.0.9")
    assert b.ips() == ["127.0.0.1"]


def test_connect_to_nothing_returns_false(make_table):
    t = make_table()
    assert t.connect_to("127.0.0.1", 1) is False