
import time

import pytest

from p2pchat import config
from p2pchat.comms.message import (
    FILE,
    JOIN,
    USER,
    make_announcement,
)
from p2pchat.node import Node, find_my_ip


TEST_UDP_PORT = 50992


def wait_for(condition, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def make_node(tmp_path):
    nodes = []

    def make(nick, password="password1", room="lab"):
        shown = []
        node = Node(
            nick,
            room,
            password,
            ip="127.0.0.1",
            deliver=shown.append,
            shared_dir=str(tmp_path / nick / "shared"),
            download_dir=str(tmp_path / nick / "downloads"),
        )
        node.start(0, udp_port=TEST_UDP_PORT, file_port=0)
        nodes.append(node)
        return node, shown

    yield make

    for node in nodes:
        node.stop()


def link(joiner, host):
    assert joiner.connect("127.0.0.1", host.peers.port)
    assert wait_for(lambda: host.peers.count() >= 1)


def test_chat_reaches_peer(make_node):
    a, shown_a = make_node("alice")
    b, shown_b = make_node("bob")

    link(b, a)
    a.chat("hello bob")

    assert wait_for(lambda: len(shown_b) == 1)
    assert shown_b[0].nick == "alice"
    assert shown_b[0].text == "hello bob"
    assert shown_a == []


def test_message_travels_through_a_middle_node(make_node):
    a, shown_a = make_node("alice")
    b, shown_b = make_node("bob")
    c, shown_c = make_node("carol")

    link(a, b)
    link(c, b)

    assert wait_for(lambda: b.peers.count() == 2)

    a.chat("hi all")

    assert wait_for(lambda: len(shown_c) == 1)
    assert shown_c[0].text == "hi all"
    assert len(shown_b) == 1


def test_wrong_password_sees_nothing(make_node):
    a, _ = make_node("alice")
    c, shown_c = make_node("carol", password="different99")

    link(c, a)
    a.chat("secret")

    time.sleep(0.3)
    assert shown_c == []


def test_join_announcement(make_node):
    a, _ = make_node("alice")
    b, shown_b = make_node("bob")

    link(b, a)
    a.say_hello()

    assert wait_for(lambda: len(shown_b) == 1)
    assert shown_b[0].announce_type == JOIN


def test_user_announcement(make_node):
    a, _ = make_node("alice")
    b, shown_b = make_node("bob")

    link(b, a)
    a.announce("Lab at 5")

    assert wait_for(lambda: len(shown_b) == 1)
    assert shown_b[0].announce_type == USER
    assert shown_b[0].text == "Lab at 5"


def test_empty_message_is_not_sent(make_node):
    a, _ = make_node("alice")

    assert a.chat("") is None
    assert a.chat("\x1b") is None
    assert a.announce("  \x07") is not None


def test_find_my_ip_looks_like_an_ip():
    assert find_my_ip().count(".") == 3


def test_join_finds_peer_and_announces(make_node):
    a, shown_a = make_node("alice")
    b, _ = make_node("bob")

    assert b.join(wait=1) == 1
    assert wait_for(lambda: a.peers.count() == 1)
    assert wait_for(lambda: len(shown_a) == 1)

    assert shown_a[0].announce_type == JOIN
    assert shown_a[0].nick == "bob"


def test_join_with_nobody_around(make_node):
    a, _ = make_node("alice")

    assert a.join(wait=0.3) == 0


def test_join_connects_to_at_most_three(make_node):
    for i in range(5):
        make_node(f"node{i}")

    joiner, _ = make_node("joiner")

    assert joiner.join(wait=1) == config.MAX_OUT


def test_join_ignores_other_rooms(make_node):
    make_node("alice", room="lab1")
    b, _ = make_node("bob", room="lab2")

    assert b.join(wait=0.3) == 0


def test_upload_register_and_download(make_node, tmp_path):
    a, _ = make_node("alice")
    b, _ = make_node("bob")

    link(b, a)

    src = tmp_path / "notes.txt"
    src.write_bytes(b"hello files" * 10000)

    a.upload(str(src))

    assert wait_for(lambda: len(b.register.all()) == 1)

    entry = b.register.get(1)
    assert entry.name == "notes.txt"
    assert entry.nick == "alice"

    assert len(a.register.all()) == 1

    downloaded_path = b.download(1)
    with open(downloaded_path, "rb") as downloaded_file:
        assert downloaded_file.read() == src.read_bytes()


def test_reupload_replaces_the_entry(make_node, tmp_path):
    a, _ = make_node("alice")
    b, _ = make_node("bob")

    link(b, a)

    src = tmp_path / "notes.txt"
    src.write_bytes(b"old content")

    a.upload(str(src))

    assert wait_for(lambda: len(b.register.all()) == 1)

    src.write_bytes(b"new content!!")
    a.upload(str(src))

    assert wait_for(lambda: b.register.get(1).size == 13)
    assert len(b.register.all()) == 1

    downloaded_path = b.download(1)
    with open(downloaded_path, "rb") as downloaded_file:
        assert downloaded_file.read() == b"new content!!"


def test_invalid_file_announcement_is_ignored(make_node):
    a, _ = make_node("alice")
    b, shown_b = make_node("bob")

    link(b, a)

    a.forwarder.send(
        make_announcement(
            FILE,
            "alice",
            "127.0.0.1",
            extra={
                "name": "x",
                "size": 5,
                "port": 1,
                "sha256": "bad",
            },
        )
    )

    time.sleep(0.3)

    assert b.register.all() == []
    assert shown_b == []


def test_upload_and_download_errors(make_node):
    a, _ = make_node("alice")

    with pytest.raises(ValueError):
        a.upload("/no/such/file")

    with pytest.raises(ValueError):
        a.download(7)
