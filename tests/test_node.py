
import time

import pytest

from p2pchat import config
from p2pchat.comms.message import JOIN, USER
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
def make_node():
    nodes = []

    def make(nick, password="password1", room="lab"):
        shown = []
        node = Node(
            nick,
            room,
            password,
            ip="127.0.0.1",
            deliver=shown.append,
        )
        node.start(0, udp_port=TEST_UDP_PORT)
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
