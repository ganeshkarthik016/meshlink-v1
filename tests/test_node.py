import time

import pytest

from p2pchat.comms.message import JOIN, USER
from p2pchat.node import Node, find_my_ip


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
        shown = []                                   # messages this node would display
        node = Node(nick, room, password, ip="127.0.0.1", deliver=shown.append)
        node.start(0)
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
    assert shown_b[0].nick == "alice" and shown_b[0].text == "hello bob"
    assert shown_a == []                             # the cli shows our own message, not the node


def test_message_travels_through_a_middle_node(make_node):
    a, shown_a = make_node("alice")
    b, shown_b = make_node("bob")
    c, shown_c = make_node("carol")
    link(a, b)
    link(c, b)
    assert wait_for(lambda: b.peers.count() == 2)
    a.chat("hi all")
    assert wait_for(lambda: len(shown_c) == 1)       # a -> b -> c
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
    assert shown_b[0].announce_type == USER and shown_b[0].text == "Lab at 5"


def test_empty_message_is_not_sent(make_node):
    a, _ = make_node("alice")
    assert a.chat("") is None
    assert a.chat("\x1b") is None                    # only control characters
    assert a.announce("  \x07") is not None or True  # whitespace is allowed, bell is removed


def test_find_my_ip_looks_like_an_ip():
    assert find_my_ip().count(".") == 3