import socket
import threading

from p2pchat import config
from p2pchat.comms.link import Link
import pytest


def make_pair():
    a, b = socket.socketpair()      # two connected sockets, no network needed
    return Link(a, "a"), Link(b, "b")


def test_round_trip():
    a, b = make_pair()
    assert a.send(b"hello")
    assert b.receive() == b"hello"


def test_message_boundaries_are_kept():
    a, b = make_pair()
    a.send(b"one")
    a.send(b"two")
    a.send(b"three")
    assert [b.receive(), b.receive(), b.receive()] == [b"one", b"two", b"three"]


def test_empty_message():
    a, b = make_pair()
    a.send(b"")
    assert b.receive() == b""


def test_large_message():
    a, b = make_pair()
    data = bytes(range(256)) * 50                       # 12,800 bytes
    threading.Thread(target=a.send, args=(data,)).start()
    assert b.receive() == data


def test_message_arriving_in_pieces():
    raw_a, raw_b = socket.socketpair()
    b = Link(raw_b, "b")
    frame = (5).to_bytes(4, "big") + b"hello"
    raw_a.sendall(frame[:3])                            # only part of the length
    threading.Timer(0.1, raw_a.sendall, args=(frame[3:],)).start()
    assert b.receive() == b"hello"


def test_closed_connection_returns_none():
    a, b = make_pair()
    a.close()
    assert b.receive() is None


def test_oversize_length_is_rejected():
    raw_a, raw_b = socket.socketpair()
    b = Link(raw_b, "b")
    raw_a.sendall((10**9).to_bytes(4, "big"))           # claims a 1 GB message
    assert b.receive() is None


def test_send_too_big_returns_false():
    a, b = make_pair()
    assert a.send(b"x" * (config.MAX_FRAME + 1)) is False


def test_send_to_closed_peer_returns_false():
    a, b = make_pair()
    b.close()
    assert a.send(b"hi") is False


def test_concurrent_sends_do_not_mix():
    a, b = make_pair()

    def spam(byte):
        for _ in range(50):
            a.send(byte * 1000)

    threads = [threading.Thread(target=spam, args=(c,)) for c in (b"x", b"y", b"z")]
    for t in threads:
        t.start()
    results = [b.receive() for _ in range(150)]
    for t in threads:
        t.join()
    assert all(len(r) == 1000 and len(set(r)) == 1 for r in results)


def test_connect_fails_returns_none():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()                                           # now nothing listens on this port
    assert Link.connect("127.0.0.1", port) is None


def test_real_tcp_connection():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    a = Link.connect("127.0.0.1", server.getsockname()[1])
    conn, addr = server.accept()
    b = Link(conn, addr[0])
    assert a is not None
    a.send(b"hi")
    assert b.receive() == b"hi"
    b.send(b"yo")
    assert a.receive() == b"yo"
    a.close()
    b.close()
    server.close()


@pytest.mark.skipif(not hasattr(socket, "TCP_KEEPIDLE"), reason="Linux only")
def test_keepalive_is_short():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    a = Link.connect("127.0.0.1", server.getsockname()[1])
    idle = a.sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE)
    assert idle == config.KEEPALIVE_IDLE
    a.close()
    server.close()